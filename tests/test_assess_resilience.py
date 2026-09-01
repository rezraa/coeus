# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""assess_resilience wired onto the Shape C engine — story-bc2dece3.

The FOURTH Coeus tool on the shared engine. It retrieves the resilience patterns a
system is missing through one ``kb.hydrate`` call (the proven four-state, fail-closed
envelope) and reuses recommend_pattern's gate polarity EXACTLY — the SINK: a
retrieved resilience pattern whose OWN ``avoid_when`` facet the constraints satisfy
is PREMATURE hardening and sinks below every appropriate one by the same
``(gated, hydrate-rank)`` key recommend_pattern sinks by. No hardcoded
_SPOF_SIGNALS / _MISSING_PATTERN_SIGNALS / _BLAST_RADIUS_INDICATORS table, no
fabricated severity, no float _compute_resilience_score.

This is the one home for the rebuilt tool's proofs. It carries:

* the NORTH-STAR anchor, RED-first — a fragile system surfaces NON-EMPTY hardening
  and can NEVER report fabricated safety (there is no resilience_score key at all;
  a retrieval-dropping mutant fails the non-empty assertion), and the SINK FIRING:
  under startup-MVP circuit_breaker (raw hydrate rank 1) is gated ``premature`` and
  sinks BELOW monolith (``recommended``), the premature tier is NON-EMPTY, while a
  caller who gates nothing degrades gracefully to all-``recommended`` (a gate-
  dropping mutant fails the sink assertion); plus a non-startup control proving the
  same pattern is NOT gated;
* the six superseded legacy tests KILLED-WITH-REASON (Directive 10): the SPOF table,
  the missing-pattern table, the float score range, the fabricated-1.0-on-empty bug,
  the detected-issue recommendations, and the blast-radius table;
* BAR 1 — the frozen coeus-Gmetric-v1 recomputed THROUGH the tool's hydrate path
  (>= 86/130, no constraints so no sink drop); BAR 2 — the before/after delta against
  the S0 legacy pin (fabricated 1.0 + all-empty before; retrieval-driven after);
* the envelope fail-closed states, determinism (incl. a fresh loader), the Hyperion
  caller-boundary ceilings, the deletions proven (incl. the now-ZERO matcher tool
  census that unblocks S6), the DRY (_resolved_related + the unified output cap live
  once in _shared), and the deep-freeze that keeps the singleton corpus uncorrupted.
