# lipapp/views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.db.models import F
from django.template.loader import render_to_string

from .models import Room, Question, Vote, Poll, PollOption
from .realtime import broadcast_room

# Rate-limit & fingerprint helpers
from .services.ratelimit import allow, Limit, fingerprint, set_rate_headers, r as redis_conn


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

HOST_SESSION_KEY = "host:{slug}"

def _is_host(request, room: Room) -> bool:
    """
    نقش میزبان را با ?host=<host_secret> یک‌بار در سشن ست می‌کنیم
    و سپس در ادامه‌ی درخواست‌ها از سشن چک می‌شود.
    """
    key = HOST_SESSION_KEY.format(slug=room.slug)
    if request.session.get(key):
        return True
    token = request.GET.get("host")
    if token and token == room.host_secret:
        request.session[key] = True
        request.session.save()
        return True
    return False

def voter_key(request) -> str:
    """برای Vote از همان fingerprint استفاده می‌کنیم."""
    return fingerprint(request)


# -------------------------------------------------------------------
# Public Views
# -------------------------------------------------------------------

def room_create(request):
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        access_mode = request.POST.get("access_mode") or Room.ACCESS_PUBLIC
        if not title:
            return render(request, "room/create.html", {"error": "Title is required"})
        room = Room(title=title, access_mode=access_mode)
        room.save()
        # هدایت میزبان با توکن به پنل
        host_url = reverse("host_view", kwargs={"slug": room.slug})
        return redirect(f"{host_url}?host={room.host_secret}")
    return render(request, "room/create.html")


def room_view(request, slug):
    """
    صفحه‌ی بیننده: سوال‌ها + Poll فعال.
    درصد Poll در این ویو محاسبه می‌شود تا داخل قالب CSS inline/templating نداشته باشیم.
    """
    room = get_object_or_404(Room, slug=slug, is_live=True)
    questions = (
        room.questions.filter(status__in=[Question.STATUS_APPROVED, Question.STATUS_ANSWERED])
        .order_by(F("pinned_at").desc(nulls_last=True), "-score_cached", "created_at")
    )

    active_poll = room.polls.filter(is_active=True).order_by("-created_at").first()
    poll_options_ctx = []
    if active_poll:
        opts = list(active_poll.options.all())
        total = sum(o.votes_cached for o in opts) or 0
        for o in opts:
            pct = int(round((o.votes_cached / total) * 100)) if total else 0
            poll_options_ctx.append({
                "id": o.id,
                "label": o.label,
                "votes": o.votes_cached,
                "pct": pct,  # 0..100
            })

    return render(
        request,
        "room/view.html",
        {
            "room": room,
            "questions": questions,
            "active_poll": active_poll,
            "poll_options": poll_options_ctx,
        },
    )


# -------------------------------------------------------------------
# Host Views & Actions
# -------------------------------------------------------------------

def host_view(request, slug):
    room = get_object_or_404(Room, slug=slug)
    if not _is_host(request, room):
        return HttpResponseForbidden("Invalid host token")

    pending = room.questions.filter(status=Question.STATUS_PENDING).order_by("created_at")
    approved = (
        room.questions.exclude(status=Question.STATUS_PENDING)
        .order_by(F("pinned_at").desc(nulls_last=True), "-score_cached", "created_at")
    )

    viewer_url = request.build_absolute_uri(reverse("room_view", kwargs={"slug": room.slug}))
    host_url = request.build_absolute_uri(reverse("host_view", kwargs={"slug": room.slug})) + f"?host={room.host_secret}"
    polls = room.polls.order_by("-created_at")

    return render(
        request,
        "room/host.html",
        {
            "room": room,
            "pending": pending,
            "approved": approved,
            "viewer_url": viewer_url,
            "host_url": host_url,
            "polls": polls,
        },
    )


