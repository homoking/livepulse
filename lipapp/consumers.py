from channels.generic.websocket import AsyncJsonWebsocketConsumer

class RoomConsumer(AsyncJsonWebsocketConsumer):
    """
    کلاینت‌ها به ws/room/<slug>/ وصل می‌شن.
    ما همه‌ی پیام‌ها رو به صورت واحد با type="dispatch" هندل می‌کنیم
    و یک فیلد event داریم که روی کلاینت سوییچ می‌شه.
    """
    async def connect(self):
        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        self.group_name = f"room_{self.slug}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"event": "hello", "room": self.slug})

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # تمام پیام‌های سرور به این متد می‌آیند
    async def dispatch(self, event):
        # event = {"type": "dispatch", "event": "...", "payload": {...}}
        await self.send_json({"event": event.get("event"), **(event.get("payload") or {})})
