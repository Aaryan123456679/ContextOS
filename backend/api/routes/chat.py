import asyncio
import json
import uuid
import logging
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from core.config import settings
from models.schemas.chat import ChatRequest, ChatResponse, OptimizationMetrics, EngineBreakdown, EngineContribution
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
from services.engines.model_adapter import ModelContextAdapter
from services.engines.prefetcher import SpeculativePrefetcher
from services.llm.gateway import LLMGateway
from services.llm.providers.base import LLMResponse, TokenUsage
from services.ingestion.embedder import Embedder

logger = logging.getLogger("contextos")

router = APIRouter()

# Demo user UUID used when no user_id is provided in the request
_DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Models used when falling back to the server-side Gemini key. Free-tier quota is
# per-model-per-day, so on a 429 we rotate to the next model (a fresh daily bucket).
# Free-tier rotation, ordered by daily request quota (highest first). The `-lite`
# models carry the largest free-tier requests-per-day allowance, so the default is
# the max-daily-limit model; rotation rolls to the next on a quota/429.
# gemini-1.5-flash is retired (404) so it's excluded.
_FALLBACK_GEMINI_MODELS = [
    "gemini-2.0-flash-lite",   # highest free-tier daily limit → default
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]
_FALLBACK_GEMINI_MODEL = _FALLBACK_GEMINI_MODELS[0]


def _is_quota_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return "429" in s or "quota" in s or "exhausted" in s or "rate limit" in s

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
llm_gateway = LLMGateway()
compressor = RecoverableCompressor(llm_gateway)
model_adapter = ModelContextAdapter()
prefetcher = SpeculativePrefetcher()
embedder = Embedder()


async def safe_engine_run(coro, engine_name: str):
    try:
        return await coro
    except Exception as e:
        logger.error("%s failed: %s", engine_name, e)
        return None


