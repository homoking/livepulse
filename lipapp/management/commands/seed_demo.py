# lipapp/management/commands/seed_demo.py
from django.core.management.base import BaseCommand
from lipapp.models import Room, Question, Poll, PollOption
import random

DEMO_TITLE = "LivePulse Demo"

class Command(BaseCommand):
    help = "Create a demo room with sample questions and a poll."

    def handle(self, *args, **kwargs):
        room, created = Room.objects.get_or_create(title=DEMO_TITLE)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created room: {room.slug}"))
        else:
            self.stdout.write(self.style.WARNING(f"Using existing room: {room.slug}"))

        # Questions
        samples = [
            "What’s the roadmap for Q4?",
            "Can you share the recording later?",
            "Will this support mobile SDKs?",
            "How does rate limiting work here?",
            "Is the poll data exportable?",
        ]
        for s in samples:
            q, _ = room.questions.get_or_create(body=s, defaults={"status": "approved"})
            q.score_cached = random.randint(0, 12)
            q.save(update_fields=["score_cached"])

        # Poll
        poll, _ = Poll.objects.get_or_create(room=room, question="Which feature should we build next?", defaults={"is_active": True})
        if not poll.options.exists():
            for o in ["Better moderation", "Emoji reactions", "Embed widget", "Analytics"]:
                PollOption.objects.create(poll=poll, label=o, votes_cached=random.randint(0, 20))

        self.stdout.write(self.style.SUCCESS(f"Demo is ready.\nViewer: /r/{room.slug}/\nHost:   /host/{room.slug}/?host={room.host_secret}"))
