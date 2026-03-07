"""Scoring service for computing entity suspicion scores.

This module provides comprehensive scoring capabilities including:
- Suspicion score computation with explainable factors
- Score history tracking
- Null score handling
- Risk factor analysis
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from neo4j import AsyncSession

from bracc.config import settings
from bracc.models.entity import SourceAttribution
from bracc.services.neo4j_service import execute_query_single

logger = logging.getLogger(__name__)

# Factor weights for suspicion score calculation
FACTOR_WEIGHTS: dict[str, float] = {
    "sanctions": 0.25,
    "pep_connections": 0.20,
    "contract_volume": 0.15,
    "offshore_connections": 0.15,
    "pattern_flags": 0.15,
    "temporal_anomalies": 0.10,
}

# Risk thresholds
RISK_THRESHOLDS = {
    "critical": 80.0,
    "high": 60.0,
    "medium": 40.0,
    "low": 20.0,
}


@dataclass
class ScoreFactor:
    """An explainable scoring factor.

    Attributes:
        name: Factor name identifier.
        score: Raw factor score (0-100).
        weight: Factor weight in overall calculation.
        weighted_score: Score * weight.
        explanation: Human-readable explanation of the factor.
        evidence: List of evidence supporting this factor.
        sources: Data sources contributing to this factor.
    """

    name: str
    score: float
    weight: float
    weighted_score: float = field(init=False)
    explanation: str = ""
    evidence: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Calculate weighted score after initialization."""
        self.weighted_score = self.score * self.weight


@dataclass
class SuspicionScoreResult:
    """Result of suspicion score computation.

    Attributes:
        entity_id: The entity ID.
        entity_name: Entity name.
        entity_type: Entity type label.
        suspicion_score: Overall suspicion score (0-100).
        risk_level: Risk level classification.
        confidence: Confidence in the score (0-1).
        factors: List of contributing factors with explanations.
        score_history: Historical scores if available.
        computed_at: ISO timestamp of computation.
        null_reason: Reason if score is null/unavailable.
    """

    entity_id: str
    entity_name: str
    entity_type: str
    suspicion_score: float | None
    risk_level: str
    confidence: float
    factors: list[ScoreFactor]
    score_history: list[dict[str, Any]]
    computed_at: str
    null_reason: str | None = None


@dataclass
class ScoreHistoryEntry:
    """A single score history entry.

    Attributes:
        score: The suspicion score at that time.
        computed_at: ISO timestamp.
        factor_count: Number of factors considered.
        sources: Data sources available at that time.
    """

    score: float
    computed_at: str
    factor_count: int
    sources: list[str]


async def _fetch_entity_data(
    session: AsyncSession,
    entity_id: str,
) -> dict[str, Any] | None:
    """Fetch comprehensive entity data for scoring.

    Args:
        session: Neo4j session.
        entity_id: Entity ID.

    Returns:
        Entity data dictionary or None if not found.
    """
    record = await execute_query_single(
        session,
        "entity_by_id",
        {"id": entity_id},
    )

    if record is None:
        return None

    node = record["e"]
    labels = record["entity_labels"]

    # Fetch additional scoring data
    degree_record = await execute_query_single(
        session,
        "node_degree",
        {"entity_id": entity_id},
    )

    return {
        "node": dict(node),
        "labels": labels,
        "degree": int(degree_record.get("degree", 0)) if degree_record else 0,
        "entity_id": entity_id,
    }


def _calculate_sanctions_factor(entity_data: dict[str, Any]) -> ScoreFactor:
    """Calculate sanctions factor score.

    Args:
        entity_data: Entity data dictionary.

    Returns:
        ScoreFactor for sanctions.
    """
    node = entity_data.get("node", {})
    evidence: list[str] = []
    score = 0.0

    # Check for direct sanctions
    if node.get("sanction_id") or node.get("is_sanctioned"):
        score = 100.0
        evidence.append("Entity has direct sanction record")

    # Check for sanction relationships
    if node.get("sanction_count"):
        count = int(node.get("sanction_count", 0))
        score = min(100.0, 50.0 + count * 25.0)
        evidence.append(f"Entity has {count} sanction relationships")

    # Check CEIS/CNEP status
    if node.get("ceis_status") == "active" or node.get("cnep_status") == "active":
        score = max(score, 90.0)
        evidence.append("Active sanction in CEIS/CNEP")

    explanation = (
        f"Sanctions factor: {score:.1f}/100 based on "
        f"{len(evidence)} sanction indicators"
        if evidence
        else "No sanctions found"
    )

    return ScoreFactor(
        name="sanctions",
        score=score,
        weight=FACTOR_WEIGHTS["sanctions"],
        explanation=explanation,
        evidence=evidence,
        sources=["ceis", "cnep", "tcu"],
    )


