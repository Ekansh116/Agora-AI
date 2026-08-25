import io
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, desc, or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.db_models import Message, Conversation
from app.schemas.api_schemas import ExplorerResponse, ExplorerStats, MessageExplorerItem

logger = logging.getLogger("community_ai")
router = APIRouter(prefix="/explorer", tags=["Explorer"])

def build_explorer_query(
    db: Session,
    source_id: Optional[int],
    relative_range: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    sender: Optional[str],
    keyword: Optional[str],
    has_media: Optional[bool]
):
    query = db.query(Message).join(Conversation)
    
    # 1. Source ID filter
    if source_id is not None:
        query = query.filter(Conversation.source_id == source_id)
        
    # 2. Relative range filter
    if relative_range and relative_range != "custom" and relative_range != "all":
        max_ts_query = db.query(func.max(Message.timestamp)).join(Conversation)
        if source_id is not None:
            max_ts_query = max_ts_query.filter(Conversation.source_id == source_id)
        max_ts = max_ts_query.scalar()
        if not max_ts:
            max_ts = datetime.utcnow()
            
        logger.info(f"[EXPLORER] Applying relative range filter: {relative_range} from base: {max_ts}")
            
        if relative_range == "1h":
            query = query.filter(Message.timestamp >= max_ts - timedelta(hours=1))
        elif relative_range == "6h":
            query = query.filter(Message.timestamp >= max_ts - timedelta(hours=6))
        elif relative_range == "12h":
            query = query.filter(Message.timestamp >= max_ts - timedelta(hours=12))
        elif relative_range == "24h":
            query = query.filter(Message.timestamp >= max_ts - timedelta(hours=24))
        elif relative_range == "yesterday":
            yesterday = max_ts - timedelta(days=1)
            start_t = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
            end_t = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
            query = query.filter(Message.timestamp.between(start_t, end_t))
        elif relative_range == "7d":
            query = query.filter(Message.timestamp >= max_ts - timedelta(days=7))
        elif relative_range == "30d":
            query = query.filter(Message.timestamp >= max_ts - timedelta(days=30))
    else:
        # Custom Range filter
        if start_date:
            query = query.filter(Message.timestamp >= start_date)
        if end_date:
            query = query.filter(Message.timestamp <= end_date)
            
    # 3. Sender filter
    if sender:
        query = query.filter(Message.sender == sender)
        
    # 4. Keyword / Full-text filter
    if keyword:
        query = query.filter(Message.content.like(f"%{keyword}%"))
        
    # 5. Media placeholder filter
    if has_media is not None:
        media_cond = or_(
            Message.content.like("%omitted%"),
            Message.content.like("%Media%"),
            Message.content.like("%Attached%"),
            Message.content.like("%omits%")
        )
        if has_media:
            query = query.filter(media_cond)
        else:
            query = query.filter(~media_cond)
            
    return query

@router.get("/messages", response_model=ExplorerResponse)
def get_explorer_messages(
    source_id: Optional[int] = None,
    relative_range: Optional[str] = "all",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sender: Optional[str] = None,
    keyword: Optional[str] = None,
    has_media: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieves a paginated list of chat messages meeting the selection filters
    along with summary activity statistics calculated dynamically over the selection span.
    """
    logger.info(f"[EXPLORER] Fetching messages with limit={limit}, offset={offset}")
    
    # Build query
    base_query = build_explorer_query(
        db, source_id, relative_range, start_date, end_date, sender, keyword, has_media
    )
    
    # Total count matching
    total_count = base_query.count()
    
    # Load messages
    messages = base_query.order_by(Message.timestamp.asc()).offset(offset).limit(limit).all()
    
    # 1. Unique members
    unique_members = base_query.with_entities(func.count(func.distinct(Message.sender))).scalar() or 0
    
    # 2. Most active sender
    active_sender_res = base_query.with_entities(
        Message.sender,
        func.count(Message.id).label("cnt")
    ).group_by(Message.sender).order_by(desc("cnt")).first()
    most_active_sender = active_sender_res[0] if active_sender_res else "N/A"
    
    # 3. Most discussed hour
    hour_res = base_query.with_entities(
        func.strftime('%H', Message.timestamp).label("hr"),
        func.count(Message.id).label("cnt")
    ).group_by("hr").order_by(desc("cnt")).first()
    most_discussed_hour = int(hour_res[0]) if hour_res and hour_res[0] is not None else None
    
    # 4. Average messages per hour
    timespan_res = base_query.with_entities(
        func.min(Message.timestamp),
        func.max(Message.timestamp)
    ).first()
    
    if timespan_res and timespan_res[0] and timespan_res[1] and total_count > 0:
        span_hours = max((timespan_res[1] - timespan_res[0]).total_seconds() / 3600.0, 1.0)
        avg_messages_per_hour = round(total_count / span_hours, 2)
    else:
        avg_messages_per_hour = 0.0
        
    stats = ExplorerStats(
        total_messages=total_count,
        unique_members=unique_members,
        most_active_sender=most_active_sender,
        most_discussed_hour=most_discussed_hour,
        avg_messages_per_hour=avg_messages_per_hour
    )
    
    # Convert models to schemas
    messages_out = [
        MessageExplorerItem(
            id=m.id,
            timestamp=m.timestamp,
            sender=m.sender,
            content=m.content
        ) for m in messages
    ]
    
    return ExplorerResponse(
        messages=messages_out,
        total_count=total_count,
        stats=stats
    )

@router.get("/export")
def export_explorer_messages(
    source_id: Optional[int] = None,
    relative_range: Optional[str] = "all",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sender: Optional[str] = None,
    keyword: Optional[str] = None,
    has_media: Optional[bool] = None,
    export_format: str = "txt", # "txt" or "json"
    db: Session = Depends(get_db)
):
    """
    Streams all matching messages as a downloadable file (either txt or json format).
    """
    logger.info(f"[EXPLORER] Exporting filtered messages as format: {export_format}")
    
    base_query = build_explorer_query(
        db, source_id, relative_range, start_date, end_date, sender, keyword, has_media
    )
    messages = base_query.order_by(Message.timestamp.asc()).all()
    
    if export_format == "json":
        data = [{
            "timestamp": m.timestamp.isoformat(),
            "sender": m.sender,
            "content": m.content
        } for m in messages]
        
        bio = io.BytesIO(json.dumps(data, indent=2).encode('utf-8'))
        return StreamingResponse(
            bio,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=exported_conversations.json"}
        )
    else:
        # Default txt
        output = io.StringIO()
        for m in messages:
            ts_str = m.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            output.write(f"[{ts_str}] {m.sender}: {m.content}\n")
        output.seek(0)
        
        bio = io.BytesIO(output.read().encode('utf-8'))
        return StreamingResponse(
            bio,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=exported_conversations.txt"}
        )
