# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: evaluate_scalability — wired onto the Shape C retrieval engine.

The THIRD Coeus tool on the shared engine; it inherits the recommend_pattern
template (recommend_pattern m-fa73d51c, analyze_architecture m-7c8f8a50) and
diverges only in the gate's POLARITY. Given the signal ids the caller recognised
against ``get_signal_index`` plus a constraints dict, it:

1. RETRIEVES candidates through one ``kb.hydrate`` call — the proven four-state,
   fail-closed envelope; ``no_match``/``dangling`` abstain to empty scaling
   patterns, never a husk.
2. PARTITIONS each retrieved pattern by the SAME deterministic gate as the sister
   tools (``is_gated`` / ``facet_matches`` / ``split_conditions``), the gate's THIRD
   presentation: recommend_pattern SINKS the gated candidate, analyze_architecture
   ELEVATES it; here the gate PARTITIONS the horizon — a pattern the constraints do
   NOT gate is what the system needs NOW (``horizon: current``); one whose own
   ``avoid_when`` facet the constraints satisfy is what it grows INTO (``horizon:
   growth``), so it costs now but pays later. The SAME total-order sort key as
   recommend_pattern — ``(gated, hydrate-rank)`` — seats every ``current`` pattern
   above every ``growth`` one, relative order within each horizon preserved. Sparse
   by design: a non-startup caller gates nothing and gets all ``current`` — the
   honest "these all apply now" — while ALL k retrieved patterns still contribute.
3. REASONS one scaling entry per retrieved pattern over its OWN 100%-populated
   fields — ``use_when`` (the bottleneck it ADDRESSES), ``avoid_when`` (what it
   COSTS_WHEN), ``principles``, and ``related_patterns`` resolved via the shared
   ``_resolved_related`` — no hardcoded threshold tiers, no retrieval-blind fixed
   bottleneck lists, no legacy substring matcher.