"""
from __future__ import annotations

import inspect
import json
from collections import defaultdict
from pathlib import Path

import pytest

import coeus.tools._shared as _shared
from coeus.knowledge.loader import DANGLING, HIT, LOW_CONFIDENCE, NO_MATCH, KnowledgeLoader, _signal_id
from coeus.tools._shared import (
    _MAX_CONSTRAINTS,
    _MAX_CONSTRAINT_VALUE_LEN,
    _MAX_DESCRIPTION_LEN,
    _MAX_MATCHED_SIGNALS,
)
from coeus.tools.assess_resilience import assess_resilience

_DATA = Path(__file__).parent / "data"
_GM = _DATA / "gmetric"
FROZEN = json.loads((_GM / "frozen_metric.json").read_text(encoding="utf-8"))
MATCHES = json.loads((_GM / "coeus_matches_v2.json").read_text(encoding="utf-8"))
PIN = json.loads((_DATA / "baseline_assess_resilience_pinned.json").read_text(encoding="utf-8"))

COUNCIL_BAR10 = 86  # bar-1: recall@10 the engine already meets; the tool path must too

# Constraints that satisfy circuit_breaker/bulkhead/fallback's OWN avoid_when facet
# {team_size:1-5, scale:startup_mvp} — the premature-hardening guard.
SMALL_MVP = {"team_size": "1-3", "scale": "startup_mvp"}
GROWTH = {"team_size": "10-20", "scale": "growth"}
LARGE_ENT = {"team_size": "50+", "scale": "enterprise"}

DESC = "context/telemetry only"


# ---------------------------------------------------------------------------
# helpers — derive sig-id inputs from the live index so tests track the corpus
# ---------------------------------------------------------------------------

def _sigs_for(kb: KnowledgeLoader, pid: str, n: int) -> list[str]:
    return [e["signal_id"] for e in kb.get_signal_index() if pid in e["pattern_ids"]][:n]


def _anchor_signals(kb: KnowledgeLoader) -> list[str]:
    """2 circuit_breaker + 2 monolith signals — a fragile system's resilience gaps.
    circuit_breaker hydrates as the rank-1 seed; under startup-MVP its own avoid_when
    facet gates it into 'premature', so it must sink below monolith ('recommended')."""
    return _sigs_for(kb, "circuit_breaker", 2) + _sigs_for(kb, "monolith", 2)


def _h_ids(res: dict) -> list[str]:
    return [h["pattern_id"] for h in res["hardening"]]


def _by_id(res: dict) -> dict[str, dict]:
    return {h["pattern_id"]: h for h in res["hardening"]}


def _pos(res: dict, pid: str) -> int:
    return _h_ids(res).index(pid)


def _fresh_call(**kwargs) -> dict:
    """assess_resilience forced through a freshly constructed loader (byte-repro)."""
    _shared._knowledge = None
    return assess_resilience(**kwargs)


def _golds_by_problem() -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for row in FROZEN["reachable_set_map"]:
        g[row["problem"]].append(row)
    return g


def _has_float(o: object) -> bool:
    if isinstance(o, float):
        return True
    if isinstance(o, dict):
        return any(_has_float(v) for v in o.values())
    if isinstance(o, (list, tuple)):
        return any(_has_float(v) for v in o)
    return False


# ===================================================================
# NORTH STAR + ANCHOR — a fragile system is never safe; the SINK fires (RED-first)
# ===================================================================

class TestNorthStar:
    def test_fragile_system_surfaces_hardening_never_fabricated_safe(self, kb: KnowledgeLoader) -> None:
        """NORTH STAR, RED-first (Directive 8): the S0 premise pinned a fragile system
        scoring resilience_score:1.0 with every list empty. The rebuild retrieves the
        resilience patterns it is missing: hardening is NON-EMPTY, posture.recommended_now
        >= 1, and there is NO resilience_score key AT ALL — nothing can fabricate safety.

        A mutant that drops retrieval (fixed/empty hardening) makes hardening empty and
        FAILS the non-empty assertion; the missing score key makes a fabricated 1.0
        impossible by construction."""
        res = assess_resilience(system_description="fragile payment API", matched_signal_ids=_anchor_signals(kb))
        assert res["retrieval_state"] in (HIT, LOW_CONFIDENCE)
        assert res["hardening"], "a fragile system must surface the hardening it lacks"
        assert "resilience_score" not in res, "no scalar score -> cannot report fabricated safety"
        ps = res["posture"]
        assert ps["retrieved"] >= 1 and ps["recommended_now"] >= 1
        assert ps["retrieved"] == ps["recommended_now"] + ps["premature"]

    def test_startup_sinks_premature_below_recommended(self, kb: KnowledgeLoader) -> None:
        """RED-first (Directive 8): circuit_breaker's own avoid_when facet
        {team_size:1-5, scale:startup_mvp} is satisfied by SMALL_MVP, so it is
        'premature' hardening — and every 'recommended' pattern sorts above every
        'premature' one.

        The FIRING binding, not an accidental order: circuit_breaker is the raw hydrate
        rank-1 seed; the sink must seat it BELOW monolith (raw rank 2, ungated ->
        'recommended'). The no-constraints control below proves circuit_breaker leads by
        default — so only the gate can seat it under monolith. A gate-dropping mutant
        leaves circuit_breaker 'recommended' at rank 1 and FAILS here."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        by = _by_id(res)
        assert "circuit_breaker" in by, "circuit_breaker must be in the retrieved set"
        assert by["circuit_breaker"]["appropriateness"] == "premature"
        assert by["circuit_breaker"]["gated"] is True
        assert by["circuit_breaker"]["rank"] != 1, "gated premature hardening must never be #1"
        # every 'recommended' precedes every 'premature'
        rec_pos = [n for n, h in enumerate(res["hardening"]) if h["appropriateness"] == "recommended"]
        prem_pos = [n for n, h in enumerate(res["hardening"]) if h["appropriateness"] == "premature"]
        assert rec_pos and prem_pos, "both tiers must be present in this set"
        assert max(rec_pos) < min(prem_pos)
        # the FIRING binding: circuit_breaker (raw rank 1) now sinks below monolith
        assert by["monolith"]["appropriateness"] == "recommended"
        assert _pos(res, "monolith") < _pos(res, "circuit_breaker")

    def test_no_constraints_graceful_all_recommended(self, kb: KnowledgeLoader) -> None:
        """Graceful degradation: a caller who supplies no gating constraints gates nothing
        — every retrieved pattern is 'recommended', nothing premature, and the order is
        exactly hydrate's (circuit_breaker, the rank-1 seed, leads). This is the ordering
        the startup sink INVERTS."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints={})
        assert all(h["appropriateness"] == "recommended" for h in res["hardening"])
        assert all(h["gated"] is False for h in res["hardening"])
        assert res["posture"]["premature"] == 0
        assert res["hardening"][0]["pattern_id"] == "circuit_breaker"
        assert _pos(res, "circuit_breaker") < _pos(res, "monolith")

    def test_non_startup_scale_does_not_flag_premature(self, kb: KnowledgeLoader) -> None:
        """A non-startup caller does not get resilience patterns shoved into 'premature':
        circuit_breaker's {team_size:1-5, scale:startup_mvp} facet matches neither a
        growth team nor an enterprise one, so it stays 'recommended'. Firing is
        categorical, not a blanket 'everything is overkill'."""
        for cons in (GROWTH, LARGE_ENT):
            res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                    constraints=cons)
            cb = _by_id(res)["circuit_breaker"]
            assert cb["appropriateness"] == "recommended", cons
            assert cb["gated"] is False, cons

    def test_all_k_patterns_contribute(self, kb: KnowledgeLoader) -> None:
        """ALL k retrieved patterns yield a hardening entry, tiered — surfacing only the
        premature (or only the recommended) ones would reproduce the dead-tool's
        blindness. Both tiers present under SMALL_MVP; every entry carries its own
        protects_against (use_when) text."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert len(res["hardening"]) >= 5
        assert any(h["appropriateness"] == "recommended" for h in res["hardening"])
        assert any(h["appropriateness"] == "premature" for h in res["hardening"])
        for h in res["hardening"]:
            assert h["protects_against"], f"empty use_when protects_against for {h['pattern_id']}"

    def test_ranks_are_contiguous(self, kb: KnowledgeLoader) -> None:
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert [h["rank"] for h in res["hardening"]] == list(range(1, len(res["hardening"]) + 1))


