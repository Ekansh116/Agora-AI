import json
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.providers.base_llm import BaseLLM
from app.services.retriever_service import RetrieverService

class RAGService:
    def __init__(self, llm_provider: BaseLLM, retriever_service: RetrieverService):
        self.llm_provider = llm_provider
        self.retriever_service = retriever_service

    def answer_query(self, query: str, db: Session, source_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Processes a user question, runs embedding search, compiles chronological context, 
        queries Qwen via Ollama, and formats the output into structured reasoning.
        """
        # 1. Retrieve matching threads
        threads = self.retriever_service.retrieve_relevant_threads(query, db, source_id, limit=3)
        
        if not threads:
            return {
                "observation": "No relevant community conversation threads were found matching your query.",
                "inference": "I cannot draw conclusions without supporting data.",
                "recommendation": "Try uploading chat logs containing discussions on this topic.",
                "evidence": [],
                "confidence": "Low",
                "confidence_reason": "No matches returned from the vector store."
            }

        # 2. Estimate retrieval confidence from hybrid evidence coverage.
        # Raw vector and BM25 scores are not comparable, so confidence is based
        # on how many independent retrieval signals support the returned threads.
        num_threads = len(threads)
        hybrid_threads = sum(
            1 for thread in threads
            if len(thread.get("retrieval_methods", [])) == 2
        )
        lexical_threads = sum(
            1 for thread in threads
            if "lexical" in thread.get("retrieval_methods", [])
        )

        if hybrid_threads >= 2:
            confidence = "High"
            confidence_reason = (
                f"{hybrid_threads} retrieved conversations were supported by both "
                "semantic and lexical search."
            )
        elif num_threads >= 2 and lexical_threads >= 1:
            confidence = "Medium"
            confidence_reason = (
                f"Retrieved {num_threads} conversations with agreement between "
                "semantic and lexical retrieval signals on part of the result set."
            )
        else:
            confidence = "Low"
            confidence_reason = (
                "The result set has limited agreement across independent retrieval signals."
            )

        # 3. Format Context and Evidence
        context_blocks = []
        evidence_citations = []
        
        for idx, thread in enumerate(threads):
            header = f"--- Conversation Thread {idx+1} (ID: {thread['conversation_id']}, Date: {thread['start_time'].strftime('%Y-%m-%d')}) ---"
            msg_lines = []
            for msg in thread["messages"]:
                ts_str = msg["timestamp"].strftime("%H:%M")
                msg_lines.append(f"{msg['sender']} ({ts_str}): {msg['content']}")
                
                evidence_citations.append({
                    "timestamp": msg["timestamp"].isoformat(),
                    "sender": msg["sender"],
                    "content": msg["content"]
                })
            context_blocks.append(header + "\n" + "\n".join(msg_lines))
            
        context_str = "\n\n".join(context_blocks)

        # 4. Construct Prompt
        system_prompt = (
            "You are an expert AI Community Analyst. Your job is to answer user questions based strictly on the provided conversation fragments.\n"
            "You must follow a strict structured reasoning format. You must respond ONLY with a raw JSON object (do not wrap in markdown ```json or backticks) containing the following structure:\n"
            "{\n"
            '  "observation": "Factual observations directly visible in the context. List specific messages/dates.",\n'
            '  "inference": "Logical deductions based on the observations.",\n'
            '  "recommendation": "Actionable advice for the community manager based on the analysis."\n'
            "}\n"
            "If the answer cannot be found in the context, set observation to 'No relevant conversation data found to answer this query.', set inference and recommendation to '', and explain this in your response.\n"
            "Do not fabricate facts or speculate outside the provided chats."
        )

        user_prompt = (
            f"Here is the retrieved community context:\n\n{context_str}\n\n"
            f"Question: {query}\n\n"
            f"Respond ONLY with the JSON structure containing 'observation', 'inference', and 'recommendation'."
        )

        # 5. Query LLM & Parse Output
        try:
            raw_response = self.llm_provider.generate(user_prompt, system_prompt)
            parsed_response = self._parse_llm_json(raw_response)
        except Exception as e:
            parsed_response = {
                "observation": f"Error interacting with the AI model: {str(e)}",
                "inference": "Verify that your Ollama server is running and accessible.",
                "recommendation": "Check the OLLAMA_URL in the .env file."
            }

        return {
            "observation": parsed_response.get("observation", ""),
            "inference": parsed_response.get("inference", ""),
            "recommendation": parsed_response.get("recommendation", ""),
            "evidence": evidence_citations[:20],  # Return up to 20 messages for visual citation
            "confidence": confidence,
            "confidence_reason": confidence_reason
        }

    def _parse_llm_json(self, raw_text: str) -> Dict[str, str]:
        # Strip markdown markers if present
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\n", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"\n```$", "", clean_text)
        clean_text = clean_text.strip()

        try:
            return json.loads(clean_text)
        except Exception:
            # Fallback regex parsing if JSON parser fails
            obs_match = re.search(r'"observation"\s*:\s*"(.*?)"', clean_text, re.DOTALL)
            inf_match = re.search(r'"inference"\s*:\s*"(.*?)"', clean_text, re.DOTALL)
            rec_match = re.search(r'"recommendation"\s*:\s*"(.*?)"', clean_text, re.DOTALL)
            
            return {
                "observation": obs_match.group(1).replace('\\"', '"') if obs_match else clean_text,
                "inference": inf_match.group(1).replace('\\"', '"') if inf_match else "Inference extraction failed.",
                "recommendation": rec_match.group(1).replace('\\"', '"') if rec_match else "Recommendation extraction failed."
            }
