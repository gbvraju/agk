"""The plan's proposals, validated and rendered (SPEC-0043 rules 3 to 7). Installed:
`kit/manifest.json` lists it in `verbatim`. Build (c1) of SPEC-0043 rule 27 (amendment 163,
ADR-0456), build (c2), `render` (ADR-0461), build (i), `publish` (ADR-0459), build (p), personas
and user stories (amendment 164 item 2, ADR-0462), and build (r), shared components and demoable
slices (amendment 164 items 3 and 4, ADR-0464), and build (a) of brief #1109, an OpenSpec file
(amendment 166 items 2 to 4, ADR-0472, ADR-0473).

    python3 plan_intake.py validate --proposals FILE [--root DIR]
    python3 plan_intake.py states [--root DIR]
    python3 plan_intake.py render --proposals FILE [--root DIR]
    python3 plan_intake.py publish --comments FILE --head SHA [--numbers FILE] [--root DIR]
    python3 plan_intake.py openspec-import PATH --slug SLUG [--root DIR]
    python3 plan_intake.py openspec --slug SLUG --out FILE [--root DIR]

Rule 3: every command exits 2 with `data guard not installed: <path>` when `scripts/agk/guard.py` or
`.claude/hooks/data_guard.py` is absent, and runs `guard.scan_text` on the whole text of every
source before it reads a line of one; a finding refuses with exit 1, naming the file, the kind and
`line <l>, column <c>`, never the matched text. Rules 4 to 6: `validate` prints `ok proposals` or
one line per problem naming the rule and the item's `key` or `id`, never its text. `states` prints
the inventory's `yes` states that no `<screen>/<state>` heading of a `Kind: design` source covers
(amendment 163 item 5). Build (p): the proposals hold `personas` (`P1`, `P2`, ... in order, each
with a `name`, non-empty `goals` and `sources`), and each requirement names its `persona` and one
`story` `As <the persona's name>, I want <capability>, so that <outcome>`, whose form only is
checked (`Q-1089-4`). Build (r): the proposals may hold `components` (`C1`, `C2`, ... in order, each
with two or more inventory `screens`, a `pattern` or null, and exactly one brief in `M1 Foundation`
whose `component` names it); a brief whose `screens` use a component names that brief in
`depends_on`. While a `Kind: design` source has a `<screen>/<state>` heading, every milestone after
`M1` has `screens`, its `exit` names `design_compare.py`, `match` and a signed-off version, and
every such heading is in a milestone's `screens`. Rule 7: `render` runs `validate` first, prints
every conflict under `Conflicts for the person` and then every open question under `Open questions
for the person`, and writes, as new files only and all or nothing, `docs/plan/scope.md`,
`docs/plan/personas.md`, `docs/plan/milestones.md`, `docs/plan/requirements-proposed.md` (each block
with its `Persona:` and `Story:` lines before its criteria; a milestone's `Demo:` line after its
`Exit:` and a brief's `Screens: <version> ...` line, build (r)), one Draft spec per area
(`new_spec.make_spec`, imported from the copy beside this script, installed or the plugin's) and
`docs/plan/briefs/M<n>/<key>.md`; it never edits `docs/requirements.md`. With a design source it
prints the declared playbook's `batch_by` as `Milestone order for the person: ...`
(`playbook_format`). Rules 8 and 25: `publish` exits 2 without `Approve: plan <--head>` by an
account of `spec_approvers` in the saved comments (`reviewers.plan_approvals`), refuses a brief that
`check_brief.py --root .` fails, and prints one `gh api` command per milestone and per brief, briefs
in `depends_on` order, each withheld until `--numbers` gives its milestone's and its dependences'
numbers; it runs none. In personal mode it writes the briefs through `forge.FilesForge`. Brief #1195
(ADR-0507): each brief issue shows one `Persona: <key> <name>` line before its milestone line, the
persona of the requirements its `Advances:` names (their `requirements-proposed.md` block, else
their `docs/requirements.md` section), and none when no requirement names one.
Brief #1196 (ADR-0508): `render` writes each open question and unsettled conflict into the
`Questions for business` section of `docs/plan/scope.md` (`### <key>`, `Question:`, `Source:`,
`Blocks:` the keys that cite one of its locations); `publish` reads that section, prints before the
briefs one `gh label create` and one issue command per question not in `--numbers`, labelled
`agk-business-question`, and withholds a brief it blocks until its number, then adds
`Blocked-by: #<n>` to the brief issue.

Amendment 166 (ADR-0473): `openspec-import` copies a combined OpenSpec `.md` file, or an `openspec/`
folder that holds `specs/` (its `.md` and `.txt` files; any other is printed `skipped:`), under
`docs/sources/openspec-<slug>/`, each file the rule 1 header (`Kind: openspec`, `Version:
sha256:<digest of the original>`), a blank line and the original bytes unchanged; never over an
existing folder, and only after `guard.scan_text` passed every file. `openspec` (also
`openspec-draft`) reads that folder by script into a proposals file outside `docs/` that `validate`
accepts: a capability is one area, a `Requirement: ` heading one requirement (its `statement` the
text exactly, `changing` when its change is open), a `Scenario: ` heading one criterion `Given ...,
when ..., then ... (<location>)`; `milestone` is null for the skill to set, the actor that starts a
`WHEN` step is a persona with `(verify)` goals, and what the file leaves open is an open question.
A heading it does not read inside a capability is printed `ignored: <file>:<line>`. Files only: no
network, no model; only `render`, personal `publish` and the two OpenSpec commands write.

Amendment 167 (brief #1118, ADR-0478): a criterion names the rules it proves with `(rules r1, r2)`,
each sentence of its requirement's `statement` holding `SHALL` one rule (`check_plan.rules_of`),
and `validate` refuses a mark naming a rule the statement does not hold. The proposals may hold
`access`, cells `{persona, screen, allowed, sources}` keyed `<persona>/<screen>`: a persona key, a
screen of `docs/design/inventory.md`, `yes` or `no`, and at least one source (a cell without one
is an open question, never a guess). A criterion names a cell with `(access <persona>/<screen>)`;
each `no` cell needs one, its denial line, and a mark naming no cell is refused. `render` writes
`docs/plan/access.md` when `access` is not empty.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_plan
import design_import
import design_signoff
import playbook_format
from common import ESTIMATE_LINES, CheckError, repo_root, run

NAME = "plan-intake"
USAGE = (
    "usage: plan_intake.py validate --proposals FILE [--root DIR] | states [--root DIR]"
    " | render --proposals FILE [--root DIR]"
    " | publish --comments FILE --head SHA [--numbers FILE] [--root DIR]"
    " | openspec-import PATH --slug SLUG [--root DIR]"
    " | openspec --slug SLUG --out FILE [--root DIR]"
)
GUARDS = ("scripts/agk/guard.py", ".claude/hooks/data_guard.py")
# The pattern of `playbook.py check-start` (SPEC-0013 rule 5). playbook.py is kit-only, so it is
# kept here and a test holds the two equal (ADR-0456 decision 4).
MEASURABLE = re.compile(r"\d|\b(?:all|every|none|zero)\b", re.IGNORECASE)
VERIFY = "(verify)"
SCOPE = ("in", "out", "assumptions", "constraints", "open_questions")
TOP = ("schema", "scope", "personas", "milestones", "requirements", "areas", "briefs", "conflicts")
COMPONENTS = "components"  # build (r): optional, an empty list when absent (`Q-1092-1`)
ACCESS = "access"  # amendment 167 item 2: optional, as components is
SECTIONS = ("personas", COMPONENTS, *TOP[3:], ACCESS)
LIST, TEXT, LOCS, MAYBE = "list", "text", "locations", "text or null"
FIELDS = {
    "scope": ("key", "text", "sources"),
    "personas": ("key", "name", "goals", "sources"),
    COMPONENTS: ("key", "name", "screens", "pattern", "sources"),
    "milestones": ("id", "title", "exit", "acceptance", "target", "sources"),
    "requirements": ("key", "title", "criteria", "milestone", "persona", "story", "sources"),
    "areas": ("name", "requirements"),
    "briefs": ("key", "milestone", "title", "size", "expected", "advances", "touches")
    + ("depends_on", "sources"),
    "conflicts": ("locations", "description"),
    ACCESS: ("persona", "screen", "allowed", "sources"),
}
KINDS = {"sources": LOCS, "target": "date", "pattern": MAYBE} | dict.fromkeys(
    ("criteria", "requirements", "advances", "touches", "depends_on", "locations", "goals")
    + ("screens",),
    LIST,
)
NON_EMPTY = ("goals",)  # a list that holds at least one item, as `sources` does
OPTIONAL = {
    "conflicts": ("settled",),
    "milestones": ("screens",),
    "briefs": ("component", "screens"),
}
OPTIONAL["requirements"] = ("statement", "changing")  # amendment 166 (`Q-1108-1`, `Q-1108-2`)
KINDS |= {"statement": MAYBE, "changing": "true or false", "allowed": "yes or no"}
TYPED = ("component", "screens", "statement", "changing")  # optional keys whose type rule 4 checks
KEYED = {"personas": "P", COMPONENTS: "C"}  # keys run P1, P2, ... and C1, C2, ... in order
FOUNDATION = "Foundation"
ID = {"milestones": "id", "areas": "name"}
SETTLED = "Settled: "
STATE_HEADING = re.compile(r"^([^/]+)/([^/]+)$")
STORY_FORM = "As <the persona's name>, I want <capability>, so that <outcome>"
WANT, SO_THAT = ", I want ", ", so that "


def guard_missing(root: Path) -> str | None:
    return next((rel for rel in GUARDS if not (root / rel).is_file()), None)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def scan_problems(root: Path, extra: list[str]) -> list[str]:
    """Rule 3: `guard.scan_text` over every source, and every cited charter, before any is read."""
    import guard  # noqa: PLC0415 - here: only after the gate has found it installed

    rels = [p.relative_to(root).as_posix() for p in check_plan.source_files(root)]
    rels += sorted({rel for rel in extra if (root / rel).is_file()} - set(rels))
    out: list[str] = []
    for rel in rels:
        text = _read(root / rel)
        if text is None:
            out.append(f"rule 3: {rel}: not UTF-8 text, not scanned")
            continue
        for f in guard.scan_text(text):
            out.append(f"rule 3: {rel}: {f.kind} line {f.line}, column {f.column}")
    return out


def cited_text(root: Path, location: str) -> str:
    """The text a resolved location cites: its line, or the section under its heading."""
    rel, _, anchor = location.partition("#") if "#" in location else location.rpartition(":")
    lines = (_read(root / rel) or "").splitlines()
    if "#" not in location:
        return lines[int(anchor) - 1]
    charter = bool(check_plan.CHARTER_NAME.match(rel))
    out: list[str] = []
    inside = fenced = False
    for line in lines:
        fenced = fenced != bool(check_plan.FENCE.match(line))
        heading = None if fenced else check_plan.HEADING.match(line)
        item = check_plan.ITEM.match(line) if charter else None
        if (heading or item) and inside:
            break
        name = heading.group(1) if heading else item.group(1).strip().rstrip(".:") if item else None
        inside = inside or name == anchor
        if inside:
            out.append(line)
    return "\n".join(out)


def _sections(data: dict) -> list[str]:
    return [s for s in SECTIONS if s in data]


def _items(data: dict) -> list[tuple[str, str, dict]]:
    """(section, name, item) of every item of the proposals, scope by its five lists."""
    out: list[tuple[str, str, dict]] = []
    for section in ("scope", *_sections(data)):
        groups = [(f"scope.{n}", data["scope"][n]) for n in SCOPE] if section == "scope" else []
        for label, items in groups or [(section, data[section])]:
            kind = label.split(".")[0]
            for n, item in enumerate(items, start=1):
                name = str(n) if kind == "conflicts" else str(item.get(ID.get(kind, "key"), n))
                if kind == ACCESS:
                    name = f"{item.get('persona', n)}/{item.get('screen', n)}"
                out.append((label, name, item))
    return out


def shape_problems(data: object) -> list[str]:
    """Rule 4: the top level, then every item's keys and types."""
    if not isinstance(data, dict):
        return ["rule 4: the proposals file is not a JSON object"]
    out = [
        f"rule 4: proposals: unknown key {k}" for k in data if k not in (*TOP, COMPONENTS, ACCESS)
    ]
    missing = [f"rule 4: proposals: missing key {k}" for k in TOP if k not in data]
    if missing:
        return out + missing
    if data["schema"] != 1:
        out.append("rule 4: proposals: schema is not 1")
    scope = data["scope"]
    if not isinstance(scope, dict) or sorted(scope) != sorted(SCOPE):
        return [*out, "rule 4: proposals: scope holds exactly " + ", ".join(SCOPE)]
    lists = [scope[n] for n in SCOPE] + [data[k] for k in _sections(data)]
    if not all(isinstance(x, list) and all(isinstance(i, dict) for i in x) for x in lists):
        return [*out, "rule 4: proposals: every section is a list of objects"]
    for label, name, item in _items(data):
        kind = label.split(".")[0]
        fields, where = FIELDS[kind], f"rule 4: {label} {name}"
        known = (*fields, *OPTIONAL.get(kind, ()))
        out += [f"{where}: unknown key {k}" for k in item if k not in known]
        out += [f"{where}: missing key {k}" for k in fields if k not in item]
        for key in (*fields, *(k for k in TYPED if k in item and k in known)):
            # a requirement's milestone may be null until the skill sets it (amendment 166)
            unset = (kind, key) == ("requirements", "milestone")
            kind_of = MAYBE if unset else KINDS.get(key, TEXT)
            if key in item and not _typed(item[key], kind_of):
                out.append(f"{where}: {key} is not {kind_of}")
            elif (kind_of == LOCS or key in NON_EMPTY) and item.get(key) == []:
                out.append(f"{where}: {key} is empty")
        if kind == "conflicts" and isinstance(item.get("locations"), list):
            if len(item["locations"]) != 2:
                out.append(f"{where}: locations is not two locations")
        pairs = item.get("screens") if kind in ("milestones", "briefs") else None
        if isinstance(pairs, list) and not all(STATE_HEADING.match(str(p)) for p in pairs):
            out.append(f"{where}: screens is not <screen>/<state> pairs")
    for n, milestone in enumerate(data["milestones"], start=1):
        if milestone.get("id") != f"M{n}":
            out.append(f"rule 4: milestones {milestone.get('id', n)}: ids run M1, M2, ... in order")
    for section, letter in KEYED.items():
        seen: list[object] = []  # a repeated key is rule 4's `the key is repeated`, said once
        for item in data.get(section, []):
            if (key := item.get("key")) not in seen:
                seen.append(key)
                if key != f"{letter}{len(seen)}":
                    out.append(
                        f"rule 4: {section} {key}: keys run {letter}1, {letter}2, ... in order"
                    )
    first = data["milestones"][0] if data["milestones"] else {}
    if data.get(COMPONENTS) and first.get("id") == "M1" and first.get("title") != FOUNDATION:
        out.append(
            f"rule 4: milestones M1: title is not {FOUNDATION} while components is not empty"
        )
    return out


