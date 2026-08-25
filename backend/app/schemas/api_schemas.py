from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class SourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    status: str
    message_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

class ChatQueryRequest(BaseModel):
    query: str
    source_id: Optional[int] = None

class EvidenceCitation(BaseModel):
    timestamp: str
    sender: str
    content: str

class ChatResponse(BaseModel):
    observation: str
    inference: str
    recommendation: str
    evidence: List[EvidenceCitation]
    confidence: str
    confidence_reason: str

class CommunityReportRequest(BaseModel):
    source_id: Optional[int] = None

class CommunityReportResponse(BaseModel):
    executive_summary: str
    most_discussed_topics: List[str]
    community_mood: str
    active_contributors: List[str]
    engagement_highlights: List[str]
    interesting_trends: List[str]
    ai_recommendations: List[str]
    confidence: str
    confidence_reason: str

class MessageExplorerItem(BaseModel):
    id: int
    timestamp: datetime
    sender: str
    content: str

    class Config:
        from_attributes = True

class ExplorerStats(BaseModel):
    total_messages: int
    unique_members: int
    most_active_sender: str
    most_discussed_hour: Optional[int]
    avg_messages_per_hour: float

class ExplorerResponse(BaseModel):
    messages: List[MessageExplorerItem]
    total_count: int
    stats: ExplorerStats
