class QueryClassifier:
    def classify(self, query: str) -> str:
        # Simple intent classifier
        q = query.lower()
        if "code" in q or "function" in q or "error" in q or "bug" in q:
            return "code_query"
        return "text_query"
