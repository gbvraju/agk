"""A small JSON Schema validator: exactly the keywords of SPEC-0009 rule 19, nothing else.

A keyword it does not implement raises ValueError, so a schema cannot quietly use more than the
validator checks. `$schema`, `title` and `description` are annotations and are ignored.
"""

from __future__ import annotations

import re
from typing import Any

ANNOTATIONS = {"$schema", "title", "description"}
KEYWORDS = {
    "type",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "enum",
    "const",
    "pattern",
    "oneOf",
}
TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def same(a: Any, b: Any) -> bool:
    return type(a) is type(b) and a == b


def errors(value: Any, schema: dict, path: str = "$") -> list[str]:
    unknown = set(schema) - KEYWORDS - ANNOTATIONS
    if unknown:
        raise ValueError(f"keyword not implemented: {sorted(unknown)}")
    found: list[str] = []
    if "type" in schema and not TYPES[schema["type"]](value):
        return [f"{path}: not of type {schema['type']}"]
    if "const" in schema and not same(value, schema["const"]):
        found.append(f"{path}: not the constant")
    if "enum" in schema and not any(same(value, e) for e in schema["enum"]):
        found.append(f"{path}: not in the enum")
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        found.append(f"{path}: does not match the pattern")
    if "oneOf" in schema:
        matching = sum(1 for s in schema["oneOf"] if not errors(value, s, path))
        if matching != 1:
            found.append(f"{path}: matches {matching} of the oneOf alternatives")
    if isinstance(value, dict):
        found += [f"{path}.{k}: missing" for k in schema.get("required", []) if k not in value]
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                found += errors(item, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                found.append(f"{path}.{key}: not allowed")
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            found += errors(item, schema["items"], f"{path}[{i}]")
    return found