def _calculate_pep_factor(entity_data: dict[str, Any]) -> ScoreFactor:
    """Calculate PEP (Politically Exposed Person) factor score.

    Args:
        entity_data: Entity data dictionary.

    Returns:
        ScoreFactor for PEP connections.
    """
    node = entity_data.get("node", {})
    evidence: list[str] = []
    score = 0.0

    # Direct PEP status
    if node.get("is_pep") or node.get("role"):
        role = str(node.get("role", "")).lower()
        if any(kw in role for kw in ["deputado", "senador", "vereador", "prefeito"]):
            score = 80.0
            evidence.append(f"Direct PEP role: {role}")
        else:
            score = 60.0
            evidence.append("Entity marked as PEP")

    # PEP connections through relationships
    degree = entity_data.get("degree", 0)
    if degree > 30:
        score = max(score, 40.0)
        evidence.append(f"High connectivity ({degree} connections) suggesting PEP network")

    explanation = (
        f"PEP factor: {score:.1f}/100 - "
        f"{'Direct PEP status' if score >= 60 else 'Possible PEP connections' if score > 0 else 'No PEP indicators'}"
    )

    return ScoreFactor(
        name="pep_connections",
        score=score,
        weight=FACTOR_WEIGHTS["pep_connections"],
        explanation=explanation,
        evidence=evidence,
        sources=["pep_cgu", "global_pep"],
    )


def _calculate_contract_factor(entity_data: dict[str, Any]) -> ScoreFactor:
    """Calculate contract volume factor score.

    Args:
        entity_data: Entity data dictionary.

    Returns:
        ScoreFactor for contract volume.
    """
    node = entity_data.get("node", {})
    evidence: list[str] = []
    score = 0.0

    # Contract values
    total_contracts = node.get("total_contracts", 0)
    contract_value = node.get("total_contract_value", 0.0)

    if contract_value > 100_000_000:  # > 100M
        score = 70.0
        evidence.append(f"Very high contract value: R$ {contract_value:,.2f}")
    elif contract_value > 10_000_000:  # > 10M
        score = 50.0
        evidence.append(f"High contract value: R$ {contract_value:,.2f}")
    elif contract_value > 1_000_000:  # > 1M
        score = 30.0
        evidence.append(f"Moderate contract value: R$ {contract_value:,.2f}")

    if total_contracts > 50:
        score = max(score, 40.0)
        evidence.append(f"High contract count: {total_contracts}")

    explanation = (
        f"Contract factor: {score:.1f}/100 based on "
        f"R$ {contract_value:,.2f} across {total_contracts} contracts"
        if contract_value > 0
        else "No contract data available"
    )

    return ScoreFactor(
        name="contract_volume",
        score=score,
        weight=FACTOR_WEIGHTS["contract_volume"],
        explanation=explanation,
        evidence=evidence,
        sources=["transparencia", "pncp", "comprasnet"],
    )


def _calculate_offshore_factor(entity_data: dict[str, Any]) -> ScoreFactor:
    """Calculate offshore connection factor score.

    Args:
        entity_data: Entity data dictionary.

    Returns:
        ScoreFactor for offshore connections.
    """
    node = entity_data.get("node", {})
    evidence: list[str] = []
    score = 0.0

    # Direct offshore links
    if node.get("offshore_entity_id") or node.get("is_offshore"):
        score = 100.0
        evidence.append("Direct offshore entity connection")

    # ICIJ leaks data
    if node.get("icij_leak"):
        score = 90.0
        evidence.append(f"Appears in ICIJ leak: {node.get('icij_leak')}")

    # Offshore officer role
    if node.get("offshore_role"):
        score = 85.0
        evidence.append(f"Offshore role: {node.get('offshore_role')}")

    explanation = (
        f"Offshore factor: {score:.1f}/100 - "
        f"{'Offshore connections detected' if score > 0 else 'No offshore indicators'}"
    )

    return ScoreFactor(
        name="offshore_connections",
        score=score,
        weight=FACTOR_WEIGHTS["offshore_connections"],
        explanation=explanation,
        evidence=evidence,
        sources=["icij_offshore", "icij_paradise"],
    )


