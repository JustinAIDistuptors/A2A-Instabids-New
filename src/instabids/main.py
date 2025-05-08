"""
Main FastAPI app export for use in tests and ASGI deployment.
This module exports the FastAPI app from app.py.
"""
from .app import app

# Export the app for tests and server deployment
__all__ = ['app']
