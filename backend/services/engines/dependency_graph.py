import networkx as nx
from typing import List, Dict, Set
from uuid import UUID
from services.query.understanding import get_nlp
from models.schemas.chunk import Chunk

class DependencyGraph:
    def __init__(self, graph: nx.DiGraph, frontier: Set[str], pruning_mask: Dict[UUID, bool],
                 chain_chunk_ids: Set[UUID] = None):
        self.graph = graph
        self.frontier = frontier
        self.pruning_mask = pruning_mask
        # Chunks that lie on the dependency chain connecting the query to the answer
        # (e.g. multi-hop A→B→C). Fusion uses this to keep the chain together.
        self.chain_chunk_ids = chain_chunk_ids or set()

class DependencyGraphBuilder:
    def __init__(self):
        # reuse spaCy loader
        pass

    async def build(self, query: str, chunks: List[Chunk]) -> DependencyGraph:
        target_concepts = self._extract_concepts(query)
        graph = nx.DiGraph()

        # Extract each chunk's concepts once (spaCy is the hot path), build the graph.
        chunk_concepts: Dict[UUID, Set[str]] = {}
        for chunk in chunks:
            concepts = self._extract_concepts(chunk.content)
            chunk_concepts[chunk.id] = set(concepts)
            for concept in concepts:
                graph.add_node(concept)
            self._add_dependency_edges(graph, concepts)

        # The "relevant" concept set is everything transitively connected to the
        # query's target concepts — so a 2-hop chain (person→company→city) is kept
        # whole instead of pruning the far hop that doesn't mention the query entity.
        relevant = self._reachable_concepts(graph, target_concepts)
        frontier = relevant

        pruning_mask: Dict[UUID, bool] = {}
        chain_chunk_ids: Set[UUID] = set()
        for chunk in chunks:
            cc = chunk_concepts[chunk.id]
            if not cc:
                pruning_mask[chunk.id] = False
                continue
            # If we couldn't anchor any query concept in the graph, don't prune
            # anything (fail open) — otherwise prune chunks disjoint from the chain.
            on_chain = bool(relevant) and not cc.isdisjoint(relevant)
            pruning_mask[chunk.id] = bool(relevant) and not on_chain
            if on_chain:
                chain_chunk_ids.add(chunk.id)

        return DependencyGraph(graph=graph, frontier=frontier, pruning_mask=pruning_mask,
                               chain_chunk_ids=chain_chunk_ids)

    def _reachable_concepts(self, graph: nx.DiGraph, targets: List[str]) -> Set[str]:
        """All concepts in the connected component(s) of the target concepts."""
        if graph.number_of_nodes() == 0:
            return set()
        undirected = graph.to_undirected()
        reachable: Set[str] = set()
        for t in targets:
            if t in undirected and t not in reachable:
                reachable |= nx.node_connected_component(undirected, t)
        return reachable

    def _extract_concepts(self, text: str) -> List[str]:
        nlp = get_nlp()
        if not nlp:
            return []
        doc = nlp(text[:10000])  # Cap character limit
        return [ent.text.lower() for ent in doc.ents] + \
               [chunk.root.lemma_.lower() for chunk in doc.noun_chunks]

    def _add_dependency_edges(self, graph: nx.DiGraph, concepts: List[str]):
        # Add a directed edge from earlier concepts to later concepts in a sequence
        for i in range(len(concepts) - 1):
            if concepts[i] != concepts[i+1]:
                graph.add_edge(concepts[i], concepts[i+1])
