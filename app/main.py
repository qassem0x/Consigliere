import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api import files, auth, chats, messages, connections, model
from app.core.config import get_env
from app.core.rate_limit import limiter
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

cors_origins = get_env("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        cors_origins.split(",")
        if cors_origins
        else ["http://localhost:5173", "http://localhost:3000"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(files.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(connections.router)
app.include_router(model.router)


from app.core.errors import RecoverableError, ErrorCode


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if isinstance(exc, RecoverableError):
        return JSONResponse(
            status_code=429 if exc.code == ErrorCode.RATE_LIMIT else 500,
            content={
                "code": exc.code.value,
                "message": exc.user_message,
                "retry_after": exc.retry_after,
            },
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "code": ErrorCode.INTERNAL_ERROR.value,
            "message": "An unexpected error occurred. Please try again.",
        },
    )


@app.get("/")
def check_health():
    return {"status": "alive", "system": "Consigliere"}


@app.get("/db-health")
def test_db_connection():
    from app.core.config import DATABASE_URL

    try:
        engine = create_engine(DATABASE_URL)

        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]

        return {"status": "connected", "database_version": version}

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "details": str(e)}
