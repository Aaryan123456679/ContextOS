# Engines Service
from services.engines.roi_engine import ROIEngine
from services.engines.dependency_graph import DependencyGraphBuilder
from services.engines.contradiction import ContradictionDetector
from services.engines.token_budget import TokenBudgetAllocator
from services.engines.fusion import FusionEngine
from services.engines.compression import RecoverableCompressor
from services.engines.model_adapter import ModelContextAdapter
from services.engines.prefetcher import SpeculativePrefetcher
