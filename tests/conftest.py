# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Shared test fixtures for Coeus — Architecture Titan test suite (S4.1)."""
from __future__ import annotations

import pytest

from coeus.knowledge.loader import KnowledgeLoader


# ---------------------------------------------------------------------------
# Knowledge base singleton
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def kb() -> KnowledgeLoader:
    """Loaded KnowledgeLoader singleton — shared across all tests."""
    return KnowledgeLoader()


# ---------------------------------------------------------------------------
# System description fixtures — architecture patterns
# ---------------------------------------------------------------------------

@pytest.fixture()
def startup_mvp() -> str:
    """Small team of 3, building a CRUD web app, PostgreSQL, single deployment."""
    return "Small team of 3, building a CRUD web app, PostgreSQL, single deployment"


@pytest.fixture()
def microservices_system() -> str:
    """50-person org, 12 services, Kubernetes, independent deployment cycles."""
    return "50-person org, 12 services, Kubernetes, independent deployment cycles"


@pytest.fixture()
def event_driven() -> str:
    """Real-time data pipeline, Kafka, multiple consumers, eventual consistency."""
    return "Real-time data pipeline, Kafka, multiple consumers, eventual consistency"


@pytest.fixture()
def api_gateway() -> str:
    """Public REST API, rate limiting, multiple backend services, OAuth2."""
    return "Public REST API, rate limiting, multiple backend services, OAuth2"


@pytest.fixture()
def legacy_monolith() -> str:
    """15-year-old monolith, 2M lines, single database, scheduled for modernization."""
    return "15-year-old monolith, 2M lines, single database, scheduled for modernization"


# ---------------------------------------------------------------------------
# Constraint profile fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def startup_constraints() -> dict:
    """Startup constraints — tiny team, MVP scale, minimal budget."""
    return {"team_size": "1-3", "scale": "startup_mvp", "budget": "minimal"}


@pytest.fixture()
def growth_constraints() -> dict:
    """Growth-phase constraints — medium team, moderate budget."""
    return {"team_size": "10-20", "scale": "growth", "budget": "moderate"}


@pytest.fixture()
def enterprise_constraints() -> dict:
    """Enterprise constraints — large team, SOC2 compliance."""
    return {
        "team_size": "50+",
        "scale": "enterprise",
        "budget": "large",
        "compliance": "SOC2",
    }


@pytest.fixture()
def regulated_constraints() -> dict:
    """Regulated industry constraints — HIPAA, low latency."""
    return {
        "team_size": "20-50",
        "scale": "enterprise",
        "compliance": "HIPAA",
        "latency": "low",
    }
