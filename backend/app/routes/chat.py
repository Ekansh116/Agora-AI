from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.rag_service import RAGService
from app.services.retriever_service import RetrieverService
from app.providers.sentence_transformer_provider import SentenceTransformerProvider
from app.providers.ollama_provider import OllamaProvider
from app.schemas.api_schemas import ChatQueryRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

# Singletons initialized lazily
rag_service = None
embedding_provider = None
llm_provider = None
retriever_service = None

def get_rag_service():
    global rag_service, embedding_provider, llm_provider, retriever_service
    if embedding_provider is None:
        embedding_provider = SentenceTransformerProvider()
    if llm_provider is None:
        llm_provider = OllamaProvider()
    if retriever_service is None:
        retriever_service = RetrieverService(embedding_provider)
    if rag_service is None:
        rag_service = RAGService(llm_provider, retriever_service)
    return rag_service

@router.post("/query", response_model=ChatResponse)
def query_community_rag(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    service: RAGService = Depends(get_rag_service)
):
    """
    Submits a natural language question to the community dataset.
    Performs RAG to retrieve matching conversations and formats the answer
    along with citations and confidence statistics.
    """
    try:
        return service.answer_query(request.query, db, request.source_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Community AI chat query failed: {str(e)}")
