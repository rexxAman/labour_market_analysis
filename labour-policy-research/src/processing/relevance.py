import json
import logging
from typing import Dict, Any
import ollama
from src.models.schemas import RelevanceResult

logger = logging.getLogger(__name__)

# List of domain keywords and terms that should never be considered labour policies
EXCLUDED_KEYWORDS = [
    "game", "warcraft", "addon", "plugin", "download", "torrent", 
    "movie", "anime", "youtube.com/answer", "baidu.com", "tripadvisor", 
    "hotel", "flight", "booking.com"
]

class RelevanceFilter:
    def __init__(self, model: str = "phi3:mini"):
        self.model = model
        
    def check_relevance(self, title: str, text_snippet: str, target_issue: str) -> Dict[str, Any]:
        """
        Uses heuristic screening + local Ollama model to classify if a document
        is a genuine government or international labour market policy.
        """
        # 1. Deterministic heuristic screening
        combined_lower = f"{title} {text_snippet}".lower()
        if any(keyword in combined_lower for keyword in EXCLUDED_KEYWORDS):
            return {"relevant": False}

        # 2. Local LLM Classification with strict criteria
        prompt = f"""
You are an expert labour market policy analyst.
Your task is to determine if the following document discusses an actual national government labour policy, law, decree, or official workforce initiative related to: "{target_issue}".

Rules:
- Non-policy articles, tech support, entertainment, video games, homework questions, or unrelated commercial pages MUST be marked relevant: false.
- Only actual government, ministry, ILO, or legitimate labour market policy reports should be marked relevant: true.

Title: {title}
Snippet: {text_snippet}

Respond ONLY with valid JSON:
If relevant: {{"relevant": true, "issue": "{target_issue}", "reason": "brief explanation"}}
If not relevant: {{"relevant": false}}
"""
        try:
            response = ollama.chat(
                model=self.model, 
                messages=[{"role": "user", "content": prompt}], 
                format="json", 
                options={"temperature": 0.0}
            )
            
            result_text = response['message']['content']
            result_json = json.loads(result_text)
            
            validated_result = RelevanceResult(**result_json)
            return validated_result.model_dump(exclude_none=True)
            
        except Exception as e:
            logger.error(f"Failed to check relevance for '{title}': {e}")
            return {"relevant": False}
