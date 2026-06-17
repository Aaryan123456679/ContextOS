"""Local corpus store: raw text files + a JSONL manifest. Reproducible & resumable.

Nothing is uploaded anywhere — the corpus lives entirely under data/corpus/.
"""
import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterator, Optional

import tiktoken

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

_enc = tiktoken.get_encoding("cl100k_base")


def n_tokens(text: str) -> int:
    return len(_enc.encode(text))


@dataclass
class DocRecord:
    source_id: str          # stable id, e.g. "arxiv:2310.06825"
    domain: str             # technical_paper | framework_docs | wikipedia | noise_* ...
    source_type: str        # arxiv | docs | wikipedia | noise
    title: str
    url: str
    tokens: int
    tier: str               # small | medium | large
    sha256: str
    fetched_at: float


class CorpusStore:
    def __init__(self):
        self.raw_dir = config.CORPUS_RAW
        self.manifest_path = config.CORPUS_MANIFEST
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, DocRecord] = {}
        self._shas: set = set()
        self._load()

    def _load(self):
        if self.manifest_path.exists():
            for line in self.manifest_path.open():
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                rec = DocRecord(**d)
                self._index[rec.source_id] = rec
                self._shas.add(rec.sha256)

    def has(self, source_id: str) -> bool:
        return source_id in self._index

    def __len__(self):
        return len(self._index)

    def _safe_name(self, source_id: str) -> str:
        return source_id.replace("/", "_").replace(":", "_")

    def add(self, source_id: str, domain: str, source_type: str, title: str,
            url: str, text: str, min_tokens: int = 200) -> Optional[DocRecord]:
        """Store a document. Skips duplicates (by id or content hash) and tiny docs."""
        if source_id in self._index:
            return self._index[source_id]
        text = (text or "").strip()
        toks = n_tokens(text)
        if toks < min_tokens:
            return None
        sha = hashlib.sha256(text.encode()).hexdigest()
        if sha in self._shas:
            return None  # exact-duplicate content
        (self.raw_dir / f"{self._safe_name(source_id)}.txt").write_text(text)
        rec = DocRecord(
            source_id=source_id, domain=domain, source_type=source_type, title=title,
            url=url, tokens=toks, tier=config.size_tier(toks), sha256=sha, fetched_at=time.time(),
        )
        with self.manifest_path.open("a") as f:
            f.write(json.dumps(asdict(rec)) + "\n")
        self._index[source_id] = rec
        self._shas.add(sha)
        return rec

    def get_text(self, source_id: str) -> str:
        return (self.raw_dir / f"{self._safe_name(source_id)}.txt").read_text()

    def records(self) -> Iterator[DocRecord]:
        return iter(self._index.values())

    def stats(self) -> dict:
        by_domain, by_tier, by_type = {}, {}, {}
        for r in self._index.values():
            by_domain[r.domain] = by_domain.get(r.domain, 0) + 1
            by_tier[r.tier] = by_tier.get(r.tier, 0) + 1
            by_type[r.source_type] = by_type.get(r.source_type, 0) + 1
        return {"total": len(self._index), "by_domain": by_domain,
                "by_tier": by_tier, "by_type": by_type}
