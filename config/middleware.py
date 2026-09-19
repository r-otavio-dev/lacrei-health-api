"""Cross-cutting request instrumentation."""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

access_logger = logging.getLogger("api.access")
UNSAFE_REQUEST_ID_CHARS = re.compile(r"[^A-Za-z0-9._:-]")


class AccessLogMiddleware:
    """Log request metadata without recording bodies, tokens, or query values."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        started_at = time.monotonic()
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request_id = UNSAFE_REQUEST_ID_CHARS.sub("", supplied_request_id)[:128]
        if not request_id:
            request_id = str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]
        try:
            response = self.get_response(request)
        except Exception:
            access_logger.exception(
                "request_failed request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.path,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                },
            )
            raise

        duration_ms = (time.monotonic() - started_at) * 1000
        response["X-Request-ID"] = request_id
        route = getattr(getattr(request, "resolver_match", None), "route", None)
        access_logger.info(
            "request request_id=%s method=%s route=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            route or request.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "route": route,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response
