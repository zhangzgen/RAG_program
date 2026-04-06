from fastapi import FastAPI

from .auth import router as auth_router
from .assessment import router as assessment_router
from .cases import router as cases_router
from .config import router as config_router
from .faq import router as faq_router
from .knowledge import router as knowledge_router
from .query import router as query_router
from .sessions import router as sessions_router


def register_routers(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(query_router)
    app.include_router(sessions_router)
    app.include_router(cases_router)
    app.include_router(knowledge_router)
    app.include_router(config_router)
    app.include_router(faq_router)
    app.include_router(assessment_router)
