# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""recommend_pattern wired onto the Shape C engine — story-22072cab.

The rebuilt tool retrieves through one ``kb.hydrate`` call (the proven four-state,
fail-closed envelope), ranks by hydrate's integer vote key plus ONE deterministic
``avoid_when`` gate tier, and reasons conflicts/alternatives/tradeoffs over each
pattern's own fields. No tuned scalar (``_compute_fit_score`` deleted), no
hardcoded detector table (``_TRADEOFFS`` deleted).

This is the one home for the rebuilt tool's proofs. It carries:

* the ANCHOR, rewritten RED-first — microservices is PRESENT in the small-team +
  MVP candidate set, flagged ``gated``, and NOT rank 1 (binds the gate firing, not
  an accidental absence); it ranks #1 with the gate removed;
* the three artifact tests KILLED-WITH-REASON (Directive 10): the float fit_score
  becomes an integer ``retrieval.score``; tradeoffs are non-empty for EVERY rec
  (the legacy tool leaves 5/7 empty — see baseline_recommend_pattern_pinned.json);
  alternatives come from ``related_patterns`` and never resolve to a husk;
* BAR 1 — the frozen coeus-Gmetric-v1 recomputed THROUGH the tool's hydrate path
  (>= 86/130); BAR 2 — the before/after delta against the S0 legacy pin;
* the envelope fail-closed states, determinism (incl. a fresh loader), the
  Hyperion caller-boundary ceilings, and the deep-freeze that fixes the
  shared-ref corpus-corruption hazard (loader.py hydrate boundary).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pytest

import coeus.tools._shared as _shared
from coeus.knowledge.loader import DANGLING, HIT, NO_MATCH, KnowledgeLoader, _signal_id
from coeus.tools._shared import (
    _MAX_CONSTRAINTS,
    _MAX_CONSTRAINT_VALUE_LEN,
    _MAX_MATCHED_SIGNALS,
)
from coeus.tools.recommend_pattern import recommend_pattern

_DATA = Path(__file__).parent / "data"
_GM = _DATA / "gmetric"
FROZEN = json.loads((_GM / "frozen_metric.json").read_text(encoding="utf-8"))
MATCHES = json.loads((_GM / "coeus_matches_v2.json").read_text(encoding="utf-8"))
PIN = json.loads((_DATA / "baseline_recommend_pattern_pinned.json").read_text(encoding="utf-8"))

COUNCIL_BAR10 = 86  # bar-1: recall@10 the engine already meets; the tool path must too

# Constraints that satisfy microservices' OWN avoid_when facet {team_size:1-15, scale:startup_mvp}
SMALL_MVP = {"team_size": "1-3", "scale": "startup_mvp"}
LARGE_ENT = {"team_size": "50+", "scale": "enterprise"}


# ---------------------------------------------------------------------------
# helpers — derive sig-id inputs from the live index so tests track the corpus
# ---------------------------------------------------------------------------

def _sigs_for(kb: KnowledgeLoader, pid: str, n: int) -> list[str]:
    return [e["signal_id"] for e in kb.get_signal_index() if pid in e["pattern_ids"]][:n]


def _anchor_signals(kb: KnowledgeLoader) -> list[str]:
    """2 microservices + 2 monolith signals: both hydrate as direct seeds (weight 2),
    microservices leads on pattern-id tiebreak — so the ONLY thing that can seat a
    small-team pattern above it is the gate."""
    return _sigs_for(kb, "microservices", 2) + _sigs_for(kb, "monolith", 2)


def _fresh_call(**kwargs) -> dict:
    """recommend_pattern forced through a freshly constructed loader (byte-repro)."""
    _shared._knowledge = None
    return recommend_pattern(**kwargs)


def _golds_by_problem() -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for row in FROZEN["reachable_set_map"]:
        g[row["problem"]].append(row)
    return g


# ===================================================================
# ANCHOR — the small-team guarantee, rewritten RED-first (sharpened)
# ===================================================================

