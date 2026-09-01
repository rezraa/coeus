# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: analyze_architecture — wired onto the Shape C retrieval engine.

The SECOND Coeus tool on the shared engine; it inherits the recommend_pattern
template (retrieve → concern gate → concern reasoning over own fields → envelope)
and diverges only where the concern demands it. Given the signal ids the caller
recognised against ``get_signal_index`` plus a constraints dict, it:

1. RETRIEVES candidates through one ``kb.hydrate`` call — the proven four-state,
   fail-closed envelope; ``no_match``/``dangling`` abstain to empty issues, never
   a husk.
2. TIERS each retrieved pattern by the SAME deterministic gate as recommend_pattern
   (``is_gated`` / ``facet_matches`` / ``split_conditions``), but with the semantic
   INVERTED: an issue is CONFIRMED when the system's constraints satisfy the
   pattern's own ``avoid_when`` facet, so a confirmed issue RISES above the
   advisory tier (recommend_pattern sinks the gated recommendation; here the gate
   ELEVATES the confirmed risk). Confirm covers only the 63/174 facet-carrying
   patterns, so ADVISORY is the default and CONFIRMED the sparse elevation — ALL
   k retrieved patterns contribute an entry, tiered.
3. REASONS one issue entry per retrieved pattern over its OWN 100%-populated
   ``avoid_when`` text (the issue bodies, via ``split_conditions``) and its OWN
   ``related_patterns`` resolved via ``_lookup_pattern`` (the remediation, 0%
   dangling, never a husk) — no hardcoded anti-pattern table, no fabricated
   severity.
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

# Caller kwarg synonyms remapped to the canonical signature. The system→description
# alias survives the rewrite; the prose ``structural_signals`` param is RETIRED with
# no alias shim (its replacement, ``matched_signal_ids``, is a different vocabulary).
_ALIASES = {"system": "description"}
_IGNORED: set[str] = set()

# The remediation set is the deduped related-pattern surface (_resolved_related) and
# its size cap (_MAX_RELATED_OUTPUT) — both the shared primitives in _shared, so the
# resolver and cap have one source of truth across every concern tool.


@normalize_kwargs
def analyze_architecture(
    description: str,
    matched_signal_ids: list[str],
    constraints: dict | None = None,
    k: int = 10,
    conn: object = None,
) -> dict:
    """Name a system's architecture issues from the retrieved patterns' own avoid_when.

    CRITICAL INVARIANT (the gate, inverted): an issue is CONFIRMED when the system's
    constraints satisfy the pattern's own ``avoid_when`` facet, and every confirmed
    issue sorts above every advisory one — so a risk the constraints actually
    trigger (small team + MVP reaching for microservices) rises to the top, while
    the ~64% no-facet-match majority still contribute advisory issues rather than
    reproducing the dead-tool empty result.

    Args:
        description: Free-text description of the system — context/telemetry only
            (retrieval is driven by ``matched_signal_ids``, not this text). Bounded
            at the caller boundary.
        matched_signal_ids: Signal ids the caller recognised against
            ``get_signal_index`` (problem-language → sig-id, the proven path).
        constraints: Optional dict — ``team_size`` (numeric range) plus categorical
            ``scale``/``budget``/``timeline``/``latency``/``compliance``/
            ``existing_stack``. Drives the deterministic confirm/advisory tiering.
        k: Number of retrieved patterns to reason over (engine-clamped to 1..50).
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with ``constraints_analyzed`` / ``architecture_issues`` (one entry per
        retrieved pattern, confirmed issues first) / ``recommendations`` (deduped
        remediation set) plus the retrieval envelope (``retrieval_state`` /
        ``unmatched`` / ``dangling``). Fail-closed: an abstaining envelope returns
        empty issues, never a husk.
    """
    description = description[:_MAX_DESCRIPTION_LEN] if isinstance(description, str) else ""
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
    #    abstains structurally — no issues, never the nearest husk.
    if res.state in (NO_MATCH, DANGLING):
        result = {
            "constraints_analyzed": constraints,
            "architecture_issues": [],
            "recommendations": [],
            **envelope,
        }
        emit_event("analyze_architecture", {
            "description": description[:120],
            "n_signals": len(matched_signal_ids),
            "state": res.state,
            "architecture_issues_count": 0,
            "confirmed_count": 0,
        })
        return result

    # 3. TIER — hydrate already ordered res.patterns by the proven integer vote key.
    #    Layer ONE boolean confirm tier with a single total-order sort on
    #    (not confirmed, hydrate-rank): a confirmed issue (its own avoid_when facet
    #    the constraints satisfy) rises above every advisory one, relative order
    #    within each tier preserved. The index is the pre-existing hydrate rank, so
    #    the key is a total order — deterministic without relying on sort stability.
    #    This is the clean inversion of recommend_pattern's (gated, rank) sink.
    confirmed_flags = [is_gated(p, constraints) for p in res.patterns]
    order = sorted(range(len(res.patterns)), key=lambda i: (not confirmed_flags[i], i))

    # 4. REASON — one issue entry per retrieved pattern over its OWN fields:
    #    avoid_when text = the issue bodies; related_patterns = the remediation.
    architecture_issues: list[dict[str, Any]] = []
    issue_pattern_ids: set[str] = set()
    for i in order:
        p = res.patterns[i]
        avoid_texts, _ = split_conditions(p.get("avoid_when"))
        issue_pattern_ids.add(p["id"])
        architecture_issues.append({
            "pattern_id": p["id"],
            "pattern_name": p.get("name", p["id"]),
            "confirmed": confirmed_flags[i],
            "issues": list(avoid_texts),
            "remediation": _resolved_related(kb, p),
            "retrieval": dict(p["retrieval"]),   # plain dict for the output surface
        })

    # 5. RECOMMENDATIONS — the deduped remediation set across the issue-patterns'
    #    OWN related_patterns, excluding what is already an issue pattern (mirrors
    #    recommend_pattern's alternatives). One source of truth (_resolved_related).
    recommendations: list[dict[str, Any]] = []
    seen_recs: set[str] = set()
    for issue in architecture_issues:
        for rec in issue["remediation"]:
            rid = rec["pattern_id"]
            if rid in issue_pattern_ids or rid in seen_recs:
                continue
            seen_recs.add(rid)
            recommendations.append(rec)
            if len(recommendations) >= _MAX_RELATED_OUTPUT:
                break
        if len(recommendations) >= _MAX_RELATED_OUTPUT:
            break

    result = {
        "constraints_analyzed": constraints,
        "architecture_issues": architecture_issues,
        "recommendations": recommendations,
        **envelope,
    }

    emit_event("analyze_architecture", {
        "description": description[:120],
        "n_signals": len(matched_signal_ids),
        "state": res.state,
        "architecture_issues_count": len(architecture_issues),
        "confirmed_count": sum(confirmed_flags),
    })

    return result
