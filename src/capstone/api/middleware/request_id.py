from __future__ import annotations

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request/response carries an X-Request-ID header.

    - If the client provides X-Request-ID, we reuse it.
    - Otherwise we generate a UUID4.
    """
    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        request.state.request_id = req_id  # optional: available to handlers

        response = await call_next(request)
        response.headers[self.HEADER] = req_id
        return response