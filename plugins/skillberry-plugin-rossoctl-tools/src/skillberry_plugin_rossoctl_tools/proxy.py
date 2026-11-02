"""Generate the proxy module for one MCP tool of a rossoctl tool (design D9).

The module is stored as an ordinary store **code** tool. It has exactly one
top-level function, named like the store tool, so:

* core's executor finds and calls it (``extract_function_and_imports``);
* core's importer re-creates exactly one tool from it (``extract_python_functions``);
* the exporter writes it verbatim to ``scripts/<tool>.py``.

Everything else — the spec, the HTTP clients, the CLI — is nested inside that
function, and the ``__main__`` guard calls it with ``_cli=True``.

Two paths, chosen at run time:

* **store** (``ROSSOCTL_BACKEND_URL`` in the environment): ``POST`` rossoctl's
  ``/api/v1/tools/{ns}/{tool}/invoke``, with a client-credentials token when
  ``ROSSOCTL_CLIENT_ID``/``_SECRET``/``ROSSOCTL_TOKEN_ENDPOINT`` are set;
* **direct** (everywhere else, e.g. an agent pod that runs scripts): MCP over
  streamable HTTP to the tool's Service, resolved in the caller's namespace.

Standard library only. Manifest values are never interpolated into code: the
spec is embedded as JSON in a raw string literal (``'`` escaped as ``\\u0027``),
and identifiers are validated. No credentials are embedded.
"""

import ast
import hashlib
import json
import keyword
import re
from typing import Any, Dict, List, Optional

GENERATOR_VERSION = "2"
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
_MCP_NAME = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")
_LABEL = re.compile(r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$")


def env_token(name: str) -> str:
    """``weather-tool`` -> ``WEATHER_TOOL``."""
    return re.sub(r"[^A-Za-z0-9]", "_", name).upper()


def canonical_schema_sha256(schema: Any) -> str:
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def python_name(name: str) -> str:
    """A valid, non-keyword Python identifier derived from ``name``."""
    ident = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not ident or ident[0].isdigit():
        ident = "t_" + ident
    if keyword.iskeyword(ident):
        ident += "_"
    return ident[:128]


def _param_names(schema: Dict[str, Any]) -> List[str]:
    """Schema properties usable as keyword parameters (others go through **kwargs)."""
    reserved = {"_cli"}
    out = []
    for prop in schema.get("properties") or {}:
        if (
            isinstance(prop, str)
            and _IDENT.match(prop)
            and not keyword.iskeyword(prop)
            and prop not in reserved
        ):
            out.append(prop)
    return out


_ANNOTATIONS = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


def _json_type(info: Any) -> Optional[str]:
    t = info.get("type") if isinstance(info, dict) else None
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), None)
    return t if isinstance(t, str) else None


def _doc_text(text: Any) -> str:
    """One printable line that cannot end or escape the generated docstring."""
    flat = " ".join(str(text or "").split())
    flat = flat.replace("\\", "/").replace('"', "'")
    return "".join(ch for ch in flat if ch.isprintable())[:300]


def build_spec(
    meta: Dict[str, Any], schema: Dict[str, Any], description: str
) -> Dict[str, Any]:
    for key in ("tool", "namespace"):
        if not isinstance(meta.get(key), str) or not _LABEL.match(meta[key]):
            raise ValueError(f"invalid {key}: {meta.get(key)!r}")
    if not isinstance(meta.get("mcp_tool_name"), str) or not _MCP_NAME.match(
        meta["mcp_tool_name"]
    ):
        raise ValueError(f"invalid mcp_tool_name: {meta.get('mcp_tool_name')!r}")
    port = meta.get("port", 8000)
    if not isinstance(port, int) or isinstance(port, bool) or not 0 < port < 65536:
        raise ValueError(f"invalid port: {port!r}")
    path = meta.get("path", "/mcp")
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError(f"invalid path: {path!r}")
    return {
        "generator_version": GENERATOR_VERSION,
        "tool": meta["tool"],
        "namespace": meta["namespace"],
        "port": port,
        "path": path,
        "mcp_tool_name": meta["mcp_tool_name"],
        "gateway_prefix": meta.get("gateway_prefix") or "",
        "read_only": bool(meta.get("read_only")),
        "description": description or "",
        "input_schema": schema or {"type": "object", "properties": {}},
        "input_schema_sha256": meta.get("input_schema_sha256")
        or canonical_schema_sha256(schema or {}),
    }


