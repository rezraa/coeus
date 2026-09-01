# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""S4.3 + S4.4 — Tool function tests and security checks.

38+ tests covering all five tools plus security invariants.
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from coeus.tools.analyze_architecture import analyze_architecture
from coeus.tools.evaluate_scalability import evaluate_scalability
from coeus.tools.recommend_pattern import recommend_pattern
from coeus.tools.design_api import design_api
from coeus.tools.assess_resilience import assess_resilience
from coeus.knowledge.loader import KnowledgeLoader


# ===================================================================
# S4.3-1  analyze_architecture — see tests/test_analyze_architecture.py
# ===================================================================
# The prose-signal TestAnalyzeArchitecture suite retired when the tool was wired
# onto the Shape C engine (story-917b281e): its input is now matched_signal_ids, it
# reasons issues from each retrieved pattern's OWN avoid_when (the _ANTI_PATTERNS
# island is deleted), inverts the gate to CONFIRMED, and drops matched_rules +
# scalability_flags + fabricated severity. The five superseded tests are killed
# strictly-stronger (Directive 10) — test_anti_pattern_detection,
# test_anti_pattern_severity, test_signal_matching_returns_matched_rules,
# test_constraint_filtering, test_result_keys_present — and every proof for the
# rebuilt tool (anchor RED-first, contract, envelope, BAR-1/2, determinism,
# Hyperion ceilings, deletions) lives in the dedicated
# tests/test_analyze_architecture.py, one source of truth for the rebuilt tool.


# ===================================================================
# S4.3-2  evaluate_scalability — see tests/test_evaluate_scalability.py
# ===================================================================
# The prose-signal TestEvaluateScalability suite retired when the tool was wired
# onto the Shape C engine (story-558f4a76): its input is now matched_signal_ids, it
# retrieves through the four-state hydrate envelope, and it drops the retrieval-BLIND
# hardcoded _SCALE_TIERS (the identical 10x/100x/1000x threshold tiers + fixed
# bottleneck/pattern lists it returned for every system). It PARTITIONS each
# retrieved pattern into horizon current-vs-growth by the deterministic gate instead.
# The seven superseded tests are killed strictly-stronger (Directive 10) —
# test_tiered_results_returned, test_each_tier_has_bottlenecks,
# test_each_tier_has_recommendations, test_each_tier_has_patterns,
# test_current_assessment_present, test_empty_description,
# test_growth_projections_influence_recommendations — and every proof for the
# rebuilt tool (anchor RED-first, contract, envelope, BAR-1/2, determinism,
# Hyperion ceilings, deletions, DRY) lives in the dedicated
# tests/test_evaluate_scalability.py, one source of truth for the rebuilt tool.


# ===================================================================
# S4.3-3  recommend_pattern — see tests/test_recommend_pattern.py
# ===================================================================
# The prose-signal TestRecommendPattern suite retired when the tool was wired onto
# the Shape C engine (story-22072cab): its input is now matched_signal_ids, its
# output drops the float fit_score for an integer retrieval vote + a deterministic
# gate. Every one of those tests — the anchor rewritten RED-first, the three
# artifact tests killed-with-reason (Directive 10) — lives in the dedicated
# tests/test_recommend_pattern.py, one source of truth for the rebuilt tool.


# ===================================================================
# S4.3-4  TestDesignApi — 6 tests
# ===================================================================

