from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


class RequestBodyLimitMiddleware:
    def __init__(self, app: Any, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self, scope: dict[str, Any], receive: ASGIReceive, send: ASGISend
    ) -> None:
        if scope.get("type") != "http" or not str(scope.get("path", "")).startswith(
            "/api/"
        ):
            await self.app(scope, receive, send)
            return

        content_length = None
        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    content_length = int(value.decode("latin-1"))
                except ValueError:
                    content_length = None
                break

        if content_length is not None and content_length > self.max_bytes:
            await self._too_large(send)
            return

        buffered: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                # Preserve disconnect and extension messages for the app.
                async def replay_message() -> dict[str, Any]:
                    return message

                await self.app(scope, replay_message, send)
                return
            chunk = message.get("body", b"") or b""
            total += len(chunk)
            if total > self.max_bytes:
                await self._too_large(send)
                return
            buffered.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(buffered)
        body_sent = False

        async def replay_body() -> dict[str, Any]:
            nonlocal body_sent
            if body_sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            body_sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_body, send)

    @staticmethod
    async def _too_large(send: ASGISend) -> None:
        body = json.dumps(
            {
                "error": {
                    "code": "request_too_large",
                    "message": "Request body exceeds the configured limit.",
                }
            }
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


