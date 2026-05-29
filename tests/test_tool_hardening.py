# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""Hardening tests for Coeus's persist-safe coercion.

``log_decision`` persists ``alternatives_considered``; a non-empty wrong-type
value must fail loud (coerce_or_raise) rather than be silently swallowed into
an empty list and stored.
"""

from __future__ import annotations

import pytest

from coeus.tools._shared import coerce_or_raise
from coeus.tools.log_decision import log_decision


@pytest.fixture()
def tmp_data_dir(monkeypatch, tmp_path):
    """Redirect COEUS_DATA_DIR so log_decision writes to a throwaway dir."""
    d = tmp_path / "coeus_data"
    d.mkdir()
    monkeypatch.setenv("COEUS_DATA_DIR", str(d))
    return d


class TestCoerceOrRaise:

    def test_none_returns_empty_default(self):
        assert coerce_or_raise(None, list, []) == []

    def test_native_list_passthrough(self):
        assert coerce_or_raise(["a", "b"], list, []) == ["a", "b"]

    def test_json_array_string(self):
        assert coerce_or_raise('["a", "b"]', list, []) == ["a", "b"]

    def test_nonempty_wrong_type_raises(self):
        with pytest.raises(TypeError):
            coerce_or_raise({"a": 1}, list, [])

    def test_bare_nonjson_string_raises(self):
        with pytest.raises(TypeError):
            coerce_or_raise("solo", list, [])


class TestLogDecisionPersistedField:

    def test_none_alternatives_ok(self, tmp_data_dir):
        result = log_decision(
            decision_type="architecture",
            context="ctx",
            choice_made="A",
            alternatives_considered=None,
        )
        assert result["recorded"] is True

    def test_list_alternatives_ok(self, tmp_data_dir):
        result = log_decision(
            decision_type="architecture",
            context="ctx",
            choice_made="A",
            alternatives_considered=["B", "C"],
        )
        assert result["recorded"] is True

    def test_json_string_alternatives_ok(self, tmp_data_dir):
        result = log_decision(
            decision_type="architecture",
            context="ctx",
            choice_made="A",
            alternatives_considered='["B", "C"]',
        )
        assert result["recorded"] is True

    def test_nonempty_wrong_type_alternatives_raises(self, tmp_data_dir):
        with pytest.raises(TypeError):
            log_decision(
                decision_type="architecture",
                context="ctx",
                choice_made="A",
                alternatives_considered={"not": "a list"},
            )
