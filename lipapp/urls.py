from django.urls import path
from . import views

urlpatterns = [
    # Home helpers
    path("join/", views.join_room, name="join_room"),

    # Rooms
    path("rooms/new/", views.room_create, name="room_create"),
    path("r/<slug:slug>/", views.room_view, name="room_view"),
    path("host/<slug:slug>/", views.host_view, name="host_view"),

    # Questions (HTMX)
    path("r/<slug:slug>/questions/create/", views.question_create, name="question_create"),
    path("r/<slug:slug>/questions/<int:pk>/vote/", views.question_vote, name="question_vote"),

    # Host actions
    path("host/<slug:slug>/questions/<int:pk>/approve/", views.host_approve, name="host_approve"),
    path("host/<slug:slug>/questions/<int:pk>/reject/", views.host_reject, name="host_reject"),
    path("host/<slug:slug>/questions/<int:pk>/answer/", views.host_answer, name="host_answer"),
    path("host/<slug:slug>/questions/<int:pk>/pin/", views.host_pin, name="host_pin"),
    path("host/<slug:slug>/questions/<int:pk>/unpin/", views.host_unpin, name="host_unpin"),

    # Polls
    path("host/<slug:slug>/polls/create/", views.poll_create, name="poll_create"),
    path("host/<slug:slug>/polls/<int:pk>/toggle/", views.poll_toggle, name="poll_toggle"),
    path("r/<slug:slug>/polls/<int:pk>/vote/<int:option_id>/", views.poll_vote, name="poll_vote"),
]
