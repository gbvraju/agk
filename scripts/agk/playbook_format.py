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

The declaration (SPEC-0038 rule 5; REQ-045 AC2; brief #650, ADR-0312): `declaration(root)` reads
the one line `work_type = "<work type>"` of the `[delivery]` table of `agk.toml` and returns the
work type and the problems of the declaration, each naming rule 5, `agk.toml` and the setting, never
a value; `selected(root)` is the path of the declared playbook, or None. With no `agk.toml`, no
`[delivery]` table or no `work_type` in it there is no declaration and no problem, and nothing
reads a playbook.

The split (SPEC-0038 rule 7; REQ-045 AC3; brief #664, ADR-0317): `split(root, goal, kind)` gives
the lines `playbook.py split` prints for the owner and the session filling briefs, the brief kinds
of the declared playbook's `brief_order` in that order, each with its `Kind:` line, one
`Depends-on:` line per `depends_on` pair and its lane (`lane: none` for a kind no lane holds), after
the work type and the milestone shape; and the problems that refuse the split, each naming the rule,
the file and the key, never a value. With no declaration there is nothing to print and no problem.
Nothing is written.

The discovery questions (SPEC-0048 rule 4, SPEC-0038 rule 2 as amendment 130 widens it; REQ-055
AC2; brief #686): every playbook holds `[[discovery]]` entries (`id`, a lower-case slug, and `text`,
one plain question) with at least the five ids of `DISCOVERY_IDS`, each id once; `discovery(path)`
returns the `(id, text)` pairs of a playbook in its order.

The skills a playbook names (SPEC-0048 rule 12; REQ-055 AC6; brief #691): the optional key `skills`
is a list of names, each matching doctor's `ENGINE_NAME`, and none holds a token of
`config/neutrality.txt` (Q-S0048-16); a problem names the rule, the file and the key, never the
value. `skills(path, root)` returns the allowed names of a playbook in its order, for doctor.
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
    "data-pipeline",  # amendment 130, SPEC-0048 rule 18 build (g)
)
FOLDER = "config/playbooks"
RUNS = "docs/runs/"
CONFIG = "agk.toml"
DELIVERY = "delivery"
WORK_TYPE = "work_type"

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
# SPEC-0048 rule 4: the ids every playbook's `[[discovery]]` holds (amendment 130, item 2).
DISCOVERY_IDS = ("constraints", "success", "data-rules", "environments", "non-functional")
SLUG = re.compile(r"^[a-z][a-z0-9-]*$")
NEUTRALITY = "config/neutrality.txt"  # SPEC-0048 rule 12, Q-S0048-16

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
    "discovery": TABLES,
}
OPTIONAL_TOP: dict[str, str] = {"skills": STRS}  # SPEC-0048 rule 12: a playbook may name skills
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
    "discovery": ({"id": STR, "text": STR}, {}),
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


def _discovery(rel: str, entries: list[dict]) -> list[str]:
    """SPEC-0048 rule 4: slug ids, each once, the five required ids, one plain question each."""
    out = []
    found = [e["id"] for e in entries if isinstance(e.get("id"), str)]
    if any(not SLUG.match(i) for i in found):
        out.append(f"rule 2: {rel}: a `[[discovery]]` id is not a lower-case slug")
    if len(set(found)) != len(found):
        out.append(f"rule 2: {rel}: a `[[discovery]]` id appears twice")
    if any(i not in found for i in DISCOVERY_IDS):
        out.append(f"rule 2: {rel}: `[[discovery]]` is missing a required id (SPEC-0048 rule 4)")
    texts = [e["text"] for e in entries if isinstance(e.get("text"), str)]
    if any(not s.strip() or "\n" in s or "\r" in s for s in texts):
        out.append(f"rule 2: {rel}: a `[[discovery]]` text is not one plain question")
    return out


def discovery(path: Path) -> list[tuple[str, str]]:
    """The `(id, text)` pairs of a playbook's `[[discovery]]`, in its order; call on a playbook that
    `problems` passes."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return [(entry["id"], entry["text"]) for entry in data["discovery"]]


def _tokens(root: Path) -> list[str]:
    """The lower-case tokens of the project's neutrality list; none when it has no list."""
    try:
        text = (Path(root) / NEUTRALITY).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    lines = (line.strip() for line in text.splitlines())
    return [line.lower() for line in lines if line and not line.startswith("#")]


def _skill_problem(name: str, tokens: list[str]) -> str | None:
    """Why SPEC-0048 rule 12 refuses a skill name, naming the rule and never the value."""
    if not SLUG.fullmatch(name):
        return "a `skills` name is not a lower-case slug"
    if any(token in name for token in tokens):
        return f"a `skills` name holds a token of {NEUTRALITY}"
    return None


def _skills(rel: str, names: list[str], root: Path) -> list[str]:
    tokens = _tokens(root)
    found = {why for name in names if (why := _skill_problem(name, tokens))}
    return [f"rule 12: {rel}: {why} (SPEC-0048 rule 12; key: skills)" for why in sorted(found)]


def skills(path: Path, root: Path) -> list[str]:
    """SPEC-0048 rule 12: the allowed names of a playbook's `skills`, in its order; none from a file
    that is not TOML or has no such list. A refused name is left out, so no reader prints it."""
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return []
    names = data.get("skills", [])
    if not _is(names, STRS):
        return []
    tokens = _tokens(root)
    return [name for name in names if _skill_problem(name, tokens) is None]


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
        elif key not in TOP and key not in OPTIONAL_TOP:
            out.append(f"rule 2 and rule 4: {rel}: the playbook has a key outside the format")
    for key, kind in TOP.items():
        if key not in data:
            out.append(f"rule 2: {rel}: the playbook is missing `{key}`")
        elif not _is(data[key], kind):
            out.append(f"rule 2: {rel}: `{key}` has the wrong type")
    for key, kind in OPTIONAL_TOP.items():
        if key in data and not _is(data[key], kind):
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
    if _is(data.get("discovery"), TABLES):
        out += _discovery(rel, data["discovery"])
    if _is(data.get("skills"), STRS):
        out += _skills(rel, data["skills"], root)
    out += _named(rel, data)
    return out


def playbooks(root: Path) -> list[Path]:
    """The playbook files of a repository, sorted."""
    folder = Path(root) / FOLDER
    return sorted(folder.glob("*.toml")) if folder.is_dir() else []


def _declared(root: Path) -> tuple[str | None, str | None]:
    """The declared work type and the problem of the declaration (one at most); (None, None) when
    nothing is declared."""
    where = f"rule 5: {CONFIG}:"
    path = Path(root) / CONFIG
    if not path.is_file():
        return None, None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None, f"{where} the file is not TOML (setting: {WORK_TYPE})"
    if DELIVERY not in data:
        return None, None
    table = data[DELIVERY]
    if not isinstance(table, dict):
        return None, f"{where} `[{DELIVERY}]` is not a table (setting: {DELIVERY})"
    if any(key != WORK_TYPE for key in table):
        return None, f"{where} `[{DELIVERY}]` holds another key (setting: {DELIVERY})"
    if WORK_TYPE not in table:
        return None, None
    value = table[WORK_TYPE]
    if not isinstance(value, str):
        # Q-S0038-1: one work type per project; a list of two is refused like any other type.
        return None, f"{where} `{WORK_TYPE}` is not one work type (setting: {WORK_TYPE})"
    if value not in WORK_TYPES:
        return None, f"{where} `{WORK_TYPE}` is not one of the work types (setting: {WORK_TYPE})"
    if not (Path(root) / FOLDER / f"{value}.toml").is_file():
        return None, (
            f"{where} `{WORK_TYPE}` names a work type whose playbook is missing under {FOLDER}/ "
            f"(setting: {WORK_TYPE})"
        )
    return value, None


def declaration(root: Path) -> tuple[str | None, list[str]]:
    """SPEC-0038 rule 5: the declared work type (None when there is none or it is refused) and the
    problems of the declaration, each naming the rule, the file and the setting, never a value."""
    value, problem = _declared(root)
    return value, [problem] if problem else []


def selected(root: Path) -> Path | None:
    """The playbook the declaration selects, `config/playbooks/<work type>.toml`, or None."""
    value, _ = _declared(root)
    return Path(root) / FOLDER / f"{value}.toml" if value else None


# SPEC-0038 rule 7: the meaning of each milestone shape, in the rule's words.
SHAPE_MEANING = {
    "per-brief": "one pull request per brief, as today",
    "per-phase": (
        "the briefs of a phase are numbered as one milestone in their titles; "
        "one pull request per brief, and a milestone groups pull requests and never merges them"
    ),
    "per-batch": (
        "the briefs of a batch are numbered as one milestone in their titles; "
        "one pull request per brief, and a milestone groups pull requests and never merges them"
    ),
}


def _blocks(data: dict, goal: str, only: str | None) -> list[str]:
    """One numbered block per kind of `brief_order` (or the one kind `only`): its title, `Kind:`,
    its `Depends-on:` lines ordered by `brief_order`, and its lane."""
    order: list[str] = data["split"]["brief_order"]
    pairs: list[list[str]] = data["split"]["depends_on"]
    lanes = {kind: lane["name"] for lane in data["lanes"] for kind in lane["kinds"]}
    out = []
    for number, kind in enumerate(order, start=1):
        if only is not None and kind != only:
            continue
        out.append(f"{number}. {goal}: {kind}" if goal else f"{number}. {kind}")
        out.append(f"   Kind: {kind}")
        earlier = sorted({e for later, e in pairs if later == kind}, key=order.index)
        out += [f"   Depends-on: #<{e} brief>" for e in earlier]
        out.append(f"   lane: {lanes.get(kind, 'none')}")
    return out


def split(root: Path, goal: str = "", kind: str | None = None) -> tuple[list[str], list[str]]:
    """SPEC-0038 rule 7: the lines `playbook.py split` prints and the problems that refuse it.

    With no declaration both are empty. A declaration or a playbook with a problem gives those
    problems and no lines; a `kind` outside `brief_order` gives one problem naming the key."""
    root = Path(root)
    work_type, problems_found = declaration(root)
    if problems_found:
        return [], problems_found
    if work_type is None:
        return [], []
    path = root / FOLDER / f"{work_type}.toml"
    rel = f"{FOLDER}/{work_type}.toml"
    found = problems(path, root)
    if found:
        return [], found
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if kind is not None and kind not in data["split"]["brief_order"]:
        return [], [f"rule 7: {rel}: the kind is not in `brief_order` (key: brief_order)"]
    shape = data["milestones"]["shape"]
    lines = [
        f"work type: {work_type} (playbook {rel})",
        f"milestone shape: {shape} (batch_by: {data['milestones']['batch_by']})",
        f"   {SHAPE_MEANING[shape]}",
    ]
    return lines + _blocks(data, goal.strip(), kind), []
