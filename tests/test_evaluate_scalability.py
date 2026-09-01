# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""evaluate_scalability wired onto the Shape C engine — story-558f4a76.

The THIRD Coeus tool on the shared engine. It retrieves through one ``kb.hydrate``
call (the proven four-state, fail-closed envelope) and PARTITIONS each retrieved
pattern by the SAME deterministic gate as recommend_pattern / analyze_architecture —
but the gate's THIRD polarity: a pattern the constraints do NOT gate is what the
system needs NOW (``horizon: current``), one whose own ``avoid_when`` facet the
constraints satisfy is what it grows INTO (``horizon: growth``), seated below the
current patterns by the same ``(gated, hydrate-rank)`` key recommend_pattern sinks
by. No hardcoded ``_SCALE_TIERS`` (the retrieval-BLIND 10x/100x/1000x threshold
tiers + fixed bottleneck/pattern lists), no legacy substring matcher.

This is the one home for the rebuilt tool's proofs. It carries:

* the ANCHOR, rewritten RED-first — two OPPOSITE systems (a scaled-out signal set
  and a single-node signal set) now yield DIFFERENT ``scaling_patterns`` (a mutant
  that ignores ``matched_signal_ids`` and reverts to a fixed list fails this); and
  the partition FIRING — under startup-MVP microservices (raw hydrate rank 1) is
  gated into ``growth`` and sinks BELOW monolith (``current``), the growth horizon
  is NON-EMPTY, while a caller who gates nothing degrades gracefully to all-``current``;
* the seven superseded tests KILLED-WITH-REASON (Directive 10): the three fixed
  threshold tiers, the fixed bottleneck lists, the fixed per-tier recommendations,
  the retrieval-blind patterns, the old current_assessment, empty-description, and
  the growth-projection routing;
* BAR 1 — the frozen coeus-Gmetric-v1 recomputed THROUGH the tool's hydrate path
  (>= 86/130, no constraints so no partition drop); BAR 2 — the before/after delta
  against the S0 legacy pin (retrieval-BLIND before, retrieval-driven after);
* the envelope fail-closed states, determinism (incl. a fresh loader), the Hyperion
  caller-boundary ceilings, the deletions proven, the DRY (_resolved_related +
  the unified output cap live once in _shared), and the deep-freeze that keeps the
  singleton corpus uncorrupted through the tool.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import coeus.tools._shared as _shared
from coeus.knowledge.loader import DANGLING, HIT, LOW_CONFIDENCE, NO_MATCH, KnowledgeLoader, _signal_id
from coeus.tools._shared import (
    _MAX_CONSTRAINTS,
    _MAX_CONSTRAINT_VALUE_LEN,
    _MAX_DESCRIPTION_LEN,
    _MAX_MATCHED_SIGNALS,
)
from coeus.tools.evaluate_scalability import evaluate_scalability

_DATA = Path(__file__).parent / "data"
_GM = _DATA / "gmetric"
FROZEN = json.loads((_GM / "frozen_metric.json").read_text(encoding="utf-8"))
MATCHES = json.loads((_GM / "coeus_matches_v2.json").read_text(encoding="utf-8"))
PIN = json.loads((_DATA / "baseline_evaluate_scalability_pinned.json").read_text(encoding="utf-8"))

COUNCIL_BAR10 = 86  # bar-1: recall@10 the engine already meets; the tool path must too

# Constraints that satisfy microservices' OWN avoid_when facet {team_size:1-15, scale:startup_mvp}
SMALL_MVP = {"team_size": "1-3", "scale": "startup_mvp"}
LARGE_ENT = {"team_size": "50+", "scale": "enterprise"}

DESC = "context/telemetry only"


# ---------------------------------------------------------------------------
# helpers — derive sig-id inputs from the live index so tests track the corpus
# ---------------------------------------------------------------------------

def _sigs_for(kb: KnowledgeLoader, pid: str, n: int) -> list[str]:
    return [e["signal_id"] for e in kb.get_signal_index() if pid in e["pattern_ids"]][:n]


def _anchor_signals(kb: KnowledgeLoader) -> list[str]:
    """2 microservices + 2 monolith signals — the same seed set as the sister anchors.
    microservices hydrates as the rank-1 seed; under startup-MVP its own avoid_when
    facet gates it into 'growth', so it must sink below monolith ('current')."""
    return _sigs_for(kb, "microservices", 2) + _sigs_for(kb, "monolith", 2)


