# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Coeus — Architecture Titan MCP server.

Thin wrappers that delegate to tool modules in coeus/tools/.
Same pattern as Themis/Phoebe/Theia/Mnemos: server registers tools, modules do the work.
"""

from __future__ import annotations

from typing import Any, Union

from fastmcp import FastMCP

from coeus.tools.analyze_architecture import analyze_architecture as _analyze_architecture
from coeus.tools.evaluate_scalability import evaluate_scalability as _evaluate_scalability
from coeus.tools.recommend_pattern import recommend_pattern as _recommend_pattern
from coeus.tools.design_api import design_api as _design_api
from coeus.tools.assess_resilience import assess_resilience as _assess_resilience
from coeus.tools.log_decision import log_decision as _log_decision
from coeus.tools._shared import coerce


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("coeus", instructions=(
    "I am Coeus, Titan of intellect and architectural foresight. "
    "I see the shape of systems before they are built, and I know why structures stand or fall. "
    "I think in tradeoffs, not absolutes. Every architecture decision has a cost. "
    "I never prescribe without understanding constraints — team size, timeline, budget, scale. "
    "I look across time horizons: what works now, what breaks at 10x, what you migrate to at 100x."
))


# ---------------------------------------------------------------------------
# Tool registrations -- thin wrappers
# ---------------------------------------------------------------------------

@mcp.tool()
def analyze_architecture(
    description: str,
    structural_signals: Union[list[str], str],
    constraints: Union[str, dict, None] = None,
    conn: Any = None,
) -> dict:
    """Analyze a system architecture for issues, anti-patterns, and risks.

    Given a description and structural signals about the architecture, returns
    matched rules, identified issues, and scalability flags.

    Args:
        description: Description of the system architecture to analyze.
        structural_signals: Agent-identified signals about the architecture, e.g.
            ["shared-database", "no-circuit-breaker", "synchronous-chain"].
        constraints: Optional dict of constraints for filtering, e.g.
            {"team_size": "1-5", "scale": "startup_mvp"}.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {matched_rules: [...], architecture_issues: [...],
              recommendations: [...], scalability_flags: [...]}
    """
    return _analyze_architecture(
        description=description,
        structural_signals=coerce(structural_signals, list),
        constraints=coerce(constraints, dict),
        conn=conn,
    )


@mcp.tool()
def evaluate_scalability(
    description: str,
    growth_projections: Union[str, dict, None] = None,
    current_scale: Union[str, None] = None,
    conn: Any = None,
) -> dict:
    """Evaluate scalability and produce a tiered scaling plan at 10x, 100x, 1000x.

    Given a system description and growth projections, returns bottleneck
    analysis and recommended patterns at each scale tier.

    Args:
        description: Description of the current system architecture.
        growth_projections: Optional dict with growth estimates, e.g.
            {"users": "10k->1M", "rps": "100->10k", "data": "10GB->1TB"}.
        current_scale: Optional string describing current scale level, e.g.
            "startup_mvp", "growth", "enterprise".
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {current_assessment: {...}, tiers: [{threshold, bottlenecks,
              recommendations, patterns}, ...]}
    """
    return _evaluate_scalability(
        description=description,
        growth_projections=coerce(growth_projections, dict),
        current_scale=current_scale,
        conn=conn,
    )


@mcp.tool()
def recommend_pattern(
    structural_signals: Union[list[str], str],
    constraints: Union[str, dict, None] = None,
    existing_stack: Union[str, None] = None,
    conn: Any = None,
) -> dict:
    """Recommend architecture patterns based on constraints and structural signals.

    The decision engine. Takes constraints (team_size, budget, timeline,
    scale_requirements, compliance_needs) and signals, returns ranked
    recommendations with tradeoff analysis.

    Small team (1-5) + MVP scale NEVER gets microservices as #1.

    Args:
        structural_signals: Agent-identified signals about the system, e.g.
            ["team of 1-5 engineers", "CRUD-dominant", "rapid iteration"].
        constraints: Dict of constraints — team_size, budget, timeline,
            scale_requirements, compliance_needs, existing_stack,
            latency_requirements.
        existing_stack: Optional string describing current technology stack.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {constraints_analyzed: {...}, recommendations: [{rank, pattern_id,
              pattern_name, rationale, tradeoffs, fit_score}, ...],
              conflicts: [...], alternatives: [...]}
    """
    return _recommend_pattern(
        structural_signals=coerce(structural_signals, list),
        constraints=coerce(constraints, dict),
        existing_stack=existing_stack,
        conn=conn,
    )


@mcp.tool()
def design_api(
    domain_model: str,
    communication_requirements: Union[str, dict, None] = None,
    style_preference: Union[str, None] = None,
    conn: Any = None,
) -> dict:
    """Design an API blueprint for a given domain model.

    Takes a domain model and communication requirements, returns an API
    blueprint with recommended style, contract structure, versioning strategy,
    error handling, and authentication approach.

    Args:
        domain_model: Description of the domain entities and relationships,
            e.g. "Users have Orders, Orders contain Items, Items reference Products".
        communication_requirements: Optional dict describing communication
            needs, e.g. {"clients": ["web", "mobile"], "latency": "low"}.
        style_preference: Optional preferred API style ("rest", "graphql",
            "grpc", "websocket", "event-driven"). Auto-detected if omitted.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {recommended_style: "...", rationale: "...",
              contract_structure: {...}, versioning_strategy: {...},
              error_handling: {...}, authentication_approach: {...}}
    """
    return _design_api(
        domain_model=domain_model,
        communication_requirements=coerce(communication_requirements, dict),
        style_preference=style_preference,
        conn=conn,
    )


@mcp.tool()
def assess_resilience(
    system_description: str,
    structural_signals: Union[list[str], str],
    conn: Any = None,
) -> dict:
    """Assess the resilience of a system architecture.

    Evaluates failure modes, identifies single points of failure, missing
    resilience patterns, blast radius, and provides hardening recommendations.

    Args:
        system_description: Description of the system architecture.
        structural_signals: Agent-identified signals about resilience, e.g.
            ["no-circuit-breaker", "single-database", "synchronous-chain"].
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {resilience_score: 0.0-1.0, single_points_of_failure: [...],
              missing_patterns: [...], blast_radius_assessment: [...],
              hardening_recommendations: [...]}
    """
    return _assess_resilience(
        system_description=system_description,
        structural_signals=coerce(structural_signals, list),
        conn=conn,
    )


@mcp.tool()
def log_decision(
    decision_type: str,
    context: str,
    choice_made: str,
    alternatives_considered: Union[list[str], str, None] = None,
    rationale: str = "",
    conn: Any = None,
) -> dict:
    """Record an architecture decision with rationale and alternatives.

    Args:
        decision_type: Category (e.g., "architecture", "pattern", "scalability",
            "api_design", "tradeoff").
        context: The situation or problem that prompted the decision.
        choice_made: The option that was selected.
        alternatives_considered: Other options evaluated but not chosen.
        rationale: Reasoning behind the choice.
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {decision_id, decision_type, recorded, timestamp}
    """
    return _log_decision(
        decision_type=decision_type,
        context=context,
        choice_made=choice_made,
        alternatives_considered=coerce(alternatives_considered, list),
        rationale=rationale,
        conn=conn,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