def _typed(value: object, kind: str) -> bool:
    if kind == "yes or no":
        return value in ("yes", "no")
    if kind == "true or false":
        return isinstance(value, bool)
    if kind == MAYBE:
        return value is None or _typed(value, TEXT)
    if kind == TEXT:
        return isinstance(value, str) and bool(value.strip())
    if kind == "date":
        return value is None or (isinstance(value, str) and check_plan.real_date(value))
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def _cycle(briefs: dict[str, list[str]]) -> set[str]:
    """The briefs on a `depends_on` cycle."""
    state: dict[str, int] = {}
    found: set[str] = set()

    def visit(key: str, path: list[str]) -> None:
        state[key] = 1
        for dep in briefs.get(key, []):
            if state.get(dep) == 1:
                found.update(path[path.index(dep) :] if dep in path else [dep])
            elif dep in briefs and dep not in state:
                visit(dep, [*path, dep])
        state[key] = 2

    for key in briefs:
        if key not in state:
            visit(key, [key])
    return found


def supported(root: Path, item: dict, pattern: str) -> bool:
    """Rule 6: one of the item's own resolved locations holds the value."""
    for loc in item["sources"]:
        if check_plan.location_problem(root, loc) is None and re.search(
            pattern, cited_text(root, loc)
        ):
            return True
    return False


def plan_problems(root: Path, data: dict) -> list[str]:
    """Rules 5 and 6 on a proposals file whose shape passed rule 4."""
    out: list[str] = []
    items = _items(data)
    names: dict[str, list[str]] = {}
    for label, name, item in items:
        names.setdefault(label.split(".")[0], []).append(name)
        for loc in item.get("sources", item.get("locations", [])):
            if (problem := check_plan.location_problem(root, loc)) is not None:
                out.append(f"rule 5: {label} {name}: {problem.removeprefix('rule 1: ')}")
    for label, keys in names.items():
        repeated = sorted({k for k in keys if keys.count(k) > 1})
        out += [f"rule 4: {label} {k}: the key is repeated" for k in repeated]
    if out:
        return out
    milestones, reqs = set(names.get("milestones", [])), set(names.get("requirements", []))
    personas = {p["key"]: p["name"] for p in data["personas"]}
    briefs = {b["key"]: b["depends_on"] for b in data["briefs"]}
    for m in data["milestones"]:
        if not MEASURABLE.search(m["exit"]):
            out.append(f"rule 5: milestones {m['id']}: exit is not measurable")
        if m["target"] is not None and not supported(root, m, re.escape(m["target"])):
            out.append(f"rule 6: open question: milestones {m['id']}: target {VERIFY}")
        if not any(b["milestone"] == m["id"] for b in data["briefs"]):
            out.append(f"rule 5: milestones {m['id']}: no brief")
    for r in data["requirements"]:
        if r["milestone"] is not None and r["milestone"] not in milestones:
            out.append(f"rule 5: requirements {r['key']}: milestone names nothing")
        out += story_problems(r, personas)
    for a in data["areas"]:
        if not set(a["requirements"]) <= reqs:
            out.append(f"rule 5: areas {a['name']}: requirements names nothing")
    cycle = _cycle(briefs)
    for b in data["briefs"]:
        where = f"briefs {b['key']}"
        for field, known in (("milestone", milestones), ("advances", reqs), ("depends_on", briefs)):
            if not set([b[field]] if field == "milestone" else b[field]) <= set(known):
                out.append(f"rule 5: {where}: {field} names nothing")
        if b["key"] in cycle:
            out.append(f"rule 5: {where}: depends_on makes a cycle")
        size = ESTIMATE_LINES["Size"].fullmatch(b["size"])
        expected = ESTIMATE_LINES["Expected"].fullmatch(b["expected"])
        if size is None:
            out.append(f"rule 5: {where}: size is not SPEC-0018's")
        elif not supported(root, b, rf"(?i:\bsize):?\s+{size.group(0)}\b"):
            out.append(f"rule 6: open question: {where}: size {VERIFY}")
        if expected is None or float(expected.group(1)) > float(expected.group(2)):
            out.append(f"rule 5: {where}: expected is not SPEC-0018's")
        elif not supported(root, b, re.escape(b["expected"])):
            out.append(f"rule 6: open question: {where}: expected {VERIFY}")
    for q in data["scope"]["open_questions"]:
        if VERIFY not in q["text"]:
            out.append(f"rule 6: scope.open_questions {q['key']}: no {VERIFY} mark")
    out += component_problems(root, data) + slice_problems(root, data)
    out += openspec_problems(root, data) + rule_problems(data) + access_problems(root, data)
    return out + conflict_problems(items)


