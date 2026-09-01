# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""analyze_architecture wired onto the Shape C engine — story-917b281e.

The SECOND Coeus tool on the shared engine. It retrieves through one ``kb.hydrate``
call (the proven four-state, fail-closed envelope), tiers each retrieved pattern by
the SAME deterministic gate as recommend_pattern but with the semantic INVERTED —
an issue is CONFIRMED when the constraints satisfy the pattern's own ``avoid_when``
facet, so a confirmed issue RISES above the advisory tier — and reasons one issue
entry per retrieved pattern over that pattern's own ``avoid_when`` text and
``related_patterns``. No hardcoded ``_ANTI_PATTERNS`` island, no fabricated
severity, no rule-derived ``matched_rules`` / ``scalability_flags``.

This is the one home for the rebuilt tool's proofs. It carries:

* the ANCHOR, rewritten RED-first — under small-team + MVP a pattern whose own
  ``avoid_when`` facet the constraints satisfy comes back ``confirmed=True`` and
  sorts above the advisory tier, INCLUDING above patterns that outranked it in the
  raw hydrate order (binds the gate FIRING, not an accidental position); a control
  with non-matching constraints comes back ``confirmed=False``;
* the five superseded tests KILLED-WITH-REASON (Directive 10): the island exact-key
  detector, the fabricated severity, the dead ``matched_rules`` rule path, the
  ``filter_by_constraints`` constraint leg, and the old key set;
* BAR 1 — the frozen coeus-Gmetric-v1 recomputed THROUGH the tool's hydrate path
  (>= 86/130, no constraints so no gate); BAR 2 — the before/after delta against the
  S0 legacy pin;
* the envelope fail-closed states, determinism (incl. a fresh loader), the Hyperion
  caller-boundary ceilings, the deletions proven, and the deep-freeze that keeps the
  singleton corpus uncorrupted through the tool.