def render(
    function_name: str, meta: Dict[str, Any], schema: Dict[str, Any], description: str
) -> str:
    """The module source for one proxy tool."""
    if not _IDENT.match(function_name) or keyword.iskeyword(function_name):
        raise ValueError(f"invalid function name: {function_name!r}")
    spec = build_spec(meta, schema, description)
    spec_json = json.dumps(spec, ensure_ascii=True, sort_keys=True).replace(
        "'", "\\u0027"
    )
    params = _param_names(spec["input_schema"])
    props = spec["input_schema"].get("properties") or {}
    required = set(spec["input_schema"].get("required") or [])
    # Annotations and defaults let core's importer rebuild the same params on
    # re-import. _cli is keyword-only, so that parser (positional args) skips it.
    sig_parts = []
    for p in [p for p in params if p in required] + [
        p for p in params if p not in required
    ]:
        ann = _ANNOTATIONS.get(_json_type(props.get(p)) or "", "")
        ann = f": {ann}" if ann else ""
        sig_parts.append(f"{p}{ann}" if p in required else f"{p}{ann} = None")
    signature = ", ".join(sig_parts + ["*", "_cli=False", "**kwargs"])
    collect = "    _args = {k: v for k, v in dict(kwargs).items()}\n"
    for p in params:
        collect += f"    if {p} is not None:\n        _args[{p!r}] = {p}\n"
    doc = [_doc_text(spec["description"]) or "Proxy for a rossoctl tool.", ""]
    if params:
        doc.append("Args:")
        for p in params:
            d = (
                _doc_text((props.get(p) or {}).get("description") or "")
                or f"The {p} argument."
            )
            doc.append(f"    {p}: {d}")
        doc.append("")
    doc.append("Returns:")
    doc.append(
        f"    The result of MCP tool {spec['mcp_tool_name']} of rossoctl tool {spec['tool']}."
    )
    docstring = "\n".join(("    " + line) if line else "" for line in doc).lstrip()
    return (
        "#!/usr/bin/env python3\n"
        "# Proxy for a rossoctl tool, generated by skillberry-store. Run with --help.\n"
        f"def {function_name}({signature}):\n"
        f'    """{docstring}\n    """\n'
        f"    import json as _json\n"
        f"    _SPEC = _json.loads(r'''{spec_json}''')\n"
        f"{collect}"
        f"{_RUNTIME}"
        '\n\nif __name__ == "__main__":\n'
        f"    {function_name}({''.join(p + '=None, ' for p in params if p in required)}_cli=True)\n"
    )


