from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.models.db_models import Source, Conversation, Message
from app.services.parser_service import ParserService
from app.services.chunker_service import ConversationChunker
from app.services.retriever_service import RetrieverService
from app.providers.sentence_transformer_provider import SentenceTransformerProvider
from app.schemas.api_schemas import SourceResponse
from typing import List

router = APIRouter(prefix="/sources", tags=["Sources"])

# Instantiate parser and chunker as singletons
parser_service = ParserService()
chunker = ConversationChunker()
embedding_provider = None

def get_embedding_provider():
    global embedding_provider
    if embedding_provider is None:
        embedding_provider = SentenceTransformerProvider()
    return embedding_provider

def run_indexing_pipeline(source_id: int, file_content: str):
    """
    Executes parsing, database writing, and vector database indexing
    asynchronously to avoid UI thread blockages.
    """
    db: Session = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return
            
        # Update status -> parsing
        source.status = "parsing"
        db.commit()
        messages = parser_service.parse(file_content)
        
        if not messages:
            source.status = "failed: empty or invalid formatting"
            db.commit()
            return
            
        source.status = "parsed"
        db.commit()
        
        # Group messages into conversations
        chunks = chunker.chunk_messages(messages)
        
        source.status = "storing"
        db.commit()
        
        source.message_count = len(messages)
        
        # Write conversations & messages to SQLite database
        for chunk in chunks:
            if not chunk:
                continue
            start_t = min(m["timestamp"] for m in chunk)
            end_t = max(m["timestamp"] for m in chunk)
            
            db_conv = Conversation(
                source_id=source.id,
                start_time=start_t,
                end_time=end_t,
                title=f"Discussion starting {start_t.strftime('%Y-%m-%d %H:%M')}"
            )
            db.add(db_conv)
            db.flush()  # Extract the conversation ID
            
            for m in chunk:
                db_msg = Message(
                    conversation_id=db_conv.id,
                    timestamp=m["timestamp"],
                    sender=m["sender"],
                    content=m["content"]
                )
                db.add(db_msg)
                
        source.status = "stored"
        db.commit()
        
        # Generate embeddings and push to ChromaDB collection
        source.status = "indexing"
        db.commit()
        
        retriever = RetrieverService(get_embedding_provider())
        
        # Load and embed conversation chunks
        db_conversations = db.query(Conversation).filter(Conversation.source_id == source.id).all()
        for conv in db_conversations:
            conv_msgs = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.timestamp.asc()).all()
            msg_list = [{
                "timestamp": m.timestamp,
                "sender": m.sender,
                "content": m.content
            } for m in conv_msgs]
            
            retriever.index_conversation_chunk(
                conversation_id=conv.id,
                source_id=source.id,
                start_time=conv.start_time,
                end_time=conv.end_time,
                messages=msg_list
            )
            
        source.status = "ready"
        db.commit()
        
    except Exception as e:
        db.rollback()
        source = db.query(Source).filter(Source.id == source_id).first()
        if source:
            source.status = f"failed: {str(e)}"
            db.commit()
        print(f"Index pipeline error for source {source_id}: {str(e)}")
    finally:
        db.close()

@router.post("/upload", response_model=SourceResponse)
async def upload_source(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_type: str = Form("whatsapp"),
    db: Session = Depends(get_db)
):
    try:
        content_bytes = await file.read()
        file_content = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read file text: {str(e)}")
        
    db_source = Source(
        source_type=source_type,
        name=file.filename,
        status="uploaded"
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    
    # Trigger background pipeline
    background_tasks.add_task(run_indexing_pipeline, db_source.id, file_content)
    
    return db_source

@router.get("/", response_model=List[SourceResponse])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).order_by(Source.uploaded_at.desc()).all()

@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    db_source = db.query(Source).filter(Source.id == source_id).first()
    if not db_source:
        raise HTTPException(status_code=404, detail="Source registry not found")
        
    # Purge vectors
    retriever = RetrieverService(get_embedding_provider())
    retriever.delete_source_vectors(source_id)
    
    # Purge SQL record (cascades child items)
    db.delete(db_source)
    db.commit()
    return {"detail": "Source deleted successfully"}
