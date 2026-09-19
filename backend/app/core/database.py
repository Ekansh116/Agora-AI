from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# For SQLite, we specify connect_args={"check_same_thread": False}
# as SQLite only allows one thread to communicate with it by default.
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_message_fts_index():
    """Create and synchronize the SQLite FTS5 index used for lexical retrieval."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    from sqlalchemy import text

    with engine.begin() as connection:
        connection.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS message_fts USING fts5(
                message_id UNINDEXED,
                conversation_id UNINDEXED,
                source_id UNINDEXED,
                sender,
                content
            )
        """))
        connection.execute(text("""
            CREATE TRIGGER IF NOT EXISTS message_fts_after_insert
            AFTER INSERT ON messages
            BEGIN
                INSERT INTO message_fts(message_id, conversation_id, source_id, sender, content)
                SELECT NEW.id, NEW.conversation_id, c.source_id, NEW.sender, NEW.content
                FROM conversations c WHERE c.id = NEW.conversation_id;
            END;
        """))
        connection.execute(text("""
            CREATE TRIGGER IF NOT EXISTS message_fts_after_delete
            AFTER DELETE ON messages
            BEGIN
                DELETE FROM message_fts WHERE message_id = OLD.id;
            END;
        """))
        connection.execute(text("""
            CREATE TRIGGER IF NOT EXISTS message_fts_after_update
            AFTER UPDATE OF conversation_id, sender, content ON messages
            BEGIN
                DELETE FROM message_fts WHERE message_id = OLD.id;
                INSERT INTO message_fts(message_id, conversation_id, source_id, sender, content)
                SELECT NEW.id, NEW.conversation_id, c.source_id, NEW.sender, NEW.content
                FROM conversations c WHERE c.id = NEW.conversation_id;
            END;
        """))
        connection.execute(text("""
            INSERT INTO message_fts(message_id, conversation_id, source_id, sender, content)
            SELECT m.id, m.conversation_id, c.source_id, m.sender, m.content
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE NOT EXISTS (SELECT 1 FROM message_fts f WHERE f.message_id = m.id)
        """))
