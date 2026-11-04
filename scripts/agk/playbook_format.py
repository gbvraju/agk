"""The playbook format (SPEC-0038 rules 1 to 4; REQ-045 AC1 and AC4). Installed: `kit/manifest.json`
lists it in `verbatim`, and `check_playbooks.py` imports it. Later builds read a playbook through
this module (ADR-0259; the kit-only `/agk:start` helper `playbook.py` is a different file).

A playbook is one TOML file per work type, `config/playbooks/<work type>.toml`, read with `tomllib`.
`problems(path, root)` returns one line per problem, each naming the rule and the file and never a
value: a file that is not TOML, an unknown work type or one that is not the file's name (rule 1); a
missing section or key, a wrong type, a phase whose `after` names an unknown phase or makes a cycle,
a lane or split kind outside `brief_order`, an unknown gate kind or a check gate without `step`
(rule 2); a claim with neither basis, or a `measured` claim whose record is not a file under
`docs/runs/` (rule 3, which reads only that the file exists); and anything that could lower a gate
(rule 4): a key outside the format, `[testing] profile = "fast"` or a `pr_tests` key, a governance
setting of `agk.toml` named as a setting (a backticked token, `<setting> =` or `<setting>:`) or a
principle or a session rule named to set aside, in any value, and a gate whose text names signing,
an apply of infrastructure, a release or a secret with `owner_only = false`. Files only: no network,
nothing written.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

FORMAT = 1
# SPEC-0038 rule 1: the fixed list. One constant, so a later amendment adds one entry here.
WORK_TYPES = (
    "web-app",
    "mobile",
    "cloud-migration",
    "rag-app",
    "mcp-server",
    "multi-agent",
    "voice-agent",
    "pilot",
)
FOLDER = "config/playbooks"
RUNS = "docs/runs/"

GATE_KINDS = ("check", "judgement")
SHAPES = ("per-brief", "per-phase", "per-batch")
BASES = ("measured", "expected")
PROFILES = ("balanced", "thorough")  # `fast` is refused by rule 4; impact.py's other profiles
LOWERING_PROFILES = ("fast",)
# SPEC-0038 rule 4: the settings of agk.toml that govern a gate.
SETTINGS = (
    "required_checks",
    "ac_coverage",
    "review_mode",
    "pr_mode",
    "agent_apps",
    "paused",
    "execution",
    "pr_tests",
)
_NAMES = "|".join(SETTINGS)
SETTING_NAMED = re.compile(rf"`\s*(?:{_NAMES})\s*`|\b(?:{_NAMES})\s*[=:]")
RULE_NAMED = re.compile(r"\b(?:principle|session\s+rule|CLAUDE\.md\s+item)\s+\d+", re.I)
OWNER_ACTION = re.compile(
    r"\bsign(?:s|ed|ing|ature|atures)?\b"
    r"|\bappl(?:y|ies|ied|ying)\b[^.]*\binfrastructure\b"
    r"|\binfrastructure\b[^.]*\bappl(?:y|ies|ied|ying)\b"
    r"|\breleases?\b"
    r"|\bsecrets?\b",
    re.I,
)

STR, INT, BOOL, STRS, PAIRS, TABLES = "str", "int", "bool", "strs", "pairs", "tables"

TOP: dict[str, str] = {
    "format": INT,
    "work_type": STR,
    "title": STR,
    "heavy_steps": STRS,
    "evidence": STRS,
    "phases": TABLES,
    "split": "table",
    "lanes": TABLES,
    "testing": "table",
    "gates": TABLES,
    "milestones": "table",
    "claims": TABLES,
}
# section -> (required keys, optional keys), each key with its type
SECTIONS: dict[str, tuple[dict[str, str], dict[str, str]]] = {
    "phases": ({"name": STR, "order": INT, "after": STRS}, {}),
    "split": ({"brief_order": STRS, "depends_on": PAIRS}, {}),
    "lanes": ({"name": STR, "kinds": STRS}, {}),
    "testing": ({"profile": STR, "always_full": STRS, "map": TABLES}, {}),
    "gates": ({"id": STR, "kind": STR, "text": STR, "owner_only": BOOL}, {"step": STR}),
    "milestones": ({"shape": STR, "batch_by": STR}, {}),
    # `basis` is required by rule 3 and `record` by rule 3 for a measured claim
    "claims": ({"text": STR}, {"basis": STR, "record": STR}),
}
MAP_KEYS = {"code": STR, "tests": STR}


def _is(value: Any, kind: str) -> bool:
    if kind == STR:
        return isinstance(value, str)
    if kind == INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == BOOL:
        return isinstance(value, bool)
    if kind == STRS:
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if kind == PAIRS:
        return isinstance(value, list) and all(
            isinstance(p, list) and len(p) == 2 and all(isinstance(v, str) for v in p)
            for p in value
        )
    if kind == TABLES:
        return isinstance(value, list) and all(isinstance(v, dict) for v in value)
    return isinstance(value, dict)  # "table"


def _strings(value: Any) -> list[str]:
    """Every string of a value, in lists and tables at any depth."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    return []


