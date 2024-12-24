import os
from typing import Callable

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.backend.metrics import e2e_response_latency


class LatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        with e2e_response_latency.labels(
            os.environ["MIDWAY_SEARCH_BACKEND__PROMETHEUS__APP_NAME"], path
        ).time():
            return await call_next(request)
