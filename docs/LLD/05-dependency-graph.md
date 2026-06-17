# Dependency Graph Builder — Detailed Design

## Purpose

Identify the minimum knowledge frontier for a query — the smallest set of chunks that fully explains the target concept — and prune redundant ancestor chunks.

## Core Insight

Knowledge has structure. When explaining "self-attention", you don't need to first explain "machine learning" and "neural networks". Those are ancestors. The minimum frontier is one hop back from the target: {attention mechanism, self-attention}.

Sending ML → Neural Nets → Attention → Self-Attention wastes tokens. ContextOS strips everything above the frontier.

## Algorithm

```
Input: query, candidate_pool (list[Chunk])
Output: pruning_mask {chunk_id: bool}  (True = prune this chunk)

1. Extract target_concepts from query
   - spaCy NER → named entities
   - spaCy noun chunks → root lemmas
   - Deduplicate, lowercase

2. For each chunk in candidate_pool:
   - Extract chunk_concepts (same method)
   - Register chunk_id → concepts mapping

3. Build directed graph G (NetworkX DiGraph):
   - Nodes = all concepts across query + chunks
   - Edges: concept_A → concept_B if A appears as prerequisite of B
     (Heuristic: A precedes B in the same chunk, A is a hypernym of B via WordNet)

4. For each target concept t:
   - If t ∈ G:
     - direct_predecessors = set(G.predecessors(t))   → frontier
     - all_ancestors = nx.ancestors(G, t)
     - redundant = all_ancestors - direct_predecessors

5. Map redundant concepts back to chunk_ids:
   - If a chunk's primary concepts are ALL in redundant set → prune

6. Return pruning_mask
```

## Concept Extraction

```python
def extract_concepts(text: str, nlp) -> list[str]:
    doc = nlp(text[:10000])  # cap for speed
    entities = [ent.text.lower() for ent in doc.ents
                if ent.label_ in ("PERSON","ORG","PRODUCT","GPE","NORP","WORK_OF_ART","EVENT","LAW","LANGUAGE","FAC")]
    noun_heads = [chunk.root.lemma_.lower() for chunk in doc.noun_chunks]
    return list(set(entities + noun_heads))
```

## Edge Heuristics (V1 — Rule-Based)

Since building a full ontology is V2 work, V1 uses simpler heuristics:

1. **Sequential co-occurrence:** if concept A appears before concept B in the same chunk more than 3 times → A → B edge
2. **Section headers:** if chunk has a heading "Introduction to X" before a chunk about "X details" → former is ancestor
3. **Explicit markers:** phrases like "building on X", "given X", "assuming knowledge of X" → dependency edge

## Failure Modes

- **Empty graph:** if no concepts extracted, pruning_mask = all False (keep everything)
- **Disconnected graph:** frontier detection per connected component
- **All concepts in frontier:** no pruning — all chunks kept (safe default)

## Performance

- spaCy `en_core_web_sm` NER on 200 × 512-token chunks: ~3–5s on CPU
- NetworkX graph operations on ~500 nodes: < 100ms
- Total engine time: ~3–5s (runs in parallel with ROI + contradiction)

## V2 — Semantic Dependency

Replace heuristic edges with semantic entailment:
- For concepts A and B, if A → B edge exists when NLI(A, B) = entailment and NLI(B, A) ≠ entailment
- This gives true knowledge dependency structure

## Output

```python
@dataclass
class DependencyResult:
    pruning_mask: dict[UUID, bool]
    frontier_concepts: set[str]
    pruned_concept_count: int
    pruned_chunk_count: int
    attribution: DependencyAttribution
```