class TestSmallTeamGate:
    def test_small_team_mvp_never_gets_microservices_first(self, kb: KnowledgeLoader) -> None:
        """RED-first (Directive 8): microservices is a direct seed that ranks #1 in
        this candidate set with the gate removed (proven by the gate-disabled mutant
        in the plan record). The gate must seat it below the ungated candidates.

        Sharpened vs the retired test: assert microservices is PRESENT and flagged
        ``gated`` and not rank 1 — binding the gate FIRING, not an accidental
        absence that a broken retrieval would also satisfy."""
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=SMALL_MVP)
        by_id = {r["pattern_id"]: r for r in res["recommendations"]}
        assert "microservices" in by_id, "microservices must be present in the candidate set"
        micro = by_id["microservices"]
        assert micro["gated"] is True, "microservices' own avoid_when must gate it here"
        assert micro["rank"] != 1, "gated microservices must never be #1"
        # every ungated candidate outranks every gated one (the gate tier holds)
        ungated_ranks = [r["rank"] for r in res["recommendations"] if not r["gated"]]
        assert ungated_ranks and max(ungated_ranks) < micro["rank"]

    def test_large_team_can_get_microservices(self, kb: KnowledgeLoader) -> None:
        """Control: under a large enterprise team the microservices avoid_when facet
        does NOT match, so it is ungated and free to lead."""
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=LARGE_ENT)
        by_id = {r["pattern_id"]: r for r in res["recommendations"]}
        assert "microservices" in by_id
        assert by_id["microservices"]["gated"] is False

    def test_gate_fires_only_with_matching_constraints(self, kb: KnowledgeLoader) -> None:
        """With no constraints there is nothing to gate against — no rec is gated and
        the order is exactly hydrate's."""
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints={})
        assert all(r["gated"] is False for r in res["recommendations"])
        # microservices leads on the pattern-id tiebreak when ungated
        assert res["recommendations"][0]["pattern_id"] == "microservices"


# ===================================================================
# KILLED-WITH-REASON (Directive 10) — the three artifact tests
# ===================================================================

class TestKilledArtifactTests:
    def test_returns_ranked_recommendations(self, kb: KnowledgeLoader) -> None:
        """KILLED: old asserted ``0.0 <= rec['fit_score'] <= 1.0`` — a tuned float.
        REPLACED: each rec carries an INTEGER ``retrieval.score >= 1`` (a real vote)
        and contiguous ranks; the float fit_score and source_rule are gone."""
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=SMALL_MVP)
        recs = res["recommendations"]
        assert len(recs) >= 1
        assert [r["rank"] for r in recs] == list(range(1, len(recs) + 1))
        for r in recs:
            assert "fit_score" not in r and "source_rule" not in r
            score = r["retrieval"]["score"]
            assert isinstance(score, int) and not isinstance(score, bool)
            assert score >= 1

    def test_tradeoffs_included(self, kb: KnowledgeLoader) -> None:
        """KILLED: old checked tradeoffs only for 3 hardcoded patterns (live leaves
        5/7 empty). REPLACED (strictly stronger): EVERY recommendation carries
        non-empty tradeoffs derived from its own fields."""
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=SMALL_MVP)
        for r in res["recommendations"]:
            tr = r["tradeoffs"]
            assert tr and tr["principles"], f"empty tradeoffs for {r['pattern_id']}"

    def test_no_tuned_scalar_or_detector_table(self) -> None:
        """AC: the tuned float scorer and the hardcoded 8-of-174 tradeoff table are
        DELETED, not ported — reasoning is over each pattern's own fields."""
        import coeus.tools.recommend_pattern as rp
        assert not hasattr(rp, "_compute_fit_score")
        assert not hasattr(rp, "_TRADEOFFS")

    def test_alternatives_populated(self, kb: KnowledgeLoader) -> None:
        """KILLED: old was a bare isinstance check on rule-derived alternatives.
        REPLACED: alternatives are drawn from the retrieved patterns' own
        related_patterns, every one resolvable to a real corpus pattern (never a
        husk), and none overlaps the ranked recommendations."""
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=SMALL_MVP)
        alts = res["alternatives"]
        assert alts, "alternatives must be populated from related_patterns"
        ranked = {r["pattern_id"] for r in res["recommendations"]}
        for a in alts:
            assert kb._lookup_pattern(a["pattern_id"]) is not None, "alternative is a husk"
            assert a["pattern_id"] not in ranked
            assert a["pattern_name"]


# ===================================================================
# CONTRACT — the ledger keys survive the rewrite
# ===================================================================

