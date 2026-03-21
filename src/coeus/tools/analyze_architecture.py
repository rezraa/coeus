# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: analyze_architecture

Takes a system description and structural signals. Identifies architectural
patterns, complexity, coupling, risks, and anti-patterns.

The agent (LLM) reads the system and identifies structural signals.
This tool matches those signals against decision_rules.json, checks for
common architecture anti-patterns, and flags scalability concerns.
"""

from __future__ import annotations

from typing import Any

from coeus.tools._shared import coerce, emit_event, get_knowledge

# ---------------------------------------------------------------------------
# Anti-pattern detectors — structural signal keywords → architecture issues
# ---------------------------------------------------------------------------

_ANTI_PATTERNS: dict[str, dict[str, Any]] = {
    "god-service": {
        "issue": "Monolithic service handling too many responsibilities",
        "severity": "high",
        "recommendation": "Decompose into bounded contexts with clear domain boundaries. Start with a modular monolith before extracting services.",
    },
    "distributed-monolith": {
        "issue": "Microservices with tight coupling behaving as a distributed monolith",
        "severity": "high",
        "recommendation": "Identify shared state and synchronous dependencies. Introduce event-driven communication and enforce service autonomy.",
    },
    "shared-database": {
        "issue": "Multiple services sharing a single database, coupling schema changes",
        "severity": "high",
        "recommendation": "Give each service its own data store. Use events or APIs for cross-service data access. Apply the database-per-service pattern.",
    },
    "chatty-services": {
        "issue": "Excessive inter-service calls creating latency and fragility",
        "severity": "medium",
        "recommendation": "Batch requests, use async messaging, or consolidate related services. Consider BFF pattern for client-facing aggregation.",
    },
    "no-circuit-breaker": {
        "issue": "Missing circuit breaker pattern for external dependencies",
        "severity": "high",
        "recommendation": "Implement circuit breakers (Hystrix, Resilience4j, Polly) on all external calls. Define fallback behavior for each dependency.",
    },
    "synchronous-chain": {
        "issue": "Long synchronous call chains creating cascading failure risk",
        "severity": "high",
        "recommendation": "Break synchronous chains with async messaging or event-driven patterns. Use sagas for distributed transactions.",
    },
    "no-caching": {
        "issue": "Missing caching layer causing unnecessary load on backend systems",
        "severity": "medium",
        "recommendation": "Add cache-aside pattern for read-heavy paths. Use CDN for static content. Consider distributed cache for session data.",
    },
    "single-point-of-failure": {
        "issue": "Critical component without redundancy or failover",
        "severity": "high",
        "recommendation": "Add redundancy at every layer. Use active-passive or active-active failover. Eliminate single-node dependencies.",
    },
    "no-health-checks": {
        "issue": "Missing health check endpoints and observability infrastructure",
        "severity": "medium",
        "recommendation": "Add /health and /ready endpoints. Implement structured logging, distributed tracing, and metric collection.",
    },
    "hardcoded-config": {
        "issue": "Configuration values hardcoded in application code",
        "severity": "medium",
        "recommendation": "Externalize configuration using environment variables, config maps, or a configuration service. Never commit secrets to source control.",
    },
    "no-versioning": {
        "issue": "APIs without a versioning strategy risking breaking changes",
        "severity": "medium",
        "recommendation": "Adopt URL-based or header-based API versioning from day one. Document deprecation policy and sunset timelines.",
    },
    "tight-coupling": {
        "issue": "Components with high coupling making independent changes impossible",
        "severity": "high",
        "recommendation": "Introduce interface boundaries, dependency inversion, and event-driven communication. Define clear contracts between modules.",
    },
}


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def analyze_architecture(
    description: str,
    structural_signals: list[str],
    constraints: dict | None = None,
    conn: object = None,
) -> dict:
    """Analyze a system architecture for issues, pattern matches, and risks.

    Args:
        description: Description of the system architecture to analyze.
        structural_signals: Agent-identified signals, e.g.
            ["shared-database", "no-circuit-breaker", "synchronous-chain"].
        constraints: Optional dict with constraint signals for filtering
            (e.g. ``{"team_size": "1-5", "scale": "startup_mvp"}``).
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: matched_rules, architecture_issues,
        recommendations, scalability_flags.
    """
    structural_signals = coerce(structural_signals, list) or []
    constraints = coerce(constraints, dict) or {}

    kb = get_knowledge(conn)

    # 1. Match structural signals against decision rules
    matched_rules: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    scalability_flags: list[dict[str, Any]] = []

    if structural_signals:
        rule_matches = kb.match_structural_signals(structural_signals)

        # Apply constraint filtering if constraints provided
        if constraints:
            filtered_rules = kb.filter_by_constraints(
                [rm["rule"] for rm in rule_matches], constraints
            )
            filtered_ids = {r["id"] for r in filtered_rules}
            rule_matches = [
                rm for rm in rule_matches if rm["rule"]["id"] in filtered_ids
            ]

        for rm in rule_matches:
            rule = rm["rule"]

            rule_entry: dict[str, Any] = {
                "signal": rm["signal"],
                "rule_id": rule["id"],
                "description": rule.get("rationale", rule.get("description", "")),
                "priority": rule.get("priority", "medium"),
                "recommended_patterns": [
                    p.get("id", "") for p in rm.get("recommended_patterns", [])
                ],
            }
            matched_rules.append(rule_entry)

            # Build recommendations from matched patterns
            for pattern in rm.get("recommended_patterns", []):
                rec: dict[str, Any] = {
                    "pattern_id": pattern.get("id", ""),
                    "pattern_name": pattern.get("name", pattern.get("id", "")),
                    "description": pattern.get("description", ""),
                    "source_rule": rule["id"],
                }
                recommendations.append(rec)

                # Check for scalability signals in the pattern
                scale_signals = pattern.get("signals", [])
                if scale_signals:
                    scalability_flags.append({
                        "pattern_id": pattern.get("id", ""),
                        "signals": scale_signals[:3],
                        "source": "pattern",
                    })

    # 2. Detect anti-patterns from structural signals
    architecture_issues: list[dict[str, Any]] = []

    for signal in structural_signals:
        sig_lower = signal.lower().strip()
        anti = _ANTI_PATTERNS.get(sig_lower)
        if anti:
            architecture_issues.append({
                "signal": signal,
                "issue": anti["issue"],
                "severity": anti["severity"],
                "recommendation": anti["recommendation"],
            })

    # 3. Build result
    result: dict[str, Any] = {
        "matched_rules": matched_rules,
        "architecture_issues": architecture_issues,
        "recommendations": recommendations,
        "scalability_flags": scalability_flags,
    }

    emit_event("analyze_architecture", {
        "description": description[:120],
        "signals": structural_signals,
        "matched_rules_count": len(matched_rules),
        "architecture_issues_count": len(architecture_issues),
        "scalability_flags_count": len(scalability_flags),
    })

    return result
