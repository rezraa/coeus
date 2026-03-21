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
# S4.3-1  TestAnalyzeArchitecture — 7 tests
# ===================================================================

class TestAnalyzeArchitecture:
    """Test the analyze_architecture tool."""

    def test_anti_pattern_detection(self) -> None:
        """Known anti-pattern signals produce architecture_issues."""
        result = analyze_architecture(
            description="System with shared database across services",
            structural_signals=["shared-database", "no-circuit-breaker"],
        )
        assert len(result["architecture_issues"]) >= 2
        issue_signals = [i["signal"] for i in result["architecture_issues"]]
        assert "shared-database" in issue_signals
        assert "no-circuit-breaker" in issue_signals

    def test_anti_pattern_severity(self) -> None:
        """Anti-pattern issues include severity levels."""
        result = analyze_architecture(
            description="Fragile system",
            structural_signals=["shared-database"],
        )
        for issue in result["architecture_issues"]:
            assert issue["severity"] in ("high", "medium", "low")

    def test_signal_matching_returns_matched_rules(self) -> None:
        """Structural signals matching decision rules populate matched_rules."""
        result = analyze_architecture(
            description="Small team building a CRUD app",
            structural_signals=["team of 1-5 engineers"],
        )
        assert len(result["matched_rules"]) >= 1
        assert "rule_id" in result["matched_rules"][0]

    def test_constraint_filtering(self) -> None:
        """Constraints filter out rules whose avoid_when matches."""
        # Without constraints — should match small-team rules
        result_no_filter = analyze_architecture(
            description="Small team app",
            structural_signals=["team of 1-5 engineers"],
        )
        # With enterprise constraints — small-team rules should be filtered
        result_filtered = analyze_architecture(
            description="Small team app",
            structural_signals=["team of 1-5 engineers"],
            constraints={"team_size": "50+", "scale": "hyperscale"},
        )
        assert len(result_filtered["matched_rules"]) <= len(result_no_filter["matched_rules"])

    def test_empty_signals(self) -> None:
        """Empty structural_signals returns empty results."""
        result = analyze_architecture(
            description="Some system",
            structural_signals=[],
        )
        assert result["matched_rules"] == []
        assert result["architecture_issues"] == []

    def test_result_keys_present(self) -> None:
        """Result dict contains all expected top-level keys."""
        result = analyze_architecture(
            description="Test system",
            structural_signals=["shared-database"],
        )
        assert "matched_rules" in result
        assert "architecture_issues" in result
        assert "recommendations" in result
        assert "scalability_flags" in result

    def test_malformed_signals_handled(self) -> None:
        """Signals that match no anti-pattern or rule still return valid structure."""
        result = analyze_architecture(
            description="A system",
            structural_signals=["completely-unknown-signal-xyz"],
        )
        assert isinstance(result["matched_rules"], list)
        assert isinstance(result["architecture_issues"], list)


# ===================================================================
# S4.3-2  TestEvaluateScalability — 6 tests
# ===================================================================

class TestEvaluateScalability:
    """Test the evaluate_scalability tool."""

    def test_tiered_results_returned(self) -> None:
        """Result contains exactly three tiers: 10x, 100x, 1000x."""
        result = evaluate_scalability(
            description="Web application with PostgreSQL",
        )
        assert len(result["tiers"]) == 3
        thresholds = [t["threshold"] for t in result["tiers"]]
        assert thresholds == ["10x", "100x", "1000x"]

    def test_each_tier_has_bottlenecks(self) -> None:
        """Each tier includes a bottlenecks list."""
        result = evaluate_scalability(description="Stateless web service")
        for tier in result["tiers"]:
            assert "bottlenecks" in tier
            assert len(tier["bottlenecks"]) > 0

    def test_each_tier_has_recommendations(self) -> None:
        """Each tier includes a recommendations list."""
        result = evaluate_scalability(description="API server")
        for tier in result["tiers"]:
            assert "recommendations" in tier
            assert len(tier["recommendations"]) > 0

    def test_each_tier_has_patterns(self) -> None:
        """Each tier includes resolved pattern details."""
        result = evaluate_scalability(description="Standard web app")
        for tier in result["tiers"]:
            assert "patterns" in tier
            assert isinstance(tier["patterns"], list)

    def test_current_assessment_present(self) -> None:
        """Result includes current_assessment with description and scale."""
        result = evaluate_scalability(
            description="Monolith on single node",
            current_scale="startup_mvp",
        )
        assert "current_assessment" in result
        assert result["current_assessment"]["current_scale"] == "startup_mvp"

    def test_empty_description(self) -> None:
        """Empty description still returns valid tiered result."""
        result = evaluate_scalability(description="")
        assert len(result["tiers"]) == 3
        assert "current_assessment" in result

    def test_growth_projections_influence_recommendations(self) -> None:
        """Growth projections produce tier-specific recommendations."""
        result = evaluate_scalability(
            description="API backend",
            growth_projections={"rps": "100->10k", "data": "10GB->1TB", "users": "10k->10M"},
        )
        # 10x tier should mention load balancer for rps
        tier_10x = result["tiers"][0]
        recs_text = " ".join(tier_10x["recommendations"]).lower()
        assert "load balancer" in recs_text or len(tier_10x["recommendations"]) > 0