"""
from __future__ import annotations

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
from coeus.tools.analyze_architecture import analyze_architecture

_DATA = Path(__file__).parent / "data"
_GM = _DATA / "gmetric"
FROZEN = json.loads((_GM / "frozen_metric.json").read_text(encoding="utf-8"))
MATCHES = json.loads((_GM / "coeus_matches_v2.json").read_text(encoding="utf-8"))
PIN = json.loads((_DATA / "baseline_analyze_architecture_pinned.json").read_text(encoding="utf-8"))

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
    """2 microservices + 2 monolith signals — the same seed set as the recommend_pattern
    anchor. microservices hydrates as the rank-1 seed; a lower-ranked confirmed pattern
    (api_gateway) is what binds the inversion when it rises above monolith."""
    return _sigs_for(kb, "microservices", 2) + _sigs_for(kb, "monolith", 2)


def _issue_ids(res: dict) -> list[str]:
    return [i["pattern_id"] for i in res["architecture_issues"]]


def _pos(res: dict, pid: str) -> int:
    return _issue_ids(res).index(pid)


def _fresh_call(**kwargs) -> dict:
    """analyze_architecture forced through a freshly constructed loader (byte-repro)."""
    _shared._knowledge = None
    return analyze_architecture(**kwargs)


def _golds_by_problem() -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for row in FROZEN["reachable_set_map"]:
        g[row["problem"]].append(row)
    return g


# ===================================================================
# ANCHOR — the gate INVERTED to confirm, rewritten RED-first (sharpened)
# ===================================================================

class TestConfirmGate:
    def test_matching_constraints_confirm_and_elevate(self, kb: KnowledgeLoader) -> None:
        """RED-first (Directive 8): microservices' own avoid_when facet
        {team_size:1-15, scale:startup_mvp} is satisfied by SMALL_MVP, so its issue is
        CONFIRMED — and every confirmed issue sorts above every advisory one.

        Sharpened: bind the gate FIRING, not an accidental order. api_gateway is
        ALSO confirmed under SMALL_MVP but sits BELOW monolith in the raw hydrate
        order; the inversion must lift it ABOVE monolith. (The no-constraints run
        below is the gate-off control that proves monolith outranks it by default.)"""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        by_id = {i["pattern_id"]: i for i in res["architecture_issues"]}
        assert "microservices" in by_id, "microservices must be in the retrieved set"
        assert by_id["microservices"]["confirmed"] is True
        # every confirmed issue precedes every advisory issue
        confirmed_pos = [n for n, i in enumerate(res["architecture_issues"]) if i["confirmed"]]
        advisory_pos = [n for n, i in enumerate(res["architecture_issues"]) if not i["confirmed"]]
        assert confirmed_pos and advisory_pos, "both tiers must be present in this set"
        assert max(confirmed_pos) < min(advisory_pos)
        # the FIRING binding: api_gateway (confirmed) rises above monolith (advisory)
        assert by_id["api_gateway"]["confirmed"] is True
        assert by_id["monolith"]["confirmed"] is False
        assert _pos(res, "api_gateway") < _pos(res, "monolith")

    def test_control_non_matching_constraints_advisory(self, kb: KnowledgeLoader) -> None:
        """Control: under a large enterprise team microservices' avoid_when facet does
        NOT match, so its issue is ADVISORY (confirmed=False) — firing, not absence."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=LARGE_ENT)
        by_id = {i["pattern_id"]: i for i in res["architecture_issues"]}
        assert "microservices" in by_id
        assert by_id["microservices"]["confirmed"] is False

    def test_no_constraints_is_pure_hydrate_order(self, kb: KnowledgeLoader) -> None:
        """Gate-off control: no constraints → nothing confirmed and the issue order is
        exactly hydrate's. Here monolith (raw rank 2) precedes api_gateway (raw rank 5)
        — the ordering the confirm gate INVERTS in test above."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints={})
        assert all(i["confirmed"] is False for i in res["architecture_issues"])
        assert _pos(res, "monolith") < _pos(res, "api_gateway")

    def test_all_k_patterns_contribute_not_only_gated(self, kb: KnowledgeLoader) -> None:
        """ALL k retrieved patterns yield an issue entry, tiered — surfacing issues ONLY
        for gated patterns would reproduce the dead-tool empty result in the ~64%
        no-facet-match majority. Advisory issues are present and non-empty."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert len(res["architecture_issues"]) >= 5
        advisory = [i for i in res["architecture_issues"] if not i["confirmed"]]
        assert advisory, "advisory tier must contribute"
        for i in res["architecture_issues"]:
            assert i["issues"], f"empty avoid_when issue text for {i['pattern_id']}"


# ===================================================================
# KILLED-WITH-REASON (Directive 10) — the five superseded tests
# ===================================================================

class TestKilledLegacyTests:
    def test_issues_from_own_avoid_when_not_island(self, kb: KnowledgeLoader) -> None:
        """KILLED test_anti_pattern_detection: it asserted island exact-key hits
        (``_ANTI_PATTERNS[sig]``) with a per-signal ``issue`` string. REPLACED
        (strictly stronger): issues are the retrieved patterns' OWN avoid_when text —
        every retrieved pattern yields an entry keyed by ``pattern_id`` with a
        non-empty ``issues`` list, and the island is gone."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert res["architecture_issues"], "must surface issues from retrieved patterns"
        for i in res["architecture_issues"]:
            assert "pattern_id" in i and "signal" not in i  # re-sourced, not island-keyed
            assert isinstance(i["issues"], list) and i["issues"]

    def test_no_fabricated_severity(self, kb: KnowledgeLoader) -> None:
        """KILLED test_anti_pattern_severity: it asserted a ``severity`` in
        (high|medium|low) fabricated by the island table. REPLACED: NO issue carries a
        severity — the corpus has no severity field, so severity is the human's to
        assign in interpretation (SKILL.md step 3), never the tool's."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        for i in res["architecture_issues"]:
            assert "severity" not in i

    def test_matched_rules_dropped(self, kb: KnowledgeLoader) -> None:
        """KILLED test_signal_matching_returns_matched_rules: it asserted the dead
        rule path populated ``matched_rules``. REPLACED: ``matched_rules`` is dropped
        from the contract entirely (the rule path was measured empty on real problem
        language — A/B council 3154bcba-decision-2)."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert "matched_rules" not in res

    def test_constraints_confirm_not_filter(self, kb: KnowledgeLoader) -> None:
        """KILLED test_constraint_filtering: it asserted enterprise constraints REMOVE
        rules via ``filter_by_constraints`` (fewer matched_rules). REPLACED: a matching
        constraint CONFIRMS and ELEVATES an issue rather than dropping it — the same
        retrieved set appears under both constraint profiles, only the confirm tier
        differs. Nothing is filtered out."""
        small = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                     constraints=SMALL_MVP)
        large = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                     constraints=LARGE_ENT)
        assert set(_issue_ids(small)) == set(_issue_ids(large)), "constraints must not filter the set"
        # microservices flips confirmed True->False across the two profiles
        s = {i["pattern_id"]: i for i in small["architecture_issues"]}
        l = {i["pattern_id"]: i for i in large["architecture_issues"]}
        assert s["microservices"]["confirmed"] is True
        assert l["microservices"]["confirmed"] is False

    def test_result_keys_are_the_new_contract(self, kb: KnowledgeLoader) -> None:
        """KILLED test_result_keys_present: it asserted matched_rules + architecture_issues
        + recommendations + scalability_flags. REWRITTEN to the new contract:
        matched_rules and scalability_flags ABSENT, retrieval_state PRESENT."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert "matched_rules" not in res
        assert "scalability_flags" not in res
        assert "retrieval_state" in res


