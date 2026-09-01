# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Two-tier ranking re-proof — story-19e9ceb1, after reconciliation council a245d0e1.

``hydrate`` step-5 selects the top-k over a TWO-TIER key. Tier 1 (council
44a3d686) is the direct-vote flag: a directly-matched seed (tier True) outranks
every propagated-only fan-out hub (tier False) regardless of score, so no
zero-direct-vote hub can evict a gold seed under the k cap. Tier 2 (council
a245d0e1) is the pre-fan-out direct-vote COUNT within the seed tier (the
accumulated vote score for propagated-only neighbours): a seed ranks by its own
direct votes, not by a score a neighbour's fan-out inflated, so fan-out cannot
re-order the seed tier. The full key is
``(pattern_id in direct_votes, direct_votes[pid] if seed else score)``. Steps 1-4
(seed hydration, seed cap, fan-out) and the two ceilings are unchanged.

This module locks that behaviour:

* ``TestHubEvictionInvariant`` — the ranking invariant, built FAILING-FIRST from
  real production ordering (Directive 8). P16's directly-matched gold seed
  ``saga_orchestration`` is evicted from top-10 by two *named zero-direct-vote
  hubs* (``async_processing``, ``dead_letter_queue``) under the flat key the fix
  replaced, and survives under the two-tier key. The reconstruction of both the
  removed flat-key path and the live two-tier key is self-checked against
  ``hydrate`` so it is provably faithful.
* ``TestFrozenGMetricLock`` — the frozen concept-recall metric coeus-Gmetric-v1
  recomputed through the PRODUCTION ``hydrate`` path over the 25-problem blind
  set (``coeus_matches_v2``) and the 130-gold concept map, with the substrate
  hash-pinned. Ratchet floor (86/130 @10, 59/130 @5) + the council's >=86
  pass-bar, now MET by the direct-count secondary.
* ``test_seed_and_topk_caps_unchanged`` — the ceilings a ranking fix must not move.
* ``test_hydrate_ranking_is_deterministic`` — identical input -> identical ranking.
* ``test_direct_seed_ranking_correct_without_fanout`` — the seeds rank correctly
  with fan-out off (the corpus has no zero-fan-out pattern, so this is how a
  "seeds with zero fan-out neighbours" problem is exercised).

Fixtures ``tests/data/gmetric/{frozen_metric.json,coeus_matches_v2.json}`` are the
verbatim frozen artifacts; the baseline per-problem covered@10 is pinned inline
from ``baseline_ruleRouted_pinned.json`` (S0, Mnemos).
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import coeus.knowledge.loader as _kl
from coeus.knowledge.loader import HIT, KnowledgeLoader, _SEED_CAP, _TOPK_CAP

_DATA = Path(__file__).parent / "data" / "gmetric"
FROZEN = json.loads((_DATA / "frozen_metric.json").read_text(encoding="utf-8"))
MATCHES = json.loads((_DATA / "coeus_matches_v2.json").read_text(encoding="utf-8"))
KDIR = Path(_kl.__file__).parent  # the live knowledge dir the loader reads

# Baseline rule-routed covered@10 per problem (frozen S0, baseline_ruleRouted_pinned.json).
BASELINE_COVERED10 = {
    "P01": 0, "P02": 1, "P03": 2, "P04": 3, "P05": 3, "P06": 0, "P07": 0,
    "P08": 3, "P09": 1, "P10": 1, "P11": 0, "P12": 1, "P13": 0, "P14": 1,
    "P15": 1, "P16": 2, "P17": 0, "P18": 0, "P19": 2, "P20": 1, "P21": 0,
    "P22": 1, "P23": 0, "P24": 0, "P25": 0,
}
BASELINE_TOTAL10 = 23  # sum of the above; the number Shape C must beat

# Locked current results of the two-tier key (Themis re-proof measurement).
# Ratcheted UP 79->86 @10 / 52->59 @5 after council a245d0e1's direct-count
# secondary key; the floor tracks the achieved locked value per the ratchet rule.
LOCK_COVERED10 = 86   # recall@10 = 86/130 = 0.6615
LOCK_COVERED5 = 59    # recall@5  = 59/130 = 0.4538
COUNCIL_BAR10 = 86    # council 44a3d686 recall@10 pass-bar — now MET


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _direct_votes(kb: KnowledgeLoader, sigs: list[str]) -> dict[str, int]:
    """hydrate step 1: matched signal -> seed pattern(s), one vote each."""
    dv: dict[str, int] = {}
    for sid in sigs:
        entry = kb._signal_index.get(sid)
        if entry is None:
            continue
        for pid in entry["pattern_ids"]:
            dv[pid] = dv.get(pid, 0) + 1
    return dv


