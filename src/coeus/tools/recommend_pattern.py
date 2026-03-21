# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: recommend_pattern

The decision engine. Takes constraints (team_size, budget, timeline,
scale_requirements, compliance_needs, existing_stack, latency_requirements)
and structural signals. Returns ranked recommendations with tradeoff analysis.

CRITICAL INVARIANT: Small team (1-5) + MVP scale NEVER gets microservices
as the #1 recommendation.
"""

from __future__ import annotations

from typing import Any

from coeus.tools._shared import coerce, emit_event, get_knowledge

# ---------------------------------------------------------------------------
# Tradeoff dimensions for common patterns
# ---------------------------------------------------------------------------

_TRADEOFFS: dict[str, dict[str, str]] = {
    "monolith": {
        "pros": "Simple deployment, easy debugging, low operational overhead, fast iteration",
        "cons": "Scaling ceiling, deployment coupling, technology lock-in",
        "best_for": "Small teams, MVPs, well-understood domains",
    },
    "modular_monolith": {
        "pros": "Module isolation with monolith simplicity, clear boundaries, easy refactoring",
        "cons": "Requires discipline to maintain boundaries, shared deployment",
        "best_for": "Growing teams (6-15), teams preparing for eventual decomposition",
    },
    "microservices": {
        "pros": "Independent deployment, technology diversity, team autonomy, granular scaling",
        "cons": "Operational complexity, distributed debugging, network latency, data consistency",
        "best_for": "Large teams (50+) with platform engineering support",
    },
    "serverless": {
        "pros": "Zero server management, pay-per-use, auto-scaling, rapid prototyping",
        "cons": "Cold starts, vendor lock-in, execution time limits, debugging difficulty",
        "best_for": "Event-driven workloads, sporadic traffic, cost-sensitive projects",
    },
    "event_driven": {
        "pros": "Loose coupling, async processing, natural scalability, audit trail",
        "cons": "Eventual consistency, complex debugging, message ordering challenges",
        "best_for": "Systems with async workflows, audit requirements, high throughput",
    },
    "cqrs": {
        "pros": "Optimized read/write models, scalable reads, clear separation of concerns",
        "cons": "Complexity overhead, eventual consistency, more code to maintain",
        "best_for": "Read-heavy systems with complex query requirements",
    },
    "hexagonal": {
        "pros": "Testability, dependency inversion, infrastructure independence",
        "cons": "More boilerplate, learning curve, over-engineering risk for simple apps",
        "best_for": "Domain-heavy applications, systems requiring infrastructure flexibility",
    },
    "clean_architecture": {
        "pros": "Clear dependency rules, testable business logic, framework independence",
        "cons": "Verbose, many layers, can slow small team velocity",
        "best_for": "Long-lived enterprise applications with complex business rules",
    },
}


# ---------------------------------------------------------------------------
# Fit scoring
# ---------------------------------------------------------------------------

def _compute_fit_score(
    pattern_id: str,
    constraints: dict[str, Any],
) -> float:
    """Compute a 0.0-1.0 fit score for a pattern given constraints.

    This is a heuristic based on constraint alignment, not a learned model.
    """
    score = 0.5  # baseline

    team_size = str(constraints.get("team_size", "")).lower()
    scale = str(constraints.get("scale_requirements", constraints.get("scale", ""))).lower()
    timeline = str(constraints.get("timeline", "")).lower()

    # Small team bonuses/penalties
    if any(x in team_size for x in ["1", "2", "3", "4", "5", "small", "solo"]):
        if pattern_id in ("monolith", "modular_monolith", "serverless"):
            score += 0.3
        elif pattern_id in ("microservices", "service_mesh_pattern", "platform_engineering"):
            score -= 0.4
        elif pattern_id in ("hexagonal", "clean_architecture"):
            score += 0.1

    # Medium team
    if any(x in team_size for x in ["6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "medium"]):
        if pattern_id in ("modular_monolith", "vertical_slice", "hexagonal"):
            score += 0.25
        elif pattern_id == "microservices":
            score -= 0.1

    # Large team
    if any(x in team_size for x in ["50", "100", "large"]):
        if pattern_id in ("microservices", "domain_driven_design", "platform_engineering"):
            score += 0.3
        elif pattern_id == "monolith":
            score -= 0.2

    # Scale alignment
    if any(x in scale for x in ["mvp", "startup", "prototype"]):
        if pattern_id in ("monolith", "modular_monolith", "serverless"):
            score += 0.2
        elif pattern_id == "microservices":
            score -= 0.3
    elif any(x in scale for x in ["enterprise", "hyperscale", "global"]):
        if pattern_id in ("microservices", "event_driven", "cqrs"):
            score += 0.2

    # Timeline pressure
    if any(x in timeline for x in ["week", "days", "urgent", "fast", "mvp"]):
        if pattern_id in ("monolith", "serverless"):
            score += 0.15
        elif pattern_id in ("microservices", "cqrs", "event_sourcing"):
            score -= 0.2

    return max(0.0, min(1.0, round(score, 2)))


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def recommend_pattern(
    structural_signals: list[str],
    constraints: dict | None = None,
    existing_stack: str | None = None,
    conn: object = None,
) -> dict:
    """Recommend architecture patterns based on constraints and signals.

    CRITICAL: Small team (1-5) + MVP scale NEVER gets microservices as #1.

    Args:
        structural_signals: Agent-identified signals about the system.
        constraints: Dict of constraints — team_size, budget, timeline,
            scale_requirements, compliance_needs, existing_stack,
            latency_requirements.
        existing_stack: Optional string describing the current technology stack.
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: constraints_analyzed, recommendations (ranked list),
        conflicts, alternatives.
    """
    structural_signals = coerce(structural_signals, list) or []
    constraints = coerce(constraints, dict) or {}

    if existing_stack and "existing_stack" not in constraints:
        constraints["existing_stack"] = existing_stack

    kb = get_knowledge(conn)

    # 1. Match structural signals against decision rules
    rule_matches = kb.match_structural_signals(structural_signals) if structural_signals else []

    # 2. Apply constraint filtering
    if constraints and rule_matches:
        filtered_rules = kb.filter_by_constraints(
            [rm["rule"] for rm in rule_matches], constraints
        )
        filtered_ids = {r["id"] for r in filtered_rules}
        rule_matches = [
            rm for rm in rule_matches if rm["rule"]["id"] in filtered_ids
        ]

    # 3. Build candidate patterns from rule matches
    seen_pattern_ids: set[str] = set()
    candidates: list[dict[str, Any]] = []

    for rm in rule_matches:
        for pattern in rm.get("recommended_patterns", []):
            pid = pattern.get("id", "")
            if pid and pid not in seen_pattern_ids:
                seen_pattern_ids.add(pid)
                fit_score = _compute_fit_score(pid, constraints)
                tradeoff = _TRADEOFFS.get(pid, {})
                candidates.append({
                    "pattern_id": pid,
                    "pattern_name": pattern.get("name", pid),
                    "rationale": rm["rule"].get("rationale", ""),
                    "tradeoffs": tradeoff,
                    "fit_score": fit_score,
                    "source_rule": rm["rule"]["id"],
                })

    # 4. Collect alternatives
    alternatives_set: set[str] = set()
    for rm in rule_matches:
        for alt in rm.get("alternatives", []):
            alt_id = alt.get("id", "")
            if alt_id and alt_id not in seen_pattern_ids:
                alternatives_set.add(alt_id)

    alternatives: list[dict[str, Any]] = []
    for alt_id in sorted(alternatives_set):
        pat = kb.get_pattern(alt_id) or kb.get_scalability_pattern(alt_id) or kb.get_api_data_pattern(alt_id)
        if pat:
            alternatives.append({
                "pattern_id": pat["id"],
                "pattern_name": pat.get("name", alt_id),
                "fit_score": _compute_fit_score(alt_id, constraints),
            })
        else:
            alternatives.append({
                "pattern_id": alt_id,
                "pattern_name": alt_id,
                "fit_score": _compute_fit_score(alt_id, constraints),
            })

    # 5. Sort candidates by fit_score descending
    candidates.sort(key=lambda c: c["fit_score"], reverse=True)

    # 6. CRITICAL INVARIANT: Small team + MVP → microservices NEVER #1
    team_size = str(constraints.get("team_size", "")).lower()
    scale = str(constraints.get("scale_requirements", constraints.get("scale", ""))).lower()
    is_small_team = any(x in team_size for x in ["1", "2", "3", "4", "5", "small", "solo"])
    is_mvp_scale = any(x in scale for x in ["mvp", "startup", "prototype"])

    if is_small_team and is_mvp_scale and candidates:
        if candidates[0]["pattern_id"] == "microservices":
            # Demote microservices — find first non-microservices candidate
            micro = candidates.pop(0)
            micro["rationale"] = (
                "Microservices demoted: team size (1-5) and MVP scale "
                "cannot absorb the operational overhead. "
                + micro.get("rationale", "")
            )
            # Insert after first position (or at end if only one candidate)
            insert_pos = min(1, len(candidates))
            candidates.insert(insert_pos, micro)

    # 7. Detect conflicts
    conflicts: list[str] = []
    pattern_ids_recommended = [c["pattern_id"] for c in candidates]

    if "monolith" in pattern_ids_recommended and "microservices" in pattern_ids_recommended:
        conflicts.append(
            "Conflicting recommendations: monolith and microservices both matched. "
            "Review constraints — these patterns serve different team sizes and scales."
        )
    if "event_sourcing" in pattern_ids_recommended and is_small_team:
        conflicts.append(
            "Event sourcing recommended but team is small. "
            "Consider if the audit trail requirement justifies the complexity."
        )

    # 8. Assign ranks
    for i, candidate in enumerate(candidates):
        candidate["rank"] = i + 1

    # 9. Build result
    result: dict[str, Any] = {
        "constraints_analyzed": constraints,
        "recommendations": candidates,
        "conflicts": conflicts,
        "alternatives": alternatives,
    }

    emit_event("recommend_pattern", {
        "signals": structural_signals,
        "constraints": {k: str(v)[:50] for k, v in constraints.items()},
        "recommendations_count": len(candidates),
        "top_pattern": candidates[0]["pattern_id"] if candidates else "none",
    })

    return result