class TestDesignApi:
    """Test the design_api tool."""

    def test_returns_valid_blueprint(self) -> None:
        """Result contains all expected blueprint keys."""
        result = design_api(
            domain_model="Users have Orders, Orders contain Items",
        )
        assert "recommended_style" in result
        assert "rationale" in result
        assert "contract_structure" in result
        assert "versioning_strategy" in result
        assert "error_handling" in result
        assert "authentication_approach" in result

    def test_rest_style_detected(self) -> None:
        """REST style is detected for CRUD resource-oriented domains."""
        result = design_api(
            domain_model="CRUD resource API for users, public API with OpenAPI swagger",
        )
        assert result["recommended_style"] == "rest"

    def test_graphql_style_detected(self) -> None:
        """GraphQL style is detected when flexible queries are needed."""
        result = design_api(
            domain_model="Flexible queries, nested data, frontend-driven schema-first",
        )
        assert result["recommended_style"] == "graphql"

    def test_explicit_style_preference(self) -> None:
        """Explicit style_preference overrides auto-detection."""
        result = design_api(
            domain_model="Simple CRUD app",
            style_preference="grpc",
        )
        assert result["recommended_style"] == "grpc"

    def test_versioning_strategy_present(self) -> None:
        """Versioning strategy includes approach and best_for fields."""
        result = design_api(domain_model="Users and Orders REST API")
        vs = result["versioning_strategy"]
        assert "approach" in vs
        assert "best_for" in vs

    def test_error_handling_present(self) -> None:
        """Error handling section includes structure and principles."""
        result = design_api(domain_model="Any domain model")
        eh = result["error_handling"]
        assert "structure" in eh
        assert "principles" in eh
        assert len(eh["principles"]) > 0


# ===================================================================
# TestAssessResilience (legacy, 6 tests) RETIRED — story-bc2dece3
# ===================================================================
# The prose-signal SPOF/missing/blast/score tool is gone; assess_resilience is
# now on the Shape C engine. Its proofs (incl. the 6 legacy tests killed-with-
# reason) live in tests/test_assess_resilience.py — strengthened, not dropped.


# ===================================================================
# S4.4  TestSecurityChecks — 5 tests
# ===================================================================

class TestSecurityChecks:
    """Security invariant tests for all tools."""

    def test_input_sanitization_no_code_injection(self) -> None:
        """Malicious descriptions with code injection do not execute."""
        malicious_inputs = [
            "__import__('os').system('rm -rf /')",
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "${7*7}",
            "{{config.items()}}",
        ]
        for payload in malicious_inputs:
            # Should not raise or execute — just treat as text (a payload as a
            # signal id is unrecognised, so it abstains; the point is no execution)
            result = analyze_architecture(
                description=payload,
                matched_signal_ids=[payload],
            )
            assert isinstance(result, dict)
            # Description should appear as-is, not interpreted
            result2 = assess_resilience(
                system_description=payload,
                matched_signal_ids=[payload],
            )
            assert isinstance(result2, dict)

    def test_vendor_neutrality(self) -> None:
        """Default recommendations do not exclusively favor one cloud vendor."""
        kb = KnowledgeLoader()
        sigs = [e["signal_id"] for e in kb.get_signal_index()
                if "monolith" in e["pattern_ids"]][:2]
        result = recommend_pattern(
            matched_signal_ids=sigs,
            constraints={"team_size": "1-3", "scale": "startup_mvp"},
        )
        # Recommendations should be about patterns, not vendor-specific services
        for rec in result["recommendations"]:
            pattern_id = rec["pattern_id"].lower()
            # Should not be a cloud-vendor-specific recommendation
            assert pattern_id not in ("aws_lambda", "azure_functions", "gcp_cloud_run")

    def test_all_tools_return_json_serializable(self) -> None:
        """All tool outputs can be serialized to JSON without errors."""
        _sigs = [e["signal_id"] for e in KnowledgeLoader().get_signal_index()[:3]]
        results = [
            analyze_architecture(
                description="Test",
                matched_signal_ids=_sigs,
            ),
            evaluate_scalability(description="Test", matched_signal_ids=_sigs),
            recommend_pattern(
                matched_signal_ids=_sigs,
                constraints={"team_size": "3"},
            ),
            design_api(domain_model="Users and Orders"),
            assess_resilience(
                system_description="Test",
                matched_signal_ids=_sigs,
            ),
        ]
        for result in results:
            # Must not raise
            serialized = json.dumps(result)
            assert isinstance(serialized, str)
            # Round-trip must preserve structure
            deserialized = json.loads(serialized)
            assert isinstance(deserialized, dict)

    def test_knowledge_file_integrity(self) -> None:
        """KnowledgeLoader loads without error and all indices are populated."""
        kb = KnowledgeLoader()
        assert len(kb._architecture_index) == len(kb._architecture_patterns)
        assert len(kb._scalability_index) == len(kb._scalability_patterns)
        assert len(kb._api_data_index) == len(kb._api_data_patterns)
        assert len(kb._rule_index) == len(kb._decision_rules)

    def test_no_sensitive_data_in_results(self) -> None:
        """Tool results do not contain file paths, env vars, or credentials."""
        _sigs = [e["signal_id"] for e in KnowledgeLoader().get_signal_index()[:3]]
        result = analyze_architecture(
            description="Test system with password=secret123 and API_KEY=abc",
            matched_signal_ids=_sigs,
        )
        result_str = json.dumps(result)
        # Should not leak environment variable names or internal paths
        assert "COEUS_DATA_DIR" not in result_str
        assert "/Users/" not in result_str
        assert "secret123" not in result_str


