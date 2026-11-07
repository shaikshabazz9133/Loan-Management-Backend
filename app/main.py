"""FastAPI application factory. Routers are registered but contain no endpoints yet.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db import mongo
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.customers.router import router as customers_router
from app.loans.router import router as loans_router
from app.eligibility.router import router as eligibility_router
from app.agents.router import router as agents_router
from app.assignments.router import router as assignments_router
from app.reviews.router import router as reviews_router
from app.managers.router import router as managers_router
from app.documents.router import router as documents_router
from app.notifications.router import router as notifications_router
from app.audit.router import router as audit_router
from app.analytics.router import router as analytics_router
from app.support.router import router as support_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await mongo.connect()
    yield
    await mongo.disconnect()


def create_app() -> FastAPI:
    settings = get_settings()
    prefix = settings.api_prefix
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    app.include_router(customers_router, prefix=prefix)
    app.include_router(loans_router, prefix=prefix)
    app.include_router(eligibility_router, prefix=prefix)
    app.include_router(agents_router, prefix=prefix)
    app.include_router(assignments_router, prefix=prefix)
    app.include_router(reviews_router, prefix=prefix)
    app.include_router(managers_router, prefix=prefix)
    app.include_router(documents_router, prefix=prefix)
    app.include_router(notifications_router, prefix=prefix)
    app.include_router(audit_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(support_router, prefix=prefix)
    return app


app = create_app()