def _scaled_signals(kb: KnowledgeLoader) -> list[str]:
    """An already-scaled system: multi-region + event-driven signals."""
    return _sigs_for(kb, "multi_region", 2) + _sigs_for(kb, "event_driven", 2)


def _single_signals(kb: KnowledgeLoader) -> list[str]:
    """A single-node system: monolith + cache-aside signals."""
    return _sigs_for(kb, "monolith", 2) + _sigs_for(kb, "cache_aside", 2)


def _sp_ids(res: dict) -> list[str]:
    return [s["pattern_id"] for s in res["scaling_patterns"]]


def _by_id(res: dict) -> dict[str, dict]:
    return {s["pattern_id"]: s for s in res["scaling_patterns"]}


def _pos(res: dict, pid: str) -> int:
    return _sp_ids(res).index(pid)


def _fresh_call(**kwargs) -> dict:
    """evaluate_scalability forced through a freshly constructed loader (byte-repro)."""
    _shared._knowledge = None
    return evaluate_scalability(**kwargs)


def _golds_by_problem() -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for row in FROZEN["reachable_set_map"]:
        g[row["problem"]].append(row)
    return g


# ===================================================================
# ANCHOR — retrieval-driven + the gate PARTITIONED, rewritten RED-first
# ===================================================================

class TestRetrievalDriven:
    def test_opposite_systems_yield_different_scaling_patterns(self, kb: KnowledgeLoader) -> None:
        """RED-first (Directive 8): the retrieval-BLIND premise pinned in S0 — an
        already-scaled system and a single-node system returned BYTE-IDENTICAL tiers.
        The rebuild is retrieval-DRIVEN: two opposite signal sets now yield DIFFERENT
        scaling_patterns. A mutant that ignores matched_signal_ids and reverts to a
        fixed list makes the two sets identical again and FAILS this (proven by the
        fixed-list mutant in the plan record)."""
        scaled = evaluate_scalability(description=DESC, matched_signal_ids=_scaled_signals(kb),
                                      current_scale="enterprise")
        single = evaluate_scalability(description=DESC, matched_signal_ids=_single_signals(kb),
                                      current_scale="startup_mvp")
        assert scaled["retrieval_state"] in (HIT, LOW_CONFIDENCE)
        assert single["retrieval_state"] in (HIT, LOW_CONFIDENCE)
        assert set(_sp_ids(scaled)) != set(_sp_ids(single)), \
            "retrieval-driven: opposite systems must differ (the S0 blindness is gone)"


