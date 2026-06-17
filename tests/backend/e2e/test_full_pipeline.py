"""E2E tests for the full pipeline — requires all external services + LLM API key.

Mark with @pytest.mark.e2e to allow selective skipping in CI.
Run with: pytest tests/backend/e2e/ -v -m e2e
"""
import pytest
import httpx
import os
from pathlib import Path

BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("TEST_OPENAI_KEY")  # required for e2e tests
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"  # seeded test user


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=60.0)


@pytest.fixture
def sample_txt(tmp_path):
    """Create a small test text file."""
    doc = tmp_path / "test_doc.txt"
    doc.write_text("""
ContextOS is a context intelligence system.
It optimizes LLM context windows by scoring chunks using cross-encoder reranking.
The ROI engine computes expected answer quality gain per token.
Recovery pointers allow compressing context while preserving expandability.
Token budget allocation uses a greedy knapsack algorithm.
    """.strip())
    return doc


@pytest.mark.e2e
@pytest.mark.skipif(not TEST_API_KEY, reason="TEST_OPENAI_KEY not set")
class TestUploadAndChat:
    def test_upload_returns_chunk_count(self, client, sample_txt):
        """Upload endpoint processes file and returns chunk count > 0."""
        with open(sample_txt, "rb") as f:
            resp = client.post("/api/upload", files={"file": f}, data={"user_id": TEST_USER_ID})
        assert resp.status_code == 200
        body = resp.json()
        assert "document_id" in body
        assert body["chunk_count"] > 0

    def test_chat_returns_metrics(self, client, sample_txt):
        """Chat endpoint returns optimization metrics."""
        # Upload first
        with open(sample_txt, "rb") as f:
            upload = client.post("/api/upload", files={"file": f}, data={"user_id": TEST_USER_ID})
        doc_id = upload.json()["document_id"]

        # Chat
        resp = client.post("/api/chat", json={
            "message": "What is the ROI engine?",
            "document_ids": [doc_id],
            "model": "gpt-4o-mini",
            "optimization_enabled": True,
            "user_api_key": TEST_API_KEY,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "content" in body
        assert "metrics" in body
        metrics = body["metrics"]
        assert "original_tokens" in metrics
        assert "optimized_tokens" in metrics
        assert metrics["optimized_tokens"] <= metrics["original_tokens"]

    def test_chat_without_optimization(self, client, sample_txt):
        """Chat with optimization_enabled=False skips optimization pipeline."""
        with open(sample_txt, "rb") as f:
            upload = client.post("/api/upload", files={"file": f}, data={"user_id": TEST_USER_ID})
        doc_id = upload.json()["document_id"]

        resp = client.post("/api/chat", json={
            "message": "What is ContextOS?",
            "document_ids": [doc_id],
            "model": "gpt-4o-mini",
            "optimization_enabled": False,
            "user_api_key": TEST_API_KEY,
        })
        assert resp.status_code == 200
        # Optimization metrics should be None or absent
        body = resp.json()
        assert body.get("metrics") is None or body.get("optimization_run_id") is None


@pytest.mark.e2e
class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
