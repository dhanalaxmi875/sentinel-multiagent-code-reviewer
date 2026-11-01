from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


class RequestBodyLimitMiddleware:
    def __init__(self, app: Any, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict[str, Any], receive: ASGIReceive, send: ASGISend) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/"):
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length:
            try:
                too_large = int(raw_length) > self.max_bytes
            except ValueError:
                too_large = False
            if too_large:
                await self._too_large(send)
                return

        buffered: list[dict[str, Any]] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                buffered.append(message)
                continue
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                await self._too_large(send)
                return
            buffered.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive() -> dict[str, Any]:
            if buffered:
                return buffered.pop(0)
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _too_large(send: ASGISend) -> None:
        body = json.dumps(
            {
                "error": {
                    "code": "request_too_large",
                    "message": "Request body exceeds the configured size limit.",
                }
            }
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
