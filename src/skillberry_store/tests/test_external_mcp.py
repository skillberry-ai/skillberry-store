"""Unit tests for the External MCPs feature.

Covers:
  - normalize_mcp_input (5 wire shapes)
  - hash_tool_interface / compute_mcp_dependencies / compute_dependency_hashes
  - tool_health: find_dependents, list_broken_tools, check_all_tools_health
    (broken transitions across dep_missing, dep_schema_changed,
    dep_code_changed, dep_broken; unbreak lifecycle; transitive propagation;
    preservation of manager-owned server_unavailable state)
  - ExternalMCPManager.find_dependents excludes self-owned primitives
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from typing import Any, Dict

from skillberry_store.modules.external_mcp_manager import (
    ExternalMCPManager,
    _normalize_entry,
    build_primitive_manifest,
    normalize_mcp_input,
    params_from_input_schema,
    redact_entry,
)
from skillberry_store.modules.file_executor import (
    compute_dependency_hashes,
    compute_mcp_dependencies,
    hash_tool_interface,
)
from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.tool_health import (
    check_all_tools_health,
    find_dependents,
    list_broken_tools,
)


# ---------------------------------------------------------------------------
# normalize_mcp_input
# ---------------------------------------------------------------------------


class NormalizeMCPInputTests(unittest.TestCase):
    def test_shape1_mcp_servers_dict(self):
        r = normalize_mcp_input(
            {
                "mcpServers": {
                    "pw": {
                        "type": "stdio",
                        "command": "cmd",
                        "args": ["/c", "npx", "@playwright/mcp@latest"],
                    },
                    "st": {
                        "type": "http",
                        "url": "https://stitch.googleapis.com/mcp",
                        "headers": {"X-K": "secret"},
                    },
                    "sks": {"type": "sse", "url": "http://localhost:9999/sse"},
                }
            }
        )
        self.assertEqual(len(r), 3)
        by_name = {e["name"]: e for e in r}
        self.assertEqual(by_name["pw"]["transport"], "stdio")
        self.assertEqual(by_name["st"]["transport"], "http")
        self.assertEqual(by_name["st"]["headers"]["X-K"], "secret")
        self.assertEqual(by_name["sks"]["transport"], "sse")

    def test_shape2_bare_dict(self):
        r = normalize_mcp_input({"foo": {"command": "python", "args": ["-m", "x"]}})
        self.assertEqual(r[0]["name"], "foo")
        self.assertEqual(r[0]["transport"], "stdio")

    def test_shape3_list(self):
        r = normalize_mcp_input([{"name": "bar", "url": "http://x/sse"}])
        self.assertEqual(r[0]["name"], "bar")
        self.assertEqual(r[0]["transport"], "sse")

    def test_shape4_single_entry(self):
        r = normalize_mcp_input({"name": "solo", "type": "http", "url": "http://x/mcp"})
        self.assertEqual(r[0]["name"], "solo")
        self.assertEqual(r[0]["transport"], "http")

    def test_shape5_source_url_recurses(self):
        fetched = {"mcpServers": {"a": {"command": "echo"}}}
        r = normalize_mcp_input(
            {"source_url": "http://nowhere.example"}, fetch_url=lambda _u: fetched
        )
        self.assertEqual(r[0]["name"], "a")

    def test_stdio_without_command_rejects(self):
        with self.assertRaises(ValueError):
            normalize_mcp_input({"xx": {"transport": "stdio"}})

    def test_unknown_transport_rejects(self):
        with self.assertRaises(ValueError):
            _normalize_entry("x", {"transport": "weird", "url": "u"})


# ---------------------------------------------------------------------------
# Params conversion + manifest + redaction
# ---------------------------------------------------------------------------


class ParamsAndManifestTests(unittest.TestCase):
    def test_params_from_input_schema_fills_optional(self):
        p = params_from_input_schema(
            {
                "type": "object",
                "properties": {"a": {"type": "string"}, "b": {"type": "number"}},
                "required": ["a"],
            }
        )
        self.assertEqual(p["required"], ["a"])
        self.assertEqual(p["optional"], ["b"])

    def test_params_from_none_gives_empty_object(self):
        p = params_from_input_schema(None)
        self.assertEqual(
            p, {"type": "object", "properties": {}, "required": [], "optional": []}
        )

    def test_primitive_manifest_shape(self):
        m = build_primitive_manifest(
            "playwright__browser_click",
            "playwright",
            "Click a button",
            {"type": "object", "properties": {}, "required": [], "optional": []},
        )
        self.assertEqual(m["packaging_format"], "mcp")
        self.assertEqual(m["mcp_server"], "playwright")
        # Primitives carry mcp_server (source); mcp_dependencies is for composites.
        self.assertEqual(m["mcp_dependencies"], [])
        self.assertIn("mcp:playwright", m["tags"])
        self.assertIsNone(m["broken_reason"])

    def test_compute_mcp_dependencies_primitive_returns_own_server(self):
        """compute_mcp_dependencies must still surface a primitive's source MCP
        even though primitives now carry empty mcp_dependencies — the source
        comes from the `mcp_server` field."""
        from skillberry_store.modules.file_executor import compute_mcp_dependencies
        prim = build_primitive_manifest(
            "pw__click", "playwright", "", {"type": "object", "properties": {}}
        )
        self.assertEqual(compute_mcp_dependencies(prim, {"pw__click": prim}), ["playwright"])

    def test_redact_entry_masks_headers_and_env(self):
        red = redact_entry(
            {
                "name": "x",
                "headers": {"X-Api-Key": "verysecrettoken123"},
                "env": {"TOKEN": "abcdefgh"},
            }
        )
        self.assertNotIn("verysecrettoken123", red["headers"]["X-Api-Key"])
        self.assertIn("•", red["headers"]["X-Api-Key"])
        self.assertIn("•", red["env"]["TOKEN"])


# ---------------------------------------------------------------------------
# hash_tool_interface / compute_* helpers
# ---------------------------------------------------------------------------


class HashAndDepsTests(unittest.TestCase):
    def test_hash_stable_and_sensitive(self):
        d = {"params": {"type": "object", "properties": {"a": {"type": "str"}}}}
        p1, m1, c1 = hash_tool_interface(d, "def f(): pass")
        self.assertEqual(len(p1), 64)
        p2, _, _ = hash_tool_interface(
            {"params": {"type": "object", "properties": {"b": {"type": "int"}}}},
            "def f(): pass",
        )
        self.assertNotEqual(p1, p2)
        _, m2, _ = hash_tool_interface(d, "def f(): return 1")
        self.assertNotEqual(m1, m2)

    def test_compute_mcp_dependencies_recursive_and_cycle_safe(self):
        tools = {
            "A": {
                "name": "A",
                "mcp_server": "playwright",
                "mcp_dependencies": ["playwright"],
            },
            "B": {"name": "B", "dependencies": ["A"], "mcp_dependencies": []},
            "C": {"name": "C", "dependencies": ["B", "A"]},
        }
        self.assertEqual(compute_mcp_dependencies(tools["B"], tools), ["playwright"])
        self.assertEqual(compute_mcp_dependencies(tools["C"], tools), ["playwright"])
        # Cycle safety
        cyc = {
            "X": {"name": "X", "dependencies": ["Y"]},
            "Y": {"name": "Y", "dependencies": ["X"], "mcp_dependencies": ["foo"]},
        }
        self.assertEqual(compute_mcp_dependencies(cyc["X"], cyc), ["foo"])

    def test_compute_dependency_hashes_splits_components(self):
        tools = {
            "A": {
                "name": "A",
                "params": {"type": "object", "properties": {"x": {"type": "str"}}},
            }
        }
        out = compute_dependency_hashes(
            {"name": "B", "dependencies": ["A"]}, tools, {"A": "def A(x): return x"}
        )
        self.assertIn("A", out)
        entry = out["A"]
        self.assertIn("params", entry)
        self.assertIn("module", entry)
        self.assertIn("combined", entry)
        # Changing A's code changes module hash but not params hash
        out2 = compute_dependency_hashes(
            {"name": "B", "dependencies": ["A"]}, tools, {"A": "def A(x): return 42"}
        )
        self.assertEqual(out2["A"]["params"], entry["params"])
        self.assertNotEqual(out2["A"]["module"], entry["module"])


# ---------------------------------------------------------------------------
# tool_health
# ---------------------------------------------------------------------------


class ToolHealthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tools_dir = os.path.join(self.tmp, "tools")
        self.files_dir = os.path.join(self.tmp, "files")
        os.makedirs(self.tools_dir)
        os.makedirs(self.files_dir)
        self.th = FileHandler(self.tools_dir)
        self.fh = FileHandler(self.files_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_tool(self, d: Dict[str, Any]):
        self.th.write_file_content(f"{d['name']}.json", json.dumps(d))

    def _read_tool(self, name: str) -> Dict[str, Any]:
        return json.loads(self.th.read_file(f"{name}.json", raw_content=True))

    def _primitive(self, name: str, server: str = "s1") -> Dict[str, Any]:
        return {
            "name": name,
            "packaging_format": "mcp",
            "mcp_server": server,
            "mcp_dependencies": [server],
            "state": "approved",
            "params": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
                "optional": [],
            },
            "module_name": None,
            "dependencies": None,
            "dependency_hashes": {},
            "broken_reason": None,
        }

    def test_find_dependents_and_list_broken(self):
        A = self._primitive("A")
        B = {
            "name": "B",
            "packaging_format": "code",
            "dependencies": ["A"],
            "mcp_dependencies": ["s1"],
            "state": "approved",
            "params": {"type": "object", "properties": {}, "required": [], "optional": []},
            "module_name": "B.py",
            "dependency_hashes": compute_dependency_hashes(
                {"dependencies": ["A"]}, {"A": A}, {"A": ""}
            ),
            "broken_reason": None,
        }
        self._write_tool(A)
        self._write_tool(B)
        self.fh.write_file_content("B.py", "def B(): A(x='hi')")

        self.assertEqual(find_dependents("A", self.th), ["B"])
        self.assertEqual(list_broken_tools(self.th), [])

    def test_check_all_tools_health_schema_change_breaks_and_unbreaks(self):
        A = self._primitive("A")
        B = {
            "name": "B",
            "packaging_format": "code",
            "dependencies": ["A"],
            "mcp_dependencies": ["s1"],
            "state": "approved",
            "params": {"type": "object", "properties": {}, "required": [], "optional": []},
            "module_name": "B.py",
            "dependency_hashes": compute_dependency_hashes(
                {"dependencies": ["A"]}, {"A": A}, {"A": ""}
            ),
            "broken_reason": None,
        }
        self._write_tool(A)
        self._write_tool(B)
        self.fh.write_file_content("B.py", "def B(): A(x='hi')")

        # Healthy initially
        r = check_all_tools_health(self.th, self.fh)
        self.assertEqual(r["broken"], [])

        # Mutate A's params schema → B goes broken with dep_schema_changed
        A2 = dict(A)
        A2["params"] = {
            "type": "object",
            "properties": {"y": {"type": "int"}},
            "required": ["y"],
            "optional": [],
        }
        self._write_tool(A2)
        r = check_all_tools_health(self.th, self.fh)
        names = {b["name"]: b["reason"] for b in r["broken"]}
        self.assertEqual(names.get("B"), "dep_schema_changed:A")

        # Restore A → B unbreaks
        self._write_tool(A)
        r = check_all_tools_health(self.th, self.fh)
        self.assertIn("B", r["unbroken"])
        self.assertEqual(self._read_tool("B")["state"], "approved")

    def test_check_all_tools_health_dep_missing(self):
        A = self._primitive("A")
        B = {
            "name": "B",
            "packaging_format": "code",
            "dependencies": ["A"],
            "mcp_dependencies": [],
            "state": "approved",
            "params": {"type": "object", "properties": {}, "required": [], "optional": []},
            "module_name": None,
            "dependency_hashes": compute_dependency_hashes(
                {"dependencies": ["A"]}, {"A": A}, {"A": ""}
            ),
            "broken_reason": None,
        }
        self._write_tool(A)
        self._write_tool(B)
        self.th.delete_file("A.json")
        r = check_all_tools_health(self.th, self.fh)
        names = {b["name"]: b["reason"] for b in r["broken"]}
        self.assertEqual(names.get("B"), "dep_missing:A")

    def test_check_all_tools_health_preserves_server_unavailable(self):
        A = self._primitive("A")
        A["state"] = "broken"
        A["broken_reason"] = "server_unavailable:s1"
        B = {
            "name": "B",
            "packaging_format": "code",
            "dependencies": ["A"],
            "mcp_dependencies": ["s1"],
            "state": "approved",
            "params": {"type": "object", "properties": {}, "required": [], "optional": []},
            "module_name": None,
            "dependency_hashes": compute_dependency_hashes(
                {"dependencies": ["A"]}, {"A": self._primitive("A")}, {"A": ""}
            ),
            "broken_reason": None,
        }
        self._write_tool(A)
        self._write_tool(B)
        r = check_all_tools_health(self.th, self.fh)

        a_now = self._read_tool("A")
        self.assertEqual(a_now["state"], "broken")
        self.assertEqual(a_now["broken_reason"], "server_unavailable:s1")
        # Transitive propagation → B also broken with dep_broken reason
        b_now = self._read_tool("B")
        self.assertEqual(b_now["state"], "broken")
        self.assertEqual(b_now["broken_reason"], "dep_broken:A")


# ---------------------------------------------------------------------------
# ExternalMCPManager.find_dependents
# ---------------------------------------------------------------------------


class ManagerFindDependentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for sub in ("tools", "files", "mcps"):
            os.makedirs(os.path.join(self.tmp, sub))
        self.th = FileHandler(os.path.join(self.tmp, "tools"))
        self.fh = FileHandler(os.path.join(self.tmp, "files"))
        self.ch = FileHandler(os.path.join(self.tmp, "mcps"))
        self.mgr = ExternalMCPManager(
            tool_handler=self.th, file_handler=self.fh, config_handler=self.ch
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_excludes_self_owned_primitives(self):
        # Two primitives from server 'p'.
        p1 = build_primitive_manifest(
            "p__a", "p", "", params_from_input_schema(None)
        )
        p2 = build_primitive_manifest(
            "p__b", "p", "", params_from_input_schema(None)
        )
        # A composite on p's primitives.
        comp = {
            "name": "wrapper",
            "packaging_format": "code",
            "mcp_server": None,
            "mcp_dependencies": ["p"],
            "dependencies": ["p__a"],
            "state": "approved",
        }
        for d in (p1, p2, comp):
            self.th.write_file_content(f"{d['name']}.json", json.dumps(d))

        dependents = self.mgr.find_dependents("p")
        # Primitives (p__a, p__b) are excluded — they're cascade-deleted, not
        # "broken"-flagged — only the real composite shows up.
        self.assertEqual(dependents, ["wrapper"])


# ---------------------------------------------------------------------------
# bundled_with_mcps default + primitive manifest
# ---------------------------------------------------------------------------


class BundledWithMcpsTests(unittest.TestCase):
    def test_primitive_manifest_defaults_bundled_true(self):
        m = build_primitive_manifest(
            "ctx7__query-docs",
            "context7",
            "docs",
            params_from_input_schema(None),
        )
        self.assertEqual(m["bundled_with_mcps"], True)


if __name__ == "__main__":
    unittest.main()
