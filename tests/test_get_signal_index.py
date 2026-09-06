# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""get_signal_index — reachability-by-construction + the uniform nested container.

story-71e4ff45 (council ae492280 / m-5a5837da; root cause m-698d738c). get_signal_index
was declared INLINE in server.py with NO ``coeus/tools/get_signal_index.py``, so Othrys'
filename-keyed seed (one graph tool per file stem) never minted it — every live
``summon('coeus','get_signal_index')`` raised LookupError and ``get_titan_tools('coeus')``
omitted it, while the benchmarks stayed green because they drive the LOADER method
directly. These tests fail-closed on that class of drop by construction:

* the tool file exists and has EXACTLY ONE public top-level function (two would collapse
  to one seed tool identity and silently drop the second);
* server.py wires EXACTLY ONE signal-index ``@mcp.tool`` (no surviving duplicate);
* the tool returns the uniform nested container ``{pattern_signals: [...]}`` (Theia's
  ``{component_signals, system_signals}`` shape, one group for Coeus's single corpus),
  delegating BYTE-IDENTICALLY to the one loader method (DRY, one source of truth);
* the firewall holds (no cross-titan / othrys import in the tool file).
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import coeus
import coeus.tools.get_signal_index as tool_mod
from coeus.knowledge.loader import KnowledgeLoader
from coeus.tools.get_signal_index import get_signal_index

_TOOL_PATH = Path(tool_mod.__file__)
_SERVER_PATH = Path(coeus.__file__).parent / "server.py"


def _public_top_level_funcs(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        n.name
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not n.name.startswith("_")
    ]


def _mcp_tool_defs_named(path: Path, name: str) -> list[str]:
    """Top-level defs named *name* carrying an ``@mcp.tool`` decorator."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for n in tree.body:
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) or n.name != name:
            continue
        for dec in n.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "tool":
                hits.append(n.name)
                break
    return hits


# ---------------------------------------------------------------------------
# Reachability-by-construction — the seed cannot drop this tool
# ---------------------------------------------------------------------------

class TestReachability:
    def test_tool_file_has_exactly_one_public_function(self) -> None:
        assert _public_top_level_funcs(_TOOL_PATH) == ["get_signal_index"]

    def test_server_wires_exactly_one_signal_index_tool(self) -> None:
        assert _mcp_tool_defs_named(_SERVER_PATH, "get_signal_index") == ["get_signal_index"]

    def test_no_duplicate_signal_index_definition(self) -> None:
        """The inline body is gone — server.py defines get_signal_index once, and it
        delegates to the tool module (parity with analyze_architecture et al.)."""
        tree = ast.parse(_SERVER_PATH.read_text(encoding="utf-8"))
        defs = [n for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == "get_signal_index"]
        assert len(defs) == 1


# ---------------------------------------------------------------------------
# The uniform nested container — shape, delegation, determinism
# ---------------------------------------------------------------------------

class TestNestedContainer:
    def test_single_named_group_for_the_one_corpus(self) -> None:
        out = get_signal_index()
        assert isinstance(out, dict)
        assert set(out) == {"pattern_signals"}

    def test_delegates_byte_identically_to_loader(self, kb: KnowledgeLoader) -> None:
        """One source of truth: the group IS the loader method's output, unwrapped."""
        assert get_signal_index()["pattern_signals"] == kb.get_signal_index()

    def test_entry_shape_unchanged(self) -> None:
        for e in get_signal_index()["pattern_signals"]:
            assert set(e) == {"signal_id", "signal_text", "pattern_ids"}

    def test_deterministic_byte_reproducible(self) -> None:
        a = json.dumps(get_signal_index(), sort_keys=True)
        b = json.dumps(get_signal_index(), sort_keys=True)
        assert a == b

    def test_group_sorted_with_sorted_id_lists(self) -> None:
        grp = get_signal_index()["pattern_signals"]
        assert grp == sorted(grp, key=lambda e: e["signal_id"])
        for e in grp:
            assert e["pattern_ids"] == sorted(e["pattern_ids"])


# ---------------------------------------------------------------------------
# Firewall — the tool must not import othrys.* or any other titan package
# ---------------------------------------------------------------------------

class TestFirewall:
    def test_no_cross_titan_or_othrys_import(self) -> None:
        tree = ast.parse(_TOOL_PATH.read_text(encoding="utf-8"), filename=str(_TOOL_PATH))
        mods: list[str] = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods += [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods.append(n.module)
        forbidden_roots = {"othrys", "theia", "mnemos", "hyperion", "phoebe", "themis"}
        offenders = [m for m in mods if m.split(".")[0] in forbidden_roots]
        assert not offenders, f"firewall breach: {offenders}"