def _scores_and_direct_votes(kb: KnowledgeLoader, sigs: list[str]):
    """Faithful replica of hydrate steps 1-4 using the loader's OWN internals.

    Reconstructs the candidate ``scores`` and ``direct_votes`` so the removed
    flat-key ranking can be reproduced for the failing-first invariant proof.
    Faithfulness is asserted against live ``hydrate`` in
    ``test_reconstruction_is_faithful``.
    """
    dv = _direct_votes(kb, sigs)
    seeds = sorted(dv.items(), key=lambda kv: (-kv[1], kv[0]))[:_SEED_CAP]
    scores: dict[str, int] = dict(seeds)
    for pid, weight in seeds:
        seed_pat = kb._lookup_pattern(pid)
        if seed_pat is None:
            continue
        for neigh in seed_pat.get("related_patterns", []):
            if kb._lookup_pattern(neigh) is None:
                continue
            scores[neigh] = scores.get(neigh, 0) + weight
    return scores, dv


def _topk(scores: dict[str, int], dv: dict[str, int], k: int, two_tier: bool) -> list[str]:
    """hydrate step 5, parametrised by key so old (flat) and live (two-tier) rank."""
    import heapq
    ordered = sorted(scores.items())
    if two_tier:
        # live production key: direct-vote tier, then the pre-fan-out direct-vote
        # COUNT within the seed tier (accumulated vote score for propagated-only
        # neighbours) — council a245d0e1's secondary.
        key = lambda kv: (kv[0] in dv, dv[kv[0]] if kv[0] in dv else kv[1])  # noqa: E731
    else:
        key = lambda kv: (kv[1],)              # noqa: E731  (the removed flat key)
    return [pid for pid, _ in heapq.nlargest(k, ordered, key=key)]


def _shape_c_recall(kb: KnowledgeLoader):
    """Recompute frozen coeus-Gmetric-v1 concept-recall via the production hydrate.

    Grader (verbatim, frozen field 1_grader/3_score): a gold is covered@k iff its
    acceptable ``corpus_ids`` intersect the method's top-k pattern IDs;
    recall@k = covered / 130. Returns (covered_by_k, per_problem_covered10).
    """
    golds_by_problem: dict[str, list[dict]] = defaultdict(list)
    for g in FROZEN["reachable_set_map"]:
        golds_by_problem[g["problem"]].append(g)
    covered = {10: 0, 5: 0}
    per10: dict[str, int] = {}
    for p, golds in golds_by_problem.items():
        top = {
            10: [x["id"] for x in kb.hydrate(MATCHES[p], k=10, fan_out=True).patterns],
            5: [x["id"] for x in kb.hydrate(MATCHES[p], k=5, fan_out=True).patterns],
        }
        for k in (10, 5):
            tk = set(top[k])
            covered[k] += sum(1 for g in golds if set(g["corpus_ids"]) & tk)
        per10[p] = sum(1 for g in golds if set(g["corpus_ids"]) & set(top[10]))
    return covered, per10


# ===================================================================
# Ranking invariant — failing-first from real production ordering
# ===================================================================