class TestHorizonPartition:
    def test_startup_gates_into_growth_and_current_sorts_first(self, kb: KnowledgeLoader) -> None:
        """RED-first (Directive 8): microservices' own avoid_when facet
        {team_size:1-15, scale:startup_mvp} is satisfied by SMALL_MVP, so it partitions
        into 'growth' — and every 'current' pattern sorts above every 'growth' one.

        The FIRING binding, not an accidental order: microservices is the raw hydrate
        rank-1 seed; the partition must sink it BELOW monolith (raw rank 2, ungated →
        'current'). The no-constraints control below proves microservices leads by
        default — so only the gate can seat it under monolith."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        by_id = _by_id(res)
        assert "microservices" in by_id, "microservices must be in the retrieved set"
        assert by_id["microservices"]["horizon"] == "growth"
        assert by_id["microservices"]["gated"] is True
        # every 'current' precedes every 'growth'
        current_pos = [n for n, s in enumerate(res["scaling_patterns"]) if s["horizon"] == "current"]
        growth_pos = [n for n, s in enumerate(res["scaling_patterns"]) if s["horizon"] == "growth"]
        assert current_pos and growth_pos, "both horizons must be present in this set"
        assert max(current_pos) < min(growth_pos)
        # the FIRING binding: microservices (raw rank 1) now sinks below monolith (current)
        assert by_id["monolith"]["horizon"] == "current"
        assert _pos(res, "monolith") < _pos(res, "microservices")
        # growth horizon NON-EMPTY (the partition fired)
        assert any(s["horizon"] == "growth" for s in res["scaling_patterns"])

    def test_no_constraints_graceful_all_current(self, kb: KnowledgeLoader) -> None:
        """Graceful degradation: a caller who supplies no gating scale gates nothing —
        every retrieved pattern is 'current' (the honest 'these all apply now'), the
        growth horizon is empty, and the order is exactly hydrate's (microservices,
        the rank-1 seed, leads). This is the ordering the startup partition INVERTS."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints={})
        assert all(s["horizon"] == "current" for s in res["scaling_patterns"])
        assert all(s["gated"] is False for s in res["scaling_patterns"])
        assert res["scaling_patterns"][0]["pattern_id"] == "microservices"
        assert _pos(res, "microservices") < _pos(res, "monolith")

    def test_non_startup_scale_does_not_gate_startup_patterns(self, kb: KnowledgeLoader) -> None:
        """A non-startup caller (growth-phase) does not get startup-only patterns shoved
        into 'growth': microservices' startup_mvp facet does not match scale='growth',
        so it stays 'current'. Firing is categorical, not a blanket 'everything is
        future work'."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints={"team_size": "10-20", "scale": "growth"})
        by_id = _by_id(res)
        assert by_id["microservices"]["horizon"] == "current"
        assert by_id["microservices"]["gated"] is False

    def test_all_k_patterns_contribute(self, kb: KnowledgeLoader) -> None:
        """ALL k retrieved patterns yield a scaling entry, partitioned — surfacing only
        the gated ones would reproduce the dead-tool's blindness. Both horizons are
        present under SMALL_MVP and every entry carries its own addresses text."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert len(res["scaling_patterns"]) >= 5
        assert any(s["horizon"] == "current" for s in res["scaling_patterns"])
        assert any(s["horizon"] == "growth" for s in res["scaling_patterns"])
        for s in res["scaling_patterns"]:
            assert s["addresses"], f"empty use_when addresses for {s['pattern_id']}"

    def test_ranks_are_contiguous(self, kb: KnowledgeLoader) -> None:
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert [s["rank"] for s in res["scaling_patterns"]] == list(
            range(1, len(res["scaling_patterns"]) + 1))


# ===================================================================
# KILLED-WITH-REASON (Directive 10) — the seven superseded legacy tests
# ===================================================================

class TestKilledLegacyTests:
    def test_no_hardcoded_threshold_tiers(self, kb: KnowledgeLoader) -> None:
        """KILLED test_tiered_results_returned: it asserted exactly three tiers with
        thresholds ['10x','100x','1000x'] from _SCALE_TIERS. REPLACED: there is no
        'tiers' key at all — scaling_patterns are retrieved and partitioned by horizon
        (current/growth), not bucketed into fixed thresholds."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert "tiers" not in res
        assert "scaling_patterns" in res
        for s in res["scaling_patterns"]:
            assert "threshold" not in s
            assert s["horizon"] in ("current", "growth")

    def test_bottlenecks_from_own_use_when_not_fixed_list(self, kb: KnowledgeLoader) -> None:
        """KILLED test_each_tier_has_bottlenecks: it asserted each fixed tier carried a
        hardcoded typical_bottlenecks list. REPLACED (strictly stronger): the bottleneck
        a pattern addresses is its OWN use_when text (addresses), and every retrieved
        pattern carries one — no fixed bottleneck strings anywhere."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        for s in res["scaling_patterns"]:
            assert isinstance(s["addresses"], list) and s["addresses"]
            assert "bottlenecks" not in s

    def test_recommendations_re_sourced_not_fixed_per_tier(self, kb: KnowledgeLoader) -> None:
        """KILLED test_each_tier_has_recommendations: it asserted fixed per-tier
        recommendation strings ('Add load balancer and horizontal scaling ...').
        REPLACED: recommendations are the deduped related-pattern set the retrieved
        patterns actually reference, every one resolvable to a real corpus pattern."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert isinstance(res["recommendations"], list)
        for r in res["recommendations"]:
            assert kb._lookup_pattern(r["pattern_id"]) is not None
            assert isinstance(r.get("pattern_name"), str) and not isinstance(r.get("pattern_name"), type(None))

    def test_patterns_are_retrieval_driven(self, kb: KnowledgeLoader) -> None:
        """KILLED test_each_tier_has_patterns: it asserted each fixed tier's key_patterns
        resolved. REPLACED: patterns come from the hydrate retrieval, carry an integer
        retrieval vote, and DIFFER for different inputs (bound in TestRetrievalDriven)."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert res["scaling_patterns"]
        for s in res["scaling_patterns"]:
            score = s["retrieval"]["score"]
            assert isinstance(score, int) and not isinstance(score, bool) and score >= 1

    def test_current_assessment_rebuilt(self, kb: KnowledgeLoader) -> None:
        """KILLED test_current_assessment_present: it asserted the legacy assessment
        (relevant_rules + keyword matched_signals from the substring matcher).
        REPLACED: rebuilt to {description, current_scale, growth_projections,
        n_matched_signals}; the rule-derived keys are gone."""
        res = evaluate_scalability(description="Monolith on single node",
                                   matched_signal_ids=_anchor_signals(kb),
                                   current_scale="startup_mvp")
        ca = res["current_assessment"]
        assert ca["current_scale"] == "startup_mvp"
        assert set(ca) == {"description", "current_scale", "growth_projections", "n_matched_signals"}
        assert "relevant_rules" not in ca and "matched_signals" not in ca
        assert ca["n_matched_signals"] == len(_anchor_signals(kb))

    def test_empty_description_still_valid(self, kb: KnowledgeLoader) -> None:
        """KILLED test_empty_description: it asserted 3 tiers survive an empty
        description. REPLACED: retrieval is driven by matched_signal_ids, so an empty
        description with real signals still returns a populated scaling_patterns set."""
        res = evaluate_scalability(description="", matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert res["scaling_patterns"]
        assert res["current_assessment"]["description"] == ""

    def test_growth_projections_recorded_not_routed(self, kb: KnowledgeLoader) -> None:
        """KILLED test_growth_projections_influence_recommendations: it asserted growth
        projections routed into fixed per-tier recommendation strings. REPLACED: growth
        projections are RECORDED in current_assessment for the caller's reference and do
        NOT drive a fixed-string recommendation path (retrieval + own-field reasoning do)."""
        gp = {"rps": "100->10k", "data": "10GB->1TB", "users": "10k->10M"}
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   growth_projections=gp, constraints=SMALL_MVP)
        assert res["current_assessment"]["growth_projections"] == gp
        # recommendations are pattern references, never fixed prose strings
        for r in res["recommendations"]:
            assert set(r) == {"pattern_id", "pattern_name"}


