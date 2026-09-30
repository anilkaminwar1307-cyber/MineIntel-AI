"""
NumberSafe 2.0 — Deterministic Calculation Layer
All quantitative mining operations route through this package.
LLMs are never asked to compute, invent, or estimate numerical values.
"""
from .calculation_engine import CalculationEngine, CalculationResult
from .metric_semantics import MetricRegistry, MetricDefinition

__all__ = ["CalculationEngine", "CalculationResult", "MetricRegistry", "MetricDefinition"]