def _table_keys(rel: str, where: str, table: dict, required: dict, optional: dict) -> list[str]:
    out = []
    for key in table:
        if key == "pr_tests":
            out.append(f"rule 4: {rel}: {where} has a `pr_tests` key")
        elif key not in required and key not in optional:
            out.append(f"rule 2 and rule 4: {rel}: {where} has a key outside the format")
    for key, kind in required.items():
        if key not in table:
            out.append(f"rule 2: {rel}: {where} is missing the key `{key}`")
        elif not _is(table[key], kind):
            out.append(f"rule 2: {rel}: {where} key `{key}` has the wrong type")
    for key, kind in optional.items():
        if key in table and not _is(table[key], kind):
            out.append(f"rule 2: {rel}: {where} key `{key}` has the wrong type")
    return out


def _cycle(after: dict[str, list[str]]) -> bool:
    state: dict[str, int] = {}

    def visit(node: str) -> bool:
        state[node] = 1
        for nxt in after.get(node, []):
            if state.get(nxt) == 1 or (nxt not in state and nxt in after and visit(nxt)):
                return True
        state[node] = 2
        return False

    return any(node not in state and visit(node) for node in after)


def _phases(rel: str, phases: list[dict]) -> list[str]:
    out = []
    names = [p["name"] for p in phases if isinstance(p.get("name"), str)]
    if len(set(names)) != len(names):
        out.append(f"rule 2: {rel}: two phases have the same name")
    if any(_is(p.get("order"), INT) and p["order"] < 1 for p in phases):
        out.append(f"rule 2: {rel}: a phase `order` is below 1")
    known = set(names)
    linked = [p for p in phases if isinstance(p.get("name"), str) and _is(p.get("after"), STRS)]
    if any(a not in known for p in linked for a in p["after"]):
        out.append(f"rule 2: {rel}: a phase `after` names an unknown phase")
    graph = {p["name"]: [a for a in p["after"] if a in known] for p in linked}
    if _cycle(graph):
        out.append(f"rule 2: {rel}: the phases' `after` make a cycle")
    return out


def _kinds(rel: str, data: dict) -> list[str]:
    split = data.get("split")
    if not isinstance(split, dict) or not _is(split.get("brief_order"), STRS):
        return []
    order = set(split["brief_order"])
    out = []
    if len(order) != len(split["brief_order"]):
        out.append(f"rule 2: {rel}: `brief_order` names a kind twice")
    pairs = split.get("depends_on")
    if _is(pairs, PAIRS) and any(k not in order for p in pairs for k in p):
        out.append(f"rule 2: {rel}: a `depends_on` kind is not in `brief_order`")
    lanes = data.get("lanes")
    if _is(lanes, TABLES) and any(
        k not in order for lane in lanes if _is(lane.get("kinds"), STRS) for k in lane["kinds"]
    ):
        out.append(f"rule 2: {rel}: a lane kind is not in `brief_order`")
    return out


def _testing(rel: str, testing: dict) -> list[str]:
    out = []
    profile = testing.get("profile")
    if isinstance(profile, str):
        if profile in LOWERING_PROFILES:
            out.append(f"rule 4: {rel}: `[testing] profile` would run fewer tests than the default")
        elif profile not in PROFILES:
            out.append(f"rule 2: {rel}: `[testing] profile` is not a known profile")
    entries = testing.get("map")
    if _is(entries, TABLES):
        for entry in entries:
            out += _table_keys(rel, "a `[testing] map` entry", entry, MAP_KEYS, {})
    return out


