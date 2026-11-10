"""FastAPI app: connects to MongoDB on startup, registers error handlers and every module's router.

Run:  uvicorn app.main:app --reload     ->  API docs at http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db import mongo
from app.db.indexes import create_indexes
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.customers.router import router as customers_router
from app.loans.router import router as loans_router
from app.eligibility.router import router as eligibility_router
from app.agents.router import router as agents_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await mongo.connect()
    await create_indexes(mongo.get_database())
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
    register_exception_handlers(app)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
    app.include_router(customers_router, prefix=prefix)
    app.include_router(loans_router, prefix=prefix)
    app.include_router(eligibility_router, prefix=prefix)
    app.include_router(agents_router, prefix=prefix)
    return app


app = create_app()