"""

from __future__ import annotations

from typing import Any

from coeus.knowledge.loader import DANGLING, NO_MATCH, is_gated, split_conditions
from coeus.tools._shared import (
    _MAX_DESCRIPTION_LEN,
    _MAX_MATCHED_SIGNALS,
    _MAX_RELATED_OUTPUT,
    _bounded_constraints,
    _resolved_related,
    coerce,
    emit_event,
    get_knowledge,
    normalize_kwargs,
)

# No caller kwarg synonyms; the prose-signal / _SCALE_TIERS legacy vocabulary is
# RETIRED with no alias shim (its replacement, ``matched_signal_ids``, is a
# different vocabulary). Declared for the shared @normalize_kwargs contract.
_ALIASES: dict[str, str] = {}
_IGNORED: set[str] = set()

# Display clip for the caller's OWN description echoed back in current_assessment —
# the untrusted free-text is bounded at the caller boundary by _MAX_DESCRIPTION_LEN;
# this is a further presentation clip, not a security ceiling.
_ASSESSMENT_DESCRIPTION_LEN = 200


@normalize_kwargs
def evaluate_scalability(
    description: str,
    matched_signal_ids: list[str],
    growth_projections: dict | None = None,
    current_scale: str | None = None,
    constraints: dict | None = None,
    k: int = 10,
    conn: object = None,
) -> dict:
    """Answer scalability from the described system — what it needs NOW vs grows INTO.

    CRITICAL INVARIANT (the gate, partitioned): a retrieved pattern the constraints
    do NOT gate is ``horizon: current`` (needed now); one whose own ``avoid_when``
    facet the constraints satisfy is ``horizon: growth`` (grown into later) and sorts
    below every ``current`` pattern. A startup-MVP caller therefore sees the
    over-engineered patterns partitioned into ``growth`` (non-empty); a caller who
    gates nothing sees all ``current`` — graceful "these all apply now" — and in
    BOTH cases every retrieved pattern contributes, ranked, retrieval-driven.

    Args:
        description: Free-text description of the system — context/telemetry only
            (retrieval is driven by ``matched_signal_ids``, not this text). Bounded
            at the caller boundary; echoed (clipped) in ``current_assessment``.
        matched_signal_ids: Signal ids the caller recognised against
            ``get_signal_index`` (problem-language → sig-id, the proven path).
        growth_projections: Optional dict with growth estimates, e.g.
            ``{"users": "10k->1M", "rps": "100->10k", "data": "10GB->1TB"}`` —
            recorded in ``current_assessment`` for the caller's own reference.
        current_scale: Optional categorical scale, e.g. ``"startup_mvp"`` /
            ``"growth"`` / ``"enterprise"``. Folded into ``constraints['scale']``
            (only when the caller did not already set ``scale``) so it drives the
            deterministic horizon partition.
        constraints: Optional dict — ``team_size`` (numeric range) plus categorical
            ``scale``/``budget``/``timeline``/``latency``/``compliance``/
            ``existing_stack``. Drives the current/growth partition.
        k: Number of retrieved patterns to reason over (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with ``current_assessment`` / ``constraints_analyzed`` /
        ``scaling_patterns`` (one entry per retrieved pattern, ``current`` first) /
        ``recommendations`` (deduped related-pattern set) plus the retrieval
        envelope (``retrieval_state`` / ``unmatched`` / ``dangling``). Fail-closed:
        an abstaining envelope returns empty scaling patterns, never a husk.
    """
    description = description[:_MAX_DESCRIPTION_LEN] if isinstance(description, str) else ""
    matched_signal_ids = coerce(matched_signal_ids, list) or []
    growth_projections = coerce(growth_projections, dict) or {}
    raw_constraints = coerce(constraints, dict) or {}
    # Fold current_scale into constraints['scale'] with setdefault semantics (the
    # explicit constraints['scale'] wins), on a fresh copy — never mutate the caller.
    if current_scale is not None and "scale" not in raw_constraints:
        raw_constraints = {**raw_constraints, "scale": current_scale}
    constraints = _bounded_constraints(raw_constraints)
    try:
        k = int(k)
    except (TypeError, ValueError):
        k = 10

    kb = get_knowledge(conn)

    # current_assessment — the caller's OWN context echoed back (description clipped,
    # scale, growth projections, and the signal count that drove retrieval). The
    # legacy relevant_rules + keyword matched_signals are dropped (rule-derived, dead).
    current_assessment: dict[str, Any] = {
        "description": description[:_ASSESSMENT_DESCRIPTION_LEN],
        "current_scale": current_scale or "unknown",
        "growth_projections": growth_projections,
        "n_matched_signals": len(matched_signal_ids),
    }

    # 1. RETRIEVE — one hydrate call; the caller-boundary cap is non-amplifying
    #    (the engine's _SEED_CAP already bounds fan-out downstream of it).
    res = kb.hydrate(matched_signal_ids[:_MAX_MATCHED_SIGNALS], k=k)

    envelope = {
        "retrieval_state": res.state,
        "unmatched": list(res.unmatched_signals),
        "dangling": list(res.dangling),
    }

    # 2. Fail closed: recognised-but-empty (no_match) or unresolvable (dangling)
    #    abstains structurally — no scaling patterns, never the nearest husk.
    if res.state in (NO_MATCH, DANGLING):
        result = {
            "current_assessment": current_assessment,
            "constraints_analyzed": constraints,
            "scaling_patterns": [],
            "recommendations": [],
            **envelope,
        }
        emit_event("evaluate_scalability", {
            "description": description[:120],
            "current_scale": current_scale or "unknown",
            "n_signals": len(matched_signal_ids),
            "state": res.state,
            "scaling_patterns_count": 0,
            "growth_count": 0,
        })
        return result

    # 3. PARTITION — hydrate already ordered res.patterns by the proven integer vote
    #    key. Layer ONE boolean horizon tier with a single total-order sort on
    #    (gated, hydrate-rank): an ungated pattern (horizon current) sorts above
    #    every gated one (horizon growth), relative order within each horizon
    #    preserved. The index is the pre-existing hydrate rank, so the key is a total
    #    order — deterministic without relying on sort stability. No float. Same key
    #    as recommend_pattern's sink; only the label it carries differs.
    gated_flags = [is_gated(p, constraints) for p in res.patterns]
    order = sorted(range(len(res.patterns)), key=lambda i: (gated_flags[i], i))

    # 4. REASON — one scaling entry per retrieved pattern over its OWN fields:
    #    use_when = the bottleneck it addresses; avoid_when = what it costs when;
    #    principles + related_patterns (the shared resolver). No hardcoded lists.
    scaling_patterns: list[dict[str, Any]] = []
    scaling_ids: set[str] = set()
    for rank, i in enumerate(order, start=1):
        p = res.patterns[i]
        addresses, _ = split_conditions(p.get("use_when"))
        costs_when, _ = split_conditions(p.get("avoid_when"))
        scaling_ids.add(p["id"])
        scaling_patterns.append({
            "rank": rank,
            "pattern_id": p["id"],
            "pattern_name": p.get("name", p["id"]),
            "rationale": p.get("description", ""),
            "horizon": "growth" if gated_flags[i] else "current",
            "addresses": list(addresses),
            "costs_when": list(costs_when),
            "principles": list(p.get("principles") or []),
            "related_patterns": _resolved_related(kb, p),
            "retrieval": dict(p["retrieval"]),   # plain dict for the output surface
            "gated": gated_flags[i],
        })

    # 5. RECOMMENDATIONS — the deduped related-pattern set across the scaling
    #    patterns' OWN related_patterns, excluding what is already a scaling pattern
    #    (mirrors recommend_pattern's alternatives / analyze's remediation set). One
    #    source of truth (_resolved_related), one shared cap (_MAX_RELATED_OUTPUT).
    recommendations: list[dict[str, Any]] = []
    seen_recs: set[str] = set()
    for sp in scaling_patterns:
        for rec in sp["related_patterns"]:
            rid = rec["pattern_id"]
            if rid in scaling_ids or rid in seen_recs:
                continue
            seen_recs.add(rid)
            recommendations.append(rec)
            if len(recommendations) >= _MAX_RELATED_OUTPUT:
                break
        if len(recommendations) >= _MAX_RELATED_OUTPUT:
            break

    result = {
        "current_assessment": current_assessment,
        "constraints_analyzed": constraints,
        "scaling_patterns": scaling_patterns,
        "recommendations": recommendations,
        **envelope,
    }

    emit_event("evaluate_scalability", {
        "description": description[:120],
        "current_scale": current_scale or "unknown",
        "n_signals": len(matched_signal_ids),
        "state": res.state,
        "scaling_patterns_count": len(scaling_patterns),
        "growth_count": sum(gated_flags),
    })

    return result