def component_problems(root: Path, data: dict) -> list[str]:
    """Rule 5 with amendment 164 item 3: two or more inventory screens, exactly one brief in `M1`,
    and every brief whose `screens` use a component names that brief in `depends_on` directly
    (`Q-1089-3`)."""
    components = {c["key"]: c for c in data.get(COMPONENTS, [])}
    listed = {screen for screen, _ in design_import.inventory_states(root) or {}}
    brief_of: dict[str, str] = {}
    out: list[str] = []
    for key, c in components.items():
        where = f"rule 5: components {key}"
        if len(set(c["screens"])) < 2:
            out.append(f"{where}: screens names fewer than two screens")
        elif not set(c["screens"]) <= listed:
            out.append(f"{where}: screens names a screen the inventory does not list")
        own = [b for b in data["briefs"] if b.get("component") == key]
        if len(own) > 1:
            out.append(f"{where}: more than one brief")
        elif not own or own[0]["milestone"] != "M1":
            out.append(f"{where}: no brief in M1")
        else:
            brief_of[key] = own[0]["key"]
    for b in data["briefs"]:
        if "component" in b and b["component"] not in components:
            out.append(f"rule 5: briefs {b['key']}: component names nothing")
        used = {pair.partition("/")[0] for pair in b.get("screens", [])}
        where = f"rule 5: briefs {b['key']}: depends_on does not name"
        for key, dep in brief_of.items():
            if dep != b["key"] and used & set(components[key]["screens"]):
                if dep not in b["depends_on"]:
                    out.append(f"{where} {dep} of component {key}")
    return out


SIGNED = re.compile(r"\b[vi][1-9]\d*\b")
COMPARE, MATCH = "design_compare.py", re.compile(r"\bmatch\b")


def signed_versions(root: Path) -> list[str]:
    """The versions of the `design` rows of `docs/design/signoffs.md` in file order (rule 9)."""
    try:
        return [r["version"] for r in design_signoff.rows(root) if r["kind"] == "design"]
    except CheckError:
        return []


def slice_problems(root: Path, data: dict) -> list[str]:
    """Rule 5 with amendment 164 item 4, only while a `Kind: design` source has a
    `<screen>/<state>` heading: each later milestone a slice proved by `design_compare.py`, and
    every such heading in a milestone (`Q-1089-6`)."""
    headings = check_plan.screens(root)
    if not headings:
        return []
    pairs = {f"{s}/{state}" for s, state in design_import.inventory_states(root) or {}}
    signed = set(signed_versions(root))
    out: list[str] = []
    for n, m in enumerate(data["milestones"]):
        where = f"rule 5: milestones {m['id']}"
        if not m.get("screens"):
            out += [f"{where}: no screens"] if n else []
            continue
        exit_text = m["exit"]
        if (
            COMPARE not in exit_text
            or not MATCH.search(exit_text)
            or not set(SIGNED.findall(exit_text)) & signed
        ):
            out.append(f"{where}: exit does not name {COMPARE}, match and a signed-off version")
        if not set(m["screens"]) <= pairs:
            out.append(f"{where}: screens names a pair the inventory does not list")
    listed = {pair for m in data["milestones"] for pair in m.get("screens", [])}
    for heading in headings:
        if heading.partition("#")[2] not in listed:
            out.append(f"rule 5: {heading}: no milestone lists this screen and state")
    return out


def _loc_file(location: str) -> str:
    return location.partition("#")[0] if "#" in location else location.rpartition(":")[0]


def openspec_files(root: Path) -> set[str]:
    """The `Kind: openspec` sources of rule 1, by their paths."""
    return {
        p.relative_to(root).as_posix()
        for p in check_plan.source_files(root)
        if (check_plan.header(_read(p) or "") or {}).get("Kind") == OPENSPEC
    }


def openspec_problems(root: Path, data: dict) -> list[str]:
    """Rule 5 with amendment 166 item 3 and 4: a requirement cited to a `Kind: openspec` source
    keeps its statement; a criterion's closing location resolves; a `changing` requirement is in
    `M1` only with an open question that cites one of its locations (`Q-1108-2`)."""
    files = openspec_files(root)
    asked = {loc for q in data["scope"]["open_questions"] for loc in q["sources"]}
    out: list[str] = []
    for r in data["requirements"]:
        where = f"rule 5: requirements {r['key']}"
        if r.get("statement") is None and any(_loc_file(s) in files for s in r["sources"]):
            out.append(f"{where}: statement is null for a Kind: {OPENSPEC} source")
        for n, criterion in enumerate(r["criteria"], start=1):
            loc = _closing_location(criterion)
            if loc is not None and check_plan.location_problem(root, loc) is not None:
                out.append(f"{where}: criterion {n} ends with a location that does not resolve")
        if r.get("changing") is True and r["milestone"] == "M1" and not asked & set(r["sources"]):
            out.append(f"{where}: changing in M1 without an open question citing it")
    return out


def rule_problems(data: dict) -> list[str]:
    """Amendment 167 item 1: a criterion's `(rules ...)` mark names rules its statement holds."""
    out: list[str] = []
    for r in data["requirements"]:
        held = len(check_plan.rules_of(r.get("statement") or ""))
        for n, criterion in enumerate(r["criteria"], start=1):
            if any(int(rule[1:]) > held for rule in check_plan.marked_rules(criterion)):
                out.append(
                    f"rule 5: requirements {r['key']}: criterion {n} names a rule its statement "
                    "does not hold"
                )
    return out


def access_problems(root: Path, data: dict) -> list[str]:
    """Amendment 167 item 2: each cell names a persona and an inventory screen, each `no` cell
    has a denial line, and every `(access ...)` mark names a cell."""
    cells = data.get(ACCESS, [])
    personas = {p["key"] for p in data["personas"]}
    screens = {screen for screen, _ in design_import.inventory_states(root) or {}}
    marks = [
        (r["key"], n, cell)
        for r in data["requirements"]
        for n, criterion in enumerate(r["criteria"], start=1)
        for cell in check_plan.marked_cells(criterion)
    ]
    named = {cell for _, _, cell in marks}
    out: list[str] = []
    for c in cells:
        where = f"rule 5: access {c['persona']}/{c['screen']}"
        if c["persona"] not in personas:
            out.append(f"{where}: persona names nothing")
        if c["screen"] not in screens:
            out.append(f"{where}: screen names no screen of the inventory")
        if c["allowed"] == "no" and f"{c['persona']}/{c['screen']}" not in named:
            out.append(f"{where}: no without a denial acceptance line")
    held = {f"{c['persona']}/{c['screen']}" for c in cells}
    for key, n, cell in marks:
        if cell not in held:
            out.append(
                f"rule 5: requirements {key}: criterion {n} names an access cell the access "
                "table does not hold"
            )
    return out


def _closing_location(criterion: str) -> str | None:
    """The `(docs/...)` location a criterion ends with, or None."""
    start = criterion.rfind(" (docs/")
    if start < 0 or not criterion.endswith(")"):
        return None
    return criterion[start + 2 : -1]


def story_problems(r: dict, personas: dict[str, str]) -> list[str]:
    """Rule 5 with amendment 164 item 2: the persona names a persona, and the story's form only
    (`Q-1089-4`): `As <its name>, I want `, then `, so that ` after it."""
    where = f"rule 5: requirements {r['key']}"
    if r["persona"] not in personas:
        return [f"{where}: persona names nothing"]
    prefix = f"As {personas[r['persona']]}{WANT}"
    rest = r["story"][len(prefix) :] if r["story"].startswith(prefix) else ""
    if SO_THAT not in rest:
        return [f"{where}: story is not `{STORY_FORM}` with its persona's name"]
    return []


def conflict_problems(items: list[tuple[str, str, dict]]) -> list[str]:
    """Rule 6: an item citing both sides of a conflict the person has not settled."""
    out: list[str] = []
    for label, name, conflict in items:
        if label != "conflicts":
            continue
        settled = conflict.get("settled")
        if settled is not None:
            side = settled[len(SETTLED) :] if isinstance(settled, str) else None
            if not str(settled).startswith(SETTLED) or side not in conflict["locations"]:
                out.append(f"rule 6: conflicts {name}: settled names neither side")
            continue
        for kind, key, item in items:
            if kind in ("milestones", "requirements", "briefs"):
                if set(conflict["locations"]) <= set(item["sources"]):
                    out.append(f"rule 6: {kind} {key}: cites both sides of conflict {name}")
    return out