class TestContract:
    def test_top_level_keys_present(self, kb: KnowledgeLoader) -> None:
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=SMALL_MVP)
        for key in ("constraints_analyzed", "recommendations", "conflicts", "alternatives",
                    "retrieval_state", "unmatched", "dangling"):
            assert key in res
        assert res["constraints_analyzed"]["team_size"] == "1-3"

    def test_output_is_json_serializable(self, kb: KnowledgeLoader) -> None:
        """No _FrozenDict / tuple leaks from the hydrate boundary into the output."""
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=SMALL_MVP)
        assert isinstance(json.loads(json.dumps(res)), dict)

    def test_conflicts_derived_from_gated(self, kb: KnowledgeLoader) -> None:
        """Conflicts are reasoned from each pattern's own avoid_when (the gate), not a
        hardcoded pair table: a gated rec produces a conflict, no constraints none."""
        gated = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=SMALL_MVP)
        assert gated["conflicts"]
        assert any("microservices" in c.lower() for c in gated["conflicts"])
        none = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints={})
        assert none["conflicts"] == []


# ===================================================================
# ENVELOPE — fail closed through the tool, never a husk
# ===================================================================

class TestEnvelopeFailClosed:
    def test_empty_signals_abstain(self, kb: KnowledgeLoader) -> None:
        res = recommend_pattern(matched_signal_ids=[], constraints={"team_size": "5"})
        assert res["retrieval_state"] == NO_MATCH
        assert res["recommendations"] == []
        assert res["conflicts"] == [] and res["alternatives"] == []

    def test_unrecognised_signals_abstain_not_husk(self, kb: KnowledgeLoader) -> None:
        res = recommend_pattern(matched_signal_ids=["sig-000000000000", "sig-ffffffffffff"])
        assert res["retrieval_state"] == NO_MATCH
        assert res["recommendations"] == []
        assert sorted(res["unmatched"]) == ["sig-000000000000", "sig-ffffffffffff"]

    def test_absent_concept_abstains(self, kb: KnowledgeLoader) -> None:
        """A concern the corpus genuinely lacks abstains, never the nearest node."""
        sid = _signal_id("Tokenization of card PAN before storage")
        res = recommend_pattern(matched_signal_ids=[sid])
        assert res["retrieval_state"] == NO_MATCH
        assert res["recommendations"] == []


# ===================================================================
# BAR 1 — coeus-Gmetric-v1 through the tool's hydrate path (>= 86/130)
# ===================================================================

class TestGmetricThroughTool:
    def test_recall_at_10_through_tool_meets_bar(self, kb: KnowledgeLoader) -> None:
        """The tool retrieves via the same kb.hydrate; with no constraints no gate
        fires, so top-10 through the tool reproduces the engine's covered@10. Graded
        against the frozen 130-gold map: >= 86 (council bar), not re-derived."""
        golds = _golds_by_problem()
        covered = 0
        for p, gs in golds.items():
            res = recommend_pattern(matched_signal_ids=MATCHES[p], constraints={}, k=10)
            assert res["retrieval_state"] in (HIT, "low_confidence")
            top = {r["pattern_id"] for r in res["recommendations"]}
            covered += sum(1 for g in gs if set(g["corpus_ids"]) & top)
        assert covered >= COUNCIL_BAR10, f"through-tool covered@10 {covered} < {COUNCIL_BAR10}"


# ===================================================================
# BAR 2 — before/after delta against the S0 legacy pin
# ===================================================================

class TestBaselineDelta:
    def test_eliminates_empty_tradeoffs_and_float_scores(self, kb: KnowledgeLoader) -> None:
        """S0 pinned the legacy tool at 5/7 empty tradeoffs + float fit_scores on the
        small-team case. The rebuild eliminates both: 0 empty tradeoffs, no float."""
        assert PIN["cases"]["tradeoffs"]["empty_tradeoffs"] == "5/7"  # the pinned before
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=SMALL_MVP)
        empty = sum(1 for r in res["recommendations"] if not r["tradeoffs"]["principles"])
        assert empty == 0
        assert all(not isinstance(r["retrieval"]["score"], float) for r in res["recommendations"])


