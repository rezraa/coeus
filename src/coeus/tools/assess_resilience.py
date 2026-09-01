# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: assess_resilience — wired onto the Shape C retrieval engine.

The FOURTH Coeus tool on the shared engine; it inherits the recommend_pattern
template (recommend_pattern m-fa73d51c, analyze_architecture m-7c8f8a50,
evaluate_scalability) and reuses its gate polarity EXACTLY — the SINK. Given the
signal ids the caller recognised against ``get_signal_index`` plus a constraints
dict, it:

1. RETRIEVES the resilience patterns the system is missing through one
   ``kb.hydrate`` call — the proven four-state, fail-closed envelope;
   ``no_match``/``dangling`` abstain to empty hardening, never a husk.
2. RANKS by hydrate's integer vote key, then layers ONE boolean gate tier via the
   SAME total-order sort as recommend_pattern — ``(gated, hydrate-rank)``: a
   retrieved resilience pattern whose OWN ``avoid_when`` facet the constraints
   satisfy is PREMATURE hardening (circuit_breaker/bulkhead/fallback name
   ``{team_size: 1-5, scale: startup_mvp}``) and sinks below every appropriate one,
   relative order intact. This is the premature-complexity guard: appropriate
   hardening ranks ABOVE premature hardening, graded by each pattern's OWN fields.