def _calculate_pattern_factor(entity_data: dict[str, Any]) -> ScoreFactor:
    """Calculate pattern detection factor score.

    Args:
        entity_data: Entity data dictionary.

    Returns:
        ScoreFactor for pattern flags.
    """
    node = entity_data.get("node", {})
    evidence: list[str] = []
    score = 0.0

    # Pattern matches
    patterns = node.get("pattern_matches", [])
    if patterns:
        pattern_count = len(patterns) if isinstance(patterns, list) else int(patterns)
        score = min(100.0, pattern_count * 20.0)
        evidence.append(f"{pattern_count} pattern matches detected")

    # Self-dealing indicators
    if node.get("self_dealing_flag"):
        score = max(score, 80.0)
        evidence.append("Self-dealing pattern detected")

    # Concentration risk
    if node.get("concentration_ratio", 0) > 0.5:
        score = max(score, 60.0)
        evidence.append("High concentration ratio")

    explanation = (
        f"Pattern factor: {score:.1f}/100 - "
        f"{len(evidence)} pattern indicators" if evidence else "No suspicious patterns detected"
    )

    return ScoreFactor(
        name="pattern_flags",
        score=score,
        weight=FACTOR_WEIGHTS["pattern_flags"],
        explanation=explanation,
        evidence=evidence,
        sources=["pattern_analysis"],
    )


def _calculate_temporal_factor(entity_data: dict[str, Any]) -> ScoreFactor:
    """Calculate temporal anomaly factor score.

    Args:
        entity_data: Entity data dictionary.

    Returns:
        ScoreFactor for temporal anomalies.
    """
    node = entity_data.get("node", {})
    evidence: list[str] = []
    score = 0.0

    # Rapid contract succession
    if node.get("rapid_contracting_flag"):
        score = 70.0
        evidence.append("Rapid contracting pattern detected")

    # Temporal clustering
    if node.get("temporal_cluster_count", 0) > 3:
        score = max(score, 50.0)
        evidence.append("Suspicious temporal clustering")

    # Election year contracts
    election_contracts = node.get("election_year_contracts", 0)
    if election_contracts > 5:
        score = max(score, 60.0)
        evidence.append(f"{election_contracts} contracts in election years")

    explanation = (
        f"Temporal factor: {score:.1f}/100 - "
        f"{len(evidence)} temporal anomalies" if evidence else "No temporal anomalies"
    )

    return ScoreFactor(
        name="temporal_anomalies",
        score=score,
        weight=FACTOR_WEIGHTS["temporal_anomalies"],
        explanation=explanation,
        evidence=evidence,
        sources=["temporal_analysis", "tse"],
    )


def _determine_risk_level(score: float) -> str:
    """Determine risk level from score.

    Args:
        score: Suspicion score.

    Returns:
        Risk level string.
    """
    if score >= RISK_THRESHOLDS["critical"]:
        return "critical"
    elif score >= RISK_THRESHOLDS["high"]:
        return "high"
    elif score >= RISK_THRESHOLDS["medium"]:
        return "medium"
    elif score >= RISK_THRESHOLDS["low"]:
        return "low"
    return "minimal"


def _calculate_confidence(factors: list[ScoreFactor]) -> float:
    """Calculate confidence score based on factor data availability.

    Args:
        factors: List of scoring factors.

    Returns:
        Confidence value between 0 and 1.
    """
    if not factors:
        return 0.0

    # Count factors with actual evidence
    factors_with_data = sum(1 for f in factors if f.evidence)
    base_confidence = factors_with_data / len(factors)

    # Adjust based on evidence richness
    total_evidence = sum(len(f.evidence) for f in factors)
    evidence_bonus = min(0.2, total_evidence * 0.02)

    return min(1.0, base_confidence + evidence_bonus)


