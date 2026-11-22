"""The startup settings check (brief #1594, ADR-0674).

Every name in `.env.example` is required. A value comes from the environment, else from the ignored
`.env` file; an empty value or a `<placeholder>` is not set. A missing setting stops the app with a
message that names the setting and never a value.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE, LOCAL = ".env.example", ".env"


def _pairs(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            out.append((key.strip(), value.strip()))
    return out


def _set(value: str | None) -> bool:
    return value is not None and value != "" and not (value.startswith("<") and value.endswith(">"))


def load(root: Path = ROOT) -> dict[str, str]:
    """The required settings by name; SystemExit naming the first one that is not set."""
    found = dict(_pairs(root / LOCAL))
    found.update({k: v for k, v in os.environ.items() if _set(v)})
    names = [name for name, _ in _pairs(root / EXAMPLE)]
    for name in names:
        if not _set(found.get(name)):
            raise SystemExit(f"refused to start: the setting {name} is not set (see {EXAMPLE})")
    return {name: found[name] for name in names}
