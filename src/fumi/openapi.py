"""Turning an OpenAPI 3 document into the flat list of operations the UI shows."""

import re

METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def _resolve(node, components: dict, depth: int = 0):
    """Inline $refs (bounded, so recursive models don't loop forever)."""
    if depth > 8:
        return {}
    if isinstance(node, dict):
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            target = components.get(name, {})
            merged = {**_resolve(target, components, depth + 1), **{k: v for k, v in node.items() if k != "$ref"}}
            return merged
        return {k: _resolve(v, components, depth + 1) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve(v, components, depth + 1) for v in node]
    return node


def _non_null(schema: dict) -> dict:
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = [s for s in schema[key] if s.get("type") != "null"]
            if options:
                return {**{k: v for k, v in schema.items() if k != key}, **options[0]}
    if "allOf" in schema:
        merged: dict = {}
        for part in schema["allOf"]:
            merged.update(part)
        return {**{k: v for k, v in schema.items() if k != "allOf"}, **merged}
    return schema


def type_label(schema: dict) -> str:
    s = _non_null(schema)
    t = s.get("type")
    if t == "array":
        return f"{type_label(s.get('items', {}))}[]"
    if "enum" in s:
        return "enum"
    return t or "any"


def example(schema: dict, depth: int = 0):
    s = _non_null(schema)
    if depth > 6:
        return None
    for key in ("example", "default"):
        if key in s:
            return s[key]
    if "examples" in s and isinstance(s["examples"], list) and s["examples"]:
        return s["examples"][0]
    if "enum" in s and s["enum"]:
        return s["enum"][0]
    t = s.get("type")
    if t == "object" or "properties" in s:
        return {k: example(v, depth + 1) for k, v in s.get("properties", {}).items()}
    if t == "array":
        return []
    if t in ("integer", "number"):
        return 0
    if t == "boolean":
        return False
    if t == "string":
        return ""
    return None


def _humanize(op_id: str, method: str, path: str) -> str:
    if not op_id:
        return f"{method.upper()} {path}"
    # FastAPI's default operationId is function name + path + method, with non-word characters as "_".
    suffix = re.sub(r"\W", "_", path) + "_" + method
    name = op_id[: -len(suffix)] if op_id.endswith(suffix) and len(op_id) > len(suffix) else op_id
    return " ".join(w for w in name.split("_") if w).capitalize()


def flatten(openapi: dict) -> list[dict]:
    components = openapi.get("components", {}).get("schemas", {})
    ops = []
    for path, item in openapi.get("paths", {}).items():
        shared = item.get("parameters", [])
        for method in METHODS:
            op = item.get(method)
            if not op:
                continue
            op_id = op.get("operationId") or f"{method}_{path}"
            params = []
            for p in _resolve([*shared, *op.get("parameters", [])], components):
                if p.get("in") not in ("path", "query", "header"):
                    continue
                schema = p.get("schema", {})
                params.append({
                    "name": p["name"], "in": p["in"], "required": bool(p.get("required") or p["in"] == "path"),
                    "type": type_label(schema), "example": example(schema) if p.get("required") else None,
                    "description": p.get("description", ""),
                })
            body = None
            content = (op.get("requestBody") or {}).get("content", {})
            if content:
                media = "application/json" if "application/json" in content else next(iter(content))
                schema = _non_null(_resolve(content[media].get("schema", {}), components))
                required = set(schema.get("required", []))
                body = {
                    "media": media,
                    "required": bool(op["requestBody"].get("required")),
                    "fields": {
                        k: {"type": type_label(v), "required": k in required}
                        for k, v in schema.get("properties", {}).items()
                    },
                    "open": schema.get("additionalProperties", False) not in (False, None) or not schema.get("properties"),
                    "example": example(schema),
                }
            ops.append({
                "id": op_id,
                "method": method.upper(),
                "path": path,
                "tag": (op.get("tags") or ["default"])[0],
                "summary": op.get("summary") or _humanize(op.get("operationId", ""), method, path),
                "description": op.get("description", ""),
                "deprecated": bool(op.get("deprecated")),
                "params": params,
                "body": body,
            })
    return ops


def diff(old: list[dict] | None, new: list[dict]) -> dict:
    if old is None:
        return {"added": [], "removed": []}
    before = {o["id"]: o for o in old}
    after = {o["id"]: o for o in new}
    label = lambda o: {"id": o["id"], "label": f"{o['method']} {o['summary']}"}  # noqa: E731
    return {
        "added": [label(after[i]) for i in after if i not in before],
        "removed": [label(before[i]) for i in before if i not in after],
    }
