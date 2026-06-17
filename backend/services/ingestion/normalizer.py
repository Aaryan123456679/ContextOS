import re
from typing import Dict, Any

class Normalizer:
    def normalize_text(self, text: str) -> str:
        # Basic cleanup: remove extra newlines/spaces
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()

    def normalize_metadata(self, filename: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
        meta = {
            "source": filename,
            "file_type": filename.split(".")[-1].lower() if "." in filename else "unknown"
        }
        if extra:
            meta.update(extra)
        return meta
