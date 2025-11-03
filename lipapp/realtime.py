from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_room(slug: str, event: str, payload: dict):
    """
    ارسال یک پیام به همه‌ی کلاینت‌های اتاق.
    event مثل "question.new" یا "vote.tally"
    payload هر چیزی می‌تونه باشه (معمولاً {html: "", id: ...})
    """
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)(
        f"room_{slug}",
        {"type": "dispatch", "event": event, "payload": payload or {}},
    )