def _gates(rel: str, gates: list[dict]) -> list[str]:
    out = []
    for gate in gates:
        kind = gate.get("kind")
        if isinstance(kind, str) and kind not in GATE_KINDS:
            out.append(f"rule 2: {rel}: a gate `kind` is not check or judgement")
        if kind == "check" and "step" not in gate:
            out.append(f"rule 2: {rel}: a check gate has no `step`")
        text = gate.get("text")
        if gate.get("owner_only") is False and isinstance(text, str) and OWNER_ACTION.search(text):
            out.append(
                f"rule 4: {rel}: a gate that names an owner's action has `owner_only = false`"
            )
    return out


def _claims(rel: str, claims: list[dict], root: Path) -> list[str]:
    out = []
    for claim in claims:
        basis = claim.get("basis")
        if basis not in BASES:
            out.append(f"rule 3: {rel}: a claim is neither measured nor expected")
            continue
        if basis != "measured":
            continue
        record = claim.get("record")
        if not isinstance(record, str):
            out.append(f"rule 3: {rel}: a measured claim names no `record`")
            continue
        parts = PurePosixPath(record).parts
        inside = (
            record.startswith(RUNS)
            and ".." not in parts
            and not PurePosixPath(record).is_absolute()
            and "\\" not in record
        )
        if not inside or not (root / record).is_file():
            out.append(f"rule 3: {rel}: a measured claim's record is not a file under {RUNS}")
    return out


def _named(rel: str, data: dict) -> list[str]:
    strings = _strings(data)
    out = []
    if any(SETTING_NAMED.search(s) for s in strings):
        out.append(f"rule 4: {rel}: a value names a governance setting of agk.toml as a setting")
    if any(RULE_NAMED.search(s) for s in strings):
        out.append(f"rule 4: {rel}: a value names a principle or a session rule")
    return out


def problems(path: Path, root: Path) -> list[str]:
    """One line per problem of the playbook at `path`, each naming the rule and the file."""
    path, root = Path(path), Path(root)
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = path.name
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return [f"rule 1: {rel}: the file is not TOML"]
    out: list[str] = []
    work_type = data.get("work_type")
    if isinstance(work_type, str):
        if work_type not in WORK_TYPES:
            out.append(f"rule 1: {rel}: `work_type` is not one of the work types")
        elif work_type != path.stem:
            out.append(f"rule 1: {rel}: `work_type` is not the file's name")
    for key in data:
        if key == "pr_tests":
            out.append(f"rule 4: {rel}: the playbook has a `pr_tests` key")
        elif key not in TOP:
            out.append(f"rule 2 and rule 4: {rel}: the playbook has a key outside the format")
    for key, kind in TOP.items():
        if key not in data:
            out.append(f"rule 2: {rel}: the playbook is missing `{key}`")
        elif not _is(data[key], kind):
            out.append(f"rule 2: {rel}: `{key}` has the wrong type")
    if _is(data.get("format"), INT) and data["format"] != FORMAT:
        out.append(f"rule 2: {rel}: `format` is not {FORMAT}")
    for section, (required, optional) in SECTIONS.items():
        value = data.get(section)
        if not _is(value, TOP[section]):
            continue
        tables = value if isinstance(value, list) else [value]
        where = f"[{section}]" if isinstance(value, dict) else f"a [[{section}]] entry"
        for table in tables:
            out += _table_keys(rel, where, table, required, optional)
    if _is(data.get("phases"), TABLES):
        out += _phases(rel, data["phases"])
    out += _kinds(rel, data)
    if _is(data.get("testing"), "table"):
        out += _testing(rel, data["testing"])
    if _is(data.get("gates"), TABLES):
        out += _gates(rel, data["gates"])
    milestones = data.get("milestones")
    if isinstance(milestones, dict) and isinstance(milestones.get("shape"), str):
        if milestones["shape"] not in SHAPES:
            out.append(f"rule 2: {rel}: `[milestones] shape` is not a known shape")
    if _is(data.get("claims"), TABLES):
        out += _claims(rel, data["claims"], root)
    out += _named(rel, data)
    return out


def playbooks(root: Path) -> list[Path]:
    """The playbook files of a repository, sorted."""
    folder = Path(root) / FOLDER
    return sorted(folder.glob("*.toml")) if folder.is_dir() else []