# ===================================================================
# KILLED-WITH-REASON (Directive 10) — the six superseded legacy tests
# ===================================================================

class TestKilledLegacyTests:
    def test_no_spof_table(self, kb: KnowledgeLoader) -> None:
        """KILLED test_spof_detection: it asserted single_points_of_failure from the
        hardcoded _SPOF_SIGNALS token table. REPLACED: there is no
        single_points_of_failure key — a SPOF is an absent redundancy pattern surfaced
        as retrieved hardening / its remediation, driven by signals not tokens."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert "single_points_of_failure" not in res
        assert res["hardening"]

    def test_no_missing_patterns_key(self, kb: KnowledgeLoader) -> None:
        """KILLED test_missing_patterns_identified: it asserted missing_patterns from the
        hardcoded _MISSING_PATTERN_SIGNALS table. REPLACED (strictly stronger): a
        missing pattern IS a retrieved hardening pattern the system lacks — the key is
        gone, subsumed into hardening."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert "missing_patterns" not in res
        assert all(set(h) >= {"pattern_id", "protects_against"} for h in res["hardening"])

    def test_no_resilience_score(self, kb: KnowledgeLoader) -> None:
        """KILLED test_resilience_score_range: it asserted 0.0 <= resilience_score <= 1.0
        from the fabricated-penalty _compute_resilience_score float. REPLACED: there is
        NO resilience_score key and NO float anywhere — posture is integer counts only."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert "resilience_score" not in res
        assert not _has_float(res)
        assert all(isinstance(v, int) and not isinstance(v, bool) for v in res["posture"].values())

    def test_empty_signals_no_fabricated_safety(self, kb: KnowledgeLoader) -> None:
        """KILLED test_perfect_score_no_issues (the exact bug): it asserted empty signals
        yield resilience_score == 1.0 — a perfect score for a system nothing was known
        about. REPLACED: empty signals ABSTAIN (no_match) to empty hardening + all-zero
        integer posture, with no score to fabricate."""
        res = assess_resilience(system_description="Well-architected system", matched_signal_ids=[])
        assert res["retrieval_state"] == NO_MATCH
        assert res["hardening"] == []
        assert res["posture"] == {"retrieved": 0, "recommended_now": 0, "premature": 0}
        assert "resilience_score" not in res

    def test_hardening_from_retrieval_not_detected_issues(self, kb: KnowledgeLoader) -> None:
        """KILLED test_recommendations_present: it asserted hardening_recommendations >= 2
        derived from detected SPOF/missing tokens. REPLACED: hardening is retrieval-
        driven, carries an integer retrieval vote, and every entry is a real corpus
        pattern (never a token-synthesised husk)."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert "hardening_recommendations" not in res
        assert res["hardening"]
        for h in res["hardening"]:
            score = h["retrieval"]["score"]
            assert isinstance(score, int) and not isinstance(score, bool) and score >= 1
            assert kb._lookup_pattern(h["pattern_id"]) is not None

    def test_no_blast_radius_table(self, kb: KnowledgeLoader) -> None:
        """KILLED test_blast_radius_assessment: it asserted blast_radius_assessment with a
        fabricated high/medium/low severity from the hardcoded _BLAST_RADIUS_INDICATORS
        table. REPLACED: there is no blast_radius_assessment key and no severity — a
        blast condition is a coupling whose remediation is a decoupling pattern, which
        collapses into retrieval + related_patterns."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert "blast_radius_assessment" not in res
        for h in res["hardening"]:
            assert "severity" not in h


# ===================================================================
# CONTRACT — the new output surface
# ===================================================================

class TestContract:
    def test_top_level_keys_present_legacy_absent(self, kb: KnowledgeLoader) -> None:
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        for key in ("constraints_analyzed", "posture", "hardening", "recommendations",
                    "retrieval_state", "unmatched", "dangling"):
            assert key in res
        for gone in ("resilience_score", "single_points_of_failure", "missing_patterns",
                     "blast_radius_assessment", "hardening_recommendations"):
            assert gone not in res
        assert res["constraints_analyzed"]["team_size"] == "1-3"

    def test_posture_is_integer_counts_only(self, kb: KnowledgeLoader) -> None:
        """posture replaces the float score with integer counts: retrieved ==
        recommended_now + premature, every value a plain int (no derived ratio)."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        ps = res["posture"]
        assert set(ps) == {"retrieved", "recommended_now", "premature"}
        for v in ps.values():
            assert isinstance(v, int) and not isinstance(v, bool)
        assert ps["retrieved"] == ps["recommended_now"] + ps["premature"]
        assert ps["retrieved"] == len(res["hardening"])

    def test_hardening_entry_shape(self, kb: KnowledgeLoader) -> None:
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        for h in res["hardening"]:
            assert set(h) == {"rank", "pattern_id", "pattern_name", "rationale",
                              "appropriateness", "protects_against", "tradeoffs",
                              "principles", "related_patterns", "retrieval", "gated"}
            assert h["appropriateness"] in ("recommended", "premature")
            assert isinstance(h["gated"], bool)
            assert isinstance(h["rank"], int)
            # appropriateness and gated are the two faces of one gate
            assert (h["appropriateness"] == "premature") == h["gated"]
            rv = h["retrieval"]
            assert set(rv) == {"score", "direct_votes", "propagated_votes", "seed"}
            assert isinstance(rv["score"], int) and not isinstance(rv["score"], bool)
            for rel in h["related_patterns"]:
                assert kb._lookup_pattern(rel["pattern_id"]) is not None  # never a husk

    def test_recommendations_are_deduped_related(self, kb: KnowledgeLoader) -> None:
        """recommendations = deduped related-pattern set across the hardening patterns'
        own related_patterns, excluding what is already a hardening pattern. Every one
        resolvable, none overlaps (mirrors recommend_pattern's alternatives)."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        ids = [r["pattern_id"] for r in res["recommendations"]]
        assert len(ids) == len(set(ids)), "recommendations must be deduped"
        h_ids = set(_h_ids(res))
        for r in res["recommendations"]:
            assert set(r) == {"pattern_id", "pattern_name"}
            assert r["pattern_id"] not in h_ids
            assert kb._lookup_pattern(r["pattern_id"]) is not None

    def test_output_is_json_serializable(self, kb: KnowledgeLoader) -> None:
        """No _FrozenDict / tuple leaks from the hydrate boundary into the output."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert isinstance(json.loads(json.dumps(res)), dict)

    def test_structural_signals_retired_no_alias(self, kb: KnowledgeLoader) -> None:
        """The prose structural_signals param is RETIRED with NO alias shim (its
        replacement, matched_signal_ids, is a different vocabulary) — passing it raises
        the standard unexpected-keyword TypeError. The system->system_description alias
        survives."""
        with pytest.raises(TypeError):
            assess_resilience(system_description=DESC, structural_signals=["single-database"])
        # system alias still works, driven by matched_signal_ids
        res = assess_resilience(system="A fragile payment API", matched_signal_ids=_anchor_signals(kb))
        assert isinstance(res, dict) and res["hardening"]