def validation(root: Path, proposals: Path) -> tuple[dict, list[str]]:
    """The proposals and what `validate` refuses in them (rules 3 to 6), in order."""
    inside = proposals.resolve().is_relative_to((root / "docs").resolve())
    try:
        data = json.loads(proposals.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        data = None
    problems = ["rule 4: the proposals file is outside docs/"] if inside else []
    problems += shape_problems(data)
    if not problems:
        charters = [i["sources"] for _, _, i in _items(data) if "sources" in i]
        cited = [loc.partition("#")[0] for locs in charters for loc in locs if "#" in loc]
        problems = scan_problems(root, cited) or plan_problems(root, data)
    return data, problems


def cmd_validate(root: Path, proposals: Path) -> int:
    _, problems = validation(root, proposals)
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print("ok proposals")
    return 0


# --- rule 7: render, once, as drafts the person owns (build (c2), ADR-0461) ----------------------

PLAN = "docs/plan"
SPEC_TEMPLATE = "docs/specs/TEMPLATE.md"
NEW_SPEC = "scripts/agk/new_spec.py"
FILE_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
HEADINGS = ("In scope", "Out of scope", "Assumptions", "Constraints", "Open questions")
SENTENCE_MAX = 300  # SPEC-0030 rule 4, `session.brief_problems`


def _one(text: str) -> str:
    return " ".join(str(text).split())


def _locs(sources: list[str]) -> str:
    return ", ".join(f"`{loc}`" for loc in sources)


def _sources(sources: list[str]) -> list[str]:
    return [f"Source: `{loc}`" for loc in sources]


def scope_text(data: dict) -> str:
    out = [
        "# Scope",
        "",
        "Drafted by `plan_intake.py render` (SPEC-0043 rule 7); the person owns it.",
    ]
    for name, heading in zip(SCOPE, HEADINGS, strict=True):
        out += ["", f"## {heading}", ""]
        items = data["scope"][name]
        out += [f"- {_one(i['text'])} ({_locs(i['sources'])})" for i in items] or ["- none"]
    questions = business_questions(data)
    out += ["", f"## {QUESTIONS_HEADING}"]
    for q in questions:
        out += ["", f"### {q['key']}", "", f"Question: {q['question']}"]
        out += [f"Source: {_locs(q['sources'])}", f"Blocks: {', '.join(q['blocks']) or 'none'}"]
    out += [] if questions else ["", "- none"]
    return "\n".join(out) + "\n"


QUESTIONS_HEADING = "Questions for business"  # brief #1196 (ADR-0508): what publish reads
CONFLICT_KEY = "conflict-{}"


def _blocks(data: dict, sources: list[str]) -> list[str]:
    """Brief #1196 answer 1: the requirements that cite one of SOURCES, then the briefs that cite
    one or advance such a requirement, by key."""
    cited = set(sources)
    reqs = [r["key"] for r in data["requirements"] if cited & set(r["sources"])]
    briefs = [
        b["key"]
        for b in data["briefs"]
        if cited & set(b["sources"]) or set(b["advances"]) & set(reqs)
    ]
    return reqs + briefs


def business_questions(data: dict) -> list[dict]:
    """Brief #1196: every open question, then every conflict the person has not settled (a
    settled one has its answer), keyed `conflict-<n>` by its place among the conflicts."""
    out = [
        {"key": str(q["key"]), "question": _one(q["text"]), "sources": q["sources"]}
        for q in data["scope"]["open_questions"]
    ]
    for n, c in enumerate(data["conflicts"], start=1):
        if c.get("settled") is None:
            text = f"The sources disagree: {_one(c['description']).rstrip('.')}. Which one holds?"
            out.append({"key": CONFLICT_KEY.format(n), "question": text, "sources": c["locations"]})
    return [q | {"blocks": _blocks(data, q["sources"])} for q in out]


def personas_text(data: dict) -> str:
    """Rule 7 with amendment 164 item 2: one `### P<n> <name>` block per persona."""
    out = [
        "# Personas",
        "",
        "Drafted by `plan_intake.py render` (SPEC-0043 rule 7); the person owns it.",
    ]
    for p in data["personas"]:
        out += ["", f"### {p['key']} {_one(p['name'])}", ""]
        out += [f"Goal: {_one(g)}" for g in p["goals"]] + _sources(p["sources"])
    return "\n".join(out) + "\n"


def access_text(data: dict) -> str:
    """Rule 7 with amendment 167 item 2: one table row per access cell."""
    out = [
        "# Access",
        "",
        "Drafted by `plan_intake.py render` (SPEC-0043 rule 7); the person owns it.",
        "",
        "| " + " | ".join(check_plan.ACCESS_COLUMNS) + " |",
        "| --- | --- | --- | --- |",
    ]
    for c in data[ACCESS]:
        cells = [c["persona"], _one(c["screen"]), c["allowed"], _locs(c["sources"])]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def milestones_text(data: dict) -> str:
    """Rule 7 with amendment 164 item 4: a `Demo:` line after `Exit:` for a slice and for
    `M1 Foundation`."""
    out = ["# Milestones"]
    for m in data["milestones"]:
        out += ["", f"### {m['id']} {_one(m['title'])}", "", f"Exit: {_one(m['exit'])}"]
        if m.get("screens"):
            out.append(f"Demo: {', '.join(m['screens'])}")
        elif m["id"] == "M1" and data.get(COMPONENTS):
            out.append("Demo: none (foundation)")
        out.append(f"Acceptance: {_one(m['acceptance'])}")
        out += [f"Target: {m['target'] or VERIFY}", *_sources(m["sources"])]
    return "\n".join(out) + "\n"


def requirements_text(data: dict) -> str:
    out = [
        "# Requirements proposed",
        "",
        "Each enters `docs/requirements.md` through its own intake.",
    ]
    names = {p["key"]: _one(p["name"]) for p in data["personas"]}
    for r in data["requirements"]:
        out += ["", f"### {r['key']} {_one(r['title'])}", ""]
        out += [f"Persona: {r['persona']} {names[r['persona']]}", f"Story: {_one(r['story'])}"]
        if r.get("statement") is not None:  # amendment 166 item 3
            out.append(f"Statement: {_one(r['statement'])}")
        if r.get("changing") is True:
            out.append("Changing: yes")
        out += ["", "Criteria:", ""]
        out += [f"- {_one(c)}" for c in r["criteria"]] or [f"- {VERIFY}"]
        out += ["", f"Milestone: {r['milestone']}", "Status: planned", *_sources(r["sources"])]
    return "\n".join(out) + "\n"


def brief_text(data: dict, b: dict, version: str = VERIFY) -> str:
    """SPEC-0034 rule 2 and SPEC-0030 rule 4, with keys on `Advances:` and `Depends-on:`."""
    from check_specs import CONTEXTS  # noqa: PLC0415 - only render needs it

    reqs = {r["key"]: r for r in data["requirements"]}
    title = _one(b["title"])
    out = [f"# {title}", "", f'Sentence: "{title}"', ""]
    out.append(
        "Answers (drafted from the sources by plan_intake.py render; the person edits them):"
    )
    for n, key in enumerate(b["advances"], start=1):
        criteria = "; ".join(_one(c) for c in reqs[key]["criteria"]) or VERIFY
        out.append(f"{n}. {key}: {_one(reqs[key]['title'])}. Criteria: {criteria}")
    out += ["", f"Advances: {', '.join(b['advances'])}", f"Touches: {', '.join(b['touches'])}"]
    out += [f"Size: {b['size']}", f"Expected: {b['expected']}", f"Milestone: {b['milestone']}"]
    if b.get("screens"):  # SPEC-0037 rule 10's line, with the signed-off version (`Q-1092-3`)
        out.append(f"Screens: {version} {', '.join(b['screens'])}")
    out += [f"Depends-on: {key}" for key in b["depends_on"]]
    out.append("Contexts: " + "; ".join(f"{c}: {VERIFY} for the person to state" for c in CONTEXTS))
    return "\n".join([*out, *_sources(b["sources"])]) + "\n"


def render_problems(data: dict) -> list[str]:
    """Rule 7: a brief that could never pass `check_brief.py` or would leave its folder, and an
    area whose name gives `new_spec.slug` no file name."""
    out: list[str] = []
    for b in data["briefs"]:
        where = f"rule 7: briefs {b['key']}"
        if not FILE_KEY.fullmatch(b["key"]):
            out.append(f"{where}: the key is not a file name")
        out += [f"{where}: {field} is empty" for field in ("touches", "advances") if not b[field]]
        if len(_one(b["title"])) > SENTENCE_MAX:
            out.append(f"{where}: the title is over {SENTENCE_MAX} characters")
    for r in data["requirements"]:
        if r["milestone"] is None:
            out.append(f"rule 7: requirements {r['key']}: milestone is not set")
    for a in data["areas"]:
        if not re.search(r"[a-z0-9]", a["name"].lower()):
            out.append(f"rule 7: areas {a['name']}: the name has no letters or digits")
    return out


def for_the_person(data: dict) -> list[str]:
    """Rule 6 and amendment 163 item 5: every conflict first, then every open question."""
    out = ["Conflicts for the person"]
    for c in data["conflicts"]:
        settled = f" ({c['settled']})" if c.get("settled") else ""
        out.append(f"- {' '.join(c['locations'])}: {_one(c['description'])}{settled}")
    out += ["- none"] if not data["conflicts"] else []
    out.append("Open questions for the person")
    questions = data["scope"]["open_questions"]
    out += [f"- {_one(q['text'])} ({_locs(q['sources'])})" for q in questions] or ["- none"]
    return out


def milestone_order(root: Path) -> str:
    """Amendment 164 item 4: the declared playbook's `[milestones] batch_by`, read through
    `playbook_format` (SPEC-0038 rule 7); the order itself is the person's to judge."""
    lines, problems = playbook_format.split(root)
    path = playbook_format.selected(root)
    head = "Milestone order for the person: "
    if not lines or problems or path is None:
        return head + "no playbook declares batch_by"
    batch_by = tomllib.loads(path.read_text(encoding="utf-8"))["milestones"]["batch_by"]
    return f"{head}{_one(batch_by)} (playbook {path.relative_to(root).as_posix()})"


def cmd_render(root: Path, proposals: Path) -> int:
    data, problems = validation(root, proposals)
    problems = problems or render_problems(data)
    if problems:
        print("\n".join(problems))
        return 1
    if not (Path(__file__).resolve().parent / "new_spec.py").is_file():
        print(f"render needs new_spec.py: {NEW_SPEC}")
        return 2
    import new_spec  # noqa: PLC0415 - the copy beside this script (installed, ADR-0503)

    files = {
        f"{PLAN}/scope.md": scope_text(data),
        f"{PLAN}/personas.md": personas_text(data),
        f"{PLAN}/milestones.md": milestones_text(data),
        f"{PLAN}/requirements-proposed.md": requirements_text(data),
    }
    if data.get(ACCESS):
        files[f"{PLAN}/access.md"] = access_text(data)
    versions = signed_versions(root)
    version = versions[-1] if versions else VERIFY
    files |= {
        f"{PLAN}/briefs/{b['milestone']}/{b['key']}.md": brief_text(data, b, version)
        for b in data["briefs"]
    }
    first = new_spec.next_number(root / "docs" / "specs")
    specs = [
        (f"docs/specs/{first + n:04d}-{new_spec.slug(a['name'])}.md", a)
        for n, a in enumerate(data["areas"])
    ]
    problems = [
        f"rule 7: {rel} already exists; nothing was written"
        for rel in [*files, *(s for s, _ in specs)]
        if (root / rel).exists() or (root / rel).is_symlink()
    ]
    if data["areas"] and _read(root / SPEC_TEMPLATE) is None:
        problems.append(f"rule 7: {SPEC_TEMPLATE} cannot be read; nothing was written")
    if problems:
        print("\n".join(sorted(problems)))
        return 1
    print("\n".join(for_the_person(data)))
    if check_plan.screens(root):
        print(milestone_order(root))
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"created {rel}")
    for _, area in specs:
        keys = ", ".join(area["requirements"]) or VERIFY
        issue = (
            "Feature area drafted by `plan_intake.py render` (SPEC-0043 rule 7). Its requirements "
            f"are proposed in `{PLAN}/requirements-proposed.md`: {keys}. They enter "
            "`docs/requirements.md` through one intake pull request with its own ADR.\n"
        )
        try:
            new_spec.make_spec(root, _one(area["name"]), [], issue)
        except new_spec.Refusal as exc:
            print(f"rule 7: refused: {exc}")
            return 1
    return 0


