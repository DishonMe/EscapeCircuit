"""
Database contention monitoring middleware.

Measures wall-clock time for every request and logs warnings when latency
suggests SQLite write-lock contention (BEGIN IMMEDIATE queueing).

Thresholds
----------
  > 1.0 s  →  INFO   (elevated latency — worth watching)
  > 3.0 s  →  WARNING (likely DB write-lock contention)

The processing time is also injected into the ``X-Process-Time`` response
header so front-end tooling can surface slow endpoints without scraping logs.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from Backend import settings

logger = logging.getLogger("escapecircuit.contention")


class ContentionMonitorMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that times every request and flags DB contention."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed = time.perf_counter() - start

        method = request.method
        path = request.url.path

        # Inject header unconditionally (cheap, always useful)
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"

        if elapsed > settings.CONTENTION_WARN_THRESHOLD_S:
            logger.warning(
                "HIGH LATENCY (%.2fs) %s %s — possible DB write-lock contention",
                elapsed,
                method,
                path,
            )
        elif elapsed > settings.CONTENTION_INFO_THRESHOLD_S:
            logger.info(
                "Elevated latency (%.2fs) %s %s",
                elapsed,
                method,
                path,
            )

        return response