# ===================================================================
# ENVELOPE — fail closed through the tool, never a husk
# ===================================================================

class TestEnvelopeFailClosed:
    def test_empty_signals_abstain(self, kb: KnowledgeLoader) -> None:
        res = assess_resilience(system_description=DESC, matched_signal_ids=[],
                                constraints={"team_size": "5"})
        assert res["retrieval_state"] == NO_MATCH
        assert res["hardening"] == []
        assert res["recommendations"] == []
        assert res["posture"] == {"retrieved": 0, "recommended_now": 0, "premature": 0}
        assert res["constraints_analyzed"] == {"team_size": "5"}  # envelope still populated

    def test_unrecognised_signals_abstain_not_husk(self, kb: KnowledgeLoader) -> None:
        res = assess_resilience(system_description=DESC,
                                matched_signal_ids=["sig-000000000000", "sig-ffffffffffff"])
        assert res["retrieval_state"] == NO_MATCH
        assert res["hardening"] == []
        assert sorted(res["unmatched"]) == ["sig-000000000000", "sig-ffffffffffff"]

    def test_absent_concept_abstains(self, kb: KnowledgeLoader) -> None:
        """A concern the corpus genuinely lacks abstains, never the nearest node."""
        sid = _signal_id("Tokenization of card PAN before storage")
        res = assess_resilience(system_description=DESC, matched_signal_ids=[sid])
        assert res["retrieval_state"] == NO_MATCH
        assert res["hardening"] == []


