import asyncio
import uuid
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from models.schemas.optimize import OptimizeRequest, OptimizeResponse
from models.schemas.chat import OptimizationMetrics, EngineBreakdown, EngineContribution
from services.query.understanding import QueryUnderstanding
from services.retrieval.hybrid import HybridRetriever
from services.retrieval.semantic import SemanticRetriever
from services.retrieval.keyword import KeywordRetriever
from services.engines.roi_engine import ROIEngine
from services.engines.dependency_graph import DependencyGraphBuilder
from services.engines.contradiction import ContradictionDetector
from services.engines.fusion import FusionEngine
from services.engines.token_budget import TokenBudgetAllocator
from services.engines.learned_select import LearnedSelector
from services.engines.compression import RecoverableCompressor
from services.ingestion.embedder import Embedder
from core.config import settings

logger = logging.getLogger("contextos")

router = APIRouter()

query_understander = QueryUnderstanding()
semantic_retriever = SemanticRetriever()
keyword_retriever = KeywordRetriever()
hybrid_retriever = HybridRetriever(semantic_retriever, keyword_retriever)
roi_engine = ROIEngine()
dep_graph_builder = DependencyGraphBuilder()
contradiction_detector = ContradictionDetector()
fusion_engine = FusionEngine()
token_allocator = TokenBudgetAllocator()
learned_selector = LearnedSelector()
compressor = RecoverableCompressor()   # no LLM gateway — uses fallback compression output
embedder = Embedder()


async def _safe(coro, name: str):
    try:
        return await coro
    except Exception as e:
        logger.error("%s failed: %s", name, e)
        return None


async def _embed_query(query: str) -> list[float]:
    try:
        return (await embedder.embed_chunks([query]))[0]
    except Exception:
        return [0.0] * 1536


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize(req: OptimizeRequest, db: AsyncSession = Depends(get_db)):
    """Standalone optimization: retrieval → engines → fusion → compression, no LLM output."""
    query = req.query

    # 1. Query understanding
    analysis = query_understander.analyze(query)

    # 2. Embed + retrieve
    query_vector = await _embed_query(analysis.reformulated_query)
    candidate_pool = await hybrid_retriever.retrieve(
        query=analysis.reformulated_query,
        query_vector=query_vector,
        document_ids=req.document_ids,
        db=db,
    )
    if not candidate_pool:
        candidate_pool = []

    # 3. ROI engine (sync)
    try:
        roi_tuples = roi_engine.score(query, candidate_pool)
        roi_scores = [score for _, score in roi_tuples]
        roi_enabled = True
    except Exception as e:
        logger.error("ROI Engine failed: %s", e)
        roi_scores = [0.5] * len(candidate_pool)
        roi_enabled = False

    # 4. Async engines in parallel
    dep_result, contra_result = await asyncio.gather(
        _safe(dep_graph_builder.build(query, candidate_pool), "Dependency Graph"),
        _safe(contradiction_detector.detect(candidate_pool), "Contradiction Detector"),
    )

    dep_mask = dep_result.pruning_mask if dep_result is not None else {}
    dep_boost = dep_result.chain_chunk_ids if dep_result is not None else set()
    contra_flags = contra_result if contra_result is not None else []

    # 5. Fusion
    scored_chunks = fusion_engine.fuse(candidate_pool, roi_scores, dep_mask, contra_flags, dep_boost)

    # 6. Selection — learned all-signal policy or density allocator (learned self-falls
    #    back to density on error).
    if settings.SELECTION_MODE == "learned":
        selected = learned_selector.select(
            scored_chunks, query, req.token_budget,
            chain_ids=dep_boost, concepts_fn=dep_graph_builder._extract_concepts)
    else:
        selected = token_allocator.allocate(scored_chunks, req.token_budget).selected
    allocated_chunks = [sc.chunk for sc in selected]

    # 7. Compress (no LLM gateway → fallback output with placeholder pointers)
    comp_result = await compressor.compress(allocated_chunks, query, api_key=None)

    # 8. Metrics
    orig_tokens = comp_result.original_token_count or 1
    comp_tokens = comp_result.compressed_token_count
    token_reduction = 1.0 - (comp_tokens / orig_tokens) if orig_tokens > 0 else 0.0

    dep_pruned = sum(1 for v in dep_mask.values() if v)
    dep_tokens_removed = sum(
        c.token_count for c in candidate_pool
        if dep_mask.get(c.id, False)
    )

    breakdown = EngineBreakdown(
        roi_engine=EngineContribution(tokens_removed=0, quality_delta=0.0, enabled=roi_enabled),
        dependency_graph=EngineContribution(
            tokens_removed=dep_tokens_removed,
            quality_delta=0.0,
            enabled=dep_result is not None,
        ),
        compression=EngineContribution(
            tokens_removed=orig_tokens - comp_tokens,
            quality_delta=0.0,
            enabled=True,
        ),
        contradiction=EngineContribution(
            tokens_removed=0,
            quality_delta=0.0,
            enabled=contra_result is not None,
        ),
    )

    metrics = OptimizationMetrics(
        original_tokens=orig_tokens,
        optimized_tokens=comp_tokens,
        token_reduction_pct=round(token_reduction * 100, 2),
        cost_original=0.0,   # no model call; caller computes cost if needed
        cost_optimized=0.0,
        bert_score=0.0,      # no LLM output to score against
        quality_score=0.0,
        engine_breakdown=breakdown,
    )

    return OptimizeResponse(
        optimized_text=comp_result.compressed_text,
        optimization_run_id=uuid.uuid4(),
        metrics=metrics,
        chunks=allocation.selected,
    )