# --- rule 25: publish, after the person's confirmation of rule 8 (build (i), ADR-0459) ------------

HEAD_ID = re.compile(r"[0-9a-f]{40}")
MILESTONE_HEADING = re.compile(r"### (M[1-9]\d*) (.+)")
DEPENDS_ON = re.compile(r"Depends-on: (.+)")
ISSUE_REF = re.compile(r"#[1-9]\d*")
BRIEF_LABEL = "agk-brief"
MILESTONES = f"{PLAN}/milestones.md"
SCOPE_FILE = f"{PLAN}/scope.md"
QUESTION_LABEL = "agk-business-question"  # brief #1196 (ADR-0508): never a builder's work
QUESTION_LABEL_TEXT = "A question for business: answer it in the issue, then close it"
QUESTION_HEADING = re.compile(r"### (\S.*?)\s*")
VERIFY_MARK = re.compile(r"\s*\(verify\)")
TITLE_MAX = 256  # GitHub's longest issue title
NO_CONFIRMATION = (
    "publish needs the person's confirmation: a comment whose first line is"
    " `Approve: plan <full head ID>` by an account of spec_approvers, naming this head"
    " (setting: spec_approvers in config/reviewers.yaml)"
)
BAD_COMMENTS = "publish reads a saved list of the plan's comments (option: --comments)"
BAD_NUMBERS = (
    "--numbers is a JSON object from a key to an issue or milestone number (option: --numbers)"
)


def _json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def confirmed(root: Path, comments: list, head: str) -> bool:
    """Rule 8: `Approve: plan <head>` by a listed approver, never through an agent app; in solo
    mode inside the person's whole `Confirmed:` comment too (session rule 29)."""
    import reviewers  # noqa: PLC0415 - only publish reads approvals
    from common import agent_apps  # noqa: PLC0415

    apps = agent_apps(root)
    items = reviewers.confirmed_comments(
        [c for c in comments if isinstance(c, dict)], apps, reviewers.solo_person(root)
    )
    return head in reviewers.plan_approvals(items, reviewers.spec_approvers(root), apps)


def plan_milestones(text: str) -> list[dict]:
    """`### M<n> <title>` blocks of `docs/plan/milestones.md`, each with its `Target:` date."""
    out: list[dict] = []
    for line in text.splitlines():
        if heading := MILESTONE_HEADING.fullmatch(line.strip()):
            out.append({"id": heading[1], "title": _one(heading[2]), "target": None})
        elif out and line.startswith("Target: "):
            value = line.removeprefix("Target: ").strip()
            out[-1]["target"] = value if check_plan.real_date(value) else None
    return out


def plan_briefs(root: Path, milestones: list[str]) -> tuple[list[dict], list[str]]:
    """Each `docs/plan/briefs/M<n>/<key>.md`: its key, milestone, title, body and dependences."""
    briefs: list[dict] = []
    out: list[str] = []
    folder = root / PLAN / "briefs"
    for path in sorted(folder.glob("*/*.md")) if folder.is_dir() else []:
        key, milestone, where = path.stem, path.parent.name, f"rule 25: briefs {path.stem}"
        body = _read(path)
        lines = (body or "").splitlines()
        if body is None or not lines or not lines[0].startswith("# ") or not lines[0][2:].strip():
            out.append(f"{where}: the file has no `# <title>` first line")
            continue
        named = [
            x.removeprefix("Milestone: ").strip() for x in lines if x.startswith("Milestone: ")
        ]
        if milestone not in milestones:
            out.append(f"{where}: milestone names nothing")
        elif named != [milestone]:
            out.append(f"{where}: Milestone: is not its folder")
        deps = [m[1].strip() for x in lines if (m := DEPENDS_ON.fullmatch(x.rstrip()))]
        briefs.append(
            {"key": key, "milestone": milestone, "title": _one(lines[0][2:]), "body": body}
            | {"depends_on": deps}
        )
    keys = [b["key"] for b in briefs]
    out += [
        f"rule 25: briefs {k}: the key is repeated" for k in sorted(set(keys)) if keys.count(k) > 1
    ]
    for b in briefs:
        if any(not ISSUE_REF.fullmatch(d) and d not in keys for d in b["depends_on"]):
            out.append(f"rule 25: briefs {b['key']}: depends_on names nothing")
    graph = {b["key"]: [d for d in b["depends_on"] if d in keys] for b in briefs}
    out += [f"rule 25: briefs {k}: depends_on makes a cycle" for k in sorted(_cycle(graph))]
    return briefs, out


def in_order(briefs: list[dict], milestones: list[str]) -> list[dict]:
    """Rule 25: `depends_on` order; among the briefs that are free, by milestone, then by key."""
    rank = {m: n for n, m in enumerate(milestones)}
    left = {b["key"]: b for b in briefs}
    done: list[dict] = []
    while left:
        ready = [b for b in left.values() if not any(d in left for d in b["depends_on"])]
        first = min(ready, key=lambda b: (rank.get(b["milestone"], len(rank)), b["key"]))
        done.append(left.pop(first["key"]))
    return done


def numbered_body(body: str, numbers: dict[str, int]) -> str:
    """Each `Depends-on: <key>` as `Depends-on: #<n>`; `#1` stands in for one not yet numbered,
    only for the shape check of `check_brief.py`."""

    def swap(match: re.Match) -> str:
        value = match[1].strip()
        return match[0] if ISSUE_REF.fullmatch(value) else f"Depends-on: #{numbers.get(value, 1)}"

    return re.sub(r"(?m)^Depends-on: (.+?)[ \t]*$", swap, body)


HIDDEN_OPEN, HIDDEN_CLOSE = "<!-- agk", "-->"
SENTENCE_LINE = re.compile(r'Sentence: "(.*)"')
ANSWER_ITEM = re.compile(r"\d+\.\s+(\S.*)")


def acceptance(lines: list[str]) -> list[str]:
    """The numbered items after the line that starts `Answers` and ends with a colon, up to the
    first line that is no item, each without its number (amendment 169 item 1)."""
    heads = [i for i, x in enumerate(lines) if x.startswith("Answers") and x.rstrip().endswith(":")]
    items: list[str] = []
    for line in lines[heads[0] + 1 :] if heads else []:
        if not (item := ANSWER_ITEM.fullmatch(line.rstrip())):
            break
        items.append(item[1])
    return items


def issue_body(b: dict, numbers: dict[str, int]) -> str:
    """Amendment 169 item 1: an engineer part (`## What`, `## Acceptance`, the milestone and the
    dependences in words), then the numbered brief body unchanged in a block GitHub hides."""
    body = numbered_body(b["body"], numbers)
    lines = body.splitlines()
    sentence = next((m[1] for x in lines if (m := SENTENCE_LINE.fullmatch(x.rstrip()))), VERIFY)
    deps = [x.rstrip().removeprefix("Depends-on: ") for x in lines if DEPENDS_ON.fullmatch(x)]
    persona = [f"Persona: {b['persona']}", ""] if b.get("persona") else []  # brief #1195
    blocked = [f"Blocked-by: #{numbers.get(k, 1)}" for k in b.get("blocked_by", [])]  # #1196
    where = f"Part of milestone {b['milestone']}."
    where += f" Depends on {', '.join(deps)}." if deps else ""
    shown = ["## What", "", sentence, "", "## Acceptance", ""]
    shown += [f"- [ ] {item}" for item in acceptance(lines)] or [f"- [ ] {VERIFY}"]
    shown += ["", *persona, where, "", *blocked, *([""] if blocked else [])]
    shown += [HIDDEN_OPEN, body.rstrip("\n"), HIDDEN_CLOSE]
    return "\n".join(shown) + "\n"