# ===================================================================
# BAR 1 — coeus-Gmetric-v1 through the tool's hydrate path (>= 86/130)
# ===================================================================

class TestGmetricThroughTool:
    def test_recall_at_10_through_tool_meets_bar(self, kb: KnowledgeLoader) -> None:
        """assess_resilience retrieves via the same kb.hydrate; with no constraints no
        sink fires, so the retrieved hardening SET at k=10 reproduces the engine's
        covered@10. Graded against the frozen 130-gold map on the hardening pattern_ids
        (there is NO frozen gold set for the protects_against / appropriateness TEXT —
        this bar grades the retrieval the tool sits on). >= 86."""
        golds = _golds_by_problem()
        covered = 0
        for p, gs in golds.items():
            res = assess_resilience(system_description=DESC, matched_signal_ids=MATCHES[p],
                                    constraints={}, k=10)
            assert res["retrieval_state"] in (HIT, LOW_CONFIDENCE)
            top = set(_h_ids(res))
            covered += sum(1 for g in gs if set(g["corpus_ids"]) & top)
        assert covered >= COUNCIL_BAR10, f"through-tool covered@10 {covered} < {COUNCIL_BAR10}"

    def test_sink_does_not_change_the_retrieved_set(self, kb: KnowledgeLoader) -> None:
        """The premature sink is a reorder, not a filter: the SET of hardening
        pattern_ids is identical with and without constraints (only rank/appropriateness
        move). This is why BAR 1 through the tool == the engine's covered@10."""
        for p in ("P01", "P08", "P16"):
            no_c = assess_resilience(system_description=DESC, matched_signal_ids=MATCHES[p],
                                     constraints={}, k=10)
            with_c = assess_resilience(system_description=DESC, matched_signal_ids=MATCHES[p],
                                       constraints=SMALL_MVP, k=10)
            assert set(_h_ids(no_c)) == set(_h_ids(with_c))


# ===================================================================
# BAR 2 — before/after delta against the S0 legacy pin
# ===================================================================

