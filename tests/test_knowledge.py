# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""S4.2 — Knowledge base loading, retrieval, matching, and filtering tests.

28+ tests covering all KnowledgeLoader functionality.
"""
from __future__ import annotations

import pytest

from coeus.knowledge.loader import KnowledgeLoader


# ===================================================================
# S4.2-1  TestKnowledgeLoading — 6 tests
# ===================================================================

class TestKnowledgeLoading:
    """Verify all four JSON knowledge files load correctly."""

    def test_architecture_patterns_load(self, kb: KnowledgeLoader) -> None:
        """Architecture patterns JSON loads with non-empty list."""
        assert len(kb._architecture_patterns) > 0

    def test_scalability_patterns_load(self, kb: KnowledgeLoader) -> None:
        """Scalability patterns JSON loads with non-empty list."""
        assert len(kb._scalability_patterns) > 0

    def test_api_data_patterns_load(self, kb: KnowledgeLoader) -> None:
        """API and data patterns JSON loads with non-empty list."""
        assert len(kb._api_data_patterns) > 0

    def test_decision_rules_load(self, kb: KnowledgeLoader) -> None:
        """Decision rules JSON loads with non-empty list."""
        assert len(kb._decision_rules) > 0

    def test_architecture_pattern_has_required_fields(self, kb: KnowledgeLoader) -> None:
        """Each architecture pattern has id, name, category, description."""
        for p in kb._architecture_patterns:
            assert "id" in p, f"Pattern missing 'id': {p}"
            assert "name" in p, f"Pattern {p['id']} missing 'name'"
            assert "category" in p, f"Pattern {p['id']} missing 'category'"
            assert "description" in p, f"Pattern {p['id']} missing 'description'"

    def test_decision_rule_has_required_fields(self, kb: KnowledgeLoader) -> None:
        """Each decision rule has id, name, category, structural_signals, recommended_patterns."""
        for r in kb._decision_rules:
            assert "id" in r, f"Rule missing 'id': {r}"
            assert "name" in r, f"Rule {r['id']} missing 'name'"
            assert "category" in r, f"Rule {r['id']} missing 'category'"
            assert "structural_signals" in r, f"Rule {r['id']} missing 'structural_signals'"
            assert "recommended_patterns" in r, f"Rule {r['id']} missing 'recommended_patterns'"


# ===================================================================
# S4.2-2  TestArchitecturePatternRetrieval — 4 tests
# ===================================================================

class TestArchitecturePatternRetrieval:
    """Retrieve architecture patterns by ID and category."""

    def test_lookup_by_id(self, kb: KnowledgeLoader) -> None:
        """Known pattern ID returns the correct pattern dict."""
        pat = kb.get_pattern("monolith")
        assert pat is not None
        assert pat["name"] == "Monolith"

    def test_lookup_by_category(self, kb: KnowledgeLoader) -> None:
        """Getting patterns by category returns a non-empty list."""
        structural = kb.get_patterns_by_category("structural")
        assert len(structural) > 0
        assert all(p["category"] == "structural" for p in structural)

    def test_list_categories(self, kb: KnowledgeLoader) -> None:
        """list_pattern_categories returns sorted unique category names."""
        cats = kb.list_pattern_categories()
        assert len(cats) >= 3
        assert cats == sorted(cats)

    def test_unknown_id_returns_none(self, kb: KnowledgeLoader) -> None:
        """Unknown pattern ID returns None."""
        assert kb.get_pattern("nonexistent_pattern_xyz") is None


# ===================================================================
# S4.2-3  TestScalabilityPatternRetrieval — 4 tests
# ===================================================================

class TestScalabilityPatternRetrieval:
    """Retrieve scalability patterns by ID and category."""

    def test_lookup_by_id(self, kb: KnowledgeLoader) -> None:
        """Known scalability pattern ID returns the correct dict."""
        pat = kb.get_scalability_pattern("horizontal_scaling")
        assert pat is not None
        assert pat["name"] == "Horizontal Scaling"

    def test_lookup_by_category(self, kb: KnowledgeLoader) -> None:
        """Getting scalability patterns by category returns a non-empty list."""
        scaling = kb.get_scalability_by_category("scaling")
        assert len(scaling) > 0
        assert all(p["category"] == "scaling" for p in scaling)

    def test_list_categories(self, kb: KnowledgeLoader) -> None:
        """list_scalability_categories returns sorted unique category names."""
        cats = kb.list_scalability_categories()
        assert len(cats) >= 3
        assert cats == sorted(cats)

    def test_unknown_id_returns_none(self, kb: KnowledgeLoader) -> None:
        """Unknown scalability pattern ID returns None."""
        assert kb.get_scalability_pattern("nonexistent_scale_xyz") is None


# ===================================================================
# S4.2-4  TestApiDataRetrieval — 4 tests
# ===================================================================

class TestApiDataRetrieval:
    """Retrieve API/data patterns by ID and category."""

    def test_lookup_by_id(self, kb: KnowledgeLoader) -> None:
        """Known API/data pattern ID returns the correct dict."""
        pat = kb.get_api_data_pattern("rest_resource_oriented")
        assert pat is not None
        assert pat["name"] == "REST Resource-Oriented API"

    def test_lookup_by_category(self, kb: KnowledgeLoader) -> None:
        """Getting API/data patterns by category returns a non-empty list."""
        rest = kb.get_api_data_by_category("api-rest")
        assert len(rest) > 0
        assert all(p["category"] == "api-rest" for p in rest)

    def test_list_categories(self, kb: KnowledgeLoader) -> None:
        """list_api_data_categories returns sorted unique category names."""
        cats = kb.list_api_data_categories()
        assert len(cats) >= 3
        assert cats == sorted(cats)

    def test_unknown_id_returns_none(self, kb: KnowledgeLoader) -> None:
        """Unknown API/data pattern ID returns None."""
        assert kb.get_api_data_pattern("nonexistent_api_xyz") is None


# ===================================================================
# S4.2-5  TestDecisionRuleRetrieval — 3 tests
# ===================================================================

class TestDecisionRuleRetrieval:
    """Retrieve decision rules by ID and category."""

    def test_lookup_by_id(self, kb: KnowledgeLoader) -> None:
        """Known rule ID returns the correct rule dict."""
        rule = kb.get_rule("rule_small_team_crud")
        assert rule is not None
        assert rule["name"] == "Small Team CRUD Application"

    def test_lookup_by_category(self, kb: KnowledgeLoader) -> None:
        """Getting rules by category returns matching rules."""
        team_rules = kb.get_rules_by_category("team-scale")
        assert len(team_rules) > 0
        assert all(r["category"] == "team-scale" for r in team_rules)

    def test_unknown_id_returns_none(self, kb: KnowledgeLoader) -> None:
        """Unknown rule ID returns None."""
        assert kb.get_rule("nonexistent_rule_xyz") is None


# ===================================================================
# S4.2-6  TestStructuralSignalMatching — RETIRED with the legacy substring matcher
# ===================================================================
# The four tests here (test_matching_signals_returns_results,
# test_multiple_signals_match_multiple_rules, test_priority_sorting,
# test_empty_signals_returns_empty_list) were the loader-level binding of
# KnowledgeLoader.match_structural_signals — the exact-substring rule matcher named in
# plan-46de7c77's root-cause A/B. All four concern tools (recommend_pattern,
# analyze_architecture, evaluate_scalability, assess_resilience) migrated onto the
# Shape C hydrate() engine, dropping the matcher's tool-caller census to zero. S6
# (story-16223628, council 9ccb9550) then deletes match_structural_signals,
# _rule_signal_pairs, and the _resolve_pattern husk, so these four tests retire WITH
# the method they bound — named, not silently dropped (Directive 12).
# Coverage reconciliation: retrieval is now proven on the hydrate engine
# (tests/test_retrieval_envelope.py, tests/test_retrieval_ranking.py,
# tests/test_recommend_pattern.py, and each concern tool's own hydrate tests); the
# regression floor that the matcher gains no callers is guarded by
# tests/test_evaluate_scalability.py and tests/test_assess_resilience.py
# (test_tool_no_longer_calls_match_structural_signals + test_matcher_has_zero_tool_callers_now).


# ===================================================================
# S4.2-7  TestConstraintFiltering — RETIRED with loader.filter_by_constraints
# ===================================================================
# The three tests here (test_filter_removes_matching_avoid_when,
# test_empty_constraints_returns_all, test_non_matching_constraints_keeps_rules)
# were the ONLY callers of KnowledgeLoader.filter_by_constraints outside the tool
# that owned it. That loader method was the constraint leg of the legacy rule path
# in analyze_architecture (its sole src caller), which the A/B (council
# 3154bcba-decision-2) measured dead on real problem language. When
# analyze_architecture moved to the Shape C engine (story-917b281e) the method was
# deleted, and — per the pre-delete gate — these three tests retire WITH it, named.
# The deterministic gate they gestured at (avoid_when facets vs constraints) is now
# the engine's own, proven in tests/test_analyze_architecture.py (the confirm/gate
# tiering) and tests/test_recommend_pattern.py (the sink tiering).


# ===================================================================
# S4.2-8  TestCompactIndex — 1 test
# ===================================================================

class TestCompactIndex:
    """Verify compact index counts match actual data."""

    def test_compact_index_counts_match(self, kb: KnowledgeLoader) -> None:
        """Compact index totals match the actual pattern/rule list lengths."""
        idx = kb.get_compact_index()
        assert idx["architecture_patterns"]["total"] == len(kb._architecture_patterns)
        assert idx["scalability_patterns"]["total"] == len(kb._scalability_patterns)
        assert idx["api_data_patterns"]["total"] == len(kb._api_data_patterns)
        assert idx["decision_rules"]["total"] == len(kb._decision_rules)
        # IDs list length matches total
        assert len(idx["architecture_patterns"]["ids"]) == idx["architecture_patterns"]["total"]
        assert len(idx["scalability_patterns"]["ids"]) == idx["scalability_patterns"]["total"]
        assert len(idx["api_data_patterns"]["ids"]) == idx["api_data_patterns"]["total"]
        assert len(idx["decision_rules"]["ids"]) == idx["decision_rules"]["total"]
