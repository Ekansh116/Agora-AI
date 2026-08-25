import sys
import os
from datetime import datetime

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Apply SSL patch before other imports
import app.core.ssl_patch

from app.services.parser_service import ParserService
from app.services.chunker_service import ConversationChunker
from app.core.database import Base, engine, SessionLocal
from app.models.db_models import Source, Conversation, Message, Report
from app.providers.ollama_provider import OllamaProvider
from app.providers.sentence_transformer_provider import SentenceTransformerProvider
from app.services.retriever_service import RetrieverService
from app.services.rag_service import RAGService
from app.services.insights_service import InsightsService
from app.services.community_report_service import CommunityReportService

def main():
    print("=== STARTING BACKEND INTEGRATION TEST ===")
    
    # 1. Test Parser & Chunker
    print("\n1. Testing Parser & Chunker...")
    sample_chat = (
        "23/10/2023, 14:15 - John Doe: Hey everyone, welcome to the AI Community!\n"
        "23/10/2023, 14:16 - Sarah Connor: Hi John! Excited to be here.\n"
        "23/10/2023, 14:20 - John Doe: Let's start the first discussion on LLMs.\n"
        "23/10/2023, 14:22 - This is a multi-line message continuation\n"
        "written by John Doe to test multi-line parsing.\n"
        "23/10/2023, 14:25 - Messages and calls are end-to-end encrypted.\n"  # System msg
        "23/10/2023, 14:45 - Sarah Connor: Sorry, I got disconnected. What did I miss?\n"
    )
    
    parser = ParserService()
    parsed = parser.parse(sample_chat)
    print(f"Parsed {len(parsed)} messages.")
    for idx, msg in enumerate(parsed):
        print(f"  [{idx+1}] [{msg['timestamp']}] {msg['sender']}: {msg['content'][:40]}...")
        
    chunker = ConversationChunker()
    chunks = chunker.chunk_messages(parsed)
    print(f"Grouped into {len(chunks)} conversation chunks.")
    for idx, chunk in enumerate(chunks):
        print(f"  Chunk {idx+1}: {len(chunk)} messages (Start: {min(m['timestamp'] for m in chunk)}, End: {max(m['timestamp'] for m in chunk)})")

    # 2. Test SQLite database tables creation
    print("\n2. Initializing SQLite Test Tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    print("SQLite initialized successfully.")

    # 3. Test Provider Instantiations (Embedding & LLM)
    print("\n3. Testing Embedding Service & LLM Provider...")
    try:
        embedder = SentenceTransformerProvider()
        test_embed = embedder.embed_query("Hello community analyst")
        print(f"Embedding success. Vector dimension: {len(test_embed)}")
    except Exception as e:
        print(f"Embedding initialization failed: {e}")
        db.close()
        return

    ollama = OllamaProvider()
    ollama_online = ollama.is_healthy()
    print(f"Ollama local instance online status: {ollama_online}")

    # 4. Write data to SQLite & ChromaDB
    print("\n4. Writing parsed data to SQLite and ChromaDB...")
    try:
        # Create test source
        src = Source(source_type="whatsapp", name="test_chat.txt", status="indexing")
        db.add(src)
        db.commit()
        db.refresh(src)
        
        retriever = RetrieverService(embedder)
        retriever.delete_source_vectors(src.id) # Clean start
        
        for idx, chunk in enumerate(chunks):
            start_t = min(m["timestamp"] for m in chunk)
            end_t = max(m["timestamp"] for m in chunk)
            
            conv = Conversation(
                source_id=src.id,
                start_time=start_t,
                end_time=end_t,
                title=f"Test Conversation {idx+1}"
            )
            db.add(conv)
            db.flush()
            
            for m in chunk:
                msg = Message(
                    conversation_id=conv.id,
                    timestamp=m["timestamp"],
                    sender=m["sender"],
                    content=m["content"]
                )
                db.add(msg)
            
            # Embed and upload to Chroma
            retriever.index_conversation_chunk(conv.id, src.id, start_t, end_t, chunk)
            
        src.status = "ready"
        src.message_count = len(parsed)
        db.commit()
        print("Successfully indexed test conversations into SQLite and ChromaDB!")
        
    except Exception as e:
        print(f"Data indexing test failed: {e}")
        db.rollback()
        db.close()
        return

    # 5. Test Analytics Insights Engine
    print("\n5. Testing Insights Service...")
    insights = InsightsService()
    dashboard = insights.get_dashboard_data(db, src.id)
    print(f"Dashboard Stats: Members={dashboard['total_members']}, Messages={dashboard['total_messages']}")
    print(f"Most Active: Member={dashboard['most_active_member']}, Day={dashboard['most_active_day']}")
    print(f"Top senders list: {dashboard['top_senders']}")

    # 6. Test RAG Pipeline & Community Report
    if ollama_online:
        print("\n6. Testing RAG & Community Report (Ollama Qwen)...")
        rag = RAGService(ollama, retriever)
        ans = rag.answer_query("Why is Sarah excited?", db, src.id)
        print("\n--- RAG Response ---")
        print(f"Observation: {ans['observation']}")
        print(f"Inference: {ans['inference']}")
        print(f"Recommendation: {ans['recommendation']}")
        print(f"Confidence: {ans['confidence']} ({ans['confidence_reason']})")
        print(f"Evidence citations count: {len(ans['evidence'])}")
        
        report_serv = CommunityReportService(ollama)
        report = report_serv.generate_report(db, src.id)
        print("\n--- Community Report ---")
        print(f"Summary: {report['executive_summary'][:150]}...")
        print(f"Topics: {report['most_discussed_topics']}")
        print(f"Mood: {report['community_mood']}")
    else:
        print("\n6. Skipping RAG & Community Report (Ollama instance offline/configured model missing).")

    # 7. Cleanup
    print("\n7. Cleaning up test data...")
    retriever.delete_source_vectors(src.id)
    db.delete(src)
    db.commit()
    db.close()
    print("Cleanup successful.")
    
    print("\n=== INTEGRATION TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