class TestBaselineDelta:
    def test_fabricated_safety_before_retrieval_driven_after(self, kb: KnowledgeLoader) -> None:
        """S0 pinned the legacy tool fabricating resilience_score:1.0 with every list
        empty on a fragile payment API (it only 'worked' on its hardcoded hyphen
        tokens). The rebuild is retrieval-DRIVEN — the same fragile system now surfaces
        NON-EMPTY hardening, there is no resilience_score to fabricate, and posture is
        integer counts."""
        assert PIN["cases"]["fragile_payment_api"]["resilience_score"] == 1.0  # the pinned before
        assert PIN["cases"]["fragile_payment_api"]["fabricated_safety"] is True
        assert "resilience_score" in PIN["_meta"]["legacy_output_keys"]
        # after: fragile system -> non-empty hardening, no score, integer posture
        res = assess_resilience(system_description=PIN["cases"]["fragile_payment_api"]["system_description"],
                                matched_signal_ids=_anchor_signals(kb))
        assert res["hardening"]
        assert "resilience_score" not in res
        assert isinstance(res["posture"]["retrieved"], int)


# ===================================================================
# DETERMINISM — identical input -> identical ranking + appropriateness + votes
# ===================================================================

class TestDeterminism:
    def test_identical_input_identical_ranking_and_votes(self, kb: KnowledgeLoader) -> None:
        sigs = _anchor_signals(kb)
        runs = [assess_resilience(system_description=DESC, matched_signal_ids=sigs,
                                  constraints=SMALL_MVP) for _ in range(4)]

        def sig(res):
            return [(h["pattern_id"], h["rank"], h["appropriateness"], h["retrieval"]["score"], h["gated"])
                    for h in res["hardening"]]

        base = sig(runs[0])
        for other in runs[1:]:
            assert sig(other) == base
        # byte-reproducible from a freshly constructed loader (a PYTHONHASHSEED 0-vs-12345
        # flip is verified out-of-band: the ranking key is a total order over integer
        # votes + pattern-id, so it does not depend on set/dict iteration order)
        assert sig(_fresh_call(system_description=DESC, matched_signal_ids=sigs, constraints=SMALL_MVP)) == base

    def test_no_float_in_ranking(self, kb: KnowledgeLoader) -> None:
        """NO float anywhere in the ranking surface — the vote key is integer throughout
        and posture is integer counts (the deleted _compute_resilience_score was the
        only float)."""
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert not _has_float(res)


# ===================================================================
# HYPERION — named ceilings at the caller boundary; no eval/regex on input
# ===================================================================

class TestCallerBoundaryCeilings:
    def test_matched_signal_ids_bounded(self, kb: KnowledgeLoader) -> None:
        """A flood of ids does not amplify work past the cap; junk abstains cleanly."""
        flood = [f"sig-{i:012x}" for i in range(_MAX_MATCHED_SIGNALS * 10)]
        res = assess_resilience(system_description=DESC, matched_signal_ids=flood)
        assert res["retrieval_state"] == NO_MATCH  # all junk

    def test_constraints_cardinality_bounded(self, kb: KnowledgeLoader) -> None:
        huge = {f"k{i}": "v" for i in range(_MAX_CONSTRAINTS * 5)}
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints=huge)
        assert len(res["constraints_analyzed"]) <= _MAX_CONSTRAINTS

    def test_constraint_value_length_clipped(self, kb: KnowledgeLoader) -> None:
        res = assess_resilience(
            system_description=DESC, matched_signal_ids=_anchor_signals(kb),
            constraints={"team_size": "1-3", "scale": "x" * (_MAX_CONSTRAINT_VALUE_LEN * 4)},
        )
        assert len(res["constraints_analyzed"]["scale"]) <= _MAX_CONSTRAINT_VALUE_LEN

    def test_description_bounded_at_caller_boundary(self, kb: KnowledgeLoader) -> None:
        """The untrusted free-text description is bounded where it enters
        (_MAX_DESCRIPTION_LEN, one source of truth in _shared) and never reaches the
        output dict at all (it is context/telemetry only — the emit_event clip is the
        caller's OWN text, absent from the return)."""
        assert isinstance(_MAX_DESCRIPTION_LEN, int) and _MAX_DESCRIPTION_LEN > 0
        marker_tail = "TAILMARKER"
        desc = "H" * (_MAX_DESCRIPTION_LEN + 500) + marker_tail
        res = assess_resilience(system_description=desc, matched_signal_ids=_anchor_signals(kb),
                                constraints=SMALL_MVP)
        assert marker_tail not in json.dumps(res)

    def test_no_eval_or_regex_on_caller_input(self, kb: KnowledgeLoader) -> None:
        """Injection-shaped constraint values are inert text, never executed, and the
        facet comparison never treats them as a pattern (categorical exact match)."""
        payloads = {"scale": "__import__('os').system('echo x')", "budget": "${7*7}",
                    "compliance": "'; DROP TABLE t; --"}
        res = assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                                constraints={"team_size": "1-3", **payloads})
        assert isinstance(res, dict)
        assert res["constraints_analyzed"]["budget"] == "${7*7}"  # inert, not evaluated


