# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""KnowledgeLoader for Coeus architecture knowledge base.

Loads architecture_patterns.json, scalability_patterns.json, api_and_data.json,
and decision_rules.json. Provides pattern retrieval, the signal-index retrieval
engine (problem-language signals hydrated directly into patterns, ranked by a
one-hop fan-out, returned in a four-state fail-closed envelope), and the legacy
rule matcher (exact substring against decision_rules).
"""

from __future__ import annotations

import hashlib
import heapq
import json
from dataclasses import dataclass, field
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).parent

# --------------------------------------------------------------------------
# Retrieval engine — the signal-index hydrate path (problem-language -> pattern)
# --------------------------------------------------------------------------
#
# The four-state retrieval envelope is the single output contract. Every
# retrieval resolves to exactly one state, and abstention is a structural field
# rather than an empty list narrated as an answer (fail closed, never a husk).
HIT = "hit"                        # >=1 pattern hydrated at/above the confidence floor
LOW_CONFIDENCE = "low_confidence"  # patterns hydrated, best below the confidence floor
NO_MATCH = "no_match"              # signals recognised but none map to a corpus pattern
DANGLING = "dangling"              # signals map only to ids absent from the corpus

# Two named ceilings bound the fan-out's agency, applied where cost is incurred:
_SEED_CAP: int = 64    # max seed patterns admitted to fan-out (bound BEFORE expansion)
_TOPK_CAP: int = 50    # hard ceiling on hydrated results (bound AFTER expansion)

# A hit needs at least this many corroborating votes (direct + propagated); a
# lone single vote is surfaced but flagged low_confidence. Auditable integer,
# not a tuned score.
_CONFIDENCE_FLOOR: int = 2


def _signal_id(text: str) -> str:
    """Deterministic, byte-reproducible id for a signal's text.

    A stable content hash so the corpus-derived index recomputes identically
    across processes and the LLM/harness can refer to a signal by a short id.
    """
    return "sig-" + hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class RetrievalResult:
    """The single retrieval output contract (see the four states above).

    ``patterns`` is the ranked, hydrated result (empty for the abstention
    states). ``votes`` is the transparent, auditable tally used for ranking
    (pattern_id -> integer vote count). ``dangling`` surfaces any referenced
    pattern id that did not resolve to a corpus pattern -- an integrity failure
    is reported, never masked by a husk. ``unmatched_signals`` records matched
    signal ids the index did not recognise.
    """

    state: str
    patterns: list[dict] = field(default_factory=list)
    votes: dict[str, int] = field(default_factory=dict)
    dangling: list[str] = field(default_factory=list)
    unmatched_signals: list[str] = field(default_factory=list)
    reason: str = ""


class _FrozenDict(dict):
    """A read-only ``dict``: refuses in-place mutation, serialises as a plain dict.

    Hydrated patterns are deep-frozen through this type so a caller cannot corrupt
    the shared singleton corpus by mutating a returned pattern (the shallow-copy
    shared-reference hazard: ``{**pat}`` copies the top dict but aliases its nested
    lists). It subclasses ``dict`` so ``json.dumps`` and ``["key"]`` reads work
    unchanged; only the mutators are sealed.
    """

    __slots__ = ()

    def _readonly(self, *_a: object, **_k: object) -> None:
        raise TypeError("hydrated pattern is read-only")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _readonly


def deep_freeze(obj: object) -> object:
    """Recursively copy *obj* into an immutable, JSON-serialisable structure.

    Dicts become :class:`_FrozenDict`, lists/tuples become tuples, scalars pass
    through. The copy severs every shared reference to the source, so this both
    fixes the shared-ref corruption hazard and makes the result tamper-proof.
    """
    if isinstance(obj, dict):
        return _FrozenDict({k: deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return tuple(deep_freeze(v) for v in obj)
    return obj


def _parse_team_range(token: object) -> tuple[float, float] | None:
    """Parse a ``team_size`` token (``"1-5"``, ``"50+"``, ``"3"``) into ``(lo, hi)``.

    Pure string arithmetic — no regex, no eval on caller input. Returns ``None``
    for anything unparseable so the gate can fail OPEN (never demote on a token it
    cannot read).
    """
    s = str(token).strip()
    if not s:
        return None
    try:
        if s.endswith("+"):
            return (int(s[:-1]), float("inf"))
        if "-" in s:
            lo, hi = s.split("-", 1)
            return (int(lo), int(hi))
        n = int(s)
        return (n, n)
    except (ValueError, TypeError):
        return None


def facet_matches(facet: dict, constraints: dict) -> bool:
    """Does one structured facet hold under the caller's *constraints*?

    The single facet-matching predicate shared by every concern tool (one source
    of truth, not one copy per tool). A facet is an AND of conditions; it matches
    only when the constraints confirm *every* key:

    * ``team_size`` — numeric range overlap (``"1-15"`` vs ``"1-3"``);
    * every other key — categorical exact match (case/whitespace-normalised, never
      substring — the legacy substring sin is what this replaces).

    Pure comparison only: no ``eval``/regex on caller input. A key the constraints
    do not specify, or a ``team_size`` neither side can parse, yields ``False`` —
    the caller is never demoted on unconfirmed or unreadable input (fail open).
    """
    if not isinstance(facet, dict) or not facet:
        return False
    for key, fval in facet.items():
        cval = constraints.get(key)
        if cval is None:
            return False
        if key == "team_size":
            fr, cr = _parse_team_range(fval), _parse_team_range(cval)
            if fr is None or cr is None:
                return False
            if not (fr[0] <= cr[1] and cr[0] <= fr[1]):
                return False
        elif str(cval).strip().lower() != str(fval).strip().lower():
            return False
    return True


def split_conditions(items: list | None) -> tuple[list[str], list[dict]]:
    """Partition a pattern ``use_when``/``avoid_when`` list into its two kinds.

    These lists are mixed by design: free-text condition strings (for LLM
    recognition) and structured facet dicts such as ``{"team_size": "1-6"}``
    (for deterministic gating). Any reader dispatches on element type through
    this one helper. Single pass; tolerates ``None``.

    Returns ``(text_conditions, facet_constraints)``.
    """
    texts: list[str] = []
    facets: list[dict] = []
    for item in items or []:
        (facets if isinstance(item, dict) else texts).append(item)
    return texts, facets


def is_gated(pattern: dict, constraints: dict) -> bool:
    """Is *pattern* gated by its OWN ``avoid_when`` facets under *constraints*?

    The one deterministic gate: a pattern whose own ``avoid_when`` carries a
    structured facet the constraints satisfy is in tension with those constraints
    and sinks below the ungated candidates. Reasoning over the pattern's own field,
    not a hardcoded detector — this is the general form of the small-team guarantee
    (microservices' ``avoid_when`` names ``{team_size: 1-15, scale: startup_mvp}``).
    """
    if not constraints:
        return False
    _, facets = split_conditions(pattern.get("avoid_when"))
    return any(facet_matches(f, constraints) for f in facets)


class KnowledgeLoader:
    """Loads and queries the Coeus knowledge base (architecture patterns,
    scalability patterns, API/data patterns, decision rules).

    All matching is structural / exact / data-driven.  No fuzzy keyword overlap.
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self._dir = knowledge_dir or _KNOWLEDGE_DIR

        with open(self._dir / "architecture_patterns.json", encoding="utf-8") as f:
            self._architecture_patterns_data = json.load(f)

        with open(self._dir / "scalability_patterns.json", encoding="utf-8") as f:
            self._scalability_patterns_data = json.load(f)

        with open(self._dir / "api_and_data.json", encoding="utf-8") as f:
            self._api_data_patterns_data = json.load(f)

        with open(self._dir / "decision_rules.json", encoding="utf-8") as f:
            self._decision_rules_data = json.load(f)

        # Build convenience lists.
        self._architecture_patterns: list[dict] = self._architecture_patterns_data["patterns"]
        self._scalability_patterns: list[dict] = self._scalability_patterns_data["patterns"]
        self._api_data_patterns: list[dict] = self._api_data_patterns_data["patterns"]
        self._decision_rules: list[dict] = self._decision_rules_data["rules"]

        # Index: id -> dict
        self._architecture_index: dict[str, dict] = {
            p["id"]: p for p in self._architecture_patterns
        }
        self._scalability_index: dict[str, dict] = {
            p["id"]: p for p in self._scalability_patterns
        }
        self._api_data_index: dict[str, dict] = {
            p["id"]: p for p in self._api_data_patterns
        }
        self._rule_index: dict[str, dict] = {
            r["id"]: r for r in self._decision_rules
        }

        # All corpus patterns in a single stable order -- one source of truth
        # for the signal index build and fan-out neighbour resolution.
        self._all_patterns: list[dict] = (
            self._architecture_patterns
            + self._scalability_patterns
            + self._api_data_patterns
        )

        # Signal index: signal_id -> {signal_id, signal_text, pattern_ids}.
        # Derived deterministically from each pattern's own ``signals`` so the
        # view is byte-reproducible (ids are content hashes; pattern_ids sorted).
        self._signal_index: dict[str, dict] = {}
        for pattern in self._all_patterns:
            pid = pattern["id"]
            for raw in pattern.get("signals", []):
                text = raw.strip()
                if not text:
                    continue
                sid = _signal_id(text)
                entry = self._signal_index.get(sid)
                if entry is None:
                    self._signal_index[sid] = {
                        "signal_id": sid,
                        "signal_text": text,
                        "pattern_ids": [pid],
                    }
                elif entry["signal_text"] != text:
                    # A 48-bit hash clash between two distinct signals would
                    # silently merge them; fail closed at load rather than
                    # serve a corrupted index.
                    raise ValueError(
                        f"signal_id collision {sid}: "
                        f"{text!r} vs {entry['signal_text']!r}"
                    )
                elif pid not in entry["pattern_ids"]:
                    entry["pattern_ids"].append(pid)
        for entry in self._signal_index.values():
            entry["pattern_ids"].sort()

    # ------------------------------------------------------------------
    # Pure retrieval — architecture patterns
    # ------------------------------------------------------------------

    def get_pattern(self, pattern_id: str) -> dict | None:
        """Get an architecture pattern by ID."""
        return self._architecture_index.get(pattern_id)

    def get_patterns_by_category(self, category: str) -> list[dict]:
        """Get all architecture patterns in a given category."""
        return [p for p in self._architecture_patterns if p.get("category") == category]

    def list_pattern_categories(self) -> list[str]:
        """List all unique architecture pattern categories."""
        cats: set[str] = set()
        for p in self._architecture_patterns:
            cat = p.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    # ------------------------------------------------------------------
    # Pure retrieval — scalability patterns
    # ------------------------------------------------------------------

    def get_scalability_pattern(self, pattern_id: str) -> dict | None:
        """Get a scalability pattern by ID."""
        return self._scalability_index.get(pattern_id)

    def get_scalability_by_category(self, category: str) -> list[dict]:
        """Get all scalability patterns in a given category."""
        return [p for p in self._scalability_patterns if p.get("category") == category]

    def list_scalability_categories(self) -> list[str]:
        """List all unique scalability pattern categories."""
        cats: set[str] = set()
        for p in self._scalability_patterns:
            cat = p.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    # ------------------------------------------------------------------
    # Pure retrieval — API and data patterns
    # ------------------------------------------------------------------

    def get_api_data_pattern(self, pattern_id: str) -> dict | None:
        """Get an API/data pattern by ID."""
        return self._api_data_index.get(pattern_id)

    def get_api_data_by_category(self, category: str) -> list[dict]:
        """Get all API/data patterns in a given category."""
        return [p for p in self._api_data_patterns if p.get("category") == category]

    def list_api_data_categories(self) -> list[str]:
        """List all unique API/data pattern categories."""
        cats: set[str] = set()
        for p in self._api_data_patterns:
            cat = p.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    # ------------------------------------------------------------------
    # Pure retrieval — decision rules
    # ------------------------------------------------------------------

    def get_rule(self, rule_id: str) -> dict | None:
        """Get a decision rule by ID."""
        return self._rule_index.get(rule_id)

    def get_rules_by_category(self, category: str) -> list[dict]:
        """Get all decision rules in a given category."""
        return [r for r in self._decision_rules if r.get("category") == category]

    # ------------------------------------------------------------------
    # Pattern-id resolution (retrieval engine + tools)
    # ------------------------------------------------------------------

    def _lookup_pattern(self, pattern_id: str) -> dict | None:
        """Resolve a pattern id across all three pattern files, fail closed.

        Returns the real pattern dict or ``None`` -- never a synthesised
        ``{id, name}`` husk. This is the single source of truth for turning a
        pattern id into a pattern; the retrieval engine records a ``None`` as a
        typed ``dangling`` reference in the envelope.
        """
        return (
            self._architecture_index.get(pattern_id)
            or self._scalability_index.get(pattern_id)
            or self._api_data_index.get(pattern_id)
        )

    # ------------------------------------------------------------------
    # Signal-index retrieval engine (problem-language -> pattern)
    # ------------------------------------------------------------------

    def get_signal_index(self) -> list[dict]:
        """Return the deterministic, byte-reproducible signal index view.

        Each entry is ``{signal_id, signal_text, pattern_ids}``; the LLM
        recognises a problem's signals against this view at runtime and passes
        the matched signal ids to :meth:`hydrate`. Sorted by ``signal_id`` with
        sorted ``pattern_ids`` so two builds serialise identically.
        """
        return [
            {
                "signal_id": e["signal_id"],
                "signal_text": e["signal_text"],
                "pattern_ids": list(e["pattern_ids"]),
            }
            for e in sorted(self._signal_index.values(), key=lambda e: e["signal_id"])
        ]

    def hydrate(
        self,
        matched_signal_ids: list[str],
        k: int = 10,
        fan_out: bool = True,
    ) -> RetrievalResult:
        """Hydrate matched signals into ranked patterns, in the four-state envelope.

        End-to-end entry point a harness drives given matched signal ids:

        * maps each signal id -> its owning pattern(s), tallying a direct vote
          per signal (a seed's weight = number of matched signals mapping to it);
        * one-hop fan-out over ``related_patterns`` from the capped seed set,
          propagating each seed's weight to its neighbours (when ``fan_out``);
        * selects the top-``k`` via a size-k heap (``heapq.nlargest``, O(n log k))
          over a two-tier composite key: direct-vote tier (a directly-matched
          seed outranks every propagated-only neighbour), then the pre-fan-out
          direct-vote count within the seed tier (accumulated vote score for
          propagated-only neighbours), then pattern id ascending — deterministic
          throughout.

        Bounded by two ceilings: ``_SEED_CAP`` before fan-out and ``_TOPK_CAP``
        after. Votes are transparent integer counts, never a tuned score.
        """
        k = min(max(int(k), 1), _TOPK_CAP)

        # 1. Direct hydration: matched signal -> seed pattern(s), one vote each.
        unmatched: list[str] = []
        direct_votes: dict[str, int] = {}
        for sid in matched_signal_ids or []:
            entry = self._signal_index.get(sid)
            if entry is None:
                unmatched.append(sid)
                continue
            for pid in entry["pattern_ids"]:
                direct_votes[pid] = direct_votes.get(pid, 0) + 1

        # Empty leg: recognised signals that hydrate to nothing -> abstain.
        if not direct_votes:
            return RetrievalResult(
                state=NO_MATCH,
                unmatched_signals=sorted(set(unmatched)),
                reason="no matched signal maps to a corpus pattern",
            )

        # 2. Seed cap BEFORE fan-out: rank seeds (weight desc, id asc), bound.
        seeds = sorted(direct_votes.items(), key=lambda kv: (-kv[1], kv[0]))[:_SEED_CAP]

        # 3. Vote tally seeded from the capped seeds' direct votes.
        scores: dict[str, int] = dict(seeds)
        dangling: set[str] = set()

        # 4. One-hop fan-out: propagate each seed's weight to its neighbours.
        if fan_out:
            for pid, weight in seeds:
                seed_pat = self._lookup_pattern(pid)
                if seed_pat is None:
                    continue
                for neighbour in seed_pat.get("related_patterns", []):
                    if self._lookup_pattern(neighbour) is None:
                        dangling.add(neighbour)   # typed dangling, surfaced loud
                        continue
                    scores[neighbour] = scores.get(neighbour, 0) + weight

        # 5. Top-k via heap-top-k over a TWO-TIER composite key. Pre-order
        #    candidates by id asc so nlargest's stable decoration breaks full
        #    ties by pattern_id ascending — the tertiary key, carried by the
        #    input order exactly as before. The key is (direct-vote tier, then
        #    the pre-fan-out direct-vote COUNT within the seed tier, else the
        #    accumulated vote score): a directly-matched seed (tier True)
        #    outranks every propagated-only neighbour (tier False) regardless
        #    of score, so no zero-direct-vote hub can evict a gold seed under
        #    the k cap. Seeds rank by direct-vote count, not accumulated score,
        #    so fan-out cannot re-order the seed tier and evict a gold seed a
        #    neighbour was lifted past. The tier is the auditable ``seed``
        #    boolean (>=1 direct vote), never a tuned score.
        ordered = sorted(scores.items())
        top = heapq.nlargest(
            k,
            ordered,
            key=lambda kv: (
                kv[0] in direct_votes,
                direct_votes[kv[0]] if kv[0] in direct_votes else kv[1],
            ),
        )

        # 6. Hydrate the winners into the envelope; never emit a husk. Each pattern
        #    is deep-frozen at this boundary: a shallow ``{**pat}`` would alias the
        #    singleton corpus's nested lists, so a caller mutating a returned
        #    pattern would corrupt the shared corpus. deep_freeze severs every
        #    reference and seals the copy, JSON-serialisable throughout.
        patterns: list[dict] = []
        votes: dict[str, int] = {}
        for pid, score in top:
            pat = self._lookup_pattern(pid)
            if pat is None:
                dangling.add(pid)
                continue
            direct = direct_votes.get(pid, 0)
            patterns.append(deep_freeze({
                **pat,
                "retrieval": {
                    "score": score,
                    "direct_votes": direct,
                    "propagated_votes": score - direct,
                    "seed": pid in direct_votes,
                },
            }))
            votes[pid] = score

        # 7. Resolve the envelope state (fail closed).
        if not patterns:
            return RetrievalResult(
                state=DANGLING,
                dangling=sorted(dangling),
                unmatched_signals=sorted(set(unmatched)),
                reason="hydrated pattern ids did not resolve to corpus patterns",
            )
        top_score = patterns[0]["retrieval"]["score"]
        if top_score >= _CONFIDENCE_FLOOR:
            state, reason = HIT, ""
        else:
            state = LOW_CONFIDENCE
            reason = f"best score {top_score} below confidence floor {_CONFIDENCE_FLOOR}"
        return RetrievalResult(
            state=state,
            patterns=patterns,
            votes=votes,
            dangling=sorted(dangling),
            unmatched_signals=sorted(set(unmatched)),
            reason=reason,
        )

    # ------------------------------------------------------------------
    # Compact index (for council awareness)
    # ------------------------------------------------------------------

    def get_compact_index(self) -> dict:
        """Return a lightweight summary of all knowledge for agent awareness.

        Includes category counts and IDs only, not full data.
        """
        # Architecture pattern categories
        arch_categories: dict[str, list[str]] = {}
        for p in self._architecture_patterns:
            cat = p.get("category", "uncategorised")
            arch_categories.setdefault(cat, []).append(p["id"])

        # Scalability pattern categories
        scale_categories: dict[str, list[str]] = {}
        for p in self._scalability_patterns:
            cat = p.get("category", "uncategorised")
            scale_categories.setdefault(cat, []).append(p["id"])

        # API/data pattern categories
        api_categories: dict[str, list[str]] = {}
        for p in self._api_data_patterns:
            cat = p.get("category", "uncategorised")
            api_categories.setdefault(cat, []).append(p["id"])

        # Decision rules by category
        rule_categories: dict[str, list[str]] = {}
        for r in self._decision_rules:
            cat = r.get("category", "uncategorised")
            rule_categories.setdefault(cat, []).append(r["id"])

        return {
            "architecture_patterns": {
                "total": len(self._architecture_patterns),
                "categories": {k: len(v) for k, v in arch_categories.items()},
                "ids": [p["id"] for p in self._architecture_patterns],
            },
            "scalability_patterns": {
                "total": len(self._scalability_patterns),
                "categories": {k: len(v) for k, v in scale_categories.items()},
                "ids": [p["id"] for p in self._scalability_patterns],
            },
            "api_data_patterns": {
                "total": len(self._api_data_patterns),
                "categories": {k: len(v) for k, v in api_categories.items()},
                "ids": [p["id"] for p in self._api_data_patterns],
            },
            "decision_rules": {
                "total": len(self._decision_rules),
                "categories": {k: len(v) for k, v in rule_categories.items()},
                "ids": [r["id"] for r in self._decision_rules],
            },
        }