@require_POST
def question_create(request, slug):
    """
    ایجاد سوال (بیننده یا میزبان). با Rate-limit:
      - 1 درخواست در هر 15 ثانیه برای هر کاربر در هر اتاق
    """
    room = get_object_or_404(Room, slug=slug, is_live=True)

    # Rate limit
    fp = fingerprint(request)
    key = f"q:create:{slug}:{fp}"
    lim = Limit(limit=1, window=15)
    ok, remaining, reset = allow(key, lim)
    if not ok:
        resp = HttpResponseBadRequest("Rate limit exceeded")
        return set_rate_headers(resp, remaining, reset, lim)

    body = (request.POST.get("body") or "").strip()
    author = (request.POST.get("author_name") or "").strip() or None
    if not body:
        return HttpResponseBadRequest("Empty question")

    Question.objects.create(room=room, author_name=author, body=body)  # status = pending

    # Host side: htmx با hx-select فقط #host-lists را از پاسخ host_view برمی‌دارد
    if request.headers.get("HX-Target") == "host-lists":
        return host_view(request, slug)

    # Viewer side: htmx با hx-select فقط فرم را جایگزین می‌کند
    return room_view(request, slug)


@require_POST
def question_vote(request, slug, pk):
    """
    رأی دادن به سوال. با Rate-limit:
      - 5 رأی در هر 10 ثانیه برای هر کاربر در هر اتاق
    و قفل 1ثانیه‌ای روی هر سوال/کاربر برای جلوگیری از دابل‌کلیک خیلی سریع.
    """
    room = get_object_or_404(Room, slug=slug, is_live=True)
    q = get_object_or_404(
        Question, pk=pk, room=room, status__in=[Question.STATUS_APPROVED, Question.STATUS_ANSWERED]
    )

    # Rate limit
    fp = fingerprint(request)
    key = f"q:vote:{slug}:{fp}"
    lim = Limit(limit=5, window=10)
    ok, remaining, reset = allow(key, lim)
    if not ok:
        resp = HttpResponseBadRequest("Rate limit exceeded")
        return set_rate_headers(resp, remaining, reset, lim)

    # Short lock (1s) per question/user
    lock_key = f"lock:vote:{slug}:{pk}:{fp}"
    if redis_conn().set(lock_key, "1", nx=True, ex=1) is None:
        return HttpResponseBadRequest("Slow down")

    # Unique vote per user/question
    vkey = voter_key(request)
    obj, created = Vote.objects.get_or_create(question=q, voter_key=vkey)
    if created:
        Question.objects.filter(pk=q.pk).update(score_cached=F("score_cached") + 1)
        q.refresh_from_db(fields=["score_cached"])

    # Broadcast updated card to all viewers
    card_html = render_to_string("room/_question_card.html", {"q": q, "room": room})
    broadcast_room(room.slug, "vote.tally", {"id": q.id, "html": card_html})

    # Return the updated card for htmx target
    return render(request, "room/_question_card.html", {"q": q, "room": room})


@require_POST
def host_approve(request, slug, pk):
    room = get_object_or_404(Room, slug=slug)
    if not _is_host(request, room):
        return HttpResponseForbidden("Invalid host token")
    q = get_object_or_404(Question, pk=pk, room=room)
    q.approve()

    # Broadcast new question card for viewers
    card_html = render_to_string("room/_question_card.html", {"q": q, "room": room})
    broadcast_room(room.slug, "question.new", {"id": q.id, "html": card_html})

    # Refresh host lists (htmx will hx-select #host-lists)
    return host_view(request, slug)


@require_POST
def host_reject(request, slug, pk):
    room = get_object_or_404(Room, slug=slug)
    if not _is_host(request, room):
        return HttpResponseForbidden("Invalid host token")
    q = get_object_or_404(Question, pk=pk, room=room)
    q.reject()
    return host_view(request, slug)


@require_POST
def host_answer(request, slug, pk):
    room = get_object_or_404(Room, slug=slug)
    if not _is_host(request, room):
        return HttpResponseForbidden("Invalid host token")
    q = get_object_or_404(Question, pk=pk, room=room)
    q.mark_answered()

    card_html = render_to_string("room/_question_card.html", {"q": q, "room": room})
    broadcast_room(room.slug, "question.update", {"id": q.id, "html": card_html})
    return host_view(request, slug)


@require_POST
def host_pin(request, slug, pk):
    room = get_object_or_404(Room, slug=slug)
    if not _is_host(request, room):
        return HttpResponseForbidden("Invalid host token")
    q = get_object_or_404(Question, pk=pk, room=room)
    q.pin()

    card_html = render_to_string("room/_question_card.html", {"q": q, "room": room})
    broadcast_room(room.slug, "question.update", {"id": q.id, "html": card_html})
    return host_view(request, slug)


