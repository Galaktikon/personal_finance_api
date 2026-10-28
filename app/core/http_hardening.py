import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BodyTooLarge(BaseException):
    """The request body exceeded the configured byte limit."""


class SafeRequestMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = get_settings().request_max_bytes
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError:
                declared_length = 0
            if declared_length > limit:
                await self._error(scope, receive, send, 413, "Request body exceeds size limit")
                return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise BodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except BodyTooLarge:
            if response_started:
                raise
            await self._error(scope, receive, send, 413, "Request body exceeds size limit")
        except Exception:
            logger.error("request_failed")
            if response_started:
                raise
            await self._error(scope, receive, send, 500, "Operation could not be completed")

    @staticmethod
    async def _error(
        scope: Scope, receive: Receive, send: Send, status_code: int, detail: str
    ) -> None:
        await JSONResponse({"detail": detail}, status_code=status_code)(scope, receive, send)
