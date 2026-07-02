from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routes import admin, health, webhook
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dental Appointment Booking Agent",
        version="0.1.0",
        description="Backend for a VAPI-style dental appointment booking workflow.",
    )
    app.include_router(health.router)
    app.include_router(webhook.router)
    app.include_router(admin.router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": exc.detail}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"message": "Request validation failed", "details": exc.errors()}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled request error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"error": {"message": "Internal server error"}},
        )

    return app


app = create_app()