PERSONA_TEXT = re.compile(r"(?:- )?Persona: (\S.*?)\s*")
BLOCK_KEY = re.compile(r"### (\S+)")


def persona_texts(text: str) -> dict[str, str]:
    """Each `### <id>` block's first `Persona:` text (a `- Persona:` list item counts too)."""
    out: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("#"):
            current = m[1] if (m := BLOCK_KEY.match(line)) else None
        elif current and current not in out and (m := PERSONA_TEXT.fullmatch(line)):
            out[current] = m[1]
    return out


def brief_persona(root: Path, body: str) -> str | None:
    """Brief #1195 answer 3 (ADR-0507): the persona of each requirement the brief advances, from
    its block of `requirements-proposed.md`, else its section of `docs/requirements.md`; several
    distinct ones joined by `, `; None when no requirement names one."""
    proposed = persona_texts(_read(root / PLAN / "requirements-proposed.md") or "")
    accepted = persona_texts(_read(root / "docs/requirements.md") or "")
    line = next((x for x in body.splitlines() if x.startswith("Advances: ")), "")
    found: list[str] = []
    for req in re.split(r"[,\s]+", line.removeprefix("Advances: ").strip()):
        text = proposed.get(req) or accepted.get(req)
        if text and text not in found:
            found.append(text)
    return ", ".join(found) or None


def brief_check(root: Path, briefs: list[dict], numbers: dict[str, int]) -> list[str]:
    """Rule 25: every brief not yet published passes `check_brief.py --root .` once numbered, on
    the whole issue body (amendment 169), and holds no `-->` that would end its hidden block."""
    import check_brief  # noqa: PLC0415 - only publish needs it

    out: list[str] = []
    for b in briefs:
        if b["key"] in numbers:
            continue
        if HIDDEN_CLOSE in b["body"]:
            out.append(
                f"rule 25: briefs {b['key']}: the body holds `{HIDDEN_CLOSE}`, which would end"
                " its hidden block (amendment 169)"
            )
            continue
        problems = check_brief.body_problems(issue_body(b, numbers), root, None)
        if problems:
            out.append(f"rule 25: briefs {b['key']}: check_brief.py fails: " + "; ".join(problems))
    return out


def plan_questions(text: str, taken: list[str]) -> tuple[list[dict], list[str]]:
    """Brief #1196 answer 1: each `### <key>` block of the `Questions for business` section of
    `docs/plan/scope.md`, with its `Question:`, `Source:` and `Blocks:` lines; TAKEN holds the
    milestone ids and brief keys, which a question's key must not repeat (one number per key)."""
    found: list[dict] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == QUESTIONS_HEADING
        elif inside and (heading := QUESTION_HEADING.fullmatch(line)):
            found.append({"key": heading[1], "question": None, "source": "", "blocks": []})
        elif inside and found:
            name, _, value = line.partition(": ")
            value = value.strip()
            if name == "Question" and value:
                found[-1]["question"] = _one(value)
            elif name == "Source":
                found[-1]["source"] = value
            elif name == "Blocks" and value != "none":
                found[-1]["blocks"] = [x.strip() for x in value.split(",") if x.strip()]
    keys = [q["key"] for q in found]
    out = [
        f"rule 25: questions {k}: the key is repeated"
        for k in sorted(set(keys))
        if keys.count(k) > 1
    ]
    out += [
        f"rule 25: questions {k}: the key is also a brief's or a milestone's"
        for k in keys
        if k in taken
    ]
    out += [
        f"rule 25: questions {q['key']}: the block has no Question: line"
        for q in found
        if not q["question"]
    ]
    return found, out


def question_title(q: dict) -> str:
    """The question's plain text: without its `(verify)` mark, cut to GitHub's longest title."""
    text = _one(VERIFY_MARK.sub("", q["question"]))
    return text if len(text) <= TITLE_MAX else text[: TITLE_MAX - 3].rstrip() + "..."


def question_body(q: dict) -> str:
    """Brief #1196 answer 1: `## Question`, the source, `Blocks:` and an empty `## Answer`."""
    blocks = ", ".join(q["blocks"]) or "none"
    lines = ["## Question", "", _one(VERIFY_MARK.sub("", q["question"])), ""]
    lines += [f"Source: {q['source'] or VERIFY}", f"Blocks: {blocks}", "", "## Answer"]
    return "\n".join(lines) + "\n"


def label_command() -> str:
    """The label, made when missing (`--force` leaves one that exists as it is named)."""
    args = ["gh", "label", "create", QUESTION_LABEL, "--description", QUESTION_LABEL_TEXT]
    return shlex.join([*args, "--color", "d4c5f9", "--force"])


def question_command(q: dict) -> str:
    args = ["gh", "api", "repos/{owner}/{repo}/issues", "-X", "POST"]
    args += ["-f", f"title={question_title(q)}", "-f", f"body={question_body(q)}"]
    return shlex.join([*args, "-f", f"labels[]={QUESTION_LABEL}"])


def milestone_command(m: dict) -> str:
    args = ["gh", "api", "repos/{owner}/{repo}/milestones", "-X", "POST"]
    args += ["-f", f"title={m['id']} {m['title']}"]
    args += ["-f", f"due_on={m['target']}T00:00:00Z"] if m["target"] else []
    return shlex.join(args)


def brief_command(b: dict, body: str, milestone: int) -> str:
    args = ["gh", "api", "repos/{owner}/{repo}/issues", "-X", "POST", "-f", f"title={b['title']}"]
    args += ["-f", f"body={body}", "-f", f"labels[]={BRIEF_LABEL}", "-F", f"milestone={milestone}"]
    return shlex.join(args)


def cmd_publish(root: Path, comments: Path, head: str, numbers_path: Path | None) -> int:
    saved = _json(comments)
    if not isinstance(saved, list):
        print(BAD_COMMENTS)
        return 2
    numbers = {} if numbers_path is None else _json(numbers_path)
    if not isinstance(numbers, dict) or not all(
        isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in numbers.values()
    ):
        print(BAD_NUMBERS)
        return 2
    if not confirmed(root, saved, head):
        print(NO_CONFIRMATION)
        return 2
    text = _read(root / MILESTONES)
    milestones = plan_milestones(text or "")
    if not milestones:
        print(f"rule 25: {MILESTONES} is missing or holds no milestone; nothing to publish")
        return 1
    ids = [m["id"] for m in milestones]
    briefs, problems = plan_briefs(root, ids)
    questions, asked = plan_questions(
        _read(root / SCOPE_FILE) or "", ids + [b["key"] for b in briefs]
    )
    problems += asked
    if not problems:
        briefs = in_order(briefs, ids)
        for b in briefs:
            b["persona"] = brief_persona(root, b["body"])
            b["blocked_by"] = [q["key"] for q in questions if b["key"] in q["blocks"]]
        problems = brief_check(root, briefs, numbers)
    if problems:
        print("\n".join(problems))
        print("nothing was printed to run and nothing was created")
        return 1
    from common import personal_table  # noqa: PLC0415

    if personal_table(root) is not None:
        return publish_files(root, milestones, questions, briefs, dict(numbers))
    return publish_github(milestones, questions, briefs, numbers)


def publish_github(
    milestones: list[dict], questions: list[dict], briefs: list[dict], numbers: dict[str, int]
) -> int:
    """Rule 25: the commands for the person's own `gh`, printed and never run; brief #1196: the
    questions after the milestones and before every brief, the label once before the first."""
    counts = dict.fromkeys(("milestones", "questions", "briefs", "withheld", "published"), 0)
    for m in milestones:
        if m["id"] in numbers:
            print(f"published {m['id']} milestone {numbers[m['id']]}")
            counts["published"] += 1
        else:
            print(milestone_command(m))
            counts["milestones"] += 1
    for q in questions:
        if q["key"] in numbers:
            print(f"published {q['key']} #{numbers[q['key']]}")
            counts["published"] += 1
            continue
        if not counts["questions"]:
            print(label_command())
        print(question_command(q))
        counts["questions"] += 1
    for b in briefs:
        if b["key"] in numbers:
            print(f"published {b['key']} #{numbers[b['key']]}")
            counts["published"] += 1
            continue
        waits = [b["milestone"]] if b["milestone"] not in numbers else []
        waits += [d for d in b["depends_on"] if not ISSUE_REF.fullmatch(d) and d not in numbers]
        waits += [k for k in b["blocked_by"] if k not in numbers]  # brief #1196
        if waits:
            print(f"withheld {b['key']}: waits for {', '.join(waits)}")
            counts["withheld"] += 1
            continue
        print(brief_command(b, issue_body(b, numbers), numbers[b["milestone"]]))
        counts["briefs"] += 1
    print(
        f"ok publish: {counts['milestones']} milestone, {counts['questions']} question and"
        f" {counts['briefs']} brief commands"
        f" printed, {counts['withheld']} withheld, {counts['published']} published before;"
        " nothing was run (save each number into --numbers and run publish again)"
        + ("" if counts["withheld"] else "; next: /agk:board --yes (ADR-0506)")
    )
    return 0