3. REASONS one hardening entry per retrieved pattern over its OWN 100%-populated
   fields — ``use_when`` is the resilience gap it fills (``protects_against``; a
   missing pattern's use_when IS the recommendation), ``avoid_when`` is when it is
   overkill (``tradeoffs``), ``principles``, and ``related_patterns`` via the shared
   ``_resolved_related``. No hardcoded SPOF/missing/blast table, no fabricated
   severity, no float score.

A SPOF is an absent redundancy pattern surfaced as its remediation; a blast
condition is a coupling whose remediation is a decoupling pattern — both collapse
into retrieval. ``posture`` is integer counts only ({retrieved, recommended_now,
premature}); there is NO resilience_score, so a fragile system can never report
fabricated safety.
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

# Caller kwarg synonyms remapped to the canonical signature. The system→
# system_description alias survives the rewrite (mirrors analyze_architecture's
# system→description); the prose ``structural_signals`` param is RETIRED with no
# alias shim (its replacement, ``matched_signal_ids``, is a different vocabulary).
_ALIASES = {"system": "system_description"}
_IGNORED: set[str] = set()

# The recommendations set is the deduped related-pattern surface (_resolved_related)
# and its size cap (_MAX_RELATED_OUTPUT) — both the shared primitives in _shared, so
# the resolver and cap have one source of truth across every concern tool.


@normalize_kwargs
def assess_resilience(
    system_description: str,
    matched_signal_ids: list[str],
    constraints: dict | None = None,
    k: int = 10,
    conn: object = None,
) -> dict:
    """Retrieve the resilience patterns a system is missing; rank appropriate hardening above premature.

    CRITICAL INVARIANT (the gate, SINK): a retrieved resilience pattern whose OWN
    ``avoid_when`` facet the constraints satisfy is PREMATURE hardening and sinks
    below every appropriate one — a startup-MVP caller therefore gets
    circuit_breaker/bulkhead flagged ``premature`` and ranked under the hardening it
    actually needs now, while a caller who gates nothing gets all ``recommended``.
    ``posture`` is integer counts only; there is NO resilience_score, so a fragile
    system can never be reported as safe.

    Args:
        system_description: Free-text description of the system — context/telemetry
            only (retrieval is driven by ``matched_signal_ids``, not this text).
            Bounded at the caller boundary.
        matched_signal_ids: Signal ids the caller recognised against
            ``get_signal_index`` (problem-language → sig-id, the proven path).
        constraints: Optional dict — ``team_size`` (numeric range) plus categorical
            ``scale``/``budget``/``timeline``/``latency``/``compliance``/
            ``existing_stack``. Drives the deterministic premature-hardening sink.
        k: Number of retrieved patterns to reason over (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with ``constraints_analyzed`` / ``posture`` (integer counts
        {retrieved, recommended_now, premature}) / ``hardening`` (one entry per
        retrieved pattern, appropriate first) / ``recommendations`` (deduped
        related-pattern set) plus the retrieval envelope (``retrieval_state`` /
        ``unmatched`` / ``dangling``). Fail-closed: an abstaining envelope returns
        empty hardening, never a husk.
    """
    system_description = (
        system_description[:_MAX_DESCRIPTION_LEN]
        if isinstance(system_description, str) else ""
    )
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
    #    abstains structurally — no hardening, never the nearest husk. posture is
    #    all-zero integer counts (never a fabricated score).
    if res.state in (NO_MATCH, DANGLING):
        result = {
            "constraints_analyzed": constraints,
            "posture": {"retrieved": 0, "recommended_now": 0, "premature": 0},
            "hardening": [],
            "recommendations": [],
            **envelope,
        }
        emit_event("assess_resilience", {
            "description": system_description[:120],
            "n_signals": len(matched_signal_ids),
            "state": res.state,
            "hardening_count": 0,
            "premature_count": 0,
        })
        return result

    # 3. RANK — SINK. hydrate already ordered res.patterns by the proven integer vote
    #    key. Layer ONE boolean gate tier with a single total-order sort on
    #    (gated, hydrate-rank): a PREMATURE pattern (its own avoid_when facet the
    #    constraints satisfy) sinks below every appropriate one, relative order within
    #    each tier preserved. The index is the pre-existing hydrate rank, so the key
    #    is a total order — deterministic without relying on sort stability. No float.
    #    Identical to recommend_pattern's sink; only the label it carries differs.
    gate_flags = [is_gated(p, constraints) for p in res.patterns]
    order = sorted(range(len(res.patterns)), key=lambda i: (gate_flags[i], i))

    # 4. REASON — one hardening entry per retrieved pattern over its OWN fields:
    #    use_when = the resilience gap it fills (a missing pattern's use_when IS the
    #    recommendation); avoid_when = when it is overkill; principles;
    #    related_patterns (the shared resolver). No hardcoded SPOF/missing/blast list.
    hardening: list[dict[str, Any]] = []
    hardening_ids: set[str] = set()
    for rank, i in enumerate(order, start=1):
        p = res.patterns[i]
        protects_against, _ = split_conditions(p.get("use_when"))
        tradeoffs, _ = split_conditions(p.get("avoid_when"))
        hardening_ids.add(p["id"])
        hardening.append({
            "rank": rank,
            "pattern_id": p["id"],
            "pattern_name": p.get("name", p["id"]),
            "rationale": p.get("description", ""),
            "appropriateness": "premature" if gate_flags[i] else "recommended",
            "protects_against": list(protects_against),
            "tradeoffs": list(tradeoffs),
            "principles": list(p.get("principles") or []),
            "related_patterns": _resolved_related(kb, p),
            "retrieval": dict(p["retrieval"]),   # plain dict for the output surface
            "gated": gate_flags[i],
        })

    # 5. POSTURE — integer counts ONLY (no derived ratio that smells like the old
    #    float score). A fragile system retrieves the hardening it lacks, so
    #    recommended_now is non-zero, and there is no scalar to fabricate safety.
    premature = sum(gate_flags)
    posture = {
        "retrieved": len(hardening),
        "recommended_now": len(hardening) - premature,
        "premature": premature,
    }

    # 6. RECOMMENDATIONS — the deduped related-pattern set across the hardening
    #    patterns' OWN related_patterns, excluding what is already a hardening pattern
    #    (mirrors recommend_pattern's alternatives / the sisters' recommendations).
    #    One source of truth (_resolved_related), one shared cap (_MAX_RELATED_OUTPUT).
    recommendations: list[dict[str, Any]] = []
    seen_recs: set[str] = set()
    for h in hardening:
        for rec in h["related_patterns"]:
            rid = rec["pattern_id"]
            if rid in hardening_ids or rid in seen_recs:
                continue
            seen_recs.add(rid)
            recommendations.append(rec)
            if len(recommendations) >= _MAX_RELATED_OUTPUT:
                break
        if len(recommendations) >= _MAX_RELATED_OUTPUT:
            break

    result = {
        "constraints_analyzed": constraints,
        "posture": posture,
        "hardening": hardening,
        "recommendations": recommendations,
        **envelope,
    }

    emit_event("assess_resilience", {
        "description": system_description[:120],
        "n_signals": len(matched_signal_ids),
        "state": res.state,
        "hardening_count": len(hardening),
        "premature_count": premature,
    })

    return result
