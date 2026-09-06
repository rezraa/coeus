# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: get_signal_index

ONE read-only accessor over Coeus's Shape-C signal index, returning a NESTED typed
view — ``{pattern_signals: [{signal_id, signal_text, pattern_ids}]}`` — composed
from the single loader view (``kb.get_signal_index()`` over the merged pattern
corpus: architecture + scalability + api_and_data, 174 patterns / 1001 signals).

The agent (LLM) recognises a problem's structural signals against the labelled
``pattern_signals`` surface in working memory, then passes the matched ``signal_id``s
to any of the four concern tools (recommend_pattern / analyze_architecture /
evaluate_scalability / assess_resilience), each of which hydrates through the
retrieval engine. This tool only exposes the view; it performs no matching itself
(matching is the LLM's job / the frozen benchmark recognizer, never a fuzzy keyword
pass in shipping code). Zero-arg — it reaches no untrusted caller input, so the
caller-boundary ceilings (coeus.tools._shared) do not apply to it.

WHY exactly ONE public top-level function (the reachability fix, council ae492280 /
m-5a5837da; root cause m-698d738c): Othrys' filename-keyed seed mints one graph tool
per file keyed by the file stem, so a tool declared inline in server.py with no
co-located ``tools/<name>.py`` is never minted — get_signal_index had no graph
identity and every live summon raised LookupError. Giving it its own file with a
single public function mints it by construction (parity with analyze_architecture et
al.); a second public function here would collapse to one tool identity and silently
drop the other, so there is exactly one.

WHY nested (not a flat list, not a per-node type tag): the container is a dict of
NAMED signal-view groups, one group per corpus. Coeus has a single merged pattern
corpus today, so there is one populated group (``pattern_signals``); a future second
corpus is a NEW key behind this SAME tool (never a new file), the id column
(``pattern_ids``) already encodes each signal's corpus so no redundant per-entry tag
is needed, and the shape matches Theia's ``{component_signals, system_signals}`` so
Coeus's recognition vocabulary is uniform with the rest of the mountain.
"""

from __future__ import annotations

from coeus.tools._shared import get_knowledge


def get_signal_index(conn: object = None) -> dict:
    """Return the deterministic signal-index view in the uniform nested container.

    Args:
        conn: Optional Kuzu/LadybugDB connection. ``None`` -> JSON singleton
            loader; a connection -> the graph-backed loader (same engine, both
            modes).

    Returns:
        ``{"pattern_signals": [{signal_id, signal_text, pattern_ids}, ...]}`` — the
        one populated group, sorted by ``signal_id`` with sorted ``pattern_ids`` (the
        loader's guarantee), so the composite serialises identically on every call.
    """
    return {"pattern_signals": get_knowledge(conn).get_signal_index()}