# ===================================================================
# CONTRACT — the new output surface
# ===================================================================

class TestContract:
    def test_top_level_keys_present_tiers_absent(self, kb: KnowledgeLoader) -> None:
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        for key in ("current_assessment", "constraints_analyzed", "scaling_patterns",
                    "recommendations", "retrieval_state", "unmatched", "dangling"):
            assert key in res
        assert "tiers" not in res
        assert res["constraints_analyzed"]["team_size"] == "1-3"

    def test_scaling_pattern_entry_shape(self, kb: KnowledgeLoader) -> None:
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        for s in res["scaling_patterns"]:
            assert set(s) == {"rank", "pattern_id", "pattern_name", "rationale", "horizon",
                              "addresses", "costs_when", "principles", "related_patterns",
                              "retrieval", "gated"}
            assert s["horizon"] in ("current", "growth")
            assert isinstance(s["gated"], bool)
            assert isinstance(s["rank"], int)
            rv = s["retrieval"]
            assert set(rv) == {"score", "direct_votes", "propagated_votes", "seed"}
            assert isinstance(rv["score"], int) and not isinstance(rv["score"], bool)
            for rel in s["related_patterns"]:
                assert kb._lookup_pattern(rel["pattern_id"]) is not None  # never a husk

    def test_recommendations_are_deduped_related(self, kb: KnowledgeLoader) -> None:
        """recommendations = deduped related-pattern set across the scaling patterns' own
        related_patterns, excluding what is already a scaling pattern. Every one
        resolvable, none overlaps (mirrors recommend_pattern's alternatives)."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        ids = [r["pattern_id"] for r in res["recommendations"]]
        assert len(ids) == len(set(ids)), "recommendations must be deduped"
        sp_ids = set(_sp_ids(res))
        for r in res["recommendations"]:
            assert r["pattern_id"] not in sp_ids
            assert kb._lookup_pattern(r["pattern_id"]) is not None

    def test_output_is_json_serializable(self, kb: KnowledgeLoader) -> None:
        """No _FrozenDict / tuple leaks from the hydrate boundary into the output."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert isinstance(json.loads(json.dumps(res)), dict)


