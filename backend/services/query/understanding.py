from typing import List, Dict, Any
from pydantic import BaseModel

class QueryAnalysis(BaseModel):
    original_query: str
    reformulated_query: str
    intent: str
    entities: List[str]
    domain: str

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            _nlp = None
    return _nlp


class QueryUnderstanding:
    def analyze(self, query: str) -> QueryAnalysis:
        nlp = get_nlp()
        entities = []
        domain = "general"
        intent = "information_seeking"
        
        if nlp:
            doc = nlp(query)
            entities = [ent.text for ent in doc.ents]
            
            # Simple keyword matching for domain/intent
            query_lower = query.lower()
            if any(w in query_lower for w in ["how", "why", "explain", "tutorial"]):
                intent = "explanation"
            elif any(w in query_lower for w in ["error", "fail", "crash", "bug", "issue"]):
                intent = "debugging"
                
            if any(w in query_lower for w in ["kubernetes", "k8s", "docker", "pod", "deployment"]):
                domain = "devops"
            elif any(w in query_lower for w in ["react", "nextjs", "javascript", "css", "html"]):
                domain = "frontend"
            elif any(w in query_lower for w in ["python", "fastapi", "django", "sql", "postgres"]):
                domain = "backend"

        # Reformulated query is just the query for basic implementation
        return QueryAnalysis(
            original_query=query,
            reformulated_query=query,
            intent=intent,
            entities=entities,
            domain=domain
        )
