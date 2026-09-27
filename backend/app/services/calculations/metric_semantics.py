"""
NumberSafe 2.0 — Metric Semantics Registry
Defines what every metric code MEANS:
  - canonical unit
  - allowed aggregation operations
  - temporal grain rules (what's additive vs latest vs weighted avg)
  - entity grain rules (which entity levels can be summed)
  - duplicate detection strategy

Rules enforced here prevent:
  - summing GCV (concentration metric — must be weighted average)
  - summing stock across months (point-in-time metric — use LATEST)
  - summing annual + monthly rows for same entity+period
  - mixing mine-level with subsidiary-level totals
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet, Optional


# ─── Temporal grain constants ─────────────────────────────────────────────────
class TemporalGrain:
    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    POINT_IN_TIME = "POINT_IN_TIME"   # e.g. stock levels
    CUMULATIVE_YTD = "CUMULATIVE_YTD" # year-to-date progress
    ANY = "ANY"


# ─── Entity grain constants ───────────────────────────────────────────────────
class EntityGrain:
    MINE = "MINE"
    SUBSIDIARY = "SUBSIDIARY"
    CONSOLIDATED = "CONSOLIDATED"   # CIL-level total
    ANY = "ANY"


# ─── Aggregation operations ───────────────────────────────────────────────────
class AggOp:
    SUM = "SUM"           # additive — production, overburden, drilling
    LATEST = "LATEST"     # point-in-time — stock
    WAVG = "WAVG"         # weighted average — GCV (weight = tonnes)
    AVG = "AVG"           # simple average — when no weight available
    RATIO = "RATIO"       # derived ratio — stripping ratio
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"


@dataclass(frozen=True)
class AggregationRule:
    """Explicit rule defining aggregation constraints for a metric."""
    allowed_operations: FrozenSet[str]
    default_operation: str
    requires_non_overlapping_periods: bool = True
    requires_non_overlapping_entities: bool = True
    requires_identical_units: bool = True
    disallow_annual_monthly_mix: bool = True
    disallow_consolidated_subsidiary_mix: bool = True


@dataclass
class MetricObservation:
    """A single normalized observation of a metric originating from evidence."""
    fact_id: str
    metric_code: str
    subsidiary: Optional[str]
    mine: Optional[str]
    reporting_period: Optional[str]
    numeric_value: float
    unit: str
    temporal_grain: str = TemporalGrain.ANY
    entity_grain: str = EntityGrain.ANY
    confidence_score: float = 1.0
    is_verified: bool = False
    is_demo: bool = False
    document_id: str = ""
    source_coordinates: str = ""


@dataclass(frozen=True)
class MetricDefinition:
    metric_code: str
    display_name: str
    canonical_unit: str
    allowed_units: FrozenSet[str]              # units that can be normalised to canonical
    primary_aggregation: str                   # preferred AggOp
    dimension: str = "QUANTITY"                # MASS, VOLUME, LENGTH, COUNT, ENERGY, CURRENCY, RATIO
    allowed_aggregation: FrozenSet[str] = field(
        default_factory=lambda: frozenset([AggOp.SUM, AggOp.AVG, AggOp.MIN, AggOp.MAX, AggOp.COUNT])
    )
    temporal_grain: str = TemporalGrain.ANY
    entity_grain: str = EntityGrain.ANY
    supports_sum: bool = True
    supports_average: bool = True
    supports_latest: bool = False
    supports_ratio: bool = False
    supports_min: bool = True
    supports_max: bool = True
    higher_is_better: Optional[bool] = None   # None = not applicable
    additive_across_entities: bool = True      # can SUM across subsidiaries/mines?
    additive_across_time: bool = True          # can SUM across periods?
    requires_non_overlapping_periods: bool = True
    requires_non_overlapping_entities: bool = True
    # When summing, which temporal grains are compatible with each other?
    # e.g. ANNUAL only — don't mix with MONTHLY components
    compatible_temporal_grains: FrozenSet[str] = field(
        default_factory=lambda: frozenset([TemporalGrain.ANY])
    )
    # Which entity grains are compatible when summing?
    compatible_entity_grains: FrozenSet[str] = field(
        default_factory=lambda: frozenset([EntityGrain.ANY])
    )
    notes: str = ""


# ─── Registry ─────────────────────────────────────────────────────────────────
class MetricRegistry:
    """Central lookup for all mining metric definitions."""

    _DEFINITIONS: dict[str, MetricDefinition] = {}

    @classmethod
    def get(cls, metric_code: str) -> Optional[MetricDefinition]:
        return cls._DEFINITIONS.get(metric_code)

    @classmethod
    def get_or_default(cls, metric_code: str) -> MetricDefinition:
        """Returns registered definition or a safe generic fallback."""
        defn = cls._DEFINITIONS.get(metric_code)
        if defn:
            return defn
        # Generic fallback: treat as additive, unit unknown
        return MetricDefinition(
            metric_code=metric_code,
            display_name=metric_code.replace("_", " ").title(),
            canonical_unit="units",
            allowed_units=frozenset(),
            primary_aggregation=AggOp.SUM,
            notes="Generic fallback — no semantic definition registered.",
        )

    @classmethod
    def register(cls, defn: MetricDefinition) -> None:
        cls._DEFINITIONS[defn.metric_code] = defn

    @classmethod
    def all_codes(cls) -> list[str]:
        return list(cls._DEFINITIONS.keys())


# ─── Register all known mining metrics ────────────────────────────────────────

MetricRegistry.register(MetricDefinition(
    metric_code="COAL_PRODUCTION",
    display_name="Raw Coal Production",
    canonical_unit="MT",
    allowed_units=frozenset(["MT", "Mt", "Million Tonnes", "million tonnes", "Mn T", "mn t"]),
    primary_aggregation=AggOp.SUM,
    supports_sum=True,
    supports_average=False,
    additive_across_entities=True,
    additive_across_time=True,
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([
        TemporalGrain.ANNUAL,
        TemporalGrain.QUARTERLY,
        TemporalGrain.MONTHLY,
        TemporalGrain.ANY,
    ]),
    compatible_entity_grains=frozenset([
        EntityGrain.MINE, EntityGrain.SUBSIDIARY, EntityGrain.ANY,
    ]),
    higher_is_better=True,
    notes=(
        "Additive only across non-overlapping entities and non-overlapping periods. "
        "A yearly total must NOT be summed with its monthly component rows. "
        "CONSOLIDATED/CIL rows must not be mixed with subsidiary rows."
    ),
))

MetricRegistry.register(MetricDefinition(
    metric_code="COAL_OFFTAKE",
    display_name="Coal Dispatch / Offtake",
    canonical_unit="MT",
    allowed_units=frozenset(["MT", "Mt", "Million Tonnes", "Mn T"]),
    primary_aggregation=AggOp.SUM,
    supports_sum=True,
    additive_across_entities=True,
    additive_across_time=True,
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=True,
))

MetricRegistry.register(MetricDefinition(
    metric_code="PRODUCTION_TARGET",
    display_name="Production Target",
    canonical_unit="MT",
    allowed_units=frozenset(["MT", "Mt", "Million Tonnes"]),
    primary_aggregation=AggOp.SUM,
    supports_sum=True,
    additive_across_entities=False,  # target scope must exactly match actual scope
    additive_across_time=False,
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=None,
    notes=(
        "Target scope MUST exactly match actual production scope "
        "(entity, period, unit) before achievement % can be computed. "
        "Do not synthesise a target from actual * factor."
    ),
))

MetricRegistry.register(MetricDefinition(
    metric_code="OVERBURDEN_REMOVAL",
    display_name="Overburden Removal (OBR)",
    canonical_unit="Mm3",
    allowed_units=frozenset(["Mm3", "BCM", "Mm³", "Million cubic metres", "MCM"]),
    primary_aggregation=AggOp.SUM,
    supports_sum=True,
    additive_across_entities=True,
    additive_across_time=True,
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=True,
    notes="Additive if records represent non-overlapping removal intervals.",
))

MetricRegistry.register(MetricDefinition(
    metric_code="DRILLING",
    display_name="Exploratory Drilling Progress",
    canonical_unit="m",
    allowed_units=frozenset(["m", "meters", "metres", "Meters"]),
    primary_aggregation=AggOp.SUM,
    supports_sum=True,
    additive_across_entities=True,
    additive_across_time=True,
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=True,
    notes="Additive only if records represent non-overlapping drilling intervals.",
))

MetricRegistry.register(MetricDefinition(
    metric_code="COAL_STOCK",
    display_name="Closing Pithead Coal Stock",
    canonical_unit="MT",
    allowed_units=frozenset(["MT", "Mt", "Million Tonnes"]),
    primary_aggregation=AggOp.LATEST,   # point-in-time — do NOT sum across months
    supports_sum=False,
    supports_latest=True,
    supports_average=True,
    additive_across_entities=True,      # can sum stock across mines at same instant
    additive_across_time=False,         # must NOT sum across periods
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([TemporalGrain.POINT_IN_TIME, TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=None,
    notes=(
        "Point-in-time metric. Use LATEST observation, not SUM. "
        "Summing stock across months is semantically incorrect."
    ),
))

MetricRegistry.register(MetricDefinition(
    metric_code="GCV",
    display_name="Gross Calorific Value",
    canonical_unit="kcal/kg",
    allowed_units=frozenset(["kcal/kg", "kcal per kg"]),
    primary_aggregation=AggOp.WAVG,     # must be weighted average
    supports_sum=False,
    supports_average=True,
    additive_across_entities=False,
    additive_across_time=False,
    compatible_temporal_grains=frozenset([TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=True,
    notes=(
        "Concentration metric. Must NOT be summed. "
        "Use weighted average (weight = production tonnes) when weight available; "
        "otherwise simple average with explicit methodology disclosure."
    ),
))

MetricRegistry.register(MetricDefinition(
    metric_code="GEOLOGICAL_RESERVES",
    display_name="Proved Geological Reserves",
    canonical_unit="MT",
    allowed_units=frozenset(["MT", "Mt", "Million Tonnes"]),
    primary_aggregation=AggOp.SUM,
    supports_sum=True,
    additive_across_entities=True,
    additive_across_time=False,   # reserves are cumulative, not flow — use latest per entity
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=True,
    notes="Use most recent estimate per entity; do not sum across years.",
))

MetricRegistry.register(MetricDefinition(
    metric_code="CAPITAL_EXPENDITURE",
    display_name="Capital Expenditure (Capex)",
    canonical_unit="INR Cr",
    allowed_units=frozenset(["INR Cr", "Cr", "Crores", "Rs Cr", "INR Crore"]),
    primary_aggregation=AggOp.SUM,
    supports_sum=True,
    additive_across_entities=True,
    additive_across_time=True,
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=None,
))

MetricRegistry.register(MetricDefinition(
    metric_code="EXPLORATION_BOREHOLES",
    display_name="Exploration Boreholes Drilled",
    canonical_unit="Count",
    allowed_units=frozenset(["Count", "Nos", "Number", "count"]),
    primary_aggregation=AggOp.SUM,
    supports_sum=True,
    additive_across_entities=True,
    additive_across_time=True,
    requires_non_overlapping_periods=True,
    requires_non_overlapping_entities=True,
    compatible_temporal_grains=frozenset([TemporalGrain.ANY]),
    compatible_entity_grains=frozenset([EntityGrain.ANY]),
    higher_is_better=True,
))