def publish_files(
    root: Path,
    milestones: list[dict],
    questions: list[dict],
    briefs: list[dict],
    numbers: dict[str, int],
) -> int:
    """Rule 25 in personal mode: the questions (brief #1196), then the briefs, as issues of the
    files forge, in order."""
    import os  # noqa: PLC0415

    from forge import FilesForge  # noqa: PLC0415 - only personal mode writes

    forge = FilesForge(root, env=os.environ)
    for m in milestones:
        print(f"milestone {m['id']}: kept in each brief's Milestone: line (no forge record)")
    made = 0
    for q in questions:
        if q["key"] in numbers:
            print(f"published {q['key']} #{numbers[q['key']]}")
            continue
        number = forge.create_issue(question_title(q), question_body(q), [QUESTION_LABEL])
        numbers[q["key"]] = number
        print(f"created question {q['key']} #{number}")
    for b in briefs:
        if b["key"] in numbers:
            print(f"published {b['key']} #{numbers[b['key']]}")
            continue
        number = forge.create_issue(b["title"], issue_body(b, numbers), [BRIEF_LABEL])
        numbers[b["key"]] = number
        print(f"created {b['key']} #{number}")
        made += 1
    print(f"ok publish: {made} briefs written to the files forge; nothing was sent to GitHub")
    return 0


def missing_states(root: Path) -> list[str]:
    """Amendment 163 item 5: `<first heading's location> <state>` for each state to ask."""
    inventory = design_import.inventory_states(root) or {}
    out: list[str] = []
    for path in check_plan.source_files(root):
        text = _read(path) or ""
        if path.suffix != ".md" or (check_plan.header(text) or {}).get("Kind") != "design":
            continue
        rel = path.relative_to(root).as_posix()
        covered: dict[str, tuple[str, set[str]]] = {}
        for heading in check_plan.headings(text):
            if match := STATE_HEADING.match(heading):
                covered.setdefault(match.group(1), (heading, set()))[1].add(match.group(2))
        for screen, (first, states) in covered.items():
            for (name, state), value in inventory.items():
                if name == screen and value == "yes" and state not in states:
                    out.append(f"{rel}#{first} {state} {VERIFY}")
    return out


def cmd_states(root: Path) -> int:
    problems = scan_problems(root, [])
    for line in problems or missing_states(root) or ["ok states (none to ask)"]:
        print(line)
    return 1 if problems else 0


# --- amendment 166: an OpenSpec file (build (a) of brief #1109, ADR-0473) -------------------------

OPENSPEC = "openspec"
OPENSPEC_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
BAD_SLUG = (
    "--slug is lowercase letters, digits and hyphens, starting with a letter or digit"
    " (option: --slug)"
)
CAPABILITY_LINE = re.compile(r"^\*Capability `([^`]+)`")
CHANGE_STATUS = re.compile(r"Defined by:[^(]*\(([^,()]+)")
STEP = re.compile(r"^\s*[-*+]\s+(?:\*\*)?(GIVEN|WHEN|THEN|AND)\b(?:\*\*)?:?\s*(.*?)\s*$", re.I)
ACTOR = re.compile(r"^(an?\s+[A-Za-z][\w-]*)\b")
CROSS_REF = re.compile(r"\(([^()]*)\)")
KIND_NUMBER = re.compile(r"([A-Za-z]+)\s+(\d+(?:\.\d+)*)")
REQUIREMENT, SCENARIO = "Requirement: ", "Scenario: "


def _import_files(given: Path) -> tuple[list[tuple[str, Path]], list[str]] | None:
    """(relative path, file) to copy and the `skipped:` lines, or None when `given` is neither a
    `.md` file nor a folder that holds `specs/` (rule 2b, `Q-1108-4`)."""
    if given.is_file() and given.suffix == ".md":
        return [(given.name, given)], []
    if not (given.is_dir() and (given / "specs").is_dir()):
        return None
    files: list[tuple[str, Path]] = []
    skipped: list[str] = []
    for path in sorted(given.rglob("*")):
        rel = path.relative_to(given).as_posix()
        if path.is_symlink():
            skipped.append(f"skipped: {rel} (a link is not copied)")
        elif path.is_file() and path.suffix in check_plan.SUFFIXES:
            files.append((rel, path))
        elif path.is_file():
            skipped.append(f"skipped: {rel} (rule 1: .md or .txt only)")
    return files, skipped


def cmd_openspec_import(root: Path, given: Path, slug: str) -> int:
    """Rule 2b: the original bytes under the rule 1 header, guarded first, never overwritten."""
    import guard  # noqa: PLC0415 - here: only after the gate has found it installed

    if not OPENSPEC_SLUG.fullmatch(slug):
        print(f"openspec-import: {BAD_SLUG}")
        return 2
    rel_target = f"{check_plan.SOURCES}/{OPENSPEC}-{slug}"
    target = root / rel_target
    if target.exists() or target.is_symlink():
        print(f"openspec-import: {rel_target}/ exists; nothing was written (option: --slug)")
        return 2
    found = _import_files(given)
    if found is None:
        print(
            "openspec-import: the path is a .md file or a folder that holds specs/ (option: PATH)"
        )
        return 2
    files, skipped = found
    originals: list[tuple[str, bytes]] = []
    for rel, path in files:
        data = path.read_bytes()
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            print(f"openspec-import: {rel}: not UTF-8 text; nothing was written")
            return 2
        originals.append((rel, data))
    findings = [
        f"rule 3: {rel}: {f.kind} line {f.line}, column {f.column}"
        for rel, data in originals
        for f in guard.scan_text(data.decode("utf-8"))
    ]
    if findings:
        print("\n".join([*findings, "openspec-import: nothing was written"]))
        return 1
    today = datetime.now(UTC).date().isoformat()
    for rel, data in originals:
        head = (
            f"Source: OpenSpec {rel}\nKind: {OPENSPEC}\n"
            f"Version: sha256:{hashlib.sha256(data).hexdigest()}\nDate: {today}\n\n"
        )
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(head.encode("utf-8") + data)
    for line in skipped:
        print(line)
    print(f"imported {len(originals)} files into {rel_target}/")
    return 0


