# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: evaluate_scalability

Takes an architecture description and growth projections. Returns a tiered
scaling plan at 10x, 100x, and 1000x thresholds with bottleneck analysis
and pattern recommendations for each tier.
"""

from __future__ import annotations

from typing import Any

from coeus.tools._shared import coerce, emit_event, get_knowledge

# ---------------------------------------------------------------------------
# Tier definitions — what breaks and what to do at each scale factor
# ---------------------------------------------------------------------------

_SCALE_TIERS = [
    {
        "threshold": "10x",
        "typical_bottlenecks": [
            "Database connection pool exhaustion",
            "Single-node memory limits",
            "Synchronous API call latency accumulation",
            "Session state scalability",
            "Deployment downtime during releases",
        ],
        "key_patterns": [
            "horizontal_scaling",
            "connection_pooling",
            "cache_aside",
            "load_balancer",
            "database_read_replicas",
        ],
    },
    {
        "threshold": "100x",
        "typical_bottlenecks": [
            "Database write throughput ceiling",
            "Cross-service latency in synchronous chains",
            "Data consistency across replicas",
            "Operational complexity of many services",
            "Observability and debugging in distributed systems",
            "Cache invalidation at scale",
        ],
        "key_patterns": [
            "data_partitioning",
            "async_processing",
            "distributed_cache",
            "circuit_breaker",
            "autoscaling_policy",
            "rate_limiting",
        ],
    },
    {
        "threshold": "1000x",
        "typical_bottlenecks": [
            "Global latency requirements",
            "Data sovereignty and residency constraints",
            "Consensus protocol overhead",
            "Network partition tolerance",
            "Cost scaling non-linearly with traffic",
            "Blast radius of failures",
        ],
        "key_patterns": [
            "cell_based",
            "multi_region",
            "eventual_consistency",
            "crdt",
            "edge_caching",
            "backpressure",
        ],
    },
]


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def evaluate_scalability(
    description: str,
    growth_projections: dict | None = None,
    current_scale: str | None = None,
    conn: object = None,
) -> dict:
    """Evaluate the scalability of a system architecture.

    Produces a tiered scaling plan at 10x, 100x, and 1000x growth factors
    with bottleneck analysis and recommended patterns at each tier.

    Args:
        description: Description of the current system architecture.
        growth_projections: Optional dict with growth estimates, e.g.
            ``{"users": "10k->1M", "rps": "100->10k", "data": "10GB->1TB"}``.
        current_scale: Optional string describing current scale level, e.g.
            "startup_mvp", "growth", "enterprise".
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: current_assessment, tiers (list of tier plans).
    """
    growth_projections = coerce(growth_projections, dict) or {}

    kb = get_knowledge(conn)

    # 1. Build current assessment from structural signals in description
    current_assessment: dict[str, Any] = {
        "description": description[:200],
        "current_scale": current_scale or "unknown",
        "growth_projections": growth_projections,
    }

    # Match signals from description keywords against rules
    desc_signals = []
    desc_lower = description.lower()
    signal_keywords = [
        "single node", "monolith", "shared database", "no caching",
        "synchronous", "no redundancy", "vertical scaling",
        "horizontal scaling", "microservices", "event-driven",
        "stateless", "stateful", "queue", "cache",
    ]
    for kw in signal_keywords:
        if kw in desc_lower:
            desc_signals.append(kw)

    if desc_signals:
        rule_matches = kb.match_structural_signals(desc_signals)
        current_assessment["matched_signals"] = desc_signals
        current_assessment["relevant_rules"] = [
            rm["rule"]["id"] for rm in rule_matches[:5]
        ]

    # 2. Build tiered scaling plan
    tiers: list[dict[str, Any]] = []

    for tier_def in _SCALE_TIERS:
        threshold = tier_def["threshold"]

        # Resolve patterns from knowledge base
        resolved_patterns: list[dict[str, Any]] = []
        for pid in tier_def["key_patterns"]:
            pat = kb.get_scalability_pattern(pid)
            if pat:
                resolved_patterns.append({
                    "id": pat["id"],
                    "name": pat["name"],
                    "description": pat.get("description", "")[:150],
                    "when_to_use": pat.get("when_to_use", [])[:3],
                })
            else:
                # Try architecture patterns
                pat = kb.get_pattern(pid)
                if pat:
                    resolved_patterns.append({
                        "id": pat["id"],
                        "name": pat["name"],
                        "description": pat.get("description", "")[:150],
                        "when_to_use": pat.get("when_to_use", [])[:3],
                    })

        # Build recommendations specific to growth projections
        tier_recommendations: list[str] = []
        if growth_projections:
            if growth_projections.get("rps") and threshold == "10x":
                tier_recommendations.append(
                    "Add load balancer and horizontal scaling for stateless services"
                )
            if growth_projections.get("data") and threshold == "100x":
                tier_recommendations.append(
                    "Implement data partitioning and consider read replicas"
                )
            if growth_projections.get("users") and threshold == "1000x":
                tier_recommendations.append(
                    "Deploy multi-region with edge caching and eventual consistency"
                )

        tiers.append({
            "threshold": threshold,
            "bottlenecks": tier_def["typical_bottlenecks"],
            "recommendations": tier_recommendations or [
                f"Review and implement {threshold} scaling patterns"
            ],
            "patterns": resolved_patterns,
        })

    # 3. Build result
    result: dict[str, Any] = {
        "current_assessment": current_assessment,
        "tiers": tiers,
    }

    emit_event("evaluate_scalability", {
        "description": description[:120],
        "current_scale": current_scale or "unknown",
        "tiers_generated": len(tiers),
    })

    return result
