import logging
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
        from app.services.vector_store import vector_store
        vector_store.initialize()
    except Exception as e:
        logger.error(f"[ERROR] Failed to init FAISS Vector Store: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
