import os
import app.core.ssl_patch
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Agora AI"
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./community_intelligence.db")
    
    # Chroma DB Directory
    chroma_dir = os.getenv("CHROMA_DB_DIR", "./chroma_db")
    if not os.path.isabs(chroma_dir):
        CHROMA_DB_DIR: str = os.path.join(BASE_DIR, chroma_dir)
    else:
        CHROMA_DB_DIR: str = chroma_dir
        
    OLLAMA_URL: str = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    
    # SSL verification setting (default is False: TLS certificate verification is enforced)
    DISABLE_SSL_VERIFY: bool = os.getenv("DISABLE_SSL_VERIFY", "false").lower() in ("true", "1", "yes")

    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")

settings = Settings()
