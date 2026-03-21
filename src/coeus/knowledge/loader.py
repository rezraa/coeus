# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""KnowledgeLoader for Coeus architecture knowledge base.

Loads architecture_patterns.json, scalability_patterns.json, api_and_data.json,
and decision_rules.json. Provides retrieval, structural signal matching
(exact substring against decision_rules), and constraint filtering.
"""

from __future__ import annotations

import json
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).parent

_PRIORITY_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


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

        # Build rule signal index: normalised structural_signal -> rule
        # Each rule has a list of structural_signals; index each one.
        self._rule_signal_pairs: list[tuple[str, dict]] = []
        for rule in self._decision_rules:
            for signal in rule.get("structural_signals", []):
                normalised = signal.lower().strip()
                if normalised:
                    self._rule_signal_pairs.append((normalised, rule))

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
    # Structural matching — exact against decision_rules.json
    # ------------------------------------------------------------------

    def _resolve_pattern(self, pattern_id: str) -> dict:
        """Look up a pattern ID across all three pattern files."""
        pat = self._architecture_index.get(pattern_id)
        if pat:
            return pat
        pat = self._scalability_index.get(pattern_id)
        if pat:
            return pat
        pat = self._api_data_index.get(pattern_id)
        if pat:
            return pat
        return {"id": pattern_id, "name": pattern_id}

    def match_structural_signals(self, signals: list[str]) -> list[dict]:
        """Given structural signals identified by the agent, find matching
        decision rules.

        Matching is exact substring on the ``structural_signals`` field of
        each rule -- NOT fuzzy keyword overlap.  For each input signal, checks
        if any of the rule's structural_signals contain it as a substring, or
        vice versa (case-insensitive).

        Returns matching rules augmented with resolved pattern details,
        sorted by priority (high > medium > low)::

            [{"rule": {...}, "signal": "...",
              "recommended_patterns": [...],
              "alternatives": [...]}]
        """
        if not signals:
            return []

        results: list[dict] = []
        seen_rule_ids: set[str] = set()

        for signal in signals:
            signal_lower = signal.lower().strip()
            if not signal_lower:
                continue

            for rule_signal, rule in self._rule_signal_pairs:
                if rule["id"] in seen_rule_ids:
                    continue

                # Exact substring match: the agent's signal appears in the
                # rule's structural_signal, or vice versa.
                if signal_lower in rule_signal or rule_signal in signal_lower:
                    seen_rule_ids.add(rule["id"])

                    # Resolve recommended patterns across all three files
                    rec_pattern_ids = rule.get("recommended_patterns", [])
                    rec_patterns = [self._resolve_pattern(pid) for pid in rec_pattern_ids]

                    # Resolve alternatives across all three files
                    alt_ids = rule.get("alternatives", [])
                    alternatives = [self._resolve_pattern(alt_id) for alt_id in alt_ids]

                    results.append({
                        "rule": rule,
                        "signal": signal,
                        "recommended_patterns": rec_patterns,
                        "alternatives": alternatives,
                    })

        # Sort by priority: high=0, medium=1, low=2
        results.sort(
            key=lambda r: _PRIORITY_RANK.get(
                r["rule"].get("priority", "low"), 2
            )
        )

        return results

    # ------------------------------------------------------------------
    # Constraint filtering
    # ------------------------------------------------------------------

    def filter_by_constraints(
        self,
        rules: list[dict],
        constraints: dict,
    ) -> list[dict]:
        """Filter rules by constraints.

        Removes rules whose ``constraints.avoid_when`` conditions match the
        provided constraints.  Each key in *constraints* is checked against
        the rule's ``avoid_when`` text (case-insensitive substring match).

        Args:
            rules: List of rule dicts (each must have ``constraints``
                with an ``avoid_when`` key).
            constraints: Dict of constraint signals.  Values that are
                truthy strings are checked against each rule's avoid_when.

        Returns:
            List of rules that survived filtering (avoid_when did not match).
        """
        if not constraints:
            return list(rules)

        # Gather constraint values as lowercase strings for matching.
        constraint_signals: list[str] = []
        for value in constraints.values():
            if isinstance(value, str) and value.strip():
                constraint_signals.append(value.lower().strip())
            elif isinstance(value, bool) and value:
                pass  # boolean flags don't have text to match

        if not constraint_signals:
            return list(rules)

        surviving: list[dict] = []

        for rule in rules:
            avoid_when = rule.get("constraints", {}).get("avoid_when", {})
            if not avoid_when:
                surviving.append(rule)
                continue

            # avoid_when can be a dict (key->value) or a string
            if isinstance(avoid_when, dict):
                avoid_values = [str(v).lower() for v in avoid_when.values()]
            else:
                avoid_values = [str(avoid_when).lower()]

            excluded = False
            for cs in constraint_signals:
                for av in avoid_values:
                    if cs in av or av in cs:
                        excluded = True
                        break
                if excluded:
                    break

            if not excluded:
                surviving.append(rule)

        return surviving

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