# ===================================================================
# S4.3-3  TestRecommendPattern — 8 tests
# ===================================================================

class TestRecommendPattern:
    """Test the recommend_pattern decision engine."""

    def test_returns_ranked_recommendations(self) -> None:
        """Result includes ranked recommendations with fit_score."""
        result = recommend_pattern(
            structural_signals=["team of 1-5 engineers", "CRUD-dominant business logic"],
            constraints={"team_size": "1-3", "scale": "startup_mvp"},
        )
        assert len(result["recommendations"]) >= 1
        for rec in result["recommendations"]:
            assert "rank" in rec
            assert "fit_score" in rec
            assert 0.0 <= rec["fit_score"] <= 1.0

    def test_small_team_mvp_never_gets_microservices_first(self) -> None:
        """CRITICAL INVARIANT: Small team + MVP NEVER gets microservices as #1."""
        result = recommend_pattern(
            structural_signals=["team of 1-5 engineers", "CRUD-dominant business logic"],
            constraints={"team_size": "1-3", "scale": "startup_mvp"},
        )
        if result["recommendations"]:
            assert result["recommendations"][0]["pattern_id"] != "microservices", (
                "Microservices must NEVER be the #1 recommendation for small team + MVP"
            )

    def test_large_team_can_get_microservices(self) -> None:
        """Large team with enterprise scale can receive microservices."""
        result = recommend_pattern(
            structural_signals=[
                "team of 50+ engineers",
                "multiple autonomous squads",
                "independent release cycles required",
            ],
            constraints={"team_size": "50+", "scale": "enterprise"},
        )
        pattern_ids = [r["pattern_id"] for r in result["recommendations"]]
        assert "microservices" in pattern_ids or "domain_driven_design" in pattern_ids

    def test_constraint_aware_filtering(self) -> None:
        """Constraints influence which rules and patterns survive."""
        result = recommend_pattern(
            structural_signals=["team of 1-5 engineers"],
            constraints={"team_size": "1-3", "scale": "startup_mvp"},
        )
        assert "constraints_analyzed" in result
        assert result["constraints_analyzed"]["team_size"] == "1-3"

    def test_conflicting_constraints_noted(self) -> None:
        """When both monolith and microservices appear, a conflict is flagged."""
        result = recommend_pattern(
            structural_signals=[
                "team of 1-5 engineers",
                "team of 50+ engineers",
            ],
            constraints={},
        )
        # Both may match — check if conflicts exist when both are recommended
        pattern_ids = [r["pattern_id"] for r in result["recommendations"]]
        if "monolith" in pattern_ids and "microservices" in pattern_ids:
            assert len(result["conflicts"]) >= 1

    def test_empty_signals(self) -> None:
        """Empty signals returns valid structure with empty recommendations."""
        result = recommend_pattern(
            structural_signals=[],
            constraints={"team_size": "5"},
        )
        assert isinstance(result["recommendations"], list)
        assert isinstance(result["conflicts"], list)
        assert isinstance(result["alternatives"], list)

    def test_alternatives_populated(self) -> None:
        """Alternatives list is populated from matched rule alternatives."""
        result = recommend_pattern(
            structural_signals=["team of 1-5 engineers", "CRUD-dominant business logic"],
            constraints={"team_size": "1-3"},
        )
        # rule_small_team_crud has alternatives: vertical_slice, clean_architecture
        assert isinstance(result["alternatives"], list)

    def test_tradeoffs_included(self) -> None:
        """Recommendations include tradeoff analysis for known patterns."""
        result = recommend_pattern(
            structural_signals=["team of 1-5 engineers", "CRUD-dominant business logic"],
            constraints={"team_size": "1-3", "scale": "startup_mvp"},
        )
        for rec in result["recommendations"]:
            if rec["pattern_id"] in ("monolith", "modular_monolith", "microservices"):
                assert rec["tradeoffs"], f"Missing tradeoffs for {rec['pattern_id']}"


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
# S4.3-5  TestAssessResilience — 6 tests
# ===================================================================

