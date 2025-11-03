from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import secrets

class Room(models.Model):
    ACCESS_PUBLIC = "public"
    ACCESS_PRIVATE = "private"
    ACCESS_CHOICES = [
        (ACCESS_PUBLIC, "Public"),
        (ACCESS_PRIVATE, "Private"),
    ]

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    is_live = models.BooleanField(default=True)

    access_mode = models.CharField(max_length=10, choices=ACCESS_CHOICES, default=ACCESS_PUBLIC)
    access_code = models.CharField(max_length=32, blank=True, null=True)

    host_secret = models.CharField(max_length=64, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "room"
            # برای جلوگیری از تکرار
            self.slug = f"{base}-{secrets.token_hex(3)}"
        if not self.host_secret:
            self.host_secret = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("room_view", kwargs={"slug": self.slug})


class Question(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_ANSWERED = "answered"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_ANSWERED, "Answered"),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="questions")
    author_name = models.CharField(max_length=60, blank=True, null=True)
    body = models.TextField(max_length=1000)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    pinned_at = models.DateTimeField(blank=True, null=True)

    score_cached = models.IntegerField(default=0)  # مجموع رأی‌ها (کش برای سورت)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["room", "-score_cached", "created_at"]),
        ]
        ordering = ["-score_cached", "created_at"]

    def __str__(self):
        return f"Q#{self.pk} in {self.room.slug} ({self.status})"

    @property
    def is_pinned(self):
        return self.pinned_at is not None

    # کمک‌کننده‌های مدیریتی
    def approve(self):
        self.status = self.STATUS_APPROVED
        self.save(update_fields=["status", "updated_at"])

    def reject(self):
        self.status = self.STATUS_REJECTED
        self.save(update_fields=["status", "updated_at"])

    def mark_answered(self):
        self.status = self.STATUS_ANSWERED
        self.save(update_fields=["status", "updated_at"])

    def pin(self):
        self.pinned_at = timezone.now()
        self.save(update_fields=["pinned_at", "updated_at"])

    def unpin(self):
        self.pinned_at = None
        self.save(update_fields=["pinned_at", "updated_at"])


class Vote(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="votes")
    voter_key = models.CharField(max_length=64)  # hash(session/ip/ua)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("question", "voter_key")]
        indexes = [
            models.Index(fields=["question", "voter_key"]),
        ]

    def __str__(self):
        return f"Vote q={self.question_id} by {self.voter_key[:8]}…"


class Poll(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="polls")
    question = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    ends_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Poll#{self.pk} in {self.room.slug}"

    @property
    def total_votes_cached(self):
        return sum(o.votes_cached for o in self.options.all())


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=120)
    votes_cached = models.IntegerField(default=0)

    def __str__(self):
        return f"Option#{self.pk} of Poll#{self.poll_id}: {self.label}"
