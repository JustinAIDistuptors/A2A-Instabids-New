"""
Main FastAPI application for InstaBids API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from instabids.api.routes.ws_chat import router as ws_router
from instabids.api.routes.messages import router as messages_router

# Create FastAPI app
app = FastAPI(
    title="InstaBids API",
    description="API for InstaBids homeowner and contractor services",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ws_router, tags=["websocket"])
app.include_router(messages_router, prefix="/api", tags=["messages"])

@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "InstaBids API"}

# Import this at the end to avoid circular imports
from instabids.api.routes import bidcard  # noqa