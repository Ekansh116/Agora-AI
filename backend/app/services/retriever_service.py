import chromadb
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.providers.base_embedding import BaseEmbedding
from app.models.db_models import Conversation, Message
from app.core.config import settings


class RetrieverService:
    """Hybrid retriever combining semantic vector search with lexical FTS5 search."""

    RRF_K = 60
    DEFAULT_CANDIDATES = 8

    def __init__(self, embedding_provider: BaseEmbedding):
        self.embedding_provider = embedding_provider
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
        self.collection = self.chroma_client.get_or_create_collection(name="conversation_chunks")

    def index_conversation_chunk(self, conversation_id: int, source_id: int, start_time: datetime, end_time: datetime, messages: List[Dict]):
        lines = [
            f"[{msg['timestamp'].strftime('%Y-%m-%d %H:%M')}] {msg['sender']}: {msg['content']}"
            for msg in messages
        ]
        doc_content = (
            f"=== Conversation Thread [{start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}] ===\n"
            + "\n".join(lines)
        )
        vector = self.embedding_provider.embed_query(doc_content)
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
        try:
            self.collection.delete(where={"source_id": source_id})
        except Exception as e:
            print(f"Error deleting source vectors for source_id {source_id}: {e}")

    def delete_all_vectors(self):
        try:
            self.chroma_client.delete_collection("conversation_chunks")
            self.collection = self.chroma_client.get_or_create_collection(name="conversation_chunks")
        except Exception as e:
            print(f"Error resetting Chroma collection: {e}")

    @staticmethod
    def _fts_query(query: str) -> str:
        import re
        tokens = re.findall(r"[\\w]+", query.lower(), flags=re.UNICODE)
        tokens = [token for token in tokens if len(token) > 1]
        return " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens[:24])

    def _vector_candidates(self, query: str, source_id: Optional[int], limit: int) -> List[Tuple[int, float]]:
        query_vector = self.embedding_provider.embed_query(query)
        where_filter = {"source_id": source_id} if source_id is not None else None
        results = self.collection.query(query_embeddings=[query_vector], n_results=limit, where=where_filter)
        if not results or not results.get("ids") or not results["ids"][0]:
            return []
        distances = results.get("distances", [[]])[0] if results.get("distances") else [1.0] * len(results["ids"][0])
        candidates = []
        for idx, conv_id_str in enumerate(results["ids"][0]):
            try:
                candidates.append((int(conv_id_str), float(distances[idx])))
            except (TypeError, ValueError):
                continue
        return candidates

    def _lexical_candidates(self, query: str, source_id: Optional[int], limit: int, db: Session) -> List[Tuple[int, float]]:
        fts_query = self._fts_query(query)
        if not fts_query:
            return []
        try:
            connection = db.get_bind().connect()
            try:
                params = {"query": fts_query, "limit": limit}
                source_clause = ""
                if source_id is not None:
                    source_clause = "AND f.source_id = :source_id"
                    params["source_id"] = source_id
                rows = connection.execute(text(f"""
                    SELECT f.conversation_id, MIN(bm25(message_fts)) AS lexical_score
                    FROM message_fts f
                    WHERE message_fts MATCH :query
                    {source_clause}
                    GROUP BY f.conversation_id
                    ORDER BY lexical_score ASC
                    LIMIT :limit
                """), params).fetchall()
                return [(int(row[0]), float(row[1])) for row in rows]
            finally:
                connection.close()
        except Exception as e:
            print(f"Lexical retrieval unavailable: {e}")
            return []

    def _hybrid_rank(self, vector_candidates: List[Tuple[int, float]], lexical_candidates: List[Tuple[int, float]]) -> List[Dict[str, Any]]:
        fused: Dict[int, Dict[str, Any]] = {}
        for rank, (conversation_id, distance) in enumerate(vector_candidates, start=1):
            item = fused.setdefault(conversation_id, {"conversation_id": conversation_id, "vector_rank": None, "lexical_rank": None, "vector_distance": None, "rrf_score": 0.0})
            item["vector_rank"] = rank
            item["vector_distance"] = distance
            item["rrf_score"] += 1.0 / (self.RRF_K + rank)
        for rank, (conversation_id, _) in enumerate(lexical_candidates, start=1):
            item = fused.setdefault(conversation_id, {"conversation_id": conversation_id, "vector_rank": None, "lexical_rank": None, "vector_distance": None, "rrf_score": 0.0})
            item["lexical_rank"] = rank
            item["rrf_score"] += 1.0 / (self.RRF_K + rank)
        return sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)

    def retrieve_relevant_threads(self, query: str, db: Session, source_id: Optional[int] = None, limit: int = 3, candidate_limit: int = DEFAULT_CANDIDATES) -> List[Dict[str, Any]]:
        """Retrieve conversations using semantic search + exact lexical search, fused with RRF."""
        vector_candidates = self._vector_candidates(query, source_id, candidate_limit)
        lexical_candidates = self._lexical_candidates(query, source_id, candidate_limit, db)
        fused_candidates = self._hybrid_rank(vector_candidates, lexical_candidates)[:limit]
        if not fused_candidates:
            return []

        matched_threads = []
        for candidate in fused_candidates:
            conv_id = candidate["conversation_id"]
            conversation = db.query(Conversation).filter(Conversation.id == conv_id).first()
            if not conversation:
                continue
            messages_db = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.timestamp.asc()).all()
            thread_messages = [{"timestamp": msg.timestamp, "sender": msg.sender, "content": msg.content} for msg in messages_db]
            matched_threads.append({
                "conversation_id": conv_id,
                "source_id": conversation.source_id,
                "title": conversation.title,
                "start_time": conversation.start_time,
                "end_time": conversation.end_time,
                "messages": thread_messages,
                "distance": candidate["vector_distance"],
                "vector_rank": candidate["vector_rank"],
                "lexical_rank": candidate["lexical_rank"],
                "rrf_score": round(candidate["rrf_score"], 6),
                "retrieval_methods": [
                    method for method, rank in (("semantic", candidate["vector_rank"]), ("lexical", candidate["lexical_rank"])) if rank is not None
                ]
            })
        return matched_threads
