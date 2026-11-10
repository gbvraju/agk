"""Print one agk configuration value (lists space-joined); used by agk.mk.

Usage: python3 scripts/agk/config.py KEY
KEY is one of default_branch, test_dirs, lint_paths, project_tests.

`guard_settings(root)` reads the `[guard]` table of agk.toml (SPEC-0042 rule 1, brief #561): it may
only add to the data guard's built-in rules. An unknown key, a key of the wrong kind, a pattern that
does not compile or an `allow_paths` entry that is not one relative file with a reason (or that
names a built-in secret file) is refused, naming the setting and never the value. An
`allow_paths` or `allowed_hosts` entry counts only when the same entry is in agk.toml at
`origin/<default branch>` as last fetched (no network), so a branch cannot loosen its own guard.

`model_settings(root)` reads the optional `[models]` table (SPEC-0045 rules 1 to 3, brief #623):
each of the five kinds gets a tier and an effort, the table's or rule 2's default; a kind, tier or
effort outside the lists, a non-string value or `review` below `strongest` at `high` is refused,
naming `setting: models.<kind>` and never the value. `model_names(root)` reads the optional
`[models.names]` table, a tier to a project's model name, which the kit never ships. No check,
gate or reading list reads either in this build (rule 1). `model_providers(root)` reads the
optional `[models.providers]` table (SPEC-0053 rule 3, brief #763): a tier to its ordered list of
plain labels.

`failures_settings(root)` reads the optional `[failures]` table (SPEC-0046 rule 2, brief #634):
`issues` and `artifacts` (booleans, false) and `artifact_paths` (relative path patterns, empty).
An unknown key or a value of the wrong kind is refused, naming `setting: failures.<key>` and never
the value.

`scorecard_settings(root)` reads the optional `[scorecard]` table (SPEC-0047 rule 3, brief #713):
a line per metric and the windows `trend_weeks` and `close_weeks`, else the kit defaults. An
unknown key, a non-number or a negative number is refused, naming `setting: scorecard.<key>`.

`caps_settings(root)` reads the optional `[caps]` table (SPEC-0049 rule 2, brief #714): `S`, `M`
and `L`, each `{ tokens = <n>, hours = <h> }`, whole numbers above zero, a larger size never below
a smaller one; None without the table. Any other shape is refused, naming `setting: caps.<key>`.
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


# --- the [models] table (SPEC-0045 rules 1 to 3, brief #623) ---------------------------------

MODEL_KINDS = ("design", "review", "build", "small", "mechanical")
MODEL_TIERS = ("strongest", "mid", "fast")
MODEL_EFFORTS = ("low", "medium", "high")  # (verify: the names a runtime accepts, Q-S0045-2)
# Rule 2's defaults (verify: what the conductor uses today; no file records it, Q-S0045-14).
MODEL_DEFAULTS = {
    "design": ("strongest", "high"),
    "review": ("strongest", "high"),
    "build": ("strongest", "medium"),
    "small": ("mid", "low"),
    "mechanical": ("mid", "low"),
}
# Rules 2 and 6: a reviewer runs on `strongest`, at `high` for a first review (Q-623-1).
REVIEW_FLOOR = {"tier": "strongest", "effort": "high"}
MODEL_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")  # SPEC-0053 rule 3


class ModelSettingError(CheckError):
    """The `[models]` table is refused (exit 2); the message names the setting, never the value."""


def _refuse_model(setting: str) -> ModelSettingError:
    return ModelSettingError(f"the [models] table is refused (setting: {setting})")


def _models_table(root: Path) -> dict:
    """The raw `[models]` table of agk.toml, {} when there is none; an unreadable file refuses."""
    try:
        table = config_source(root).get("models", {})
    except (OSError, ValueError):
        raise _refuse_model("models") from None
    if not isinstance(table, dict):
        raise _refuse_model("models")
    return table


def model_names(root: Path) -> dict[str, str]:
    """The optional `[models.names]` table: a tier to a project's own model name (rule 3)."""
    names = _models_table(root).get("names", {})
    if not isinstance(names, dict):
        raise _refuse_model("models.names")
    for tier, name in names.items():
        if tier not in MODEL_TIERS or not isinstance(name, str) or not name.strip():
            raise _refuse_model(f"models.names.{tier}")
    return dict(names)