class Reading:
    """Rule 4b: the requirements, personas and open questions of one imported folder, in order."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.areas: list[dict] = []
        self.requirements: list[dict] = []
        self.personas: dict[str, dict] = {}
        self.questions: list[tuple[str, str]] = []  # (text, location)
        self.warnings: list[str] = []
        self.unnamed: list[str] = []  # requirement keys with no actor
        self.scenarios = 0

    def ask(self, text: str, location: str) -> None:
        self.questions.append((f"{text} {VERIFY}", location))

    def capability(self, name: str, changing: bool) -> dict:
        area = {"name": name, "requirements": [], "changing": changing}
        self.areas.append(area)
        return area

    def read_file(self, rel: str, text: str, area: dict | None) -> None:
        """One file: `area` is set for a folder's `specs/<slug>/` file; a combined file finds its
        capabilities by their `*Capability ` line."""
        lines = text.splitlines()
        counts: dict[str, int] = {}
        for h in check_plan.headings(text):
            counts[h] = counts.get(h, 0) + 1

        def loc(heading: str, number: int) -> str:
            return f"{rel}#{heading}" if counts.get(heading) == 1 else f"{rel}:{number}"

        combined = area is None
        req: dict | None = None
        scenario: list[tuple[str, str]] | None = None
        statement: list[str] | None = None
        seen_requirement = False
        fenced = False
        for index, line in enumerate(lines):
            if check_plan.FENCE.match(line):
                fenced = not fenced
                continue
            heading = None if fenced else check_plan.HEADING.match(line)
            if heading is None:
                if fenced or CAPABILITY_LINE.match(line.strip()):
                    continue
                if statement is not None and line.strip():
                    statement.append(line.strip())
                elif scenario is not None and (step := STEP.match(line)):
                    scenario.append((step.group(1).upper(), step.group(2)))
                continue
            name, number = heading.group(1), index + 1
            self._close(req, statement)
            statement = scenario = None
            following = next((x.strip() for x in lines[index + 1 :] if x.strip()), "")
            if combined and CAPABILITY_LINE.match(following):
                status = CHANGE_STATUS.search(following)
                changing = status is not None and status.group(1).strip().lower() == "open"
                area, req, seen_requirement = self.capability(name, changing), None, False
            elif area is not None and name.startswith(REQUIREMENT):
                req = self._requirement(area, name, loc(name, number))
                statement, seen_requirement = [], True
            elif req is not None and name.startswith(SCENARIO):
                scenario = []
                req["_scenarios"].append((loc(name, number), scenario))
            elif seen_requirement or name.startswith((REQUIREMENT, SCENARIO)):
                self.warnings.append(
                    f"ignored: {rel}:{number}: heading is not a capability, requirement or"
                    " scenario (rule 4b)"
                )
                req = None
        self._close(req, statement)

    def _requirement(self, area: dict, name: str, location: str) -> dict:
        key = f"R{len(self.requirements) + 1}"
        req: dict = {"key": key, "title": name[len(REQUIREMENT) :].strip(), "location": location}
        req |= {"changing": area["changing"], "_scenarios": [], "statement": None}
        self.requirements.append(req)
        area["requirements"].append(key)
        return req

    @staticmethod
    def _close(req: dict | None, statement: list[str] | None) -> None:
        if req is not None and statement:
            req["statement"] = " ".join(statement)

    def finish(self) -> None:
        """The criteria, the persona of each requirement and the cross-references (rule 6)."""
        for r in self.requirements:
            r["criteria"], r["sources"], actor = [], [r["location"]], None
            for location, steps in r.pop("_scenarios"):
                self.scenarios += 1
                r["criteria"].append(f"{criterion(steps)} ({location})")
                for word, text in steps:
                    if actor is None and word == "WHEN" and (m := ACTOR.match(text)):
                        actor = m.group(1)
                        self.personas.setdefault(actor, {"sources": [location]})
            if not r["criteria"]:
                r["criteria"] = [VERIFY]
                self.ask(
                    f"requirements {r['key']}: no scenario, so no acceptance line", r["location"]
                )
            if r["statement"] is None:
                self.ask(f"requirements {r['key']}: no requirement text", r["location"])
            r["actor"] = actor
            if actor is None:
                self.unnamed.append(r["key"])
            self.cross_references(r)

    def cross_references(self, r: dict) -> None:
        """Rule 6: `<kind> <number>` resolves to the one heading of the one source of that kind;
        any other is an open question naming its position, never its text (`Q-1108-9`)."""
        refs = [
            part.strip()
            for group in CROSS_REF.findall(r["statement"] or "")
            for part in group.split(",")
        ]
        for n, ref in enumerate(refs, start=1):
            target = self.resolve(ref)
            if target is not None:
                r["sources"].append(target)
            else:
                self.ask(
                    f"requirements {r['key']}: cross-reference {n} of its statement names no one"
                    " source heading",
                    r["location"],
                )

    def resolve(self, ref: str) -> str | None:
        match = KIND_NUMBER.fullmatch(ref)
        if match is None:
            return None
        kind, number = match.group(1).lower(), match.group(2)
        paths = [  # every source of the kind, `.md` or `.txt`; only one `.md` can link
            p
            for p in check_plan.source_files(self.root)
            if (check_plan.header(_read(p) or "") or {}).get("Kind") == kind
        ]
        if len(paths) != 1 or paths[0].suffix != ".md":
            return None
        text = _read(paths[0]) or ""
        found = [
            h for h in check_plan.headings(text) if re.match(rf"{re.escape(number)}(?:\s|$)", h)
        ]
        if len(found) != 1 or check_plan.headings(text).count(found[0]) != 1:
            return None
        return f"{paths[0].relative_to(self.root).as_posix()}#{found[0]}"

    def proposals(self) -> dict:
        personas = [
            {"key": f"P{n}", "name": name, "goals": [VERIFY], "sources": p["sources"]}
            for n, (name, p) in enumerate(self.personas.items(), start=1)
        ]
        keys = {p["name"]: p["key"] for p in personas}
        if self.unnamed:
            first = next(r for r in self.requirements if r["key"] == self.unnamed[0])
            unnamed = {"key": f"P{len(personas) + 1}", "name": VERIFY, "goals": [VERIFY]}
            personas.append(unnamed | {"sources": [first["location"]]})
            self.ask(
                f"personas {unnamed['key']}: no step names who uses requirements "
                + ", ".join(self.unnamed),
                first["location"],
            )
        requirements = []
        for r in self.requirements:
            persona = keys.get(r["actor"]) if r["actor"] else personas[-1]["key"]
            name = r["actor"] or VERIFY
            requirements.append(
                {"key": r["key"], "title": r["title"], "statement": r["statement"]}
                | {"criteria": r["criteria"], "milestone": None, "persona": persona}
                | {"story": f"As {name}{WANT}{VERIFY}{SO_THAT}{VERIFY}"}
                | {"changing": r["changing"], "sources": r["sources"]}
            )
        questions = [
            {"key": f"Q{n}", "text": text, "sources": [location]}
            for n, (text, location) in enumerate(self.questions, start=1)
        ]
        scope: dict[str, list[dict]] = {name: [] for name in SCOPE[:-1]}
        scope["open_questions"] = questions
        areas = [{"name": a["name"], "requirements": a["requirements"]} for a in self.areas]
        return {"schema": 1, "scope": scope, "personas": personas, "milestones": []} | {
            "requirements": requirements,
            "areas": areas,
            "briefs": [],
            "conflicts": [],
        }


def criterion(steps: list[tuple[str, str]]) -> str:
    """`Given ..., when ..., then ...` of a scenario's steps; `AND` joins the clause before it."""
    clauses: dict[str, list[str]] = {"GIVEN": [], "WHEN": [], "THEN": []}
    last = "GIVEN"
    for word, text in steps:
        if word == "AND":
            clauses[last].append(text)
        else:
            clauses[word].append(text)
            last = word
    parts = [f"{word.lower()} {' and '.join(texts)}" for word, texts in clauses.items() if texts]
    if not parts:
        return VERIFY
    text = ", ".join(parts)
    return text[0].upper() + text[1:]


def read_openspec(root: Path, folder: Path) -> Reading:
    """Rule 4b over `docs/sources/openspec-<slug>/`: the folder layout when it holds `specs/`,
    else each combined `.md` file at its top; nothing under `changes/` is a requirement."""
    reading = Reading(root)

    def body(path: Path) -> str:
        return _read(path) or ""

    def rel(path: Path) -> str:
        return path.relative_to(root).as_posix()

    specs, changes = folder / "specs", folder / "changes"
    if not specs.is_dir():
        for path in sorted(folder.glob("*.md")):
            reading.read_file(rel(path), body(path), None)
        reading.finish()
        return reading
    live = (
        [c for c in sorted(changes.iterdir()) if c.is_dir() and c.name != "archive"]
        if changes.is_dir()
        else []
    )
    for cap in sorted(p for p in specs.iterdir() if p.is_dir()):
        changing = any((c / "specs" / cap.name).is_dir() for c in live)
        area = reading.capability(cap.name, changing)
        for path in sorted(cap.glob("*.md")):
            reading.read_file(rel(path), body(path), area)
    reading.finish()
    for n, change in enumerate(live, start=1):
        files = sorted(change.rglob("*.md"), key=lambda p: (p.name != "proposal.md", p.as_posix()))
        if not files:
            continue
        heads = check_plan.headings(body(files[0]))
        first = heads[0] if heads and heads.count(heads[0]) == 1 else None
        location = (
            f"{rel(files[0])}#{first}" if first else f"{rel(files[0])}:{len(check_plan.HEADER) + 2}"
        )
        reading.ask(
            f"change {n}: its tasks and delta specs are hints for the briefs, never requirements",
            location,
        )
    return reading


def cmd_openspec(root: Path, slug: str, out_file: Path) -> int:
    """Rule 4b: the partial proposals file the skill completes, outside `docs/`, never over one."""
    if not OPENSPEC_SLUG.fullmatch(slug):
        print(f"openspec: {BAD_SLUG}")
        return 2
    rel_folder = f"{check_plan.SOURCES}/{OPENSPEC}-{slug}"
    folder = root / rel_folder
    if not folder.is_dir():
        print(f"openspec: {rel_folder}/ does not exist; run openspec-import first (option: --slug)")
        return 2
    if out_file.resolve().is_relative_to((root / "docs").resolve()):
        print("openspec: the proposals file is outside docs/ (option: --out)")
        return 2
    if out_file.exists() or out_file.is_symlink():
        print("openspec: the proposals file exists; nothing was written (option: --out)")
        return 2
    problems = scan_problems(root, [])
    if problems:
        print("\n".join(problems))
        return 1
    reading = read_openspec(root, folder)
    data = reading.proposals()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    for line in reading.warnings:
        print(line)
    print(
        f"wrote the proposals: {len(data['areas'])} areas, {len(data['requirements'])}"
        f" requirements, {reading.scenarios} scenarios, {len(data['personas'])} personas,"
        f" {len(data['scope']['open_questions'])} open questions; set each milestone, then"
        " add milestones and briefs"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command, rest = (args[0], args[1:]) if args else ("", [])
    if command == "openspec-draft":  # amendment 166's name for `openspec` (ADR-0473)
        command = "openspec"
    if command == "openspec-import":  # the path first, then the options
        if not rest or rest[0].startswith("--"):
            print(USAGE, file=sys.stderr)
            return 2
        rest = ["--path", *rest]
    options = dict(zip(rest[::2], rest[1::2], strict=False)) if len(rest) % 2 == 0 else None
    allowed = {"validate": {"--proposals", "--root"}, "states": {"--root"}}
    allowed["publish"] = {"--comments", "--head", "--numbers", "--root"}
    allowed["openspec-import"] = {"--path", "--slug", "--root"}
    allowed["openspec"] = {"--slug", "--out", "--root"}
    known = (allowed | {"render": allowed["validate"]}).get(command)
    if known is None or options is None or not set(options) <= known:
        print(USAGE, file=sys.stderr)
        return 2
    needed = {"openspec-import": {"--slug"}, "openspec": {"--slug", "--out"}}.get(command, set())
    if not needed <= set(options):
        print(USAGE, file=sys.stderr)
        return 2
    if command in ("validate", "render") and "--proposals" not in options:
        print(USAGE, file=sys.stderr)
        return 2
    if command == "publish" and (
        "--comments" not in options or not HEAD_ID.fullmatch(options.get("--head", ""))
    ):
        print(USAGE, file=sys.stderr)
        return 2
    return run(NAME, lambda: dispatch(command, options))


def dispatch(command: str, options: dict[str, str]) -> int:
    root = Path(options["--root"]) if "--root" in options else repo_root()
    if (missing := guard_missing(root)) is not None:
        print(f"data guard not installed: {missing}")
        return 2
    if command == "states":
        return cmd_states(root)
    if command == "openspec-import":
        return cmd_openspec_import(root, Path(options["--path"]), options["--slug"])
    if command == "openspec":
        return cmd_openspec(root, options["--slug"], Path(options["--out"]))
    if command == "render":
        return cmd_render(root, Path(options["--proposals"]))
    if command == "publish":
        numbers = Path(options["--numbers"]) if "--numbers" in options else None
        return cmd_publish(root, Path(options["--comments"]), options["--head"], numbers)
    return cmd_validate(root, Path(options["--proposals"]))


if __name__ == "__main__":
    sys.exit(main())