@require_POST
def host_unpin(request, slug, pk):
    room = get_object_or_404(Room, slug=slug)
    if not _is_host(request, room):
        return HttpResponseForbidden("Invalid host token")
    q = get_object_or_404(Question, pk=pk, room=room)
    q.unpin()

    card_html = render_to_string("room/_question_card.html", {"q": q, "room": room})
    broadcast_room(room.slug, "question.update", {"id": q.id, "html": card_html})
    return host_view(request, slug)


# -------------------------------------------------------------------
# Polls (no partials; viewer refreshes poll-block from full page)
# -------------------------------------------------------------------

@require_POST
def poll_create(request, slug):
    room = get_object_or_404(Room, slug=slug)
    if not _is_host(request, room):
        return HttpResponseForbidden("Invalid host token")

    question = (request.POST.get("question") or "").strip()
    options_raw = (request.POST.get("options") or "").strip()
    if not question or not options_raw:
        return HttpResponseBadRequest("Question and options are required")

    opts = [o.strip() for o in options_raw.split("\n") if o.strip()]
    if len(opts) < 2:
        return HttpResponseBadRequest("At least two options required")

    # Only one active poll at a time
    room.polls.filter(is_active=True).update(is_active=False)
    poll = Poll.objects.create(room=room, question=question, is_active=True)
    PollOption.objects.bulk_create([PollOption(poll=poll, label=o) for o in opts])

    # Viewers fetch poll-block (signal only)
    broadcast_room(room.slug, "poll.update", {"reason": "created"})
    return host_view(request, slug)


@require_POST
def poll_toggle(request, slug, pk):
    room = get_object_or_404(Room, slug=slug)
    if not _is_host(request, room):
        return HttpResponseForbidden("Invalid host token")

    poll = get_object_or_404(Poll, pk=pk, room=room)
    if poll.is_active:
        poll.is_active = False
        poll.save(update_fields=["is_active"])
    else:
        room.polls.filter(is_active=True).update(is_active=False)
        poll.is_active = True
        poll.save(update_fields=["is_active"])

    broadcast_room(room.slug, "poll.update", {"reason": "toggled"})
    return host_view(request, slug)


@require_POST
def poll_vote(request, slug, pk, option_id):
    """
    رأی به Poll. Rate-limit سبک مثل رأی سوال‌ها:
      - 5 رأی / 10 ثانیه برای هر کاربر در هر اتاق
    """
    room = get_object_or_404(Room, slug=slug, is_live=True)
    poll = get_object_or_404(Poll, pk=pk, room=room, is_active=True)
    try:
        option = poll.options.get(pk=option_id)
    except PollOption.DoesNotExist:
        return HttpResponseBadRequest("Invalid option")

    fp = fingerprint(request)
    key = f"poll:vote:{slug}:{fp}"
    lim = Limit(limit=5, window=10)
    ok, remaining, reset = allow(key, lim)
    if not ok:
        resp = HttpResponseBadRequest("Rate limit exceeded")
        return set_rate_headers(resp, remaining, reset, lim)

    # افزایش شمارش رأی گزینه (کش DB)
    PollOption.objects.filter(pk=option.pk).update(votes_cached=F("votes_cached") + 1)

    # اطلاع به بیننده‌ها برای تازه‌سازی poll-block
    broadcast_room(room.slug, "poll.update", {"reason": "vote"})
    # بازگرداندن کل صفحه‌ی viewer؛ htmx با hx-select فقط #poll-block را جایگزین می‌کند
    return room_view(request, slug)

def home(request):
    return render(request, "home.html")

@require_POST
def join_room(request):
    slug = (request.POST.get("slug") or "").strip()
    if not slug:
        return redirect("home")
    return redirect("room_view", slug=slug)


from django.http import JsonResponse
from django.conf import settings

def healthz(request):
    return JsonResponse({"ok": True})

def version(request):
    return JsonResponse({
        "name": "LivePulse",
        "debug": settings.DEBUG,
        "redis": bool(getattr(settings, "CHANNEL_LAYERS", None)),
    })
