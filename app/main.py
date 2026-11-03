
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

VERSION = os.getenv("SHOPSPHERE_VERSION", "0.1.0")
SERVICE_NAME = "shopsphere-api"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(SERVICE_NAME)

REQUESTS = Counter(
    "shopsphere_api_http_requests_total",
    "Total HTTP requests handled by ShopSphere",
    ["method", "route", "status"],
)
IN_PROGRESS = Gauge(
    "shopsphere_api_http_requests_in_progress",
    "HTTP requests currently being handled by ShopSphere",
)
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("event=application_start version=%s", VERSION)
    yield
    logger.info("event=application_stop version=%s", VERSION)


app = FastAPI(
    title="ShopSphere API",
    version=VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    IN_PROGRESS.inc()
    started = time.perf_counter()
    status = 500

    try:
        response = await call_next(request)
        status = response.status_code
        return response
    except Exception:
        logger.exception(
            "event=request_failed method=%s path=%s",
            request.method,
            request.url.path,
        )
        raise
    finally:
        IN_PROGRESS.dec()
        route = request.scope.get("route")
        route_name = getattr(route, "path", request.url.path)
        REQUESTS.labels(
            method=request.method,
            route=route_name,
            status=str(status),
        ).inc()
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "event=http_request method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            status,
            elapsed_ms,
        )


@app.get("/")
def home():
    return {
        "service": SERVICE_NAME,
        "message": "Welcome to ShopSphere",
        "version": VERSION,
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": SERVICE_NAME, "version": VERSION}


@app.get("/ready")
def ready():
    # Database readiness will be added when the DB connection is integrated.
    return {"status": "ready", "service": SERVICE_NAME}


@app.get("/version")
def version():
    return {"service": SERVICE_NAME, "version": VERSION}


@app.get("/simulate-error")
def simulate_error():
    logger.warning("event=simulated_error_requested")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Intentional test error"},
    )


@app.get("/metrics")
def metrics():
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