# ===================================================================
# ENVELOPE — fail closed through the tool, never a husk
# ===================================================================

class TestEnvelopeFailClosed:
    def test_empty_signals_abstain(self, kb: KnowledgeLoader) -> None:
        res = evaluate_scalability(description=DESC, matched_signal_ids=[],
                                   constraints={"team_size": "5"})
        assert res["retrieval_state"] == NO_MATCH
        assert res["scaling_patterns"] == []
        assert res["recommendations"] == []
        assert res["constraints_analyzed"] == {"team_size": "5"}  # envelope still populated
        assert res["current_assessment"]["n_matched_signals"] == 0

    def test_unrecognised_signals_abstain_not_husk(self, kb: KnowledgeLoader) -> None:
        res = evaluate_scalability(description=DESC,
                                   matched_signal_ids=["sig-000000000000", "sig-ffffffffffff"])
        assert res["retrieval_state"] == NO_MATCH
        assert res["scaling_patterns"] == []
        assert sorted(res["unmatched"]) == ["sig-000000000000", "sig-ffffffffffff"]

    def test_absent_concept_abstains(self, kb: KnowledgeLoader) -> None:
        """A concern the corpus genuinely lacks abstains, never the nearest node."""
        sid = _signal_id("Tokenization of card PAN before storage")
        res = evaluate_scalability(description=DESC, matched_signal_ids=[sid])
        assert res["retrieval_state"] == NO_MATCH
        assert res["scaling_patterns"] == []


# ===================================================================
# BAR 1 — coeus-Gmetric-v1 through the tool's hydrate path (>= 86/130)
# ===================================================================

class TestGmetricThroughTool:
    def test_recall_at_10_through_tool_meets_bar(self, kb: KnowledgeLoader) -> None:
        """evaluate_scalability retrieves via the same kb.hydrate; the horizon partition
        REORDERS but never drops, so the retrieved pattern SET at k=10 reproduces the
        engine's covered@10. Graded against the frozen 130-gold map on the scaling
        pattern_ids (there is NO frozen gold set for the horizon labels / addresses
        text — this bar grades the retrieval the tool sits on). >= 86."""
        golds = _golds_by_problem()
        covered = 0
        for p, gs in golds.items():
            res = evaluate_scalability(description=DESC, matched_signal_ids=MATCHES[p],
                                       constraints={}, k=10)
            assert res["retrieval_state"] in (HIT, LOW_CONFIDENCE)
            top = set(_sp_ids(res))
            covered += sum(1 for g in gs if set(g["corpus_ids"]) & top)
        assert covered >= COUNCIL_BAR10, f"through-tool covered@10 {covered} < {COUNCIL_BAR10}"

    def test_partition_does_not_change_the_retrieved_set(self, kb: KnowledgeLoader) -> None:
        """The horizon partition is a reorder, not a filter: the SET of scaling
        pattern_ids is identical with and without constraints (only rank/horizon move).
        This is why BAR 1 through the tool == the engine's covered@10."""
        for p in ("P01", "P08", "P16"):
            no_c = evaluate_scalability(description=DESC, matched_signal_ids=MATCHES[p],
                                        constraints={}, k=10)
            with_c = evaluate_scalability(description=DESC, matched_signal_ids=MATCHES[p],
                                          constraints=SMALL_MVP, k=10)
            assert set(_sp_ids(no_c)) == set(_sp_ids(with_c))


# ===================================================================
# BAR 2 — before/after delta against the S0 legacy pin
# ===================================================================

class TestBaselineDelta:
    def test_retrieval_blind_before_retrieval_driven_after(self, kb: KnowledgeLoader) -> None:
        """S0 pinned the legacy tool retrieval-BLIND: an already-scaled system and a
        single-node system returned BYTE-IDENTICAL tiers/patterns. The rebuild is
        retrieval-DRIVEN — the two opposite systems now differ — and the hardcoded
        'tiers' contract is gone, replaced by scaling_patterns."""
        assert PIN["cases"]["retrieval_blind"]["tiers_byte_identical"] is True  # the pinned before
        assert "tiers" in PIN["_meta"]["legacy_output_keys"]
        # after: opposite systems differ, tiers gone, scaling_patterns present
        scaled = evaluate_scalability(description=DESC, matched_signal_ids=_scaled_signals(kb),
                                      current_scale="enterprise")
        single = evaluate_scalability(description=DESC, matched_signal_ids=_single_signals(kb),
                                      current_scale="startup_mvp")
        assert set(_sp_ids(scaled)) != set(_sp_ids(single))
        assert "tiers" not in scaled and "scaling_patterns" in scaled


