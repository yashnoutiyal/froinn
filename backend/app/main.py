from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.redis import close_redis


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        summary="Super Admin company provisioning API",
        description=(
            "REST API for Frontech platform administration. Authenticate with `/api/v1/auth/login`, "
            "then use the returned bearer token through **Authorize**. Company provisioning is atomic: "
            "tenant, company, module entitlements, default roles, primary admin, AMC and audit entry are created together."
        ),
        openapi_tags=[
            {"name": "Authentication", "description": "Sign-in and current access context."},
            {
                "name": "Super Admin · Companies",
                "description": "Platform-level company, AMC and entitlement controls. Super Admin only.",
            },
            {"name": "health", "description": "Service probes."},
        ],
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
