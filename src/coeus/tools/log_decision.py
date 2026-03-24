# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: log_decision

Record an architecture decision with rationale and alternatives considered.

Supports dual-mode storage: writes to the Kuzu graph when a connection
is available, or to a local JSONL file in standalone mode.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import logging

from coeus.tools._shared import append_decision, coerce, emit_event, get_knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid decision types — for categorisation and filtering
# ---------------------------------------------------------------------------

_DECISION_TYPES: set[str] = {
    "architecture",
    "pattern",
    "scalability",
    "api_design",
    "data_model",
    "infrastructure",
    "integration",
    "migration",
    "performance",
    "resilience",
    "security",
    "technology",
    "tradeoff",
    "other",
}


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def log_decision(
    decision_type: str,
    context: str,
    choice_made: str,
    alternatives_considered: list[str] | None = None,
    rationale: str = "",
    conn: object = None,
) -> dict:
    """Record an architecture decision with rationale and alternatives.

    Args:
        decision_type: Category of the decision, e.g. "architecture",
            "pattern", "scalability", "api_design", "tradeoff".
        context: Description of the situation or problem that prompted
            the decision.
        choice_made: The option that was selected.
        alternatives_considered: Other options that were evaluated
            but not chosen.
        rationale: Reasoning behind the choice.
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: decision_id, decision_type, recorded, timestamp.
    """
    alternatives_considered = coerce(alternatives_considered, list) or []

    # Normalise decision type — warn on unknown but preserve original
    dt_lower = decision_type.lower().strip()
    if dt_lower not in _DECISION_TYPES:
        logger.warning(
            "Unknown decision_type '%s', accepting anyway (valid: %s)",
            decision_type, _DECISION_TYPES,
        )

    ts = datetime.now(timezone.utc).isoformat()

    record: dict[str, Any] = {
        "decision_type": dt_lower,
        "context": context,
        "choice_made": choice_made,
        "alternatives_considered": alternatives_considered,
        "rationale": rationale,
    }

    # Dual-mode storage
    if conn is not None:
        # Graph mode — write as memory node
        try:
            from coeus.knowledge.graph_loader import GraphKnowledgeLoader

            graph = GraphKnowledgeLoader(conn)
            decision_id = graph.write_memory(
                memory_type="architecture_decision",
                data=record,
            )
        except Exception:
            # Fall back to local storage if graph write fails
            decision_id = append_decision(record)
    else:
        # Standalone mode — local JSONL
        decision_id = append_decision(record)

    emit_event("decision_logged", {
        "decision_id": decision_id,
        "decision_type": dt_lower,
        "context": context[:200],
    })

    return {
        "decision_id": decision_id,
        "decision_type": dt_lower,
        "recorded": True,
        "timestamp": ts,
    }