# ===================================================================
# DETERMINISM — identical input -> identical ranking + horizon + votes
# ===================================================================

class TestDeterminism:
    def test_identical_input_identical_partition_and_votes(self, kb: KnowledgeLoader) -> None:
        sigs = _anchor_signals(kb)
        runs = [evaluate_scalability(description=DESC, matched_signal_ids=sigs,
                                     constraints=SMALL_MVP) for _ in range(4)]

        def sig(res):
            return [(s["pattern_id"], s["rank"], s["horizon"], s["retrieval"]["score"], s["gated"])
                    for s in res["scaling_patterns"]]

        base = sig(runs[0])
        for other in runs[1:]:
            assert sig(other) == base
        # byte-reproducible from a freshly constructed loader
        assert sig(_fresh_call(description=DESC, matched_signal_ids=sigs, constraints=SMALL_MVP)) == base

    def test_no_float_in_ranking(self, kb: KnowledgeLoader) -> None:
        """NO float anywhere in the ranking surface — the vote key is integer throughout."""
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        for s in res["scaling_patterns"]:
            for v in s["retrieval"].values():
                assert not isinstance(v, float)
            assert isinstance(s["rank"], int)


# ===================================================================
# HYPERION — named ceilings at the caller boundary; no eval/regex on input
# ===================================================================

class TestCallerBoundaryCeilings:
    def test_matched_signal_ids_bounded(self, kb: KnowledgeLoader) -> None:
        """A flood of ids does not amplify work past the cap; junk abstains cleanly."""
        flood = [f"sig-{i:012x}" for i in range(_MAX_MATCHED_SIGNALS * 10)]
        res = evaluate_scalability(description=DESC, matched_signal_ids=flood)
        assert res["retrieval_state"] == NO_MATCH  # all junk

    def test_constraints_cardinality_bounded(self, kb: KnowledgeLoader) -> None:
        huge = {f"k{i}": "v" for i in range(_MAX_CONSTRAINTS * 5)}
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=huge)
        assert len(res["constraints_analyzed"]) <= _MAX_CONSTRAINTS

    def test_constraint_value_length_clipped(self, kb: KnowledgeLoader) -> None:
        res = evaluate_scalability(
            description=DESC, matched_signal_ids=_anchor_signals(kb),
            constraints={"team_size": "1-3", "scale": "x" * (_MAX_CONSTRAINT_VALUE_LEN * 4)},
        )
        assert len(res["constraints_analyzed"]["scale"]) <= _MAX_CONSTRAINT_VALUE_LEN

    def test_description_bounded_at_caller_boundary(self, kb: KnowledgeLoader) -> None:
        """The untrusted free-text description is bounded where it enters
        (_MAX_DESCRIPTION_LEN, one source of truth in _shared) and echoed CLIPPED in
        current_assessment (blessed by the design — the caller's own text, not a
        retrieval driver). The tail beyond the clip never reaches the output."""
        assert isinstance(_MAX_DESCRIPTION_LEN, int) and _MAX_DESCRIPTION_LEN > 0
        marker_tail = "TAILMARKER"
        desc = "H" * 500 + marker_tail  # 200-char echo clip lands well before the tail
        res = evaluate_scalability(description=desc, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        echoed = res["current_assessment"]["description"]
        assert len(echoed) <= 200
        assert marker_tail not in json.dumps(res)

    def test_current_scale_folds_into_scale_without_overriding(self, kb: KnowledgeLoader) -> None:
        """current_scale folds into constraints['scale'] with setdefault semantics: it
        fills scale when absent, but an explicit constraints['scale'] wins."""
        # fills when absent
        filled = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                      current_scale="startup_mvp", constraints={"team_size": "1-3"})
        assert filled["constraints_analyzed"]["scale"] == "startup_mvp"
        # explicit scale wins
        explicit = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                        current_scale="enterprise",
                                        constraints={"team_size": "1-3", "scale": "startup_mvp"})
        assert explicit["constraints_analyzed"]["scale"] == "startup_mvp"

    def test_no_eval_or_regex_on_caller_input(self, kb: KnowledgeLoader) -> None:
        """Injection-shaped constraint values are inert text, never executed, and the
        facet comparison never treats them as a pattern (categorical exact match)."""
        payloads = {"scale": "__import__('os').system('echo x')", "budget": "${7*7}",
                    "compliance": "'; DROP TABLE t; --"}
        res = evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints={"team_size": "1-3", **payloads})
        assert isinstance(res, dict)
        assert res["constraints_analyzed"]["budget"] == "${7*7}"  # inert, not evaluated


