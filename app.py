from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Backend.services.database import init_db

from Backend.Routes.auth import router as auth_router
from Backend.Routes.history import router as history_router
from Backend.Routes.reality import router as reality_router
from Backend.Routes.digital import router as digital_router


# ==========================================
# APPLICATION LIFECYCLE
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Initialize SQLite database on startup
    print("Starting PrismShift AI...")

    init_db()

    print("Database initialized successfully.")
    print("PrismShift AI backend is ready.")

    yield

    # Shutdown
    print("PrismShift AI backend shutting down.")


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="PrismShift AI",
    description="""
    One image. Two worlds. Infinite possibilities.

    PrismShift AI is a locally running multimodal AI application
    powered by Gemma 4 through Ollama.

    Reality Mode:
    Analyze real-world photographs and generate formal documents.

    Digital Mode:
    Analyze digital design references and generate reusable
    AI design prompts.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ==========================================
# CORS CONFIGURATION
# ==========================================

ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5501",
    "http://localhost:5501"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==========================================
# REGISTER API ROUTES
# ==========================================

app.include_router(
    auth_router
)

app.include_router(
    history_router
)

app.include_router(
    reality_router
)

app.include_router(
    digital_router
)


# ==========================================
# ROOT ENDPOINT
# ==========================================

@app.get("/", tags=["System"])
def home():

    return {
        "success": True,
        "application": "PrismShift AI",
        "version": "1.0.0",
        "status": "running",
        "message": "Backend is ready."
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health", tags=["System"])
def health():

    return {
        "success": True,
        "status": "online",
        "application": "PrismShift AI",
        "ai_model": "gemma4:latest",
        "ai_provider": "Ollama",
        "database": "SQLite"
    }


# ==========================================
# API INFORMATION
# ==========================================

@app.get("/api/info", tags=["System"])
def api_info():

    return {
        "application": "PrismShift AI",
        "version": "1.0.0",
        "modes": [
            "Reality Mode",
            "Digital Mode"
        ],
        "features": [
            "Image Analysis",
            "Formal Document Generation",
            "AI Prompt Generation",
            "Conversation Editing",
            "PDF Export",
            "DOCX Export",
            "PPTX Export",
            "User Authentication",
            "Conversation History"
        ],
        "model": "gemma4:latest",
        "execution": "Local"
    }