# ===================================================================
# CONTRACT — the new output surface
# ===================================================================

class TestContract:
    def test_top_level_keys_present(self, kb: KnowledgeLoader) -> None:
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        for key in ("constraints_analyzed", "architecture_issues", "recommendations",
                    "retrieval_state", "unmatched", "dangling"):
            assert key in res
        assert res["constraints_analyzed"]["team_size"] == "1-3"

    def test_issue_entry_shape(self, kb: KnowledgeLoader) -> None:
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        for i in res["architecture_issues"]:
            assert set(i) == {"pattern_id", "pattern_name", "confirmed", "issues",
                              "remediation", "retrieval"}
            assert isinstance(i["confirmed"], bool)
            assert isinstance(i["retrieval"]["score"], int) and not isinstance(i["retrieval"]["score"], bool)
            for rem in i["remediation"]:
                assert kb._lookup_pattern(rem["pattern_id"]) is not None  # never a husk

    def test_recommendations_are_deduped_remediation(self, kb: KnowledgeLoader) -> None:
        """recommendations = deduped remediation across the issue-patterns' own
        related_patterns, excluding what is already an issue pattern (mirrors
        recommend_pattern's alternatives). Every one resolvable, none overlaps."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        ids = [r["pattern_id"] for r in res["recommendations"]]
        assert len(ids) == len(set(ids)), "recommendations must be deduped"
        issue_ids = set(_issue_ids(res))
        for r in res["recommendations"]:
            assert r["pattern_id"] not in issue_ids
            assert kb._lookup_pattern(r["pattern_id"]) is not None
            assert r["pattern_name"]

    def test_output_is_json_serializable(self, kb: KnowledgeLoader) -> None:
        """No _FrozenDict / tuple leaks from the hydrate boundary into the output."""
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert isinstance(json.loads(json.dumps(res)), dict)


# ===================================================================
# ENVELOPE — fail closed through the tool, never a husk
# ===================================================================

class TestEnvelopeFailClosed:
    def test_empty_signals_abstain(self, kb: KnowledgeLoader) -> None:
        res = analyze_architecture(description=DESC, matched_signal_ids=[],
                                   constraints={"team_size": "5"})
        assert res["retrieval_state"] == NO_MATCH
        assert res["architecture_issues"] == []
        assert res["recommendations"] == []
        assert res["constraints_analyzed"] == {"team_size": "5"}  # envelope still populated

    def test_unrecognised_signals_abstain_not_husk(self, kb: KnowledgeLoader) -> None:
        res = analyze_architecture(description=DESC,
                                   matched_signal_ids=["sig-000000000000", "sig-ffffffffffff"])
        assert res["retrieval_state"] == NO_MATCH
        assert res["architecture_issues"] == []
        assert sorted(res["unmatched"]) == ["sig-000000000000", "sig-ffffffffffff"]

    def test_absent_concept_abstains(self, kb: KnowledgeLoader) -> None:
        """A concern the corpus genuinely lacks abstains, never the nearest node."""
        sid = _signal_id("Tokenization of card PAN before storage")
        res = analyze_architecture(description=DESC, matched_signal_ids=[sid])
        assert res["retrieval_state"] == NO_MATCH
        assert res["architecture_issues"] == []


# ===================================================================
# BAR 1 — coeus-Gmetric-v1 through the tool's hydrate path (>= 86/130)
# ===================================================================

class TestGmetricThroughTool:
    def test_recall_at_10_through_tool_meets_bar(self, kb: KnowledgeLoader) -> None:
        """analyze_architecture retrieves via the same kb.hydrate; with no constraints
        no gate fires, so the retrieved PATTERNS at k=10 reproduce the engine's
        covered@10. Graded against the frozen 130-gold map on the pattern_ids that
        back the issues (there is NO frozen gold set for avoid_when issue TEXT — this
        bar grades the retrieval the tool sits on, not the issue coverage). >= 86."""
        golds = _golds_by_problem()
        covered = 0
        for p, gs in golds.items():
            res = analyze_architecture(description=DESC, matched_signal_ids=MATCHES[p],
                                       constraints={}, k=10)
            assert res["retrieval_state"] in (HIT, LOW_CONFIDENCE)
            top = set(_issue_ids(res))
            covered += sum(1 for g in gs if set(g["corpus_ids"]) & top)
        assert covered >= COUNCIL_BAR10, f"through-tool covered@10 {covered} < {COUNCIL_BAR10}"


# ===================================================================
# BAR 2 — before/after delta against the S0 legacy pin
# ===================================================================

class TestBaselineDelta:
    def test_dead_containers_gone_and_issues_live(self, kb: KnowledgeLoader) -> None:
        """S0 pinned the legacy tool DEAD on real problem language: matched_rules=0 AND
        architecture_issues=0 (both dead ends). The rebuild eliminates both failure
        modes: on real matched signals the retrieved-issue set is non-empty, and the
        three dead rule-derived containers are gone from the contract."""
        assert PIN["cases"]["real_problem_language"]["matched_rules_count"] == 0
        assert PIN["cases"]["real_problem_language"]["architecture_issues_count"] == 0
        assert "matched_rules" in PIN["_meta"]["legacy_output_keys"]
        # after: a real hit produces issues, and the dead containers are gone
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert res["architecture_issues"]
        assert "matched_rules" not in res
        assert "scalability_flags" not in res
        assert "recommendations" in res  # kept, re-sourced


# ===================================================================
# DETERMINISM — identical input -> identical tiering + votes (fresh loader too)
# ===================================================================

class TestDeterminism:
    def test_identical_input_identical_tiering_and_votes(self, kb: KnowledgeLoader) -> None:
        sigs = _anchor_signals(kb)
        runs = [analyze_architecture(description=DESC, matched_signal_ids=sigs,
                                     constraints=SMALL_MVP) for _ in range(4)]

        def sig(res):
            return [(i["pattern_id"], i["confirmed"], i["retrieval"]["score"])
                    for i in res["architecture_issues"]]

        base = sig(runs[0])
        for other in runs[1:]:
            assert sig(other) == base
        # byte-reproducible from a freshly constructed loader
        assert sig(_fresh_call(description=DESC, matched_signal_ids=sigs, constraints=SMALL_MVP)) == base


# ===================================================================
# HYPERION — named ceilings at the caller boundary; no eval/regex on input
# ===================================================================

class TestCallerBoundaryCeilings:
    def test_matched_signal_ids_bounded(self, kb: KnowledgeLoader) -> None:
        """A flood of ids does not amplify work past the cap; junk abstains cleanly."""
        flood = [f"sig-{i:012x}" for i in range(_MAX_MATCHED_SIGNALS * 10)]
        res = analyze_architecture(description=DESC, matched_signal_ids=flood)
        assert res["retrieval_state"] == NO_MATCH  # all junk

    def test_constraints_cardinality_bounded(self, kb: KnowledgeLoader) -> None:
        huge = {f"k{i}": "v" for i in range(_MAX_CONSTRAINTS * 5)}
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints=huge)
        assert len(res["constraints_analyzed"]) <= _MAX_CONSTRAINTS

    def test_constraint_value_length_clipped(self, kb: KnowledgeLoader) -> None:
        res = analyze_architecture(
            description=DESC, matched_signal_ids=_anchor_signals(kb),
            constraints={"team_size": "1-3", "scale": "x" * (_MAX_CONSTRAINT_VALUE_LEN * 4)},
        )
        assert len(res["constraints_analyzed"]["scale"]) <= _MAX_CONSTRAINT_VALUE_LEN

    def test_description_bounded_and_never_surfaced(self, kb: KnowledgeLoader) -> None:
        """The untrusted free-text description is bounded where it enters
        (_MAX_DESCRIPTION_LEN, one source of truth in _shared) and never reaches the
        output surface — retrieval is driven by matched_signal_ids, not this text."""
        assert isinstance(_MAX_DESCRIPTION_LEN, int) and _MAX_DESCRIPTION_LEN > 0
        marker = "SENSITIVE_MARKER_" + "z" * (_MAX_DESCRIPTION_LEN * 3)
        res = analyze_architecture(description=marker, matched_signal_ids=_anchor_signals(kb),
                                   constraints=SMALL_MVP)
        assert isinstance(res, dict)
        assert "SENSITIVE_MARKER_" not in json.dumps(res)

    def test_no_eval_or_regex_on_caller_input(self, kb: KnowledgeLoader) -> None:
        """Injection-shaped constraint values are inert text, never executed, and the
        facet comparison never treats them as a pattern (categorical exact match)."""
        payloads = {"scale": "__import__('os').system('echo x')", "budget": "${7*7}",
                    "compliance": "'; DROP TABLE t; --"}
        res = analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                                   constraints={"team_size": "1-3", **payloads})
        assert isinstance(res, dict)
        assert res["constraints_analyzed"]["budget"] == "${7*7}"  # inert, not evaluated


# ===================================================================
# DELETIONS PROVEN — island gone, loader method gone, legacy matcher deleted (S6)
# ===================================================================

class TestDeletions:
    def test_anti_patterns_island_deleted(self) -> None:
        import coeus.tools.analyze_architecture as aa
        assert not hasattr(aa, "_ANTI_PATTERNS")

    def test_filter_by_constraints_deleted(self, kb: KnowledgeLoader) -> None:
        assert not hasattr(kb, "filter_by_constraints")
        assert not hasattr(KnowledgeLoader, "filter_by_constraints")

    # RETIRED (S6, story-16223628, council 9ccb9550): test_match_structural_signals_untouched
    # asserted hasattr(kb, "match_structural_signals") + that it still returned results — an
    # inverting guard that goes red the instant S6 deletes the matcher. The matcher is now
    # gone; its loader-level deletion is covered by the retired-class note in
    # tests/test_knowledge.py, and the zero-caller regression floor by
    # test_tool_no_longer_calls_match_structural_signals in tests/test_evaluate_scalability.py
    # and tests/test_assess_resilience.py. Retired named, no silent drop (Directive 12).


# ===================================================================
# DEEP-FREEZE — the singleton corpus stays uncorrupted through the tool
# ===================================================================

class TestCorpusUncorrupted:
    def test_corpus_singleton_uncorrupted_through_tool(self, kb: KnowledgeLoader) -> None:
        """The tool reads over deep-frozen hydrated patterns and builds fresh output
        dicts, so a full run cannot mutate the shared corpus (the shallow-ref hazard
        the hydrate-boundary deep_freeze closes)."""
        before = list(kb._lookup_pattern("microservices")["avoid_when"])
        analyze_architecture(description=DESC, matched_signal_ids=_anchor_signals(kb),
                             constraints=SMALL_MVP)
        after = list(kb._lookup_pattern("microservices")["avoid_when"])
        assert after == before
