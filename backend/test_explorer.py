import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.database import SessionLocal, Base, engine
from app.models.db_models import Source, Conversation, Message
from app.services.parser_service import ParserService
from app.services.insights_service import InsightsService
from app.routes.explorer import build_explorer_query

def run_test():
    print("=== STARTING CONVERSATION EXPLORER & HOURLY DIAGNOSTICS ===")
    
    # 1. Initialize schemas
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    try:
        # Clear existing data to ensure fresh environment
        db.query(Message).delete()
        db.query(Conversation).delete()
        db.query(Source).delete()
        db.commit()

        # 2. Test Parser for dot-separated AM/PM and optional commas
        print("\n1. Testing Parser regex improvements...")
        parser = ParserService()
        test_chat = (
            "07/07/2026, 2:15 p.m. - John Doe: Hey there! Did you hear about the hackathon?\n"
            "07/07/2026, 2:16 p. m. - Sarah Connor: Yes, John! Excited to attend.\n"
            "[07/07/2026 18:45:12] Alex Mercer: Is there a registration link?\n"
            "08/07/2026 09:30 AM - John Doe: Here it is: link.com (attached media)\n"
        )
        parsed = parser.parse(test_chat)
        print(f"Parsed {len(parsed)} messages successfully.")
        for idx, p in enumerate(parsed):
            print(f"  [{idx+1}] [{p['timestamp']}] {p['sender']}: {p['content']}")
            
        assert len(parsed) == 4, "Should parse exactly 4 messages"
        assert parsed[0]["timestamp"].hour == 14, "2:15 p.m. should parse to hour 14"
        assert parsed[1]["timestamp"].hour == 14, "2:16 p. m. should parse to hour 14"
        assert parsed[2]["timestamp"].hour == 18, "18:45 should parse to hour 18"
        assert parsed[3]["timestamp"].hour == 9, "09:30 AM should parse to hour 9"
        print("Parser test passed!")

        # 3. Store in database
        print("\n2. Storing mock chats in SQLite...")
        source = Source(source_type="whatsapp", name="test_explorer.txt", status="ready")
        db.add(source)
        db.commit()
        
        conv = Conversation(source_id=source.id, start_time=parsed[0]["timestamp"], end_time=parsed[-1]["timestamp"])
        db.add(conv)
        db.commit()
        
        for p in parsed:
            msg = Message(
                conversation_id=conv.id,
                timestamp=p["timestamp"],
                sender=p["sender"],
                content=p["content"]
            )
            db.add(msg)
        db.commit()
        print("Successfully stored conversation threads!")

        # 4. Test Hourly Analysis
        print("\n3. Testing Hourly activity frequency analyzer...")
        insights = InsightsService()
        data = insights.get_dashboard_data(db, source.id)
        
        hours_active = {item["hour"]: item["count"] for item in data["active_hours"]}
        print(f"Computed hours map: { {k: v for k, v in hours_active.items() if v > 0} }")
        
        assert hours_active[14] == 2, "Hour 14 should have 2 messages (2:15 p.m. and 2:16 p. m.)"
        assert hours_active[18] == 1, "Hour 18 should have 1 message"
        assert hours_active[9] == 1, "Hour 9 should have 1 message"
        assert len(hours_active) == 24, "Should return stats for all 24 hours (0-23)"
        print("Hourly Analysis test passed!")

        # 5. Test Explorer Filters
        print("\n4. Testing Explorer SQL Query Filter Builder...")
        
        # Test keyword filter
        q_keyword = build_explorer_query(db, source.id, "all", None, None, None, "hackathon", None)
        assert q_keyword.count() == 1, "Should find exactly 1 message containing 'hackathon'"
        print("Keyword filter test passed!")
        
        # Test sender filter
        q_sender = build_explorer_query(db, source.id, "all", None, None, "John Doe", None, None)
        assert q_sender.count() == 2, "John Doe should have exactly 2 messages"
        print("Sender filter test passed!")

        # Test media filter
        q_media = build_explorer_query(db, source.id, "all", None, None, None, None, True)
        assert q_media.count() == 1, "Should find exactly 1 message with media ('attached')"
        print("Media filter test passed!")
        
        print("\n=== ALL DIAGNOSTIC TESTS PASSED SUCCESSFULLY ===")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