def model_providers(root: Path) -> dict[str, list[str]]:
    """The optional `[models.providers]` table: a tier to its labels in the order of trial
    (SPEC-0053 rule 3). An unknown tier names only the table, for a key may be anything."""
    table = _models_table(root).get("providers", {})
    if not isinstance(table, dict):
        raise _refuse_model("models.providers")
    names = model_names(root)
    seen: set[str] = set()
    for tier, labels in table.items():
        if tier not in MODEL_TIERS:
            raise _refuse_model("models.providers")
        if (
            not isinstance(labels, list)
            or not labels
            or not all(isinstance(x, str) and MODEL_LABEL.fullmatch(x) for x in labels)
            or len(set(labels)) != len(labels)
            or seen & set(labels)
            or labels[0] != names.get(tier, labels[0])
        ):
            raise _refuse_model(f"models.providers.{tier}")
        seen |= set(labels)
    return {tier: list(labels) for tier, labels in table.items()}


def model_settings(root: Path) -> dict[str, dict[str, str]]:
    """The tier and effort of every kind (rule 2): the table's entry or the default. A kind, tier
    or effort outside the lists, a value that is not a string, an entry that is not exactly
    `{ tier, effort }` and `review` below `strongest` at `high` are refused."""
    table = _models_table(root)
    model_providers(root)
    settings = {k: {"tier": t, "effort": e} for k, (t, e) in MODEL_DEFAULTS.items()}
    for kind, entry in table.items():
        if kind in ("names", "providers"):
            continue
        if (
            kind not in MODEL_KINDS
            or not isinstance(entry, dict)
            or set(entry) != {"tier", "effort"}
            or entry["tier"] not in MODEL_TIERS
            or entry["effort"] not in MODEL_EFFORTS
            or (kind == "review" and entry != REVIEW_FLOOR)
        ):
            raise _refuse_model(f"models.{kind}")
        settings[kind] = {"tier": entry["tier"], "effort": entry["effort"]}
    return settings


FAILURES_DEFAULTS = {"issues": False, "artifacts": False, "artifact_paths": []}


class FailuresSettingError(CheckError):
    """The `[failures]` table is refused (exit 2), naming the setting and never the value."""


def _refuse_failures(setting: str) -> FailuresSettingError:
    return FailuresSettingError(f"the [failures] table is refused (setting: {setting})")


def _relative(value: object) -> bool:
    """A non-empty path pattern inside the run's folder: not absolute, no drive, no `..` part."""
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        return False
    return not value.startswith("/") and ":" not in value and ".." not in value.split("/")


def failures_settings(root: Path) -> dict:
    """The three `[failures]` settings (rule 2): the table's value or the default."""
    try:
        table = config_source(root).get("failures", {})
    except (OSError, ValueError):
        raise _refuse_failures("failures") from None
    if not isinstance(table, dict) or any(k not in FAILURES_DEFAULTS for k in table):
        raise _refuse_failures("failures")
    for key in ("issues", "artifacts"):
        if not isinstance(table.get(key, False), bool):
            raise _refuse_failures(f"failures.{key}")
    paths = table.get("artifact_paths", [])
    if not isinstance(paths, list) or not all(_relative(p) for p in paths):
        raise _refuse_failures("failures.artifact_paths")
    return {**FAILURES_DEFAULTS, **table, "artifact_paths": list(paths)}


# --- the [scorecard] table (SPEC-0047 rule 3, brief #713) ------------------------------------

