from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.middleware.error_handler import ErrorHandlerMiddleware
from src.api.v1.middleware.logging_middleware import LoggingMiddleware
from src.api.v1.router import v1_router
from src.config import settings
from src.utils.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.debug)
    logger = get_logger("startup")
    logger.info("Starting AI Content Production System", version="0.1.0")

    from src.skills.registry import SkillRegistry

    registry = SkillRegistry()
    registry.discover(settings.skills_public_dir, settings.skills_user_dir)
    app.state.skills_registry = registry
    logger.info("Skills registry initialized", skill_count=len(registry.list_all()))

    yield

    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Content Production System",
        description="Skill-driven intelligent content production",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware is applied in reverse order -- outermost first.
    # 1. CORS (outermost -- handles preflight before anything else)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # 2. Error handler (catches exceptions from inner layers)
    app.add_middleware(ErrorHandlerMiddleware)
    # 3. Request/response logger (innermost -- logs timing around handler)
    app.add_middleware(LoggingMiddleware)

    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
