import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import auth, documents, chat

app = FastAPI(
    title="FinSentinelAI API",
    description="Enterprise API for Financial Document RAG",
    version="1.0.0"
)

# Configure CORS - configurable via FINSENTINEL_CORS_ORIGINS env var
cors_origins = os.getenv(
    "FINSENTINEL_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