class TestHubEvictionInvariant:
    """P16: two named zero-direct-vote hubs evict a gold seed under the flat key."""

    def test_reconstruction_is_faithful(self, kb: KnowledgeLoader) -> None:
        """The two-tier reconstruction must reproduce the live hydrate exactly,
        so the flat-key ranking it also produces is trustworthy evidence."""
        for p in ("P16", "P04"):
            scores, dv = _scores_and_direct_votes(kb, MATCHES[p])
            recon = _topk(scores, dv, 10, two_tier=True)
            real = [x["id"] for x in kb.hydrate(MATCHES[p], k=10, fan_out=True).patterns]
            assert recon == real, f"{p}: reconstruction diverged from hydrate"

    def test_old_flat_key_evicts_gold_seed(self, kb: KnowledgeLoader) -> None:
        """FAILING-FIRST: under the removed flat key, two zero-direct-vote hubs
        occupy top-10 and the directly-matched gold seed is evicted."""
        scores, dv = _scores_and_direct_votes(kb, MATCHES["P16"])
        old = _topk(scores, dv, 10, two_tier=False)
        # saga_orchestration is a directly matched seed ...
        assert dv.get("saga_orchestration", 0) >= 1
        # ... the two hubs carry ZERO direct votes (pure fan-out) ...
        assert "async_processing" not in dv
        assert "dead_letter_queue" not in dv
        # ... yet the flat key seats both hubs in top-10 and drops the seed.
        assert "async_processing" in old
        assert "dead_letter_queue" in old
        assert "saga_orchestration" not in old

    def test_two_tier_key_rescues_gold_seed(self, kb: KnowledgeLoader) -> None:
        """Under the new two-tier key the gold seed survives in top-10, flagged as
        a real direct-vote seed, and the demoted hubs are gone."""
        res = kb.hydrate(MATCHES["P16"], k=10, fan_out=True)
        top = [p["id"] for p in res.patterns]
        assert "saga_orchestration" in top
        saga = next(p for p in res.patterns if p["id"] == "saga_orchestration")
        assert saga["retrieval"]["seed"] is True
        assert saga["retrieval"]["direct_votes"] >= 1
        # the zero-direct-vote hubs no longer displace a seat
        assert "async_processing" not in top
        assert "dead_letter_queue" not in top

    def test_rescued_seed_is_a_graded_gold_win(self, kb: KnowledgeLoader) -> None:
        """Tie the invariant to the METRIC: the P16 Saga gold is MISSED under the
        old flat key and COVERED under the new two-tier key."""
        golds = [g for g in FROZEN["reachable_set_map"] if g["problem"] == "P16"]
        saga_gold = next(g for g in golds if "saga_orchestration" in g["corpus_ids"])
        scores, dv = _scores_and_direct_votes(kb, MATCHES["P16"])
        old = set(_topk(scores, dv, 10, two_tier=False))
        new = {p["id"] for p in kb.hydrate(MATCHES["P16"], k=10, fan_out=True).patterns}
        assert not (set(saga_gold["corpus_ids"]) & old)   # missed under flat key
        assert set(saga_gold["corpus_ids"]) & new         # covered under two-tier key

    def test_second_case_time_series_db(self, kb: KnowledgeLoader) -> None:
        """P04: the hub ``lambda_architecture`` (score 7, zero direct votes) evicts
        the gold seed ``time_series_db`` (score 6) under the flat key; the two-tier
        key keeps it."""
        scores, dv = _scores_and_direct_votes(kb, MATCHES["P04"])
        old = _topk(scores, dv, 10, two_tier=False)
        assert dv.get("time_series_db", 0) >= 1
        assert "lambda_architecture" not in dv
        assert "time_series_db" not in old
        new = [p["id"] for p in kb.hydrate(MATCHES["P04"], k=10, fan_out=True).patterns]
        assert "time_series_db" in new


# ===================================================================
# Frozen G-metric lock (coeus-Gmetric-v1 via production hydrate)
# ===================================================================

