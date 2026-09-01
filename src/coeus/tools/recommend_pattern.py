# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: recommend_pattern — wired onto the Shape C retrieval engine.

The decision engine, and the reusable TEMPLATE the other Coeus tools inherit.
Given the signal ids the caller recognised against ``get_signal_index`` plus a
constraints dict, it:

1. RETRIEVES candidates through one ``kb.hydrate`` call — the proven four-state,
   fail-closed envelope; ``no_match``/``dangling`` abstain structurally, never a husk.
2. RANKS by hydrate's already-proven integer vote key, then layers ONE boolean
   ``avoid_when`` gate tier via a single stable sort: a pattern whose own
   ``avoid_when`` facet the constraints satisfy sinks below every ungated
   candidate, relative order intact. No float, no re-scoring — this is the general
   form of the small-team guarantee (microservices sinks under small-team + MVP
   because its OWN ``avoid_when`` names ``{team_size: 1-15, scale: startup_mvp}``).
3. REASONS conflicts / alternatives / tradeoffs over each retrieved pattern's OWN
   100%-populated fields (``use_when``/``avoid_when``/``principles``/
   ``related_patterns``) — no hardcoded detector table, no tuned scalar.
"""

from __future__ import annotations

from typing import Any

from coeus.knowledge.loader import DANGLING, NO_MATCH, is_gated, split_conditions
from coeus.tools._shared import (
    _MAX_MATCHED_SIGNALS,
    _MAX_RELATED_OUTPUT,
    _bounded_constraints,
    coerce,
    emit_event,
    get_knowledge,
)

# The caller-boundary input caps and the output cross-product cap
# (_MAX_RELATED_OUTPUT — bounds the derived alternatives set across k patterns'
# related_patterns) both live once in _shared, one source of truth per concept.


def _tradeoffs(pattern: dict) -> dict:
    """Derive a tradeoff view from the pattern's OWN fields.

    ``strengths_when`` (its ``use_when`` prose) / ``costs_when`` (its ``avoid_when``
    prose) / ``principles`` — all 100%-populated across the corpus, so this is
    non-empty for every recommendation (the live empty-tradeoff bug is a
    consequence of the deleted 8-of-174 hardcoded ``_TRADEOFFS`` table).
    """
    use_texts, _ = split_conditions(pattern.get("use_when"))
    avoid_texts, _ = split_conditions(pattern.get("avoid_when"))
    return {
        "strengths_when": list(use_texts),
        "costs_when": list(avoid_texts),
        "principles": list(pattern.get("principles") or []),
    }


def recommend_pattern(
    matched_signal_ids: list[str],
    constraints: dict | None = None,
    k: int = 10,
    conn: object = None,
) -> dict:
    """Recommend architecture patterns for a problem's matched signals.

    CRITICAL INVARIANT: a pattern whose own ``avoid_when`` facet the constraints
    satisfy is gated below every ungated candidate — small team (1-5) + MVP scale
    therefore NEVER gets microservices as the #1 recommendation.

    Args:
        matched_signal_ids: Signal ids the caller recognised against
            ``get_signal_index`` (problem-language → sig-id, the proven path).
        constraints: Optional dict — ``team_size`` (numeric range) plus categorical
            ``scale``/``budget``/``timeline``/``latency``/``compliance``/
            ``existing_stack``. Drives the deterministic gate.
        k: Number of ranked recommendations to return (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with the contract keys ``constraints_analyzed`` / ``recommendations``
        (ranked) / ``conflicts`` / ``alternatives`` plus the retrieval envelope
        (``retrieval_state`` / ``unmatched`` / ``dangling``). Fail-closed: an
        abstaining envelope returns empty lists, never a husk.
    """
    matched_signal_ids = coerce(matched_signal_ids, list) or []
    constraints = _bounded_constraints(coerce(constraints, dict) or {})
    try:
        k = int(k)
    except (TypeError, ValueError):
        k = 10

    kb = get_knowledge(conn)

    # 1. RETRIEVE — one hydrate call; the caller-boundary cap is non-amplifying
    #    (the engine's _SEED_CAP already bounds fan-out downstream of it).
    res = kb.hydrate(matched_signal_ids[:_MAX_MATCHED_SIGNALS], k=k)

    envelope = {
        "retrieval_state": res.state,
        "unmatched": list(res.unmatched_signals),
        "dangling": list(res.dangling),
    }

    # 2. Fail closed: recognised-but-empty (no_match) or unresolvable (dangling)
    #    abstains structurally — no recommendations, never the nearest husk.
    if res.state in (NO_MATCH, DANGLING):
        result = {
            "constraints_analyzed": constraints,
            "recommendations": [],
            "conflicts": [],
            "alternatives": [],
            **envelope,
        }
        emit_event("recommend_pattern", {
            "n_signals": len(matched_signal_ids),
            "state": res.state,
            "recommendations_count": 0,
            "top_pattern": "none",
        })
        return result

    # 3. RANK — hydrate already ordered res.patterns by the proven integer vote key.
    #    Layer ONE boolean gate tier with a single stable sort on (gated, rank):
    #    gated patterns sink below every ungated one, relative order within each
    #    tier preserved. The index is the pre-existing hydrate rank, so the key is
    #    a total order — deterministic without relying on sort stability. No float.
    gate_flags = [is_gated(p, constraints) for p in res.patterns]
    order = sorted(range(len(res.patterns)), key=lambda i: (gate_flags[i], i))

    recommendations: list[dict[str, Any]] = []
    recommended_ids: set[str] = set()
    for rank, i in enumerate(order, start=1):
        p = res.patterns[i]
        recommended_ids.add(p["id"])
        recommendations.append({
            "rank": rank,
            "pattern_id": p["id"],
            "pattern_name": p.get("name", p["id"]),
            "rationale": p.get("description", ""),
            "tradeoffs": _tradeoffs(p),
            "retrieval": dict(p["retrieval"]),   # plain dict for the output surface
            "gated": gate_flags[i],
        })

    # 4. CONFLICTS — derived from each pattern's OWN avoid_when: a gated pattern is
    #    in tension with the stated constraints. One source of truth (the gate).
    conflicts = [
        f"{r['pattern_name']} conflicts with your constraints — its own avoid_when "
        f"matches them; ranked below the ungated options."
        for r in recommendations if r["gated"]
    ]

    # 5. ALTERNATIVES — each retrieved pattern's OWN related_patterns, resolved via
    #    _lookup_pattern (never a husk; a truly-absent id is already surfaced in the
    #    envelope's dangling field), deduped, and excluding what is already ranked.
    alternatives: list[dict[str, Any]] = []
    seen_alts: set[str] = set()
    for p in res.patterns:
        for alt_id in p.get("related_patterns", []):
            if alt_id in recommended_ids or alt_id in seen_alts:
                continue
            alt = kb._lookup_pattern(alt_id)
            if alt is None:
                continue
            seen_alts.add(alt_id)
            alternatives.append({
                "pattern_id": alt["id"],
                "pattern_name": alt.get("name", alt_id),
            })
            if len(alternatives) >= _MAX_RELATED_OUTPUT:
                break
        if len(alternatives) >= _MAX_RELATED_OUTPUT:
            break

    result = {
        "constraints_analyzed": constraints,
        "recommendations": recommendations,
        "conflicts": conflicts,
        "alternatives": alternatives,
        **envelope,
    }

    emit_event("recommend_pattern", {
        "n_signals": len(matched_signal_ids),
        "state": res.state,
        "recommendations_count": len(recommendations),
        "gated_count": sum(gate_flags),
        "top_pattern": recommendations[0]["pattern_id"] if recommendations else "none",
    })

    return result
