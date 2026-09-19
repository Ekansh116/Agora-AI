import app.core.ssl_patch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.routes import upload, insights, chat, explorer
from app.providers.ollama_provider import OllamaProvider

# Initialize SQLite database schema
Base.metadata.create_all(bind=engine)\n\n# Initialize the lexical index used by hybrid retrieval.\nfrom app.core.database import ensure_message_fts_index\nensure_message_fts_index()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend engine for the AI Community Intelligence Platform",
    version="1.0.0"
)

# Allow cross-origin requests (e.g. from local React dev servers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect endpoint routers under the API namespace
app.include_router(upload.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(explorer.router, prefix="/api")

@app.get("/api/health")
def health_check():
    ollama = OllamaProvider()
    ollama_healthy = ollama.is_healthy()
    return {
        "status": "online",
        "project_name": settings.PROJECT_NAME,
        "ollama_online": ollama_healthy,
        "model_configured": settings.LLM_MODEL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