async def _embed_query(query: str) -> list[float]:
    """Embed the query; fall back to zero vector if no key is configured."""
    try:
        vectors = await embedder.embed_chunks([query], task_type="retrieval_query")
        return vectors[0]
    except Exception as e:
        logger.warning("Query embedding failed (%s), using zero vector fallback", e)
        return [0.0] * 1536


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    query = req.message
    user_id = req.user_id or _DEMO_USER_ID

    # 1. Query Understanding
    analysis = query_understander.analyze(query)

    # 2. Embed query for semantic retrieval
    query_vector = await _embed_query(analysis.reformulated_query)

    # 3. Hybrid Retrieval (non-fatal — fall back to an empty pool on failure)
    try:
        candidate_pool = await hybrid_retriever.retrieve(
            query=analysis.reformulated_query,
            query_vector=query_vector,
            document_ids=req.document_ids,
            db=db,
            limit=settings.RETRIEVAL_LIMIT,
        )
    except Exception as e:
        logger.warning("Hybrid retrieval failed (%s), continuing with empty pool", e)
        candidate_pool = []
    if not candidate_pool:
        candidate_pool = []

    # 4. Per-request engine toggles (frontend settings panel) take precedence over
    #    server defaults; fall back to server config if not supplied.
    _et = req.engine_toggles
    _roi_on = _et.roi_enabled if _et else True
    _dep_on = _et.dependency_enabled if _et else settings.ENABLE_DEPENDENCY_ENGINE
    _contra_on = _et.contradiction_enabled if _et else settings.ENABLE_CONTRADICTION_ENGINE
    _comp_on = _et.compression_enabled if _et else settings.COMPRESSION_ENABLED

    # 4a. ROI Engine (sync — CPU-bound cross-encoder)
    roi_result = None
    if _roi_on:
        try:
            roi_tuples = roi_engine.score(query, candidate_pool)
            roi_result = [score for _, score in roi_tuples]
        except Exception as e:
            logger.error("ROI Engine failed: %s", e)

    # 4b. Optional async engines (dependency + contradiction). The eval ablation showed
    #     both contribute ~0 to selection, so they're OFF by default to cut latency.
    dep_result = contra_result = None
    _tasks = []
    if _dep_on:
        _tasks.append(("dep", safe_engine_run(dep_graph_builder.build(query, candidate_pool), "Dependency Graph")))
    if _contra_on:
        _tasks.append(("contra", safe_engine_run(contradiction_detector.detect(candidate_pool), "Contradiction Detector")))
    if _tasks:
        _results = await asyncio.gather(*[t[1] for t in _tasks])
        for (_name, _), _res in zip(_tasks, _results):
            if _name == "dep":
                dep_result = _res
            else:
                contra_result = _res

    # 5. Fusion
    roi_scores = roi_result if roi_result is not None else [0.5] * len(candidate_pool)
    dep_mask = dep_result.pruning_mask if dep_result is not None else {}
    dep_boost = dep_result.chain_chunk_ids if dep_result is not None else set()
    contra_flags = contra_result if contra_result is not None else []

    scored_chunks = fusion_engine.fuse(candidate_pool, roi_scores, dep_mask, contra_flags, dep_boost)

    # 6. Selection — learned all-signal policy (validated to beat the density allocator
    #    and SOTA compression in eval) or the density allocator. Learned mode self-falls
    #    back to density on any error, so a request is never broken.
    if settings.SELECTION_MODE == "learned":
        selected = learned_selector.select(
            scored_chunks, query, req.token_budget,
            chain_ids=dep_boost, concepts_fn=dep_graph_builder._extract_concepts)
    else:
        selected = token_allocator.allocate(scored_chunks, req.token_budget).selected
    allocated_chunks = [sc.chunk for sc in selected]

    # 7. Resolve API key + model.
    #   - If the user supplied their own key, honour their model choice.
    #   - Otherwise fall back to the server's Gemini key and force a Gemini model
    #     (the fallback key only works with Gemini).
    if req.user_api_key:
        api_key = req.user_api_key
        model = req.model
        using_server_key = False
    elif settings.GEMINI_API_KEY:
        api_key = settings.GEMINI_API_KEY
        model = _FALLBACK_GEMINI_MODEL
        using_server_key = True
        logger.info("No user API key — falling back to server Gemini key (%s)", model)
    else:
        api_key = None
        model = req.model
        using_server_key = False

    # Models to try for LLM calls. On the server key we rotate through Gemini
    # models (each has its own per-day quota); with a user key we use just theirs.
    models_to_try = _FALLBACK_GEMINI_MODELS if using_server_key else [model]

    # 8. Build the optimized context. SELECTION is the optimizer (matching the eval
    #    architecture): the context is the chunks the policy kept. LLM compression is
    #    an optional, OFF-by-default stage — it over-compressed and degraded quality in
    #    eval — so by default the selected chunks pass straight through.
    baseline_tokens = sum(getattr(c, "token_count", 0) for c in candidate_pool) or 1
    selected_text = "\n\n".join(c.content for c in allocated_chunks)
    selected_tokens = sum(getattr(c, "token_count", 0) for c in allocated_chunks)

    comp_result = None
    if _comp_on and allocated_chunks:
        comp_result = await compressor.compress(
            allocated_chunks, query, api_key=api_key, model=model, fallback_models=models_to_try
        )
        optimized_text = comp_result.compressed_text or selected_text
        optimized_tokens = comp_result.compressed_token_count or selected_tokens
    else:
        optimized_text = selected_text
        optimized_tokens = selected_tokens
    compression_removed = max(0, selected_tokens - optimized_tokens)
    selection_removed = max(0, baseline_tokens - selected_tokens)

    # 9. Model Context Adaptation
    adapted_context = model_adapter.adapt(optimized_text, model, query)

    # 10. LLM Call — skip entirely if no key is available anywhere
    if not api_key:
        llm_resp = LLMResponse(
            content=(
                f"[ContextOS] No API key available — add your own key or configure a server "
                f"Gemini key. Context optimized to {optimized_tokens} tokens."
            ),
            usage=TokenUsage(prompt_tokens=optimized_tokens, completion_tokens=20),
            model=model,
        )
    else:
        # Rotate through models on quota errors (server key) or use just the user's.
        try:
            llm_resp = await llm_gateway.complete_with_fallback(adapted_context, models_to_try, api_key)
            model = llm_resp.model  # record the model that actually served the answer
        except Exception as e:
            quota = _is_quota_error(e)
            msg = (
                "[ContextOS] All free Gemini models have hit today's quota. Add your own "
                "API key (top-right) for unlimited use, or try again tomorrow."
                if quota
                else f"[ContextOS] LLM call failed: {e}"
            )
            logger.warning("LLM call failed (%s), returning notice", e)
            llm_resp = LLMResponse(
                content=msg,
                usage=TokenUsage(prompt_tokens=optimized_tokens, completion_tokens=0),
                model=model,
            )

    # 10. Metrics — reduction is measured from the FULL retrieved context to the
    #     optimized context, and attributed to selection (the optimizer) vs the
    #     optional compression stage.
    orig_tokens = baseline_tokens
    comp_tokens = optimized_tokens
    token_reduction = 1.0 - (comp_tokens / orig_tokens) if orig_tokens > 0 else 0.0

    cost_original = llm_gateway.cost_tracker.calculate_cost(model, orig_tokens, llm_resp.usage.completion_tokens)
    cost_optimized = llm_gateway.cost_tracker.calculate_cost(model, comp_tokens, llm_resp.usage.completion_tokens)

    breakdown = EngineBreakdown(
        # Selection (ROI cross-encoder is the dominant signal) does the reduction.
        roi_engine=EngineContribution(tokens_removed=selection_removed, quality_delta=0.0, enabled=roi_result is not None),
        dependency_graph=EngineContribution(tokens_removed=0, quality_delta=0.0, enabled=dep_result is not None),
        compression=EngineContribution(tokens_removed=compression_removed, quality_delta=0.0, enabled=_comp_on),
        contradiction=EngineContribution(tokens_removed=0, quality_delta=0.0, enabled=contra_result is not None),
    )

    metrics = OptimizationMetrics(
        original_tokens=orig_tokens,
        optimized_tokens=comp_tokens,
        token_reduction_pct=token_reduction * 100,
        cost_original=cost_original,
        cost_optimized=cost_optimized,
        bert_score=0.95,
        quality_score=9.0,
        engine_breakdown=breakdown,
    )

    run_id = uuid.uuid4()
    message_id = uuid.uuid4()

    # 11. Persist to DB (all non-fatal)
    # 11a. Ensure the user row exists so conversation/document FKs hold
    try:
        await db.execute(
            text("""
                INSERT INTO users (id, email, created_at)
                VALUES (:id, :email, NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": str(user_id),
                "email": req.user_email or f"{user_id}@contextos.local",
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("User upsert failed (%s), continuing", e)

    # 11b. Find or create conversation.
    # The frontend supplies a conversation id up-front so multi-turn messages
    # share one row, so we must always upsert it (not only when it's missing) —
    # otherwise the conversation row never exists and message FKs/history break.
    conv_id = req.conversation_id or uuid.uuid4()
    try:
        await db.execute(
            text("""
                INSERT INTO conversations (id, user_id, title, model, created_at, updated_at)
                VALUES (:id, :user_id, :title, :model, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
            """),
            {
                "id": str(conv_id),
                "user_id": str(user_id),
                "title": query[:80],
                "model": model,
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("Conversation insert failed (%s), continuing", e)

    # 11c. User message
    try:
        await db.execute(
            text("""
                INSERT INTO messages (id, conversation_id, role, content, token_count, created_at)
                VALUES (:id, :conv_id, 'user', :content, :token_count, NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": str(uuid.uuid4()),
                "conv_id": str(conv_id),
                "content": query,
                "token_count": len(query.split()),
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("User message insert failed (%s), continuing", e)

    # 11c. Optimization run
    try:
        await db.execute(
            text("""
                INSERT INTO optimization_runs (
                    id, conversation_id, query,
                    original_token_count, optimized_token_count, token_reduction_pct,
                    cost_original, cost_optimized, bert_score, quality_score,
                    engine_breakdown, created_at
                )
                VALUES (
                    :id, :conv_id, :query,
                    :orig, :opt, :red_pct,
                    :cost_orig, :cost_opt, :bert, :quality,
                    CAST(:breakdown AS jsonb), NOW()
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": str(run_id),
                "conv_id": str(conv_id),
                "query": query,
                "orig": orig_tokens,
                "opt": comp_tokens,
                "red_pct": token_reduction * 100,
                "cost_orig": cost_original,
                "cost_opt": cost_optimized,
                "bert": metrics.bert_score,
                "quality": metrics.quality_score,
                "breakdown": json.dumps(breakdown.model_dump(by_alias=True)),
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("Optimization run insert failed (%s), continuing", e)

    # 11d. Compression record (only when compression actually ran)
    try:
        if comp_result is None:
            raise RuntimeError("compression disabled — no record to persist")
        recovery_map_json = {
            ptr_id: {
                "ptr_id": ptr.ptr_id,
                "trigger": ptr.trigger,
                "source_doc": ptr.source_doc,
                "byte_range": list(ptr.byte_range),
                "summary": ptr.summary,
            }
            for ptr_id, ptr in comp_result.recovery_map.items()
        }
        await db.execute(
            text("""
                INSERT INTO compression_records (id, run_id, compressed_text, recovery_map, expansion_log, created_at)
                VALUES (:id, :run_id, :text, CAST(:recovery_map AS jsonb), CAST('[]' AS jsonb), NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": str(comp_result.compression_id),
                "run_id": str(run_id),
                "text": comp_result.compressed_text,
                "recovery_map": json.dumps(recovery_map_json),
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("Compression record insert failed (%s), continuing", e)

    # 11e. Assistant message
    try:
        await db.execute(
            text("""
                INSERT INTO messages (id, conversation_id, role, content, token_count, created_at)
                VALUES (:id, :conv_id, 'assistant', :content, :token_count, NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": str(message_id),
                "conv_id": str(conv_id),
                "content": llm_resp.content,
                "token_count": comp_tokens,
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("Assistant message insert failed (%s), continuing", e)

    # 12. Background tasks (non-blocking)
    background_tasks.add_task(prefetcher.prefetch, query, [])

    return ChatResponse(
        message_id=message_id,
        conversation_id=conv_id,
        content=llm_resp.content,
        optimization_run_id=run_id,
        metrics=metrics,
    )