# ===================================================================
# DELETIONS PROVEN — SPOF/missing/blast/score gone; legacy matcher deleted (S6); census ZERO
# ===================================================================

class TestDeletions:
    def test_legacy_tables_and_scorer_deleted(self) -> None:
        import coeus.tools.assess_resilience as ar
        for gone in ("_SPOF_SIGNALS", "_MISSING_PATTERN_SIGNALS",
                     "_BLAST_RADIUS_INDICATORS", "_compute_resilience_score"):
            assert not hasattr(ar, gone), gone
        src = inspect.getsource(ar)
        for gone in ("_SPOF_SIGNALS", "_MISSING_PATTERN_SIGNALS",
                     "_BLAST_RADIUS_INDICATORS", "_compute_resilience_score"):
            assert gone not in src, f"{gone} still referenced in source"

    def test_tool_no_longer_calls_match_structural_signals(self) -> None:
        import coeus.tools.assess_resilience as ar
        assert "match_structural_signals" not in inspect.getsource(ar)

    def test_matcher_has_zero_tool_callers_now(self) -> None:
        """The tool-caller census across every tool module is ZERO — no tool references
        match_structural_signals. This zero census unblocked S6 (story-16223628), which
        deleted the matcher / _rule_signal_pairs / _resolve_pattern from the loader; the
        guard now holds the floor against any tool reintroducing a call to the removed
        matcher."""
        import coeus.tools as tools_pkg
        tool_dir = Path(tools_pkg.__file__).parent
        callers = []
        for py in sorted(tool_dir.glob("*.py")):
            if "match_structural_signals" in py.read_text(encoding="utf-8"):
                callers.append(py.name)
        assert callers == [], f"unexpected matcher callers remain: {callers}"

    # RETIRED (S6, story-16223628, council 9ccb9550): test_matcher_itself_untouched asserted
    # hasattr(kb, "match_structural_signals") — an inverting guard that goes red once S6
    # deletes the matcher. It is now gone; test_tool_no_longer_calls_match_structural_signals
    # and test_matcher_has_zero_tool_callers_now above hold the zero-caller floor. Named, no
    # silent drop (Directive 12).


# ===================================================================
# DRY PROVEN — _resolved_related + the output cap live once in _shared
# ===================================================================

class TestDrySharedPrimitives:
    def test_resolved_related_single_source_of_truth(self) -> None:
        """_resolved_related lives once in _shared; assess_resilience imports THAT one."""
        import coeus.tools._shared as sh
        import coeus.tools.assess_resilience as ar
        assert ar._resolved_related is sh._resolved_related
        assert "def _resolved_related" not in inspect.getsource(ar)

    def test_output_cap_is_one_shared_constant(self) -> None:
        import coeus.tools._shared as sh
        import coeus.tools.assess_resilience as ar
        assert ar._MAX_RELATED_OUTPUT is sh._MAX_RELATED_OUTPUT
        assert not hasattr(ar, "_MAX_ALTERNATIVES")
        assert not hasattr(ar, "_MAX_HARDENING")


# ===================================================================
# DEEP-FREEZE — the singleton corpus stays uncorrupted through the tool
# ===================================================================

class TestCorpusUncorrupted:
    def test_corpus_singleton_uncorrupted_through_tool(self, kb: KnowledgeLoader) -> None:
        """The tool reads over deep-frozen hydrated patterns and builds fresh output
        dicts, so a full run cannot mutate the shared corpus (the shallow-ref hazard the
        hydrate-boundary deep_freeze closes)."""
        before = list(kb._lookup_pattern("circuit_breaker")["use_when"])
        assess_resilience(system_description=DESC, matched_signal_ids=_anchor_signals(kb),
                          constraints=SMALL_MVP)
        after = list(kb._lookup_pattern("circuit_breaker")["use_when"])
        assert after == before
