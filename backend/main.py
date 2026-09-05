import asyncio
import logging
import os
from dotenv import load_dotenv

# Load .env file before anything else
load_dotenv()
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.auth_routes import router as auth_router
from app.api.v1.coach_routes import router as coach_router
from app.api.v1.experience_routes import router as experience_router
from app.database import engine, Base

# Configure simple logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="The Viva Verse", version="1.0.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Create tables
Base.metadata.create_all(bind=engine)

# CORS — registered first, allow_credentials=False required when allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Global exception handler — ensures CORS headers are ALWAYS present
# even when the backend crashes with an unhandled exception
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    with open("error_log.txt", "w") as f:
        f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        
    logger.error(f"[UNHANDLED ERROR] {type(exc).__name__}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {type(exc).__name__}: {str(exc)}"},
        headers={"Access-Control-Allow-Origin": "*"},
    )

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(coach_router, prefix="/api/v1/coach", tags=["coach"])
app.include_router(experience_router, prefix="/api/v1/interview-experiences", tags=["experiences"])

async def _self_ping():
    # Render free tier shuts down after ~50s of inactivity; ping every 40s to stay alive.
    url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000") + "/health"
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(40)
            try:
                r = await client.get(url, timeout=10)
                logger.info(f"[PING] {url} -> {r.status_code}")
            except Exception as e:
                logger.warning(f"[PING] health check failed: {e}")


def _auto_seed_on_startup() -> bool:
    """Seed mock data when enabled and the experiences table is empty."""
    auto_seed = os.environ.get("AUTO_SEED_ON_STARTUP", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    if not auto_seed:
        logger.info("[INFO] AUTO_SEED_ON_STARTUP disabled — skipping seed check.")
        return False

    from seed_mock_data import run_seed

    seeded = run_seed(force=False)
    if seeded:
        logger.info("[INFO] Startup seed completed.")
    return seeded


@app.on_event("startup")
async def startup_event():
    logger.info("[INFO] Starting The Viva Verse API...")
    try:
        from app.database import init_fts
        init_fts()
        logger.info("[INFO] SQLite FTS5 initialized.")
    except Exception as e:
        logger.error(f"[ERROR] Failed to init FTS5: {e}")

    try:
        seeded = await asyncio.to_thread(_auto_seed_on_startup)
    except Exception as e:
        logger.error(f"[ERROR] Failed to run startup seed: {e}")
        seeded = False

    try:
        from app.services.vector_store import vector_store
        if seeded:
            vector_store.clear()
        vector_store.initialize()
    except Exception as e:
        logger.error(f"[ERROR] Failed to init FAISS Vector Store: {e}")

    asyncio.create_task(_self_ping())
    logger.info("[INFO] Self-ping task started (every 40s).")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