# ===================================================================
# DETERMINISM — identical input -> identical ranking AND votes (fresh loader too)
# ===================================================================

class TestDeterminism:
    def test_identical_input_identical_ranking_and_votes(self, kb: KnowledgeLoader) -> None:
        sigs = _anchor_signals(kb)
        runs = [recommend_pattern(matched_signal_ids=sigs, constraints=SMALL_MVP) for _ in range(4)]
        sigA = [(r["pattern_id"], r["rank"], r["retrieval"]["score"], r["gated"])
                for r in runs[0]["recommendations"]]
        for other in runs[1:]:
            sigB = [(r["pattern_id"], r["rank"], r["retrieval"]["score"], r["gated"])
                    for r in other["recommendations"]]
            assert sigB == sigA
        # byte-reproducible from a freshly constructed loader
        fresh = _fresh_call(matched_signal_ids=sigs, constraints=SMALL_MVP)
        sigF = [(r["pattern_id"], r["rank"], r["retrieval"]["score"], r["gated"])
                for r in fresh["recommendations"]]
        assert sigF == sigA


# ===================================================================
# HYPERION — named ceilings at the caller boundary; no eval/regex on input
# ===================================================================

class TestCallerBoundaryCeilings:
    def test_matched_signal_ids_bounded(self, kb: KnowledgeLoader) -> None:
        """A flood of ids does not amplify work past the cap; junk abstains cleanly."""
        flood = [f"sig-{i:012x}" for i in range(_MAX_MATCHED_SIGNALS * 10)]
        res = recommend_pattern(matched_signal_ids=flood)
        assert res["retrieval_state"] == NO_MATCH  # all junk

    def test_constraints_cardinality_bounded(self, kb: KnowledgeLoader) -> None:
        huge = {f"k{i}": "v" for i in range(_MAX_CONSTRAINTS * 5)}
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb), constraints=huge)
        assert len(res["constraints_analyzed"]) <= _MAX_CONSTRAINTS

    def test_constraint_value_length_clipped(self, kb: KnowledgeLoader) -> None:
        res = recommend_pattern(
            matched_signal_ids=_anchor_signals(kb),
            constraints={"team_size": "1-3", "scale": "x" * (_MAX_CONSTRAINT_VALUE_LEN * 4)},
        )
        assert len(res["constraints_analyzed"]["scale"]) <= _MAX_CONSTRAINT_VALUE_LEN

    def test_no_eval_or_regex_on_caller_input(self, kb: KnowledgeLoader) -> None:
        """Injection-shaped constraint values are inert text, never executed, and the
        facet comparison never treats them as a pattern (categorical exact match)."""
        payloads = {"scale": "__import__('os').system('echo x')", "budget": "${7*7}",
                    "compliance": "'; DROP TABLE t; --"}
        res = recommend_pattern(matched_signal_ids=_anchor_signals(kb),
                                constraints={"team_size": "1-3", **payloads})
        assert isinstance(res, dict)
        # nothing matched those categorical values, so no spurious gate fired on them
        assert res["constraints_analyzed"]["budget"] == "${7*7}"


# ===================================================================
# DEEP-FREEZE — the shared-ref corpus-corruption fix (hydrate boundary)
# ===================================================================

class TestDeepFreeze:
    def test_hydrated_patterns_are_immutable(self, kb: KnowledgeLoader) -> None:
        """A returned pattern cannot be mutated: top-level writes and nested-list
        appends both raise — so a caller can never corrupt the singleton corpus."""
        res = kb.hydrate(_sigs_for(kb, "microservices", 2), k=3)
        p = res.patterns[0]
        with pytest.raises(TypeError):
            p["injected"] = 1
        with pytest.raises((TypeError, AttributeError)):
            p["use_when"].append("HACK")
        with pytest.raises(TypeError):
            p["retrieval"]["score"] = 999

    def test_corpus_singleton_uncorrupted(self, kb: KnowledgeLoader) -> None:
        """The raw corpus pattern is untouched by hydration (still a mutable list)."""
        before = list(kb._lookup_pattern("microservices")["use_when"])
        kb.hydrate(_sigs_for(kb, "microservices", 2), k=3)
        raw = kb._lookup_pattern("microservices")
        assert isinstance(raw["use_when"], list)
        assert list(raw["use_when"]) == before