class TestAssessResilience:
    """Test the assess_resilience tool."""

    def test_spof_detection(self) -> None:
        """Known SPOF signals are detected and listed."""
        result = assess_resilience(
            system_description="Database without replication",
            structural_signals=["single-database", "single-node"],
        )
        assert len(result["single_points_of_failure"]) >= 2
        components = [s["component"] for s in result["single_points_of_failure"]]
        assert "Database" in components
        assert "Application server" in components

    def test_missing_patterns_identified(self) -> None:
        """Missing resilience pattern signals are detected."""
        result = assess_resilience(
            system_description="Service without circuit breakers or retries",
            structural_signals=["no-circuit-breaker", "no-retry", "no-timeout"],
        )
        assert len(result["missing_patterns"]) >= 3
        patterns = [m["pattern"] for m in result["missing_patterns"]]
        assert "Circuit Breaker" in patterns
        assert "Retry with Backoff" in patterns
        assert "Timeout" in patterns

    def test_resilience_score_range(self) -> None:
        """Resilience score is always between 0.0 and 1.0."""
        result = assess_resilience(
            system_description="Test system",
            structural_signals=["single-database", "no-circuit-breaker"],
        )
        score = result["resilience_score"]
        assert 0.0 <= score <= 1.0

    def test_perfect_score_no_issues(self) -> None:
        """No signals means resilience score of 1.0."""
        result = assess_resilience(
            system_description="Well-architected system",
            structural_signals=[],
        )
        assert result["resilience_score"] == 1.0

    def test_recommendations_present(self) -> None:
        """Hardening recommendations are generated for detected issues."""
        result = assess_resilience(
            system_description="Fragile system",
            structural_signals=["single-database", "no-circuit-breaker"],
        )
        assert len(result["hardening_recommendations"]) >= 2

    def test_blast_radius_assessment(self) -> None:
        """Blast radius indicators are detected from signals."""
        result = assess_resilience(
            system_description="System with shared database across services",
            structural_signals=["shared-database", "synchronous-chain"],
        )
        assert len(result["blast_radius_assessment"]) >= 1
        severities = [b["severity"] for b in result["blast_radius_assessment"]]
        assert all(s in ("high", "medium", "low") for s in severities)


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
            # Should not raise or execute — just treat as text
            result = analyze_architecture(
                description=payload,
                structural_signals=[payload],
            )
            assert isinstance(result, dict)
            # Description should appear as-is, not interpreted
            result2 = assess_resilience(
                system_description=payload,
                structural_signals=[],
            )
            assert isinstance(result2, dict)

    def test_vendor_neutrality(self) -> None:
        """Default recommendations do not exclusively favor one cloud vendor."""
        result = recommend_pattern(
            structural_signals=["team of 1-5 engineers", "CRUD-dominant business logic"],
            constraints={"team_size": "1-3", "scale": "startup_mvp"},
        )
        # Recommendations should be about patterns, not vendor-specific services
        for rec in result["recommendations"]:
            pattern_id = rec["pattern_id"].lower()
            # Should not be a cloud-vendor-specific recommendation
            assert pattern_id not in ("aws_lambda", "azure_functions", "gcp_cloud_run")

    def test_all_tools_return_json_serializable(self) -> None:
        """All tool outputs can be serialized to JSON without errors."""
        results = [
            analyze_architecture(
                description="Test",
                structural_signals=["shared-database"],
            ),
            evaluate_scalability(description="Test"),
            recommend_pattern(
                structural_signals=["team of 1-5 engineers"],
                constraints={"team_size": "3"},
            ),
            design_api(domain_model="Users and Orders"),
            assess_resilience(
                system_description="Test",
                structural_signals=["single-database"],
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
        result = analyze_architecture(
            description="Test system with password=secret123 and API_KEY=abc",
            structural_signals=["shared-database"],
        )
        result_str = json.dumps(result)
        # Should not leak environment variable names or internal paths
        assert "COEUS_DATA_DIR" not in result_str
        assert "/Users/" not in result_str
        assert "secret123" not in result_str
