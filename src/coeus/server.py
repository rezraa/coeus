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
from coeus.tools._shared import coerce, get_knowledge


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
    matched_signal_ids: Union[list[str], str],
    constraints: Union[str, dict, None] = None,
    k: int = 10,
    conn: Any = None,
) -> dict:
    """Name a system's architecture issues from the retrieved patterns' own avoid_when.

    Wired onto the Shape C retrieval engine. Recognise the system's structural
    signals against get_signal_index, pass their ids here with a constraints dict;
    the tool retrieves through the four-state hydrate envelope and reasons one issue
    entry per retrieved pattern over that pattern's OWN avoid_when text. An issue is
    CONFIRMED when the constraints satisfy the pattern's avoid_when facet (it then
    rises above the advisory issues); otherwise ADVISORY. Severity is the human's
    to assign in interpretation, not the tool's.

    Args:
        description: Free-text description of the system (context/telemetry only —
            retrieval is driven by matched_signal_ids, not this text).
        matched_signal_ids: Signal ids recognised against get_signal_index.
        constraints: Optional dict — team_size (numeric range) plus categorical
            scale, budget, timeline, latency, compliance, existing_stack.
        k: Number of retrieved patterns to reason over (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {constraints_analyzed: {...}, architecture_issues: [{pattern_id,
              pattern_name, confirmed, issues: [...], remediation: [...],
              retrieval: {score, ...}}, ...], recommendations: [...],
              retrieval_state, unmatched, dangling}. Fail-closed: an abstaining
              envelope returns empty issues, never a husk.
    """
    return _analyze_architecture(
        description=description,
        matched_signal_ids=coerce(matched_signal_ids, list),
        constraints=coerce(constraints, dict),
        k=k,
        conn=conn,
    )


@mcp.tool()
def evaluate_scalability(
    description: str,
    matched_signal_ids: Union[list[str], str],
    growth_projections: Union[str, dict, None] = None,
    current_scale: Union[str, None] = None,
    constraints: Union[str, dict, None] = None,
    k: int = 10,
    conn: Any = None,
) -> dict:
    """Answer scalability from the described system — what it needs NOW vs grows INTO.

    Wired onto the Shape C retrieval engine. Recognise the system's structural
    signals against get_signal_index, pass their ids here with a constraints dict;
    the tool retrieves through the four-state hydrate envelope and partitions each
    retrieved pattern by the deterministic gate: a pattern the constraints do NOT
    gate is what the system needs NOW (horizon: current); one whose own avoid_when
    facet the constraints satisfy is what it grows INTO (horizon: growth, sorted
    below the current patterns). No hardcoded threshold tiers, no fixed bottleneck
    lists — each entry reasons over the pattern's own use_when/avoid_when/principles.

    Args:
        description: Free-text description of the system (context/telemetry only —
            retrieval is driven by matched_signal_ids, not this text).
        matched_signal_ids: Signal ids recognised against get_signal_index.
        growth_projections: Optional dict with growth estimates, e.g.
            {"users": "10k->1M", "rps": "100->10k", "data": "10GB->1TB"}.
        current_scale: Optional categorical scale ("startup_mvp"/"growth"/
            "enterprise"); folded into constraints['scale'] to drive the partition.
        constraints: Optional dict — team_size (numeric range) plus categorical
            scale, budget, timeline, latency, compliance, existing_stack.
        k: Number of retrieved patterns to reason over (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {current_assessment: {description, current_scale, growth_projections,
              n_matched_signals}, constraints_analyzed: {...}, scaling_patterns:
              [{rank, pattern_id, pattern_name, rationale, horizon, addresses,
              costs_when, principles, related_patterns, retrieval: {score, ...},
              gated}, ...], recommendations: [...], retrieval_state, unmatched,
              dangling}. Fail-closed: an abstaining envelope returns empty scaling
              patterns, never a husk.
    """
    return _evaluate_scalability(
        description=description,
        matched_signal_ids=coerce(matched_signal_ids, list),
        growth_projections=coerce(growth_projections, dict),
        current_scale=current_scale,
        constraints=coerce(constraints, dict),
        k=k,
        conn=conn,
    )


