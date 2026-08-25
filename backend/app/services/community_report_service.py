import json
import re
import logging
from typing import Dict, Any, Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from app.providers.base_llm import BaseLLM
from app.models.db_models import Conversation, Message, Report

logger = logging.getLogger("community_ai")

class CommunityReportService:
    def __init__(self, llm_provider: BaseLLM):
        self.llm_provider = llm_provider

    def generate_report(self, db: Session, source_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Gathers active threads, constructs a comprehensive summarization request,
        sends it to the local Qwen LLM, parses the JSON structure, and caches it in SQL.
        """
        logger.info(f"[REPORT SERVICE] Report request received for source_id: {source_id}")

        # 1. Check if a report was already generated for this source
        existing_report = db.query(Report).filter(Report.source_id == source_id).order_by(desc(Report.generated_at)).first()
        if existing_report:
            try:
                logger.info("[REPORT SERVICE] Cached report found in SQLite database. Returning cached report.")
                return json.loads(existing_report.report_data)
            except Exception as e:
                logger.warning(f"[REPORT SERVICE] Failed to load cached report JSON: {str(e)}. Regenerating...")

        # 2. Check Ollama service health status
        logger.info("[REPORT SERVICE] Verifying local Ollama service availability")
        if not self.llm_provider.is_healthy():
            logger.error("[REPORT SERVICE] Ollama local service health check failed. Service is offline or model is not pulled.")
            raise RuntimeError("Ollama local service is offline or the active model is not pulled. Please check 'ollama list' and ensure the Ollama daemon is running.")

        # 3. Retrieve representative conversations
        logger.info("[REPORT SERVICE] Retrieving active conversations from SQLite database")
        # We target the top 5 conversations by message density
        query = db.query(Conversation, func.count(Message.id).label("cnt")).join(Message)
        if source_id is not None:
            query = query.filter(Conversation.source_id == source_id)
        
        active_conversations = query.group_by(Conversation.id).order_by(desc("cnt")).limit(5).all()

        if not active_conversations:
            logger.warning("[REPORT SERVICE] No conversation data exists in SQLite database for report compilation")
            return self._empty_report("No conversation data exists in the database to generate a report.")

        # 4. Build context details
        conversation_contexts = []
        total_messages_analyzed = 0
        
        for conv, cnt in active_conversations:
            total_messages_analyzed += cnt
            messages = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.timestamp.asc()).all()
            
            lines = []
            for m in messages:
                timestamp_str = m.timestamp.strftime("%Y-%m-%d %H:%M")
                lines.append(f"[{timestamp_str}] {m.sender}: {m.content}")
                
            conv_text = f"--- Discussion Thread (ID: {conv.id}) ---\n" + "\n".join(lines)
            conversation_contexts.append(conv_text)
            
        context_str = "\n\n".join(conversation_contexts)

        # Metadata confidence scoring
        num_conversations = len(active_conversations)
        if total_messages_analyzed > 100:
            confidence = "High"
            confidence_reason = f"Analysis run on {total_messages_analyzed} messages across {num_conversations} highly active discussions."
        elif total_messages_analyzed > 25:
            confidence = "Medium"
            confidence_reason = f"Analysis run on {total_messages_analyzed} messages across {num_conversations} discussions."
        else:
            confidence = "Low"
            confidence_reason = f"Limited conversation volume ({total_messages_analyzed} messages) for broad insights."

        # 5. Prompt construction
        logger.info("[REPORT SERVICE] Building intelligence summary prompt for LLM")
        system_prompt = (
            "You are a master Community Intelligence Analyst. Your task is to analyze the provided conversation threads and generate a structured Community Report.\n"
            "You must respond ONLY with a raw JSON object (do not wrap in markdown ```json or backticks) containing the following fields:\n"
            "{\n"
            '  "executive_summary": "A concise paragraph summarizing recent discussions and highlights.",\n'
            '  "most_discussed_topics": ["Topic 1", "Topic 2", "Topic 3"],\n'
            '  "community_mood": "Overall sentiment, emotional tone, and frustration/excitement levels.",\n'
            '  "active_contributors": ["User A", "User B"],\n'
            '  "engagement_highlights": ["Key highlight 1", "Key highlight 2"],\n'
            '  "interesting_trends": ["Trend 1", "Trend 2"],\n'
            '  "ai_recommendations": ["Recommendation 1", "Recommendation 2"]\n'
            "}\n"
            "Ensure everything is grounded strictly in the provided logs. Do not fabricate names, topics, or recommendations."
        )

        user_prompt = (
            f"Here are the active conversations to analyze:\n\n{context_str}\n\n"
            f"Generate the structured Community Report JSON."
        )

        # 6. Call Ollama
        logger.info(f"[REPORT SERVICE] Calling local Ollama LLM endpoint with prompt size={len(user_prompt)} chars")
        try:
            raw_response = self.llm_provider.generate(user_prompt, system_prompt)
            
            logger.info("[REPORT SERVICE] Parsing structured response from Ollama")
            report_dict = self._parse_llm_json(raw_response)
        except Exception as e:
            logger.error(f"[REPORT SERVICE] LLM Generation error: {str(e)}")
            return self._empty_report(f"Failed to generate report from LLM: {str(e)}")

        # Normalize schema formatting to ensure Pydantic parsing succeeds
        logger.info("[REPORT SERVICE] Normalizing report keys to enforce schema validation compliance")
        report_dict = self._normalize_report_schema(report_dict, confidence, confidence_reason)
        
        # Save to relational cache
        try:
            logger.info("[REPORT SERVICE] Caching completed community report to SQL DB")
            db_report = Report(
                source_id=source_id,
                report_data=json.dumps(report_dict)
            )
            db.add(db_report)
            db.commit()
        except Exception as e:
            logger.warning(f"[REPORT SERVICE] Failed to cache report to SQL DB: {str(e)}")

        logger.info("[REPORT SERVICE] Returning completed community report data to router")
        return report_dict

    def _empty_report(self, reason: str) -> Dict[str, Any]:
        return {
            "executive_summary": f"Could not generate report. Reason: {reason}",
            "most_discussed_topics": ["Unavailable"],
            "community_mood": "N/A",
            "active_contributors": ["N/A"],
            "engagement_highlights": ["N/A"],
            "interesting_trends": ["N/A"],
            "ai_recommendations": ["N/A"],
            "confidence": "Low",
            "confidence_reason": reason
        }

    def _parse_llm_json(self, raw_text: str) -> Dict[str, Any]:
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"\n```$", "", clean_text)
        clean_text = clean_text.strip()

        try:
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"[REPORT SERVICE] JSON loads error: {str(e)}. Raw response content: {raw_text}")
            return {
                "executive_summary": f"Failed to parse structured JSON from LLM. Raw output: {clean_text[:250]}",
                "most_discussed_topics": ["JSON Parsing Failed"],
                "community_mood": "Unknown",
                "active_contributors": [],
                "engagement_highlights": [],
                "interesting_trends": [],
                "ai_recommendations": []
            }

    def _normalize_report_schema(self, report_dict: Dict[str, Any], confidence: str, confidence_reason: str) -> Dict[str, Any]:
        # Handle cases where the JSON is wrapped in a top-level key like {"CommunityReport": {...}}
        if isinstance(report_dict, dict) and len(report_dict) == 1:
            first_val = list(report_dict.values())[0]
            if isinstance(first_val, dict):
                report_dict = first_val

        normalized = {}
        
        # Helper to extract a string
        def extract_str(keys, default):
            for k in keys:
                val = report_dict.get(k)
                if val:
                    return str(val)
            return default

        # Helper to extract a list
        def extract_list(keys, default_list):
            for k in keys:
                val = report_dict.get(k)
                if isinstance(val, list):
                    return [str(v) for v in val]
                elif isinstance(val, dict):
                    return [str(v) for v in val.values()]
                elif isinstance(val, str):
                    return [val]
            return default_list

        normalized["executive_summary"] = extract_str(["executive_summary", "summary", "Summary", "IncidentDetails"], "No summary generated.")
        normalized["community_mood"] = extract_str(["community_mood", "mood", "Mood", "sentiment"], "Sentiment is active and participating.")
        normalized["most_discussed_topics"] = extract_list(["most_discussed_topics", "topics", "Topics"], ["General Discussions"])
        normalized["active_contributors"] = extract_list(["active_contributors", "contributors", "Contributors", "Participants"], ["N/A"])
        normalized["engagement_highlights"] = extract_list(["engagement_highlights", "highlights", "Highlights", "Actions"], ["No highlights logged."])
        normalized["interesting_trends"] = extract_list(["interesting_trends", "trends", "Trends"], ["No significant trends observed."])
        normalized["ai_recommendations"] = extract_list(["ai_recommendations", "recommendations", "Recommendations", "Rules"], ["Maintain standard guidelines."])

        # Ensure lists are not empty
        for key in ["most_discussed_topics", "active_contributors", "engagement_highlights", "interesting_trends", "ai_recommendations"]:
            if not normalized[key]:
                normalized[key] = ["N/A"]

        normalized["confidence"] = confidence
        normalized["confidence_reason"] = confidence_reason
        return normalized