def extract_spec(source: str) -> Optional[Dict[str, Any]]:
    """Read the embedded spec back without executing the module."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "_SPEC"
            and isinstance(node.value, ast.Call)
            and node.value.args
            and isinstance(node.value.args[0], ast.Constant)
        ):
            try:
                return json.loads(node.value.args[0].value)
            except ValueError:
                return None
    return None


# The function body after _SPEC and _args are set. Indented 4 spaces: it is
# pasted inside the generated function. Standard library only.
_RUNTIME = r'''
    import os as _os
    import sys as _sys
    import urllib.error as _uerr
    import urllib.request as _ureq

    class ToolError(Exception):
        """The tool reported an error (CLI exit 1)."""

    class Unreachable(Exception):
        """The tool or rossoctl could not be reached (CLI exit 3)."""

    def _tok(name):
        return "".join(c.upper() if c.isalnum() and c.isascii() else "_" for c in name)

    T = _tok(_SPEC["tool"])
    timeout = float(_os.environ.get("ROSSOCTL_TOOL_TIMEOUT") or 60)

    def _http(method, url, body=None, headers=None, form=None):
        data = None
        hdrs = dict(headers or {})
        if form is not None:
            import urllib.parse as _up
            data = _up.urlencode(form).encode()
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        elif body is not None:
            data = _json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        req = _ureq.Request(url, data=data, method=method, headers=hdrs)
        try:
            return _ureq.urlopen(req, timeout=timeout)
        except _uerr.HTTPError as e:
            detail = ""
            try:
                detail = e.read(2000).decode("utf-8", "replace").strip()
            except Exception:
                pass
            raise Unreachable("HTTP %s from %s%s" % (e.code, url, (": " + detail) if detail else ""))
        except (_uerr.URLError, OSError) as e:
            raise Unreachable("cannot reach %s: %s" % (url, getattr(e, "reason", e)))

    # ---- store path: rossoctl backend /invoke -------------------------------
    def _token():
        cid, sec, ep = (_os.environ.get(k, "") for k in ("ROSSOCTL_CLIENT_ID", "ROSSOCTL_CLIENT_SECRET", "ROSSOCTL_TOKEN_ENDPOINT"))
        if not (cid and sec and ep):
            return None
        with _http("POST", ep, form={"grant_type": "client_credentials", "client_id": cid, "client_secret": sec}) as r:
            return _json.loads(r.read() or b"{}").get("access_token")

    def _via_backend(base):
        url = "%s/api/v1/tools/%s/%s/invoke" % (base.rstrip("/"), _SPEC["namespace"], _SPEC["tool"])
        headers = {}
        tok = _token()
        if tok:
            headers["Authorization"] = "Bearer " + tok
        with _http("POST", url, body={"tool_name": _SPEC["mcp_tool_name"], "arguments": _args}, headers=headers) as r:
            result = (_json.loads(r.read() or b"{}") or {}).get("result") or {}
        return result

    # ---- direct path: MCP over streamable HTTP ------------------------------
    def _endpoint():
        url = _os.environ.get("ROSSOCTL_TOOL_%s_URL" % T, "").strip()
        if url:
            return url, _SPEC["mcp_tool_name"]
        gw = _os.environ.get("ROSSOCTL_MCP_GATEWAY_URL", "").strip()
        if gw and _SPEC["gateway_prefix"]:
            return gw, _SPEC["gateway_prefix"] + _SPEC["mcp_tool_name"]
        ns = _os.environ.get("ROSSOCTL_NAMESPACE", "").strip()
        if not ns:
            try:
                with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
                    ns = f.read().strip()
            except OSError:
                ns = ""
        ns = ns or _SPEC["namespace"]
        port = _os.environ.get("ROSSOCTL_TOOL_%s_PORT" % T, "").strip() or str(_SPEC["port"])
        return "http://%s-mcp.%s.svc.cluster.local:%s%s" % (_SPEC["tool"], ns, port, _SPEC["path"]), _SPEC["mcp_tool_name"]

    def _messages(resp):
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "text/event-stream" in ctype:
            buf = []
            for raw in resp:
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if line == "":
                    if buf:
                        try:
                            yield _json.loads("\n".join(buf))
                        except ValueError:
                            pass
                        buf = []
                    continue
                if line.startswith("data:"):
                    buf.append(line[5:].lstrip(" ") if line[5:6] == " " else line[5:])
            if buf:
                try:
                    yield _json.loads("\n".join(buf))
                except ValueError:
                    pass
        else:
            text = resp.read().decode("utf-8", "replace").strip()
            if text:
                msg = _json.loads(text)
                for m in (msg if isinstance(msg, list) else [msg]):
                    yield m

    def _direct():
        url, name = _endpoint()
        state = {"sid": None, "ver": None, "id": 0}

        def headers():
            h = {"Accept": "application/json, text/event-stream"}
            if state["sid"]:
                h["Mcp-Session-Id"] = state["sid"]
            if state["ver"]:
                h["MCP-Protocol-Version"] = state["ver"]
            auth = _os.environ.get("MCP_PROXY_AUTH_HEADER", "").strip()
            if auth:
                h["Authorization"] = auth
            for env, hdr in (("TRACEPARENT", "traceparent"), ("TRACESTATE", "tracestate")):
                if _os.environ.get(env):
                    h[hdr] = _os.environ[env]
            return h

        def post(body, expect=True):
            with _http("POST", url, body=body, headers=headers()) as r:
                sid = r.headers.get("Mcp-Session-Id")
                if sid:
                    state["sid"] = sid
                if not expect:
                    return None
                for m in _messages(r):
                    if isinstance(m, dict) and "method" in m and "id" in m:
                        try:
                            post({"jsonrpc": "2.0", "id": m["id"], "error": {"code": -32601, "message": "not supported"}}, expect=False)
                        except Unreachable:
                            pass
                        continue
                    if isinstance(m, dict) and m.get("id") == body.get("id"):
                        if "error" in m:
                            raise ToolError((m["error"] or {}).get("message", "JSON-RPC error"))
                        return m.get("result") or {}
            raise Unreachable("no response from %s" % url)

        def call(method, params):
            state["id"] += 1
            return post({"jsonrpc": "2.0", "id": state["id"], "method": method, "params": params})

        init = call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "skillberry-proxy", "version": _SPEC["generator_version"]}})
        state["ver"] = init.get("protocolVersion") or "2025-06-18"
        post({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect=False)
        try:
            return call("tools/call", {"name": name, "arguments": _args})
        finally:
            if state["sid"]:
                try:
                    _http("DELETE", url, headers=headers()).close()
                except Exception:
                    pass

    def _invoke():
        base = _os.environ.get("ROSSOCTL_BACKEND_URL", "").strip()
        return _via_backend(base) if base else _direct()

    def _text(result):
        parts = []
        for c in result.get("content") or []:
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif c.get("type") == "data":
                d = c.get("data")
                parts.append(d if isinstance(d, str) else _json.dumps(d))
        return "\n".join(parts)

    # ---- function call (store executor, or `import`) ------------------------
    if not _cli:
        try:
            result = _invoke()
        except Unreachable as e:
            raise RuntimeError("rossoctl tool %s unreachable: %s" % (_SPEC["tool"], e))
        text = _text(result)
        if result.get("isError"):
            raise RuntimeError(text or "the tool reported an error")
        try:
            return _json.loads(text)
        except ValueError:
            return text

    # ---- CLI ----------------------------------------------------------------
    import argparse as _ap

    schema = _SPEC["input_schema"]
    parser = _ap.ArgumentParser(description=_SPEC["description"], epilog="Exit codes: 0 ok, 1 tool error, 2 usage, 3 unreachable.")
    parser.add_argument("--json", dest="_json_args", metavar="JSON", help="arguments as one JSON object")
    parser.add_argument("--describe", dest="_describe", action="store_true", help="print the tool's spec")
    dests = []
    for i, (prop, info) in enumerate((schema.get("properties") or {}).items()):
        if prop in ("json", "describe", "help") or not prop:
            continue
        t = (info or {}).get("type")
        if isinstance(t, list):
            t = next((x for x in t if x != "null"), None)
        dest = "p%d" % i
        if t == "boolean":
            parser.add_argument("--" + prop, dest=dest, action="store_const", const=True, default=None)
            parser.add_argument("--no-" + prop, dest=dest, action="store_const", const=False, help=_ap.SUPPRESS)
        else:
            conv = {"string": str, "integer": int, "number": float}.get(t)
            if conv is None:
                conv = lambda v: _json.loads(v)  # noqa: E731
            parser.add_argument("--" + prop, dest=dest, type=conv, default=None, help=(info or {}).get("description"))
        dests.append((prop, dest))
    ns = parser.parse_args()
    if ns._describe:
        print(_json.dumps({k: _SPEC[k] for k in ("tool", "mcp_tool_name", "description", "read_only", "input_schema")}, indent=2))
        _sys.exit(0)
    if ns._json_args:
        try:
            _args.update(_json.loads(ns._json_args))
        except (ValueError, TypeError) as e:
            parser.error("--json: %s" % e)
    for prop, dest in dests:
        if getattr(ns, dest) is not None:
            _args[prop] = getattr(ns, dest)
    missing = [r for r in schema.get("required") or [] if r not in _args]
    if missing:
        parser.error("missing: " + ", ".join("--" + m for m in missing))
    try:
        result = _invoke()
    except Unreachable as e:
        _sys.stderr.write("unreachable: %s\n" % e)
        _sys.exit(3)
    except ToolError as e:
        _sys.stderr.write("error: %s\n" % e)
        _sys.exit(1)
    text = _text(result)
    if result.get("isError"):
        _sys.stderr.write((text or "the tool reported an error") + "\n")
        _sys.exit(1)
    print(text)
    _sys.exit(0)
'''
