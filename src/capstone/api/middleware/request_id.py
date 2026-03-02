import uuid

class RequestIdMiddleware:
    def __init__(self, app, header_name: str = "X-Request-ID"):
        self.app = app
        self.header_name = header_name
        self.header_name_bytes = header_name.lower().encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(self.header_name_bytes)
        request_id = incoming.decode() if incoming else str(uuid.uuid4())

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"].append((self.header_name_bytes, request_id.encode()))
            await send(message)

        await self.app(scope, receive, send_wrapper)