# The kit's lines, all guesses until build (f) measures four weeks (verify). None: no line (a
# count reported and judged by its trend), or, for the rule counts, the totals of the budget file.
SCORECARD_LINES: dict[str, float | None] = {
    "full_check_minutes": 20,
    "prepush_seconds": 300,  # the [testing] budget_seconds default
    "red_hours": 4,
    "flaky_rate": 2,
    "fix_list_rate": 50,
    "lead_time_hours": 48,
    "restore_hours": 4,
    "ci_minutes_per_merge": 30,
    "rule_words": None,
    "rule_lines": None,
    "old_failure_issues": 0,
    "verify_marks": None,
    "verify_oldest_days": 90,
    "residuals_past_due": 0,
    "pins_behind": None,
    "pins_oldest_gap_days": 180,
    "kit_releases_behind": 3,
    "stale_guides": 0,
    "goals_not_met": 0,  # SPEC-0051 rule 9 (verify)
}
SCORECARD_WINDOWS = {"trend_weeks": 4, "close_weeks": 2}  # (verify)


class ScorecardSettingError(CheckError):
    """The `[scorecard]` table is refused, naming the setting and never the value."""


def _refuse_scorecard(setting: str) -> ScorecardSettingError:
    return ScorecardSettingError(f"the [scorecard] table is refused (setting: {setting})")


def scorecard_settings(root: Path) -> dict:
    """`lines` (metric to number or None) and the two windows: the table's or the default. A
    window is a whole number of weeks, at least 1."""
    try:
        table = config_source(root).get("scorecard", {})
    except (OSError, ValueError):
        raise _refuse_scorecard("scorecard") from None
    if not isinstance(table, dict) or any(
        k not in SCORECARD_LINES and k not in SCORECARD_WINDOWS for k in table
    ):
        raise _refuse_scorecard("scorecard")
    for key, value in table.items():
        number = isinstance(value, int | float) and not isinstance(value, bool) and value >= 0
        if key in SCORECARD_WINDOWS:
            number = number and isinstance(value, int) and value >= 1
        if not number:
            raise _refuse_scorecard(f"scorecard.{key}")
    lines = {k: table.get(k, v) for k, v in SCORECARD_LINES.items()}
    return {"lines": lines, **{k: table.get(k, v) for k, v in SCORECARD_WINDOWS.items()}}


# --- the [caps] table (SPEC-0049 rule 2, brief #714) -----------------------------------------

CAP_SIZES = ("S", "M", "L")  # smallest first: a larger size is never below a smaller one
CAP_KEYS = ("tokens", "hours")


class CapsSettingError(CheckError):
    """The `[caps]` table is refused, naming the setting and never the value."""


def _refuse_caps(setting: str) -> CapsSettingError:
    return CapsSettingError(f"the [caps] table is refused (setting: {setting})")


def caps_settings(root: Path) -> dict | None:
    """Each size's `{tokens, hours}` cap, or None without the table (nothing is capped)."""
    try:
        source = config_source(root)
    except (OSError, ValueError):
        raise _refuse_caps("caps") from None
    if "caps" not in source:
        return None
    table = source["caps"]
    if not isinstance(table, dict):
        raise _refuse_caps("caps")
    for size in [*table, *CAP_SIZES]:
        entry = table.get(size)
        if (
            size not in CAP_SIZES
            or not isinstance(entry, dict)
            or set(entry) != set(CAP_KEYS)
            or not all(type(entry[k]) is int and entry[k] > 0 for k in CAP_KEYS)
        ):
            raise _refuse_caps(f"caps.{size}")
    for smaller, larger in zip(CAP_SIZES, CAP_SIZES[1:], strict=False):
        if any(table[larger][k] < table[smaller][k] for k in CAP_KEYS):
            raise _refuse_caps(f"caps.{larger}")
    return {size: dict(table[size]) for size in CAP_SIZES}


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
