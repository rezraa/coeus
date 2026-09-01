# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""G-envelope proof — the four-state retrieval contract of ``hydrate``.

story-19e9ceb1 S7. Proves every state of the fail-closed envelope is reachable
and that abstention is a *structural* verdict, never a husk or a bare list
narrated as an answer:

* ``hit``            — >=1 pattern hydrated at/above the confidence floor.
* ``low_confidence`` — patterns hydrated, best below the floor.
* ``no_match``       — the empty leg: signals produce zero corpus patterns.
* ``dangling``       — hydrated ids do not resolve to corpus patterns
                       (dormant on the clean frozen corpus; reachability of the
                       state machine is proven against an injected dangling ref).

Plus a RED negation test: signals for a concern the corpus genuinely lacks must
abstain (``no_match``), never surface the nearest confident node.
"""
from __future__ import annotations

from collections import defaultdict

import pytest

from coeus.knowledge.loader import (
    DANGLING,
    HIT,
    LOW_CONFIDENCE,
    NO_MATCH,
    KnowledgeLoader,
    RetrievalResult,
    _signal_id,
)


# ---------------------------------------------------------------------------
# helpers — derive fixtures from the live index so the tests track the corpus
# ---------------------------------------------------------------------------

def _sig_ids_for_one_pattern(kb: KnowledgeLoader) -> tuple[str, list[str]]:
    """Return (pattern_id, [>=2 distinct signal ids all owned by it]).

    Every signal maps to exactly one pattern in this corpus, so two distinct
    signals sharing a pattern give that pattern a direct weight of 2 -> a hit.
    """
    by_pat: dict[str, list[str]] = defaultdict(list)
    for e in kb.get_signal_index():
        if len(e["pattern_ids"]) == 1:
            by_pat[e["pattern_ids"][0]].append(e["signal_id"])
    for pid, sigs in sorted(by_pat.items()):
        if len(sigs) >= 2:
            return pid, sorted(sigs)[:2]
    raise AssertionError("corpus has no pattern with >=2 signals")


def _one_sig_id(kb: KnowledgeLoader) -> str:
    """A single recognised signal id (weight 1 -> best score 1 -> low_confidence)."""
    return kb.get_signal_index()[0]["signal_id"]


def _is_husk(pattern: dict) -> bool:
    """A husk is the synthesised ``{id, name}`` stand-in for a missing pattern."""
    return set(pattern.keys()) <= {"id", "name", "retrieval"} and pattern.get("id") == pattern.get("name")


# ===================================================================
# State (a) — hit
# ===================================================================

class TestHitState:
    def test_two_signals_on_one_pattern_hit(self, kb: KnowledgeLoader) -> None:
        """Two signals feeding one pattern clear the confidence floor -> hit."""
        pid, sigs = _sig_ids_for_one_pattern(kb)
        res = kb.hydrate(sigs, k=10)
        assert res.state == HIT
        assert res.patterns, "hit must carry ranked patterns"
        assert res.patterns[0]["retrieval"]["score"] >= 2
        # the directly-matched seed is present and is a real pattern, not a husk
        by_id = {p["id"]: p for p in res.patterns}
        assert pid in by_id
        assert not _is_husk(by_id[pid])
        assert "category" in by_id[pid] and "description" in by_id[pid]

    def test_hit_patterns_are_all_real(self, kb: KnowledgeLoader) -> None:
        """No hydrated pattern in a hit is a husk."""
        _, sigs = _sig_ids_for_one_pattern(kb)
        res = kb.hydrate(sigs, k=10)
        assert all(not _is_husk(p) for p in res.patterns)


# ===================================================================
# State (b) — low_confidence
# ===================================================================

class TestLowConfidenceState:
    def test_single_signal_is_low_confidence(self, kb: KnowledgeLoader) -> None:
        """One signal (weight 1) hydrates patterns but stays below the floor."""
        res = kb.hydrate([_one_sig_id(kb)], k=10)
        assert res.state == LOW_CONFIDENCE
        assert res.patterns, "low_confidence still surfaces the ranked patterns"
        assert res.patterns[0]["retrieval"]["score"] < 2
        assert "below confidence floor" in res.reason


# ===================================================================
# State (c) — no_match  (the empty leg: recognised input, zero patterns)
# ===================================================================

class TestNoMatchEmptyLeg:
    def test_empty_input_abstains(self, kb: KnowledgeLoader) -> None:
        """An empty signal list is a structural no_match, not a bare []."""
        res = kb.hydrate([], k=10)
        assert isinstance(res, RetrievalResult)
        assert res.state == NO_MATCH
        assert res.patterns == []

    def test_unrecognised_signals_abstain_not_husk(self, kb: KnowledgeLoader) -> None:
        """Signals that hydrate to zero patterns return no_match — never a husk,
        never a bare list dressed up as an answer."""
        res = kb.hydrate(["sig-000000000000", "sig-ffffffffffff"], k=10)
        assert res.state == NO_MATCH
        assert res.patterns == []                     # abstention, not an empty "answer"
        assert res.unmatched_signals == ["sig-000000000000", "sig-ffffffffffff"]
        # the fail-closed contract: the caller is told WHY, structurally
        assert res.reason
        # and nothing husk-shaped leaked into the (empty) result
        assert all(not _is_husk(p) for p in res.patterns)


# ===================================================================
# State (d) — dangling  (dormant on the frozen corpus; reachable in principle)
# ===================================================================

class TestDanglingState:
    def test_frozen_corpus_never_dangles(self, kb: KnowledgeLoader) -> None:
        """Referential integrity: no live signal maps to an unresolvable id, so
        the frozen corpus never surfaces a dangling field or state. This is the
        desired production posture — the mechanism is armed but has nothing to
        report."""
        all_ids = {p["id"] for p in kb._all_patterns}
        for e in kb.get_signal_index():
            assert all(pid in all_ids for pid in e["pattern_ids"])
        # a real multi-signal hit carries an empty dangling field
        _, sigs = _sig_ids_for_one_pattern(kb)
        assert kb.hydrate(sigs, k=10).dangling == []

    def test_dangling_state_reachable_via_unresolvable_seed(self) -> None:
        """Inject a signal whose only pattern id is a ghost: the envelope must
        fail closed to state=dangling and surface the ghost id — never a husk."""
        kb = KnowledgeLoader()
        kb._signal_index["sig-ghostseed01"] = {
            "signal_id": "sig-ghostseed01",
            "signal_text": "ghost seed",
            "pattern_ids": ["__ghost_pattern__"],
        }
        res = kb.hydrate(["sig-ghostseed01"], k=10)
        assert res.state == DANGLING
        assert res.patterns == []
        assert "__ghost_pattern__" in res.dangling

    def test_dangling_field_surfaces_loud_on_a_hit(self) -> None:
        """A ghost *neighbour* on an otherwise-good seed is surfaced in the
        dangling field of a hit, not silently dropped."""
        kb = KnowledgeLoader()
        pid, sigs = _sig_ids_for_one_pattern(kb)
        kb._lookup_pattern(pid)["related_patterns"] = ["__ghost_neighbour__"]
        res = kb.hydrate(sigs, k=10, fan_out=True)
        assert res.state == HIT
        assert "__ghost_neighbour__" in res.dangling


# ===================================================================
# RED negation — a concern the corpus genuinely lacks must abstain
# ===================================================================

# absent-content golds (frozen_metric coeus-Gmetric-v1 absent_content_floor),
# each verified to have no corpus pattern id and no signal text.
ABSENT_CONCERNS = [
    "Tokenization of card PAN before storage",
    "Bloom Filter for frequency capping",
    "WebRTC SFU for selective forwarding",
    "Hedged Requests to cut tail latency",
    "Geohash spatial index for proximity",
    "Shuffle Sharding for tenant isolation",
]


class TestRedNegation:
    @pytest.mark.parametrize("concern", ABSENT_CONCERNS)
    def test_absent_concern_abstains_not_nearest_node(
        self, kb: KnowledgeLoader, concern: str
    ) -> None:
        """A signal for a concept absent from the corpus produces no recognised
        signal id, so hydrate abstains (no_match) rather than returning the
        nearest confident pattern."""
        sid = _signal_id(concern)
        assert sid not in kb._signal_index, f"unexpected corpus signal for {concern!r}"
        res = kb.hydrate([sid], k=10)
        assert res.state == NO_MATCH
        assert res.patterns == []          # NOT the nearest node

    def test_present_concern_does_not_abstain(self, kb: KnowledgeLoader) -> None:
        """Control: a real corpus signal is not swallowed by the negation path."""
        res = kb.hydrate([_one_sig_id(kb)], k=10)
        assert res.state in (HIT, LOW_CONFIDENCE)
        assert res.patterns
