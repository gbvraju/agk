# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
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

The foundation kind (SPEC-0072 rule 4; REQ-079 AC3; brief #1587, ADR-0667): every shipped
`brief_order` starts with `foundation`; in the split, a kind that no `depends_on` pair orders after
another depends on `foundation` when the order holds it, so every other kind follows it.

The discovery questions (SPEC-0048 rule 4, SPEC-0038 rule 2 as amendment 130 widens it; REQ-055
AC2; brief #686): every playbook holds `[[discovery]]` entries (`id`, a lower-case slug, and `text`,
one plain question) with at least the five ids of `DISCOVERY_IDS`, each id once; `discovery(path)`
returns the `(id, text)` pairs of a playbook in its order.

The skills a playbook names (SPEC-0048 rule 12; REQ-055 AC6; brief #691): the optional key `skills`
is a list of names, each matching doctor's `ENGINE_NAME`, and none holds a token of
`config/neutrality.txt` (Q-S0048-16); a problem names the rule, the file and the key, never the
value. `skills(path, root)` returns the allowed names of a playbook in its order, for doctor.

The base playbook (SPEC-0048 rule 21; REQ-055 AC8; brief #692): `BASE` is a playbook name and never
a work type. `config/playbooks/default.toml` alone may carry it, and `declaration` refuses it as it
refuses any name outside `WORK_TYPES`.

A derived playbook (SPEC-0048 rule 22; REQ-055 AC8; brief #694): a name outside `WORK_TYPES` is
derived only when it is the slug of a research record, `docs/research/<slug>.md`; each gate of its
own carries `source`, `<URL> (accessed YYYY-MM-DD)`, or `basis = "expected"`, and a gate of a
shipped playbook carries neither. Any other unknown name stays refused by rule 1.

The modules a playbook names (SPEC-0048 rule 23; REQ-055 AC8; brief #693): the optional key
`modules` is a list of shipped playbooks, each a name of `WORK_TYPES` whose file is under
`config/playbooks/`; one that is not shipped is a problem naming the rule, the file and the key,
never the value. `modules(path, root)` returns the shipped names in their order, for
`check_playbooks.py`, which composes the gates.

The standard part (SPEC-0072 rules 1 and 2; REQ-079 AC1; brief #1585, ADR-0665): the optional
tables `[architecture]` (`layers` of `{ name, paths }`, `allow` of `{ from, to }` with an optional
`adr`) and `[[standards]]` (`stack`, `lint`, `format`, `type`, `config`, `rules = { tool, version,
codes }`), and the gate key `reason`. A playbook's own `[architecture]` puts each `[testing] map`
code in exactly one layer and holds no layer path that is not a map code; the base's one `src`
layer is exempt (it constrains nothing until a work type is set). One of the eight `ENTERPRISE`
gate ids restated as `judgement` needs a `reason` of at least `REASON_MIN` characters, and the
refusal names that fixed id, never a value; a `[[standards]]` stack is a `[[stack]]` name of
`config/stack-signals.toml` when that file is present.

The resolver (REQ-078; brief #1666, ADR-0697): `folder(root, name)`, `path(root, name)` and
`default_playbook(root)` give where a playbook is read from: the project's `config/playbooks/` in
the installed layout; in a clean project the project's own `<name>.toml` when it exists, else the
plugin's (`kit_root.plugin_root`). Every reader, the declaration check and the modules use them;
`playbooks(root)` still lists the project's own files alone.

A pack's playbook (SPEC-0077 rules 3 and 5; REQ-084; brief #2040, ADR-0844): `_pack_layer(path,
root)` asks the resolver for the file's layer; for a pack id (neither `agk-core` nor the project's)
each `[[phases]]`, `[[lanes]]`, `[[gates]]`, `[[claims]]`, `[[discovery]]` and `[[standards]]`
entry also takes `source` and `basis` (`PACK_KEYS`), and a present one is checked by rule 3: a
`source` that is not a URL and an access date, or a `basis` other than `expected` (a claim's
`basis` keeps its claim meaning, `Q-PS-1`). A missing one is `check_packs`'s line. The kit's and the
project's playbooks keep today's format; a nested table takes neither (`Q-PS-2`).
"""

from __future__ import annotations

import datetime
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from types import ModuleType

kit_root: ModuleType | None
try:
    import kit_root  # standalone, so no cycle (brief #1666)
except ImportError:  # a partial copy of the scripts (a test's stub project) reads its own folder
    kit_root = None
Refused = kit_root.Refused if kit_root is not None else RuntimeError

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
    "api-service",  # ADR-0682, brief #1602
)
BASE = "default"  # SPEC-0048 rule 21: a playbook every kind of work carries, never declared
FOLDER = "config/playbooks"
RUNS = "docs/runs/"
CONFIG = "agk.toml"
DELIVERY = "delivery"
WORK_TYPE = "work_type"

GATE_KINDS = ("check", "judgement")
SHAPES = ("per-brief", "per-phase", "per-batch")
BASES = ("measured", "expected")
# SPEC-0048 rule 22: a project's derived playbook, named by the slug of its research record.
RESEARCH = "docs/research"
DERIVED_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GATE_SOURCE = re.compile(r"^https?://\S+ \(accessed (\d{4}-\d{2}-\d{2})\)$")
DERIVED_GATE_KEYS: dict[str, str] = {"source": "str", "basis": "str"}
PACK_KEYS = DERIVED_GATE_KEYS  # SPEC-0077 rule 3: a pack's entry, the same two keys (ADR-0844)
PACK_SECTIONS = ("phases", "lanes", "gates", "claims", "discovery")
SPEC77 = "SPEC-0077 rule 3"
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
# Brief #1933 (ADR-0801): the ten common topic ids, which `front_door.TOPICS` and `engines.TOPICS`
# mirror (a test pins all three equal); a grill id never reuses one.
TOPIC_IDS = (
    "users",
    "existing",
    "runs",
    "data",
    "scale",
    "compliance",
    "devices",
    "accessibility",
    "languages",
    "brand",
)
# SPEC-0073 rule 3 (amendment 237 item 1): a `[[discovery]]` entry with `depth` and `critical` is a
# grill item; the depths in order, each asking the items of the ones before it.
GRILL_DEPTHS = ("light", "standard", "deep")
GRILL_KEYS = ("depth", "critical")
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
# SPEC-0048 rule 12: a playbook may name skills; rule 23: and shipped playbooks as modules
OPTIONAL_TOP: dict[str, str] = {
    "skills": STRS,
    "modules": STRS,
    "architecture": "table",  # SPEC-0072 rule 2
    "standards": TABLES,
}
# section -> (required keys, optional keys), each key with its type
SECTIONS: dict[str, tuple[dict[str, str], dict[str, str]]] = {
    "phases": ({"name": STR, "order": INT, "after": STRS}, {}),
    "split": ({"brief_order": STRS, "depends_on": PAIRS}, {}),
    "lanes": ({"name": STR, "kinds": STRS}, {}),
    "testing": ({"profile": STR, "always_full": STRS, "map": TABLES}, {}),
    "gates": (
        {"id": STR, "kind": STR, "text": STR, "owner_only": BOOL},
        {"step": STR, "reason": STR},  # SPEC-0072 rule 2: `reason`
    ),
    "milestones": ({"shape": STR, "batch_by": STR}, {}),
    # `basis` is required by rule 3 and `record` by rule 3 for a measured claim
    "claims": ({"text": STR}, {"basis": STR, "record": STR}),
    "discovery": ({"id": STR, "text": STR}, {"depth": STR, "critical": BOOL}),
}
MAP_KEYS = {"code": STR, "tests": STR}
# SPEC-0072 rule 2: the eight enterprise gates, fixed ids of the kit, so a refusal may name them.
ENTERPRISE = (
    "sign-in-permissions",
    "secrets",
    "input-validation",
    "logging-tracing",
    "environment-settings",
    "migrations",
    "accessibility",
    "performance",
)
REASON_MIN = 20
STACKS = "config/stack-signals.toml"
SPEC72 = "SPEC-0072 rule 2"
FOUNDATION = "foundation"  # SPEC-0072 rule 4: the first kind of every `brief_order`
ARCH_KEYS = ({"layers": TABLES}, {"allow": TABLES})
LAYER_KEYS = {"name": STR, "paths": STRS}
ALLOW_KEYS = ({"from": STR, "to": STR}, {"adr": STR})
STANDARD_KEYS = {
    "stack": STR,
    "lint": STR,
    "format": STR,
    "type": STR,
    "config": STR,
    "rules": "table",
}
RULES_KEYS = {"tool": STR, "codes": STRS}
# brief #1764 (ADR-0739): optional, as a pack whose tools are the product's own pins names none
RULES_OPTIONAL = {"version": STR}
ADR_ID = re.compile(r"^ADR-\d{4}$")


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


def is_derived(name: str, root: Path) -> bool:
    """SPEC-0048 rule 22: a name outside the list that is the slug of a research record of `root`,
    so a mistyped work type with no record stays an unknown one (rule 1)."""
    return (
        name not in WORK_TYPES
        and name != BASE
        and DERIVED_NAME.match(name) is not None
        and (Path(root) / RESEARCH / f"{name}.md").is_file()
    )


def source_date(value: Any) -> datetime.date | None:
    """The access date of a gate's `source`, `<URL> (accessed YYYY-MM-DD)`, or None."""
    found = GATE_SOURCE.match(value) if isinstance(value, str) else None
    try:
        return datetime.date.fromisoformat(found.group(1)) if found else None
    except ValueError:
        return None


def source_dates(path: Path) -> list[datetime.date]:
    """SPEC-0048 rule 25: the access dates of the playbook's own gate sources; a file that cannot
    be read has none, and `problems` reports it."""
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return []
    gates = data.get("gates")
    if not isinstance(gates, list):
        return []
    dates = [source_date(g.get("source")) for g in gates if isinstance(g, dict)]
    return [when for when in dates if when is not None]


def _sourced(rel: str, gate: dict) -> list[str]:
    """SPEC-0048 rule 22: a gate of a derived playbook carries a dated source or `expected`."""
    if "source" not in gate and "basis" not in gate:
        return [f'rule 22: {rel}: a gate has neither `source` nor `basis = "expected"`']
    out = []
    if "source" in gate and source_date(gate["source"]) is None:
        out.append(f"rule 22: {rel}: a gate `source` is not a URL and an access date")
    if "basis" in gate and gate["basis"] != "expected":
        out.append(f"rule 22: {rel}: a gate `basis` is not expected")
    return out


def _provenance(rel: str, section: str, entry: dict) -> list[str]:
    """SPEC-0077 rule 3: the form of a pack entry's present provenance, never its value."""
    out = []
    if "source" in entry and source_date(entry["source"]) is None:
        out.append(
            f"{SPEC77}: {rel}: an entry `source` is not a URL and an access date (key: source)"
        )
    if section != "claims" and "basis" in entry and entry["basis"] != "expected":
        out.append(f"{SPEC77}: {rel}: an entry `basis` is not expected (key: basis)")
    return out


def _pack_layer(path: Path, root: Path) -> str | None:
    """SPEC-0077 rule 5: the pack id of the layer the resolver reads PATH from (a pack of
    `packs.used` whose manifest lists it under `playbooks/`, as `packs.files` reads it), else None:
    no resolver, no pack in use, a refused table or pack, the kit's or the project's own file."""
    packs = resolver()
    if packs is None:
        return None
    try:
        used = packs.used(Path(root))
    except packs.Refused:
        return None
    import check_packs  # here: check_packs imports this module

    want = Path(path).resolve()
    for pid, where in used:
        listed = (check_packs.load(where / check_packs.MANIFEST) or {}).get("files", {})
        names = [n for n in listed if n.startswith("playbooks/")]
        if any((where / n).resolve() == want for n in names):
            return pid
    return None


def _gates(rel: str, gates: list[dict], derived: bool = False) -> list[str]:
    out = []
    for gate in gates:
        if derived:
            out += _sourced(rel, gate)
        kind = gate.get("kind")
        if isinstance(kind, str) and kind not in GATE_KINDS:
            out.append(f"rule 2: {rel}: a gate `kind` is not check or judgement")
        if kind == "check" and "step" not in gate:
            out.append(f"rule 2: {rel}: a check gate has no `step`")
        reason = gate.get("reason")
        short = not isinstance(reason, str) or len(reason.strip()) < REASON_MIN
        if gate.get("id") in ENTERPRISE and kind == "judgement" and short:
            out.append(
                f"{SPEC72}: {rel}: an enterprise gate is judgement without a reason of "
                f"{REASON_MIN} characters (gate: {gate['id']}, key: reason)"
            )
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


def _grill(rel: str, entries: list[dict], base: set[str]) -> list[str]:
    """SPEC-0073 rule 3, amendment 237 item 1: each grill item's two keys and its id, which reuses
    no topic, fixed or other `[[discovery]]` id, nor (BASE) a grill id of `default.toml`; each
    refusal names the playbook and the key, never a value."""
    out = []
    found = [e.get("id") for e in entries]
    items = [e for e in entries if any(k in e for k in GRILL_KEYS)]
    where = f"rule 2: {rel}: a grill item"
    for key in GRILL_KEYS:
        if any(key not in e for e in items):
            out.append(f"{where} has one of `depth` and `critical` only (key: {key})")
    if any("depth" in e and e["depth"] not in GRILL_DEPTHS for e in items):
        out.append(f"{where}'s depth is not light, standard or deep (key: depth)")
    if any("critical" in e and not isinstance(e["critical"], bool) for e in items):
        out.append(f"{where}'s critical is not a boolean (key: critical)")
    ids = [e.get("id") for e in items]
    if any(i in TOPIC_IDS or i in DISCOVERY_IDS or found.count(i) > 1 for i in ids):
        out.append(f"{where}'s id reuses a topic, fixed or other `[[discovery]]` id (key: id)")
    if any(i in base for i in ids):
        out.append(f"{where}'s id reuses a grill id of {BASE}.toml (key: id)")
    return out


def _base_grill_ids(root: Path) -> set[str]:
    """The grill ids of `default.toml` (by `folder`); none when it is missing or does not parse."""
    found = default_playbook(root)
    if found is None:
        return set()
    try:
        return {i for i, *_ in grill_items(found)}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError):
        return set()


def discovery(path: Path) -> list[tuple[str, str]]:
    """The `(id, text)` pairs of a playbook's `[[discovery]]` questions, in its order, leaving out
    its grill items (brief #1933); call on a playbook that `problems` passes."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return [(e["id"], e["text"]) for e in data["discovery"] if "depth" not in e]


def grill_items(path: Path) -> list[tuple[str, str, str, bool]]:
    """SPEC-0073 rule 3: the `(id, text, depth, critical)` of a playbook's grill items, in its
    order; call on a playbook that `problems` passes."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("discovery", [])
    return [(e["id"], e["text"], e["depth"], e["critical"]) for e in rows if "depth" in e]


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


def resolver() -> ModuleType | None:
    """`packs` (SPEC-0077 rule 5, brief #2032), imported here so this module's own imports stay
    those of the standing import ruling (ADR-0824); None in a partial copy of the scripts."""
    try:
        import packs
    except ImportError:
        return None
    return packs if kit_root is not None else None


def folder(root: Path, name: str | None = None) -> Path:
    """The folder a playbook is read from (brief #1666, ADR-0697): the folder of the last layer of
    `packs.files` (SPEC-0077 rule 5, brief #2032) that holds `<name>.toml`, so the project's
    when it holds one, else a pack's in use, else the kit's; with none the project's in the
    installed layout and the plugin's in a clean one. A derived name (`is_derived`) is the
    project's alone in both layouts (brief #1908, ADR-0790, SPEC-0048 rule 22). Raises
    `kit_root.Refused` and `packs.Refused`, whose line names the setting."""
    own = Path(root) / FOLDER
    packs = resolver()
    if kit_root is None or packs is None or (name and is_derived(name, root)):
        return own
    try:
        found = packs.files(Path(root), "playbooks")
    except Refused:  # a clean project with no plugin: its own file still reads, as before
        if name and (own / f"{name}.toml").is_file():
            return own
        raise
    held = [p.parent for _, p in found if p.stem == name]
    if held:
        return held[-1]
    return (
        own
        if kit_root.layout(Path(root)) != "plugin"
        else kit_root.plugin_root(Path(root)) / FOLDER
    )


def clean(root: Path) -> bool:
    """A clean-layout project, or one whose `[kit] layout` is refused (never read as installed)."""
    try:
        return kit_root is not None and kit_root.layout(Path(root)) == "plugin"
    except Refused:
        return True


def path(root: Path, name: str) -> Path:
    """The playbook file of `name` by `folder`; the project's own path when it is refused."""
    try:
        return folder(root, name) / f"{name}.toml"
    except Refused:
        return Path(root) / FOLDER / f"{name}.toml"


def default_playbook(root: Path) -> Path | None:
    """`default.toml` by `folder`, or None when it is found in neither place."""
    found = path(root, BASE)
    return found if found.is_file() else None


def _shipped(name: str, root: Path) -> bool:
    """SPEC-0048 rule 23: a module is a work type of the list whose playbook is on disk."""
    return name in WORK_TYPES and path(root, name).is_file()


def _modules(rel: str, names: list[str], root: Path) -> list[str]:
    if all(_shipped(name, root) for name in names):
        return []
    return [f"rule 23: {rel}: `modules` names a playbook that is not shipped (key: modules)"]


def modules(path: Path, root: Path) -> list[str]:
    """SPEC-0048 rule 23: the shipped names of a playbook's `modules`, in its order; none from a
    file that is not TOML or has no such list. One that is not shipped is left out."""
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return []
    names = data.get("modules", [])
    if not _is(names, STRS):
        return []
    return [name for name in names if _shipped(name, root)]


def load(path: Path) -> dict[str, Any]:
    """The playbook at `path`, or an empty table when it cannot be read: `problems` reports it."""
    try:
        return tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return {}


def _inside(path: str) -> bool:
    """A relative path inside the project, written with forward slashes."""
    pure = PurePosixPath(path)
    return bool(path) and "\\" not in path and not pure.is_absolute() and ".." not in pure.parts


def _architecture(rel: str, data: dict, root: Path) -> list[str]:
    """SPEC-0072 rule 2: the form of `[architecture]` and its fit to the `[testing] map`."""
    arch = data["architecture"]
    where = f"{SPEC72}: {rel}:"
    out = _table_keys(rel, "[architecture]", arch, *ARCH_KEYS)
    layers = arch.get("layers") if _is(arch.get("layers"), TABLES) else []
    allow = arch.get("allow") if _is(arch.get("allow"), TABLES) else []
    for layer in layers:
        out += _table_keys(rel, "an `[architecture]` layer", layer, LAYER_KEYS, {})
    for entry in allow:
        out += _table_keys(rel, "an `[architecture]` allow entry", entry, *ALLOW_KEYS)
    names = [layer["name"] for layer in layers if isinstance(layer.get("name"), str)]
    paths = [p for layer in layers if _is(layer.get("paths"), STRS) for p in layer["paths"]]
    if any(not SLUG.match(n) for n in names) or len(set(names)) != len(names):
        out.append(f"{where} a layer name is not a slug or is twice (key: architecture.layers)")
    if any(not _inside(p) for p in paths):
        out.append(f"{where} a layer path is not inside the project (key: architecture.layers)")
    ends = [(e.get("from"), e.get("to")) for e in allow]
    if any(a not in names or b not in names or a == b for a, b in ends):
        out.append(f"{where} an `allow` entry names an unknown layer (key: architecture.allow)")
    if any("adr" in e and not ADR_ID.match(str(e["adr"])) for e in allow):
        out.append(f"{where} an `allow` entry `adr` is not an ADR id (key: architecture.allow)")
    work_type = data.get("work_type")
    derived = isinstance(work_type, str) and is_derived(work_type, root)
    if work_type not in WORK_TYPES and not derived:
        return out  # the base (it constrains nothing), or a name rule 1 already refuses
    testing = data.get("testing")
    entries = testing.get("map") if isinstance(testing, dict) else None
    codes = [e["code"] for e in entries or [] if isinstance(e, dict) and _is(e.get("code"), STR)]
    if any(paths.count(code) != 1 for code in codes):
        out.append(f"{where} a `[testing] map` code is in no layer (key: architecture.layers)")
    if any(p not in codes for p in paths):
        out.append(f"{where} a layer path is no `[testing] map` code (key: architecture.layers)")
    return out


def stacks(root: Path) -> list[str] | None:
    """The `[[stack]]` names of `config/stack-signals.toml`, or None when the file is absent; a
    clean project's table is the plugin's (brief #1826, ADR-0759). Raises `kit_root.Refused`."""
    found = Path(root)
    path = found / STACKS if kit_root is None else kit_root.kit_file(found, STACKS)
    if not path.is_file():
        return None
    rows = load(path).get("stack")
    if not isinstance(rows, list):
        return []
    return [r["name"] for r in rows if isinstance(r, dict) and isinstance(r.get("name"), str)]


def _standards(rel: str, entries: list[dict], root: Path, pack: bool = False) -> list[str]:
    """SPEC-0072 rule 2: each `[[standards]]` entry's form, a known stack once, a relative
    config; a pack's entry also takes rule 3's provenance (SPEC-0077, ADR-0844)."""
    where = f"{SPEC72}: {rel}:"
    out = []
    for entry in entries:
        extra = PACK_KEYS if pack else {}
        out += _table_keys(rel, "a `[[standards]]` entry", entry, STANDARD_KEYS, extra)
        out += _provenance(rel, "standards", entry) if pack else []
        if _is(entry.get("rules"), "table"):
            rules = entry["rules"]
            out += _table_keys(rel, "a `[[standards]]` `rules`", rules, RULES_KEYS, RULES_OPTIONAL)
    found = [e["stack"] for e in entries if isinstance(e.get("stack"), str)]
    known = stacks(root)
    if known is not None and any(name not in known for name in found):
        out.append(f"{where} a `[[standards]]` stack is not a stack of {STACKS} (key: standards)")
    if len(set(found)) != len(found):
        out.append(f"{where} a `[[standards]]` stack appears twice (key: standards)")
    if any(isinstance(e.get("config"), str) and not _inside(e["config"]) for e in entries):
        out.append(f"{where} a `[[standards]]` config is not inside the project (key: standards)")
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
    derived = isinstance(work_type, str) and is_derived(work_type, root)
    pack = _pack_layer(path, root) is not None  # SPEC-0077 rule 3 (brief #2040, ADR-0844)
    if isinstance(work_type, str):
        if work_type not in WORK_TYPES and work_type != BASE and not derived:
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
        if section == "gates" and derived:
            optional = {**optional, **DERIVED_GATE_KEYS}
        listed = pack and section in PACK_SECTIONS and isinstance(value, list)
        if listed:
            optional = {**PACK_KEYS, **optional}  # a claim's `basis` keeps its type (Q-PS-1)
        tables = value if isinstance(value, list) else [value]
        where = f"[{section}]" if isinstance(value, dict) else f"a [[{section}]] entry"
        for table in tables:
            out += _table_keys(rel, where, table, required, optional)
            out += _provenance(rel, section, table) if listed and isinstance(table, dict) else []
    if _is(data.get("phases"), TABLES):
        out += _phases(rel, data["phases"])
    out += _kinds(rel, data)
    if _is(data.get("testing"), "table"):
        out += _testing(rel, data["testing"])
    if _is(data.get("gates"), TABLES):
        out += _gates(rel, data["gates"], derived)
    milestones = data.get("milestones")
    if isinstance(milestones, dict) and isinstance(milestones.get("shape"), str):
        if milestones["shape"] not in SHAPES:
            out.append(f"rule 2: {rel}: `[milestones] shape` is not a known shape")
    if _is(data.get("claims"), TABLES):
        out += _claims(rel, data["claims"], root)
    if _is(data.get("discovery"), TABLES):
        out += _discovery(rel, data["discovery"])
        base = set() if work_type == BASE else _base_grill_ids(root)
        out += _grill(rel, data["discovery"], base)
    if _is(data.get("skills"), STRS):
        out += _skills(rel, data["skills"], root)
    if _is(data.get("modules"), STRS):
        out += _modules(rel, data["modules"], root)
    if _is(data.get("architecture"), "table"):
        out += _architecture(rel, data, root)
    if _is(data.get("standards"), TABLES):
        out += _standards(rel, data["standards"], root, pack)
    out += _named(rel, data)
    return out


def playbooks(root: Path) -> list[Path]:
    """The playbook files of a repository, sorted, then those of each pack in use (SPEC-0077
    rule 5): the kit's own in a clean project are the plugin's, not the repository's."""
    own = Path(root) / FOLDER
    packs = resolver()
    if packs is None:
        return sorted(own.glob("*.toml")) if own.is_dir() else []
    found = packs.files(Path(root), "playbooks", core=own)
    return [p for layer, p in found if layer == packs.CORE] + [
        p for layer, p in found if layer not in (packs.CORE, packs.PROJECT)
    ]


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
    # brief #1908 (ADR-0790): a derived playbook's slug, by the one test `problems` uses
    if value not in WORK_TYPES and not is_derived(value, root):
        return None, f"{where} `{WORK_TYPE}` is not one of the work types (setting: {WORK_TYPE})"
    try:
        found = folder(root, value) / f"{value}.toml"
    except Refused as exc:
        return None, str(exc)
    if not found.is_file():
        return None, (
            f"{where} `{WORK_TYPE}` names a work type whose playbook is missing under {FOLDER}/ "
            f"(setting: {WORK_TYPE})"
        )
    return value, None


def declaration(root: Path) -> tuple[str | None, list[str]]:
    """SPEC-0038 rule 5: the declared work type (None when there is none or it is refused) and the
    problems of the declaration, each naming the rule, the file and the setting, never a value."""
    value, problem = _declared(root)
    problem = problem or layout_problem(root)  # brief #1666: a refused layout, declared or not
    return value, [problem] if problem else []


DISCOVERY = "docs/discovery"
DISCOVERED = re.compile(r"^- Work type: ([a-z-]+) \(proposed\)$", re.M)


def discovered_work_types(root: Path) -> dict[str, list[str]]:
    """Brief #1757 (ADR-0735): each work type other than `pilot` that a discovery document
    names, with the documents that name it."""
    found: dict[str, list[str]] = {}
    for path in sorted((Path(root) / DISCOVERY).glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for kind in DISCOVERED.findall(text):
            if kind in WORK_TYPES and kind != "pilot":
                found.setdefault(kind, []).append(f"{DISCOVERY}/{path.name}")
    return found


def layout_problem(root: Path) -> str | None:
    """`kit_root.layout`'s refusal of `[kit] layout`, naming the setting, or None."""
    try:
        if kit_root is not None:
            kit_root.layout(Path(root))
    except Refused as exc:
        return str(exc)
    return None


def selected(root: Path) -> Path | None:
    """The playbook the declaration selects, `<work type>.toml` by `folder`, or None."""
    value, _ = _declared(root)
    return path(root, value) if value else None


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
        if not earlier and kind != FOUNDATION and FOUNDATION in order:  # SPEC-0072 rule 4
            earlier = [FOUNDATION]
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
    book = path(root, work_type)
    rel = f"{FOLDER}/{work_type}.toml"
    found = problems(book, root)
    if found:
        return [], found
    data = tomllib.loads(book.read_text(encoding="utf-8"))
    if kind is not None and kind not in data["split"]["brief_order"]:
        return [], [f"rule 7: {rel}: the kind is not in `brief_order` (key: brief_order)"]
    shape = data["milestones"]["shape"]
    lines = [
        f"work type: {work_type} (playbook {rel})",
        f"milestone shape: {shape} (batch_by: {data['milestones']['batch_by']})",
        f"   {SHAPE_MEANING[shape]}",
    ]
    return lines + _blocks(data, goal.strip(), kind), []
