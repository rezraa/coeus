# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: assess_resilience

Evaluates failure modes of a system architecture. Identifies single points
of failure, missing resilience patterns, blast radius, and provides
hardening recommendations.
"""

from __future__ import annotations

from typing import Any

from coeus.tools._shared import coerce, emit_event, get_knowledge

# ---------------------------------------------------------------------------
# SPOF detectors — structural signal keywords → single points of failure
# ---------------------------------------------------------------------------

_SPOF_SIGNALS: dict[str, dict[str, Any]] = {
    "single-database": {
        "component": "Database",
        "risk": "Single database instance without replication or failover",
        "impact": "Total system outage if database fails",
        "mitigation": "Add read replicas, configure automatic failover, implement connection pooling",
    },
    "single-node": {
        "component": "Application server",
        "risk": "Application runs on a single node without redundancy",
        "impact": "Complete service unavailability during node failure or deployment",
        "mitigation": "Deploy minimum 2 instances behind a load balancer, use rolling deployments",
    },
    "single-region": {
        "component": "Infrastructure",
        "risk": "All infrastructure in one cloud region or data center",
        "impact": "Total outage during regional failure or cloud provider incident",
        "mitigation": "Deploy to multiple availability zones, plan for multi-region failover",
    },
    "no-load-balancer": {
        "component": "Network",
        "risk": "No load balancer distributing traffic across instances",
        "impact": "Single server overload, no failover capability",
        "mitigation": "Add L4/L7 load balancer, configure health checks and automatic removal",
    },
    "single-queue": {
        "component": "Message queue",
        "risk": "Single queue broker without clustering or replication",
        "impact": "Message loss and processing halt during broker failure",
        "mitigation": "Use clustered broker (RabbitMQ cluster, Kafka with replication factor 3+)",
    },
    "single-cache": {
        "component": "Cache layer",
        "risk": "Single cache node (e.g., solo Redis) without replication",
        "impact": "Cache stampede and backend overload on cache failure",
        "mitigation": "Use Redis Sentinel/Cluster, implement graceful degradation without cache",
    },
}

# ---------------------------------------------------------------------------
# Missing resilience pattern detectors
# ---------------------------------------------------------------------------

_MISSING_PATTERN_SIGNALS: dict[str, dict[str, Any]] = {
    "no-circuit-breaker": {
        "pattern": "Circuit Breaker",
        "risk": "Cascading failures propagate through dependent services",
        "recommendation": "Implement circuit breakers on all external calls with defined fallbacks",
    },
    "no-retry": {
        "pattern": "Retry with Backoff",
        "risk": "Transient failures cause permanent errors",
        "recommendation": "Add exponential backoff with jitter for retries, ensure idempotency",
    },
    "no-timeout": {
        "pattern": "Timeout",
        "risk": "Hung connections consume resources indefinitely",
        "recommendation": "Set timeouts on all network calls, use timeout budgets for call chains",
    },
    "no-bulkhead": {
        "pattern": "Bulkhead",
        "risk": "One failing dependency exhausts shared thread/connection pools",
        "recommendation": "Isolate thread pools and connection pools per dependency",
    },
    "no-fallback": {
        "pattern": "Fallback / Graceful Degradation",
        "risk": "Failures result in complete feature unavailability",
        "recommendation": "Define fallback responses (cached data, defaults, degraded mode) for each dependency",
    },
    "no-health-checks": {
        "pattern": "Health Check",
        "risk": "Unhealthy instances continue receiving traffic",
        "recommendation": "Add /health (liveness) and /ready (readiness) endpoints, configure load balancer checks",
    },
    "no-dead-letter": {
        "pattern": "Dead Letter Queue",
        "risk": "Failed messages are silently lost or block processing",
        "recommendation": "Route unprocessable messages to a DLQ for inspection and replay",
    },
    "no-idempotency": {
        "pattern": "Idempotency",
        "risk": "Retries cause duplicate side effects (double charges, duplicate records)",
        "recommendation": "Use idempotency keys for all mutation operations, especially payments",
    },
    "no-rate-limiting": {
        "pattern": "Rate Limiting",
        "risk": "Sudden traffic spikes or abuse overwhelm the system",
        "recommendation": "Implement token bucket or leaky bucket rate limiting at the API gateway",
    },
    "no-observability": {
        "pattern": "Observability",
        "risk": "Cannot diagnose failures, performance issues are invisible",
        "recommendation": "Implement structured logging, distributed tracing, and metric collection (the three pillars)",
    },
}


# ---------------------------------------------------------------------------
# Blast radius assessment
# ---------------------------------------------------------------------------

_BLAST_RADIUS_INDICATORS: dict[str, dict[str, Any]] = {
    "shared-database": {
        "scope": "All services sharing the database",
        "severity": "high",
        "description": "Schema change or database outage affects every dependent service",
    },
    "synchronous-chain": {
        "scope": "Entire call chain depth",
        "severity": "high",
        "description": "Failure at any point in the chain cascades to all upstream callers",
    },
    "shared-library": {
        "scope": "All services using the library",
        "severity": "medium",
        "description": "Bug in shared library requires redeploying all consumers",
    },
    "monolith": {
        "scope": "Entire application",
        "severity": "medium",
        "description": "Any failure in any module can affect the entire application",
    },
    "shared-cache": {
        "scope": "All services using the cache",
        "severity": "medium",
        "description": "Cache invalidation error or outage affects all consumers simultaneously",
    },
    "global-load-balancer": {
        "scope": "All traffic",
        "severity": "high",
        "description": "Load balancer misconfiguration or failure affects 100% of requests",
    },
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _compute_resilience_score(
    spof_count: int,
    missing_count: int,
    blast_count: int,
) -> float:
    """Compute a 0.0-1.0 resilience score.

    1.0 = no issues found, 0.0 = severely lacking resilience.
    """
    # Each issue category reduces the score
    penalty = (spof_count * 0.15) + (missing_count * 0.08) + (blast_count * 0.10)
    return max(0.0, min(1.0, round(1.0 - penalty, 2)))


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def assess_resilience(
    system_description: str,
    structural_signals: list[str] | None = None,
    conn: object = None,
) -> dict:
    """Assess the resilience of a system architecture.

    Identifies single points of failure, missing resilience patterns,
    blast radius of failures, and provides hardening recommendations.

    Args:
        system_description: Description of the system architecture.
        structural_signals: Agent-identified signals about the system's
            resilience characteristics, e.g. ["no-circuit-breaker",
            "single-database", "synchronous-chain"].
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: resilience_score, single_points_of_failure,
        missing_patterns, blast_radius_assessment, hardening_recommendations.
    """
    structural_signals = coerce(structural_signals, list) or []

    kb = get_knowledge(conn)

    # 1. Identify single points of failure
    single_points_of_failure: list[dict[str, Any]] = []
    for signal in structural_signals:
        sig_lower = signal.lower().strip()
        spof = _SPOF_SIGNALS.get(sig_lower)
        if spof:
            single_points_of_failure.append({
                "signal": signal,
                **spof,
            })

    # 2. Identify missing resilience patterns
    missing_patterns: list[dict[str, Any]] = []
    for signal in structural_signals:
        sig_lower = signal.lower().strip()
        missing = _MISSING_PATTERN_SIGNALS.get(sig_lower)
        if missing:
            missing_patterns.append({
                "signal": signal,
                **missing,
            })

    # 3. Assess blast radius
    blast_radius_assessment: list[dict[str, Any]] = []
    for signal in structural_signals:
        sig_lower = signal.lower().strip()
        blast = _BLAST_RADIUS_INDICATORS.get(sig_lower)
        if blast:
            blast_radius_assessment.append({
                "signal": signal,
                **blast,
            })

    # 4. Match against decision rules for additional context
    hardening_recommendations: list[dict[str, Any]] = []

    if structural_signals:
        rule_matches = kb.match_structural_signals(structural_signals)
        for rm in rule_matches:
            rule = rm["rule"]
            # Only include resilience-related rules
            if any(kw in rule.get("category", "").lower()
                   for kw in ["resilience", "reliability", "failure"]):
                for pattern in rm.get("recommended_patterns", []):
                    hardening_recommendations.append({
                        "pattern_id": pattern.get("id", ""),
                        "pattern_name": pattern.get("name", pattern.get("id", "")),
                        "rationale": rule.get("rationale", ""),
                        "priority": rule.get("priority", "medium"),
                        "source_rule": rule["id"],
                    })

    # Add recommendations from detected issues
    for spof in single_points_of_failure:
        hardening_recommendations.append({
            "pattern_id": f"fix_{spof['signal'].replace('-', '_')}",
            "pattern_name": f"Address {spof['component']} SPOF",
            "rationale": spof["mitigation"],
            "priority": "high",
            "source_rule": "spof_detection",
        })

    for mp in missing_patterns:
        hardening_recommendations.append({
            "pattern_id": mp["pattern"].lower().replace(" ", "_"),
            "pattern_name": f"Add {mp['pattern']}",
            "rationale": mp["recommendation"],
            "priority": "high",
            "source_rule": "missing_pattern_detection",
        })

    # 5. Compute resilience score
    resilience_score = _compute_resilience_score(
        spof_count=len(single_points_of_failure),
        missing_count=len(missing_patterns),
        blast_count=len(blast_radius_assessment),
    )

    # 6. Build result
    result: dict[str, Any] = {
        "resilience_score": resilience_score,
        "single_points_of_failure": single_points_of_failure,
        "missing_patterns": missing_patterns,
        "blast_radius_assessment": blast_radius_assessment,
        "hardening_recommendations": hardening_recommendations,
    }

    emit_event("assess_resilience", {
        "description": system_description[:120],
        "signals": structural_signals,
        "resilience_score": resilience_score,
        "spof_count": len(single_points_of_failure),
        "missing_patterns_count": len(missing_patterns),
        "blast_radius_count": len(blast_radius_assessment),
    })

    return result