class TestFrozenGMetricLock:
    def test_substrate_matches_frozen_pins(self) -> None:
        """The metric is a pure function of the pinned corpus; if a pattern file
        drifts from its frozen hash the metric is INVALID (recompute_contract)."""
        pins = FROZEN["5_reproducibility"]["corpus_snapshot_patterns_sha256"]
        for fname, pin in pins.items():
            assert _sha256(KDIR / fname) == pin, f"{fname} drifted from frozen pin"

    def test_denominator_is_130_all_E(self) -> None:
        rm = FROZEN["reachable_set_map"]
        assert len(rm) == FROZEN["2_denominator"]["FROZEN_reachable_set_size"] == 130
        assert all(g["verdict"] == "E" for g in rm)

    def test_recall_recomputes_deterministically(self, kb: KnowledgeLoader) -> None:
        """Frozen map + hydrate = pure function: two recomputes are identical."""
        a, pa = _shape_c_recall(kb)
        b, pb = _shape_c_recall(kb)
        assert a == b
        assert pa == pb

    def test_all_matched_signals_resolve(self, kb: KnowledgeLoader) -> None:
        """Every matched signal id must exist in the live index, else the metric
        would silently measure a degraded input."""
        index_ids = {e["signal_id"] for e in kb.get_signal_index()}
        unresolved = {p: [s for s in sigs if s not in index_ids]
                      for p, sigs in MATCHES.items()}
        unresolved = {p: v for p, v in unresolved.items() if v}
        assert not unresolved, f"unresolved matched signals: {unresolved}"

    def test_recall_ratchet_floor(self, kb: KnowledgeLoader) -> None:
        """Locked floor: the two-tier key must not regress below the measured
        86/130 @10 and 59/130 @5 (25 problems present, denominator 130)."""
        covered, per10 = _shape_c_recall(kb)
        assert len(per10) == 25
        assert covered[10] >= LOCK_COVERED10
        assert covered[5] >= LOCK_COVERED5

    def test_beats_baseline_on_all_25(self, kb: KnowledgeLoader) -> None:
        """Council criterion (b): Shape C covered@10 >= rule-routed baseline
        covered@10 on every one of the 25 problems (baseline total 23/130)."""
        _, per10 = _shape_c_recall(kb)
        losses = {p: (per10[p], BASELINE_COVERED10[p])
                  for p in per10 if per10[p] < BASELINE_COVERED10[p]}
        assert not losses, f"regressed vs baseline on: {losses}"
        assert sum(BASELINE_COVERED10.values()) == BASELINE_TOTAL10

    def test_k5_is_prefix_of_k10(self, kb: KnowledgeLoader) -> None:
        """k=5 is the same ranking under a tighter cap: a strict prefix of k=10."""
        for p in MATCHES:
            b10 = [x["id"] for x in kb.hydrate(MATCHES[p], k=10, fan_out=True).patterns]
            b5 = [x["id"] for x in kb.hydrate(MATCHES[p], k=5, fan_out=True).patterns]
            assert b5 == b10[:5], f"{p}: k5 not a prefix of k10"

    def test_meets_council_recall_bar(self, kb: KnowledgeLoader) -> None:
        """Council a245d0e1 pass-bar (recall@10 >= 86/130) — MET. The direct-count
        secondary key lifts the seed tier 79 -> 86 (net +7 over the seed-tier
        reorder) while preserving every hub-eviction closure; the ratchet floor
        above is re-frozen at 86."""
        covered, _ = _shape_c_recall(kb)
        assert covered[10] >= COUNCIL_BAR10


# ===================================================================
# Regression guard — the ceilings a ranking fix must not move
# ===================================================================

def test_seed_and_topk_caps_unchanged() -> None:
    """Hyperion's bounds: a ranking fix must not move the fan-out ceilings."""
    assert _SEED_CAP == 64
    assert _TOPK_CAP == 50


# ===================================================================
# Determinism
# ===================================================================

def test_hydrate_ranking_is_deterministic(kb: KnowledgeLoader) -> None:
    """Same matched-signal input -> identical ranking and votes across runs, and
    across a freshly constructed loader (byte-reproducible index)."""
    sigs = MATCHES["P08"]
    runs = [[p["id"] for p in kb.hydrate(sigs, k=10, fan_out=True).patterns] for _ in range(5)]
    assert all(r == runs[0] for r in runs)
    vote_runs = [kb.hydrate(sigs, k=10, fan_out=True).votes for _ in range(3)]
    assert all(v == vote_runs[0] for v in vote_runs)
    fresh = [p["id"] for p in KnowledgeLoader().hydrate(sigs, k=10, fan_out=True).patterns]
    assert fresh == runs[0]


# ===================================================================
# Happy-path-not-only — direct-seed ranking with zero fan-out
# ===================================================================

def test_direct_seed_ranking_correct_without_fanout(kb: KnowledgeLoader) -> None:
    """No corpus pattern has empty ``related_patterns`` (min fan-out is 3), so a
    "seeds with zero fan-out neighbours" problem is exercised with fan_out=False:
    scores collapse to direct votes and the seeds must still rank correctly
    (weight desc, id asc) and surface as a hit with the seeds present."""
    sigs = MATCHES["P01"]
    res = kb.hydrate(sigs, k=10, fan_out=False)
    assert res.state == HIT
    assert res.patterns
    # with fan-out off, every hydrated pattern is a direct seed, zero propagation
    assert all(p["retrieval"]["seed"] is True for p in res.patterns)
    assert all(p["retrieval"]["propagated_votes"] == 0 for p in res.patterns)
    # ranking is exactly the direct votes ordered (-weight, id), truncated to k
    dv = _direct_votes(kb, sigs)
    expected = [pid for pid, _ in sorted(dv.items(), key=lambda kv: (-kv[1], kv[0]))][:10]
    assert [p["id"] for p in res.patterns] == expected
    # the top seed's score equals its raw direct vote count
    top = res.patterns[0]
    assert top["retrieval"]["score"] == dv[top["id"]]
