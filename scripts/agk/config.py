"""Print one agk configuration value (lists space-joined); used by agk.mk.

Usage: python3 scripts/agk/config.py KEY
KEY is one of default_branch, test_dirs, lint_paths, project_tests.

`guard_settings(root)` reads the `[guard]` table of agk.toml (SPEC-0042 rule 1, brief #561): it may
only add to the data guard's built-in rules. An unknown key, a key of the wrong kind, a pattern that
does not compile or an `allow_paths` entry that is not one relative file with a reason (or that
names a built-in secret file) is refused, naming the setting and never the value. An
`allow_paths` or `allowed_hosts` entry counts only when the same entry is in agk.toml at
`origin/<default branch>` as last fetched (no network), so a branch cannot loosen its own guard.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import DEFAULT_CONFIG, CheckError, config_source, load_config, repo_root, run, show

NAME = "config"
GUARD_LISTS = ("deny_paths", "deny_commands", "allowed_hosts")
GUARD_KEYS = ("patterns", *GUARD_LISTS, "allow_paths")
PATTERN_NAME = re.compile(r"[A-Za-z0-9_-]+")


class GuardSettingError(CheckError):
    """The `[guard]` table is refused (exit 2); the message names the setting, never the value."""


def _refuse(key: str) -> GuardSettingError:
    return GuardSettingError(f"the [guard] table is refused (setting: [guard] {key})")


def _strings(table: dict, key: str) -> list[str]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise _refuse(key)
    return list(value)


def _allow_path(entry: object) -> dict:
    from guard import secret_file_name  # noqa: PLC0415 - agk.mk runs config.py without guard.py

    if not isinstance(entry, dict) or set(entry) != {"path", "reason"}:
        raise _refuse("allow_paths")
    path, reason = entry["path"], entry["reason"]
    if not isinstance(path, str) or not isinstance(reason, str) or not reason.strip():
        raise _refuse("allow_paths")
    parts = path.replace("\\", "/").split("/")
    if (
        not path
        or path.startswith(("/", "~", "\\"))
        or re.match(r"[A-Za-z]:", path)
        or any(c in path for c in "*?[]{}")
        or ".." in parts
        or secret_file_name(path)
    ):
        raise _refuse("allow_paths")
    return {"path": path, "reason": reason}


def _guard_table(source: dict) -> dict:
    """The validated `[guard]` table of one agk.toml, with every key present."""
    table = source.get("guard", {})
    if not isinstance(table, dict):
        raise _refuse("guard")
    for key in table:
        if key not in GUARD_KEYS:
            raise _refuse(key)
    patterns = []
    raw = table.get("patterns", [])
    if not isinstance(raw, list):
        raise _refuse("patterns")
    for entry in raw:
        if not isinstance(entry, dict) or set(entry) != {"name", "regex"}:
            raise _refuse("patterns")
        name, regex = entry["name"], entry["regex"]
        if (
            not isinstance(name, str)
            or not PATTERN_NAME.fullmatch(name)
            or not isinstance(regex, str)
        ):
            raise _refuse("patterns")
        try:
            re.compile(regex)
        except re.error:
            raise _refuse("patterns") from None
        patterns.append((name, regex))
    allow = table.get("allow_paths", [])
    if not isinstance(allow, list):
        raise _refuse("allow_paths")
    settings = {"patterns": patterns, **{k: _strings(table, k) for k in GUARD_LISTS}}
    settings["allow_paths"] = [_allow_path(e) for e in allow]
    return settings


def guard_settings(root: Path) -> dict:
    """The `[guard]` additions that count; raises GuardSettingError when the table is refused."""
    try:
        source = config_source(root)
    except (OSError, ValueError):
        raise _refuse("guard") from None
    settings = _guard_table(source)
    branch = load_config(root)["default_branch"]
    default_text = show(root, f"origin/{branch}", "agk.toml")
    try:
        default = _guard_table(tomllib.loads(default_text)) if default_text else None
    except (CheckError, ValueError):
        default = None  # an unreadable or refused default-branch table: no escape counts
    for key in ("allow_paths", "allowed_hosts"):
        settings[key] = [e for e in settings[key] if default and e in default[key]]
    return settings


def guard_patterns(start: Path) -> list:
    """The `[guard] patterns` of the nearest agk.toml at or above START, read with no program and
    no network, for the log reader (SPEC-0042 rule 11): patterns only add, so they need no
    default-branch check. No agk.toml means none; a refused table raises GuardSettingError."""
    for folder in (start, *start.parents):
        path = folder / "agk.toml"
        if path.is_file():
            try:
                source = tomllib.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raise _refuse("guard") from None
            return _guard_table(source)["patterns"]
    return []


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise CheckError("usage: config.py KEY")
    key = args[0]
    if key not in DEFAULT_CONFIG:
        raise CheckError(f"unknown configuration setting '{key}'")
    value = load_config(repo_root())[key]
    print(" ".join(value) if isinstance(value, list) else value)
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