# ===========================================================================
# E2/S6 hardening — failure shapes from the S5 post-mortem matrix.
# ===========================================================================

from coeus.tools._shared import coerce
from coeus.tools.log_decision import log_decision


class TestCoerce:

    def test_str_to_dict_mismatch_returns_default(self):
        assert coerce("production", dict, default={}) == {}

    def test_list_where_dict_expected_returns_default(self):
        assert coerce(["a"], dict, default={}) == {}

    def test_json_string_to_list(self):
        assert coerce("[1,2]", list, default=[]) == [1, 2]

    def test_native_dict_passthrough(self):
        assert coerce({"k": 1}, dict) == {"k": 1}

    def test_none_returns_default(self):
        assert coerce(None, dict, default={}) == {}

    def test_two_arg_call_still_works(self):
        assert coerce("[1]", list) == [1]


class TestLogDecisionHardening:

    def test_choice_alias(self, tmp_path):
        import os
        os.environ["COEUS_DATA_DIR"] = str(tmp_path)
        try:
            result = log_decision(
                decision_type="architecture",
                context="picking a store",
                choice="kuzu",  # alias of choice_made
            )
            assert result["recorded"] is True
        finally:
            os.environ.pop("COEUS_DATA_DIR", None)

    def test_decision_and_alternatives_aliases(self, tmp_path):
        import os
        os.environ["COEUS_DATA_DIR"] = str(tmp_path)
        try:
            result = log_decision(
                decision_type="pattern",
                context="evaluating queues",
                decision="kafka",  # alias of choice_made
                alternatives=["rabbitmq"],  # alias of alternatives_considered
            )
            assert result["recorded"] is True
        finally:
            os.environ.pop("COEUS_DATA_DIR", None)

    def test_choice_made_and_choice_collision_raises(self, tmp_path):
        import os
        os.environ["COEUS_DATA_DIR"] = str(tmp_path)
        try:
            with pytest.raises(TypeError):
                log_decision(
                    decision_type="architecture",
                    context="x",
                    choice_made="canonical",
                    choice="alias",
                )
        finally:
            os.environ.pop("COEUS_DATA_DIR", None)

    def test_choice_and_decision_both_aliases_collide(self, tmp_path):
        import os
        os.environ["COEUS_DATA_DIR"] = str(tmp_path)
        try:
            # Two synonyms of the same canonical -> ambiguous -> raise.
            with pytest.raises(TypeError):
                log_decision(
                    decision_type="architecture",
                    context="x",
                    choice="a",
                    decision="b",
                )
        finally:
            os.environ.pop("COEUS_DATA_DIR", None)


class TestAssessResilienceHardening:

    def test_system_alias(self):
        _sigs = [e["signal_id"] for e in KnowledgeLoader().get_signal_index()[:3]]
        result = assess_resilience(
            system="A single-database monolith",  # alias of system_description
            matched_signal_ids=_sigs,
        )
        assert isinstance(result, dict)


class TestAnalyzeArchitectureHardening:

    def test_system_alias(self):
        _sigs = [e["signal_id"] for e in KnowledgeLoader().get_signal_index()[:3]]
        result = analyze_architecture(
            system="A shared-database microservice mesh",  # alias of description
            matched_signal_ids=_sigs,
        )
        assert isinstance(result, dict)

    def test_truthy_wrong_type_constraints_does_not_crash(self):
        _sigs = [e["signal_id"] for e in KnowledgeLoader().get_signal_index()[:3]]
        result = analyze_architecture(
            description="x",
            matched_signal_ids=_sigs,
            constraints=["wrong", "shape"],
        )
        assert isinstance(result, dict)
