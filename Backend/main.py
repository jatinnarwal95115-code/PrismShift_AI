import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from Backend.config import BASE_DIR, CORS_ORIGIN_REGEX
from Backend.services.database import init_db
from Backend.services.gemma_service import warm_up_model
from Backend.services.auth_service import delete_expired_sessions
from Backend.Routes import auth, reality, digital, history


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    delete_expired_sessions()
    threading.Thread(target=warm_up_model, daemon=True).start()
    yield


app = FastAPI(title="PrismShift AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, reality, digital, history):
    app.include_router(module.router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}


# Serve the Frontend folder from the same server (http://127.0.0.1:8000/).
# This avoids Live Server's auto-reload, which refreshes the page whenever the
# backend writes an upload / database / report file and wipes the result.
FRONTEND_DIR = BASE_DIR.parent / "Frontend"

if FRONTEND_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend"
    )
