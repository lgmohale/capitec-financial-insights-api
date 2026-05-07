import re
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging import get_logger, request_id_context
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY

logger = get_logger(__name__)
UUID_PATH_SEGMENT_PATTERN = re.compile(
    r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)"
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request_id_context.set(request_id)
        request.state.request_id = request_id
        method = request.method
        route_path = get_normalized_path(request)
        start_time = time.perf_counter()

        logger.info(
            "API request received",
            extra={
                "request_id": request_id,
                "method": method,
                "path": route_path,
                "event_name": "api_request_received",
            },
        )

        try:
            response = await call_next(request)
        except Exception:
            route_path = get_normalized_path(request)
            duration_seconds = time.perf_counter() - start_time
            REQUEST_COUNT.labels(method, route_path, "500").inc()
            REQUEST_LATENCY.labels(method, route_path).observe(duration_seconds)
            logger.exception(
                "Unhandled API request failure",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": route_path,
                    "status_code": 500,
                    "duration_ms": round(duration_seconds * 1000, 2),
                    "event_name": "api_request_failure",
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error.",
                    "request_id": request_id,
                },
            )

        duration_seconds = time.perf_counter() - start_time
        status_code = str(response.status_code)
        route_path = get_normalized_path(request)
        REQUEST_COUNT.labels(method, route_path, status_code).inc()
        REQUEST_LATENCY.labels(method, route_path).observe(duration_seconds)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "API response completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": route_path,
                "status_code": response.status_code,
                "duration_ms": round(duration_seconds * 1000, 2),
                "event_name": "api_response_completed",
            },
        )
        return response


def get_normalized_path(request: Request) -> str:
    route = request.scope.get("route")
    route_template = getattr(route, "path", None)
    if route_template:
        return route_template

    return UUID_PATH_SEGMENT_PATTERN.sub("/{uuid}", request.url.path)