@mcp.tool()
def get_signal_index(conn: Any = None) -> list[dict]:
    """Return the corpus signal index — the recognition vocabulary shared by all
    four concern tools (recommend_pattern, analyze_architecture,
    evaluate_scalability, assess_resilience).

    Each entry is {signal_id, signal_text, pattern_ids}. Recognise a problem's
    structural signals against these texts, then pass the matched signal_ids to
    any of the four tools; each hydrates the signal index into ranked patterns.
    Deterministic and byte-reproducible — ids are content hashes, entries sorted
    by signal_id with sorted pattern_ids.
    """
    return get_knowledge(conn).get_signal_index()


@mcp.tool()
def recommend_pattern(
    matched_signal_ids: Union[list[str], str],
    constraints: Union[str, dict, None] = None,
    k: int = 10,
    conn: Any = None,
) -> dict:
    """Recommend architecture patterns for a problem's matched signals.

    Wired onto the Shape C retrieval engine. Recognise the problem's signals
    against get_signal_index, pass their ids here with a constraints dict; the
    tool retrieves through the four-state hydrate envelope, gates any pattern
    whose own avoid_when facet the constraints satisfy below the ungated
    candidates (small team + MVP therefore never gets microservices as #1), and
    reasons conflicts/alternatives/tradeoffs over each pattern's own fields.

    Args:
        matched_signal_ids: Signal ids recognised against get_signal_index.
        constraints: Optional dict — team_size (numeric range) plus categorical
            scale, budget, timeline, latency, compliance, existing_stack.
        k: Number of ranked recommendations (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {constraints_analyzed: {...}, recommendations: [{rank, pattern_id,
              pattern_name, rationale, tradeoffs, retrieval: {score, ...},
              gated}, ...], conflicts: [...], alternatives: [...],
              retrieval_state, unmatched, dangling}. Fail-closed: an abstaining
              envelope returns empty recommendations, never a husk.
    """
    return _recommend_pattern(
        matched_signal_ids=coerce(matched_signal_ids, list),
        constraints=coerce(constraints, dict),
        k=k,
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
    matched_signal_ids: Union[list[str], str],
    constraints: Union[str, dict, None] = None,
    k: int = 10,
    conn: Any = None,
) -> dict:
    """Retrieve the resilience patterns a system is missing; rank appropriate hardening above premature.

    Wired onto the Shape C retrieval engine. Recognise the system's structural
    signals against get_signal_index, pass their ids here with a constraints dict;
    the tool retrieves through the four-state hydrate envelope and reasons one
    hardening entry per retrieved pattern over that pattern's OWN fields: use_when
    is the resilience gap it fills (protects_against), avoid_when is when it is
    overkill (tradeoffs). A pattern whose own avoid_when facet the constraints
    satisfy is PREMATURE hardening (small team + MVP reaching for a circuit breaker)
    and sinks below the appropriate hardening. posture is integer counts only —
    there is no resilience_score, so a fragile system can never be reported as safe.

    Args:
        system_description: Free-text description of the system (context/telemetry
            only — retrieval is driven by matched_signal_ids, not this text).
        matched_signal_ids: Signal ids recognised against get_signal_index.
        constraints: Optional dict — team_size (numeric range) plus categorical
            scale, budget, timeline, latency, compliance, existing_stack.
        k: Number of retrieved patterns to reason over (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode (injected by Othrys).

    Returns: {constraints_analyzed: {...}, posture: {retrieved, recommended_now,
              premature}, hardening: [{rank, pattern_id, pattern_name, rationale,
              appropriateness, protects_against, tradeoffs, principles,
              related_patterns, retrieval: {score, ...}, gated}, ...],
              recommendations: [...], retrieval_state, unmatched, dangling}.
              Fail-closed: an abstaining envelope returns empty hardening, never
              a husk.
    """
    return _assess_resilience(
        system_description=system_description,
        matched_signal_ids=coerce(matched_signal_ids, list),
        constraints=coerce(constraints, dict),
        k=k,
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
