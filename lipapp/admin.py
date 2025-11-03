from django.contrib import admin
try:
    from unfold.admin import ModelAdmin  # اگر نصب شد، همینه
except Exception:
    from django.contrib.admin import ModelAdmin  # fallback

from .models import Room, Question, Vote, Poll, PollOption
from django.utils.html import format_html
from django.utils.timezone import localtime

@admin.register(Room)
class RoomAdmin(ModelAdmin):
    list_display = ("title", "slug", "is_live", "access_mode", "created_at_local", "host_secret_short")
    list_filter = ("is_live", "access_mode", "created_at")
    search_fields = ("title", "slug")
    readonly_fields = ("host_secret", "created_at")
    ordering = ("-created_at",)

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime("%Y-%m-%d %H:%M")
    created_at_local.short_description = "Created"

    def host_secret_short(self, obj):
        return f"{obj.host_secret[:6]}…"
    host_secret_short.short_description = "Host Secret"

@admin.action(description="Approve selected questions")
def action_approve(modeladmin, request, queryset):
    for q in queryset:
        q.approve()

@admin.action(description="Reject selected questions")
def action_reject(modeladmin, request, queryset):
    for q in queryset:
        q.reject()

@admin.action(description="Mark selected as answered")
def action_answered(modeladmin, request, queryset):
    for q in queryset:
        q.mark_answered()

@admin.action(description="Pin selected questions")
def action_pin(modeladmin, request, queryset):
    for q in queryset:
        q.pin()

@admin.action(description="Unpin selected questions")
def action_unpin(modeladmin, request, queryset):
    for q in queryset:
        q.unpin()

@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    list_display = ("short_body", "room", "status_badge", "score_cached", "is_pinned", "created_at_local")
    list_filter = ("status", "room", "created_at")
    search_fields = ("body", "author_name", "room__slug")
    ordering = ("-score_cached", "created_at")
    actions = [action_approve, action_reject, action_answered, action_pin, action_unpin]

    def short_body(self, obj):
        text = obj.body
        return (text[:70] + "…") if len(text) > 70 else text
    short_body.short_description = "Question"

    def status_badge(self, obj):
        color = {
            "pending": "#f59e0b",   # amber
            "approved": "#10b981",  # emerald
            "rejected": "#ef4444",  # red
            "answered": "#3b82f6",  # blue
        }.get(obj.status, "#6b7280")
        return format_html('<span style="padding:2px 8px;border-radius:9999px;background:{};color:white;font-size:12px;">{}</span>',
                           color, obj.status)
    status_badge.short_description = "Status"

    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime("%Y-%m-%d %H:%M")
    created_at_local.short_description = "Created"

@admin.register(Vote)
class VoteAdmin(ModelAdmin):
    list_display = ("question", "voter_key_short", "created_at")
    list_filter = ("created_at",)
    search_fields = ("voter_key", "question__id", "question__room__slug")

    def voter_key_short(self, obj):
        return f"{obj.voter_key[:10]}…"
    voter_key_short.short_description = "Voter"

class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 1

@admin.register(Poll)
class PollAdmin(ModelAdmin):
    list_display = ("question", "room", "is_active", "total_votes_display", "created_at")
    list_filter = ("is_active", "room", "created_at")
    search_fields = ("question", "room__slug")
    inlines = [PollOptionInline]

    def total_votes_display(self, obj):
        return obj.total_votes_cached
    total_votes_display.short_description = "Total votes"

@admin.register(PollOption)
class PollOptionAdmin(ModelAdmin):
    list_display = ("label", "poll", "votes_cached")
    list_filter = ("poll",)
    search_fields = ("label", "poll__question")
