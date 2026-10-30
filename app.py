"""Compatibility entry point for `uvicorn app:app`.

The canonical FastAPI application lives in Backend.main.
"""
from Backend.main import app

__all__ = ["app"]
