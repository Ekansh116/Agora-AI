import chromadb
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.providers.base_embedding import BaseEmbedding
from app.models.db_models import Conversation, Message
from app.core.config import settings

class RetrieverService:
    def __init__(self, embedding_provider: BaseEmbedding):
        self.embedding_provider = embedding_provider
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
        self.collection = self.chroma_client.get_or_create_collection(name="conversation_chunks")

    def index_conversation_chunk(
        self, 
        conversation_id: int, 
        source_id: int, 
        start_time: datetime, 
        end_time: datetime, 
        messages: List[Dict]
    ):
        """
        Formulate document content and insert embedding into ChromaDB
        """
        # Format text representation for embedding
        lines = []
        for msg in messages:
            timestamp_str = msg["timestamp"].strftime("%Y-%m-%d %H:%M")
            lines.append(f"[{timestamp_str}] {msg['sender']}: {msg['content']}")
            
        doc_content = f"=== Conversation Thread [{start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}] ===\n" + "\n".join(lines)
        
        # Generate embedding
        vector = self.embedding_provider.embed_query(doc_content)
        
        # Add to ChromaDB collection
        self.collection.add(
            ids=[str(conversation_id)],
            embeddings=[vector],
            documents=[doc_content],
            metadatas=[{
                "conversation_id": conversation_id,
                "source_id": source_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "message_count": len(messages)
            }]
        )

    def delete_source_vectors(self, source_id: int):
        """
        Remove vectors associated with a deleted source
        """
        try:
            self.collection.delete(where={"source_id": source_id})
        except Exception as e:
            print(f"Error deleting source vectors for source_id {source_id}: {e}")

    def delete_all_vectors(self):
        """
        Delete all indexed documents
        """
        try:
            self.chroma_client.delete_collection("conversation_chunks")
            self.collection = self.chroma_client.get_or_create_collection(name="conversation_chunks")
        except Exception as e:
            print(f"Error resetting Chroma collection: {e}")

    def retrieve_relevant_threads(
        self, 
        query: str, 
        db: Session, 
        source_id: Optional[int] = None, 
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        1. Embed the query
        2. Query ChromaDB for top_k matches (filter by source_id if present)
        3. Load entire conversation threads from SQLite using matched ids
        4. Package results with distance/similarity scores for transparency
        """
        query_vector = self.embedding_provider.embed_query(query)
        
        where_filter = {}
        if source_id is not None:
            where_filter = {"source_id": source_id}
            
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=where_filter if where_filter else None
        )
        
        if not results or not results["ids"] or not results["ids"][0]:
            return []
            
        matched_threads = []
        ids = results["ids"][0]
        distances = results["distances"][0] if "distances" in results else [1.0] * len(ids)
        
        for idx, conv_id_str in enumerate(ids):
            conv_id = int(conv_id_str)
            distance = distances[idx]
            
            # Fetch complete conversation and messages chronologically from SQLite
            conversation = db.query(Conversation).filter(Conversation.id == conv_id).first()
            if not conversation:
                continue
                
            messages_db = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.timestamp.asc()).all()
            
            thread_messages = []
            for msg in messages_db:
                thread_messages.append({
                    "timestamp": msg.timestamp,
                    "sender": msg.sender,
                    "content": msg.content
                })
                
            matched_threads.append({
                "conversation_id": conv_id,
                "source_id": conversation.source_id,
                "title": conversation.title,
                "start_time": conversation.start_time,
                "end_time": conversation.end_time,
                "messages": thread_messages,
                "distance": distance,
                "similarity_score": round(max(0.0, 1.0 - (distance / 2.0)), 3)
            })
            
        return matched_threads
