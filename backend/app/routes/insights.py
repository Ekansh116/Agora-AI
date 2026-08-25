from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.insights_service import InsightsService
from app.services.community_report_service import CommunityReportService
from app.providers.ollama_provider import OllamaProvider
from app.schemas.api_schemas import CommunityReportRequest, CommunityReportResponse
from typing import Optional

router = APIRouter(prefix="/insights", tags=["Insights"])

# Initialize services
insights_service = InsightsService()
llm_provider = None
report_service = None

def get_report_service():
    global llm_provider, report_service
    if llm_provider is None:
        llm_provider = OllamaProvider()
    if report_service is None:
        report_service = CommunityReportService(llm_provider)
    return report_service

@router.get("/dashboard")
def get_dashboard_insights(source_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Returns SQL aggregated metrics (members, messages, trends, senders, hourly activities)
    for display in dashboard visualizations.
    """
    return insights_service.get_dashboard_data(db, source_id)

@router.post("/report", response_model=CommunityReportResponse)
def generate_community_report(
    request: CommunityReportRequest,
    db: Session = Depends(get_db),
    service: CommunityReportService = Depends(get_report_service)
):
    """
    Triggers local Qwen generation of a structured community intelligence report
    analyzing topics, contributors, mood, and recommendations.
    """
    try:
        return service.generate_report(db, request.source_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Community report generation failed: {str(e)}")
