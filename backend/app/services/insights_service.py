from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from app.models.db_models import Message, Conversation

class InsightsService:
    def get_dashboard_data(self, db: Session, source_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes database aggregation queries to build analytical dashboard datasets,
        optionally filtered by a single source.
        """
        # Base query linking Messages to Conversations
        msg_query = db.query(Message).join(Conversation)
        
        if source_id is not None:
            msg_query = msg_query.filter(Conversation.source_id == source_id)
            
        total_messages = msg_query.count()
        
        # Total members (distinct senders)
        total_members_query = db.query(Message.sender).join(Conversation)
        if source_id is not None:
            total_members_query = total_members_query.filter(Conversation.source_id == source_id)
        total_members = total_members_query.distinct().count()
        
        # Most active member
        active_member_query = db.query(
            Message.sender, 
            func.count(Message.id).label("cnt")
        ).join(Conversation)
        if source_id is not None:
            active_member_query = active_member_query.filter(Conversation.source_id == source_id)
        active_member_result = active_member_query.group_by(Message.sender).order_by(desc("cnt")).first()
        
        most_active_member = active_member_result[0] if active_member_result else "N/A"
        most_active_member_count = active_member_result[1] if active_member_result else 0
        
        # Most active day
        active_day_query = db.query(
            func.strftime('%Y-%m-%d', Message.timestamp).label("day"),
            func.count(Message.id).label("cnt")
        ).join(Conversation)
        if source_id is not None:
            active_day_query = active_day_query.filter(Conversation.source_id == source_id)
        active_day_result = active_day_query.group_by("day").order_by(desc("cnt")).first()
        
        most_active_day = active_day_result[0] if active_day_result else "N/A"
        most_active_day_count = active_day_result[1] if active_day_result else 0

        # Top 10 Senders (Chart Data)
        top_senders_query = db.query(
            Message.sender,
            func.count(Message.id).label("cnt")
        ).join(Conversation)
        if source_id is not None:
            top_senders_query = top_senders_query.filter(Conversation.source_id == source_id)
        top_senders = top_senders_query.group_by(Message.sender).order_by(desc("cnt")).limit(10).all()
        top_senders_list = [{"sender": s[0], "count": s[1]} for s in top_senders]

        # Message volume over time (Daily)
        volume_query = db.query(
            func.strftime('%Y-%m-%d', Message.timestamp).label("day"),
            func.count(Message.id).label("cnt")
        ).join(Conversation)
        if source_id is not None:
            volume_query = volume_query.filter(Conversation.source_id == source_id)
        volume_data = volume_query.group_by("day").order_by("day").all()
        volume_list = [{"date": v[0], "count": v[1]} for v in volume_data]

        # Active hours of the day (Hourly frequency distribution)
        hours_query = db.query(
            func.strftime('%H', Message.timestamp).label("hour"),
            func.count(Message.id).label("cnt")
        ).join(Conversation)
        if source_id is not None:
            hours_query = hours_query.filter(Conversation.source_id == source_id)
        hours_data = hours_query.group_by("hour").order_by("hour").all()
        
        # Populate all 24 hours (including zero counts)
        hours_map = {h: 0 for h in range(24)}
        for h in hours_data:
            if h[0] is not None:
                try:
                    hours_map[int(h[0])] = h[1]
                except ValueError:
                    pass
        active_hours_list = [{"hour": k, "count": v} for k, v in sorted(hours_map.items())]

        return {
            "total_members": total_members,
            "total_messages": total_messages,
            "most_active_member": f"{most_active_member} ({most_active_member_count} msgs)" if most_active_member != "N/A" else "N/A",
            "most_active_day": f"{most_active_day} ({most_active_day_count} msgs)" if most_active_day != "N/A" else "N/A",
            "top_senders": top_senders_list,
            "message_volume": volume_list,
            "active_hours": active_hours_list
        }