# ===================================================================
# DELETIONS PROVEN — _SCALE_TIERS gone, matcher not called here, legacy matcher deleted (S6)
# ===================================================================

class TestDeletions:
    def test_scale_tiers_and_legacy_helpers_deleted(self) -> None:
        import coeus.tools.evaluate_scalability as es
        assert not hasattr(es, "_SCALE_TIERS")
        assert not hasattr(es, "_project_pattern")

    def test_tool_no_longer_calls_match_structural_signals(self) -> None:
        """This tool retrieves via the hydrate engine and must never call the legacy
        substring matcher (deleted in S6, story-16223628) — regression guard against
        reintroducing the matcher leg."""
        import inspect
        import coeus.tools.evaluate_scalability as es
        src = inspect.getsource(es)
        assert "match_structural_signals" not in src

    # RETIRED (S6, story-16223628, council 9ccb9550): test_match_structural_signals_untouched
    # asserted hasattr + that the matcher still returned results — an inverting guard that
    # goes red once S6 deletes it. The matcher is now gone; the KEPT guard above proves this
    # tool never calls it, and test_matcher_has_zero_tool_callers_now in
    # tests/test_assess_resilience.py proves the census stays zero. Named, no silent drop
    # (Directive 12).


# ===================================================================
# DRY PROVEN — _resolved_related + the output cap live once in _shared
# ===================================================================

class TestDrySharedPrimitives:
    def test_resolved_related_single_source_of_truth(self) -> None:
        """_resolved_related lives once in _shared; analyze_architecture and
        evaluate_scalability import THAT one (zero duplicate defs)."""
        import coeus.tools._shared as sh
        import coeus.tools.analyze_architecture as aa
        import coeus.tools.evaluate_scalability as es
        assert hasattr(sh, "_resolved_related")
        # imported, not redefined: the module binding IS the shared object (identity),
        # and neither module defines its own in its source.
        assert aa._resolved_related is sh._resolved_related
        assert es._resolved_related is sh._resolved_related
        import inspect
        assert "def _resolved_related" not in inspect.getsource(aa)
        assert "def _resolved_related" not in inspect.getsource(es)

    def test_output_cap_is_one_shared_constant(self) -> None:
        """The output cross-product cap is a single _shared constant, imported by all
        three tools (the twin per-tool _MAX_ALTERNATIVES / _MAX_RECOMMENDATIONS unified)."""
        import coeus.tools._shared as sh
        import coeus.tools.analyze_architecture as aa
        import coeus.tools.evaluate_scalability as es
        import coeus.tools.recommend_pattern as rp
        assert isinstance(sh._MAX_RELATED_OUTPUT, int)
        assert not hasattr(rp, "_MAX_ALTERNATIVES")
        assert not hasattr(aa, "_MAX_RECOMMENDATIONS")
        assert aa._MAX_RELATED_OUTPUT is sh._MAX_RELATED_OUTPUT
        assert es._MAX_RELATED_OUTPUT is sh._MAX_RELATED_OUTPUT
        assert rp._MAX_RELATED_OUTPUT is sh._MAX_RELATED_OUTPUT


# ===================================================================
# DEEP-FREEZE — the singleton corpus stays uncorrupted through the tool
# ===================================================================

class TestCorpusUncorrupted:
    def test_corpus_singleton_uncorrupted_through_tool(self, kb: KnowledgeLoader) -> None:
        """The tool reads over deep-frozen hydrated patterns and builds fresh output
        dicts, so a full run cannot mutate the shared corpus (the shallow-ref hazard
        the hydrate-boundary deep_freeze closes)."""
        before = list(kb._lookup_pattern("microservices")["use_when"])
        evaluate_scalability(description=DESC, matched_signal_ids=_anchor_signals(kb),
                             constraints=SMALL_MVP)
        after = list(kb._lookup_pattern("microservices")["use_when"])
        assert after == before