async def compute_suspicion_score(
    session: AsyncSession,
    entity_id: str,
    include_history: bool = False,
) -> SuspicionScoreResult:
    """Compute comprehensive suspicion score for an entity.

    Args:
        session: Neo4j session.
        entity_id: Entity ID.
        include_history: Whether to include score history.

    Returns:
        SuspicionScoreResult with scores and explanations.

    Raises:
        ValueError: If entity not found.
    """
    entity_data = await _fetch_entity_data(session, entity_id)

    if entity_data is None:
        raise ValueError(f"Entity not found: {entity_id}")

    node = entity_data.get("node", {})
    labels = entity_data.get("labels", ["Unknown"])
    entity_name = str(node.get("name", "Unknown"))
    entity_type = labels[0] if labels else "Unknown"

    # Calculate all factors
    factors = [
        _calculate_sanctions_factor(entity_data),
        _calculate_pep_factor(entity_data),
        _calculate_contract_factor(entity_data),
        _calculate_offshore_factor(entity_data),
        _calculate_pattern_factor(entity_data),
        _calculate_temporal_factor(entity_data),
    ]

    # Calculate weighted total score
    total_weight = sum(f.weight for f in factors)
    if total_weight > 0:
        suspicion_score = sum(f.weighted_score for f in factors) / total_weight
        suspicion_score = round(max(0.0, min(100.0, suspicion_score)), 2)
    else:
        suspicion_score = 0.0

    # Determine risk level
    risk_level = _determine_risk_level(suspicion_score)

    # Calculate confidence
    confidence = round(_calculate_confidence(factors), 2)

    # Build score history if requested
    score_history: list[dict[str, Any]] = []
    if include_history:
        # In production, this would fetch from a historical table
        # For now, return empty list
        score_history = []

    return SuspicionScoreResult(
        entity_id=entity_id,
        entity_name=entity_name,
        entity_type=entity_type,
        suspicion_score=suspicion_score,
        risk_level=risk_level,
        confidence=confidence,
        factors=factors,
        score_history=score_history,
        computed_at=datetime.now(UTC).isoformat(),
    )


async def compute_suspicion_score_safe(
    session: AsyncSession,
    entity_id: str,
    include_history: bool = False,
) -> SuspicionScoreResult:
    """Compute suspicion score with null handling.

    This version handles missing data gracefully by returning
    a result with null_reason instead of raising exceptions.

    Args:
        session: Neo4j session.
        entity_id: Entity ID.
        include_history: Whether to include score history.

    Returns:
        SuspicionScoreResult, possibly with null score.
    """
    try:
        return await compute_suspicion_score(session, entity_id, include_history)
    except ValueError as e:
        # Entity not found
        return SuspicionScoreResult(
            entity_id=entity_id,
            entity_name="Unknown",
            entity_type="Unknown",
            suspicion_score=None,
            risk_level="unknown",
            confidence=0.0,
            factors=[],
            score_history=[],
            computed_at=datetime.now(UTC).isoformat(),
            null_reason=str(e),
        )
    except Exception as e:
        # Other errors
        logger.exception("Error computing suspicion score for %s", entity_id)
        return SuspicionScoreResult(
            entity_id=entity_id,
            entity_name="Unknown",
            entity_type="Unknown",
            suspicion_score=None,
            risk_level="error",
            confidence=0.0,
            factors=[],
            score_history=[],
            computed_at=datetime.now(UTC).isoformat(),
            null_reason=f"Computation error: {str(e)}",
        )


def format_factor_explanation(factor: ScoreFactor, lang: str = "pt") -> str:
    """Format a factor explanation for display.

    Args:
        factor: The score factor.
        lang: Language code (pt or en).

    Returns:
        Formatted explanation string.
    """
    if lang == "pt":
        base = f"**{factor.name}**: {factor.score:.1f}/100 (peso {factor.weight:.0%})"
        if factor.explanation:
            base += f"\n  {factor.explanation}"
        if factor.evidence:
            base += f"\n  Evidências: {', '.join(factor.evidence[:3])}"
        return base
    else:
        base = f"**{factor.name}**: {factor.score:.1f}/100 (weight {factor.weight:.0%})"
        if factor.explanation:
            base += f"\n  {factor.explanation}"
        if factor.evidence:
            base += f"\n  Evidence: {', '.join(factor.evidence[:3])}"
        return base
