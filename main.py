import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.apify_scrape import router as apify_scrape_router
from src.api.routes.bylines import router as bylines_router
from src.api.routes.byline_pipeline import router as byline_pipeline_router
from src.api.routes.health import router as health_router
from src.api.routes.sources import router as sources_router
from src.api.routes.users import router as users_router
from src.core.config import settings
from src.db.mongo import close_mongo_connection, connect_to_mongo, ensure_indexes, ping_database
from src.jobs.scheduler import shutdown_scheduler, start_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Connecting to MongoDB for database '%s'.", settings.db_name)

    try:
        connect_to_mongo()
        ping_database()
        ensure_indexes()
        logger.info("MongoDB startup connection established for '%s'.", settings.db_name)
        try:
            start_scheduler()
        except Exception:
            logger.exception("Failed to start APScheduler; continuing without cron jobs.")
        yield
    except Exception:
        logger.exception("MongoDB startup connection failed for '%s'.", settings.db_name)
        raise
    finally:
        shutdown_scheduler()
        close_mongo_connection()
        logger.info("MongoDB connection closed.")


app = FastAPI(title="LinkedIn Scrapper Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(users_router)
app.include_router(sources_router)
app.include_router(bylines_router)
app.include_router(apify_scrape_router)
app.include_router(byline_pipeline_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
