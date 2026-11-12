"""The plan's proposals, validated and rendered (SPEC-0043 rules 3 to 7). Installed:
`kit/manifest.json` lists it in `verbatim`. Build (c1) of SPEC-0043 rule 27 (amendment 163,
ADR-0456), build (c2), `render` (ADR-0461), build (i), `publish` (ADR-0459), and build (p), personas
and user stories (amendment 164 item 2, ADR-0462).

    python3 plan_intake.py validate --proposals FILE [--root DIR]
    python3 plan_intake.py states [--root DIR]
    python3 plan_intake.py render --proposals FILE [--root DIR]
    python3 plan_intake.py publish --comments FILE --head SHA [--numbers FILE] [--root DIR]

Rule 3: every command exits 2 with `data guard not installed: <path>` when `scripts/agk/guard.py`
or `.claude/hooks/data_guard.py` is absent, and runs `guard.scan_text` on the whole text of every
source before it reads a line of one; a finding refuses with exit 1, naming the file, the kind and
`line <l>, column <c>`, never the matched text. Rules 4 to 6: `validate` prints `ok proposals` or
one line per problem naming the rule and the item's `key` or `id`, never its text. `states` prints
the inventory's `yes` states that no `<screen>/<state>` heading of a `Kind: design` source covers
(amendment 163 item 5). Build (p): the proposals hold `personas` (`P1`, `P2`, ... in order, each
with a `name`, non-empty `goals` and `sources`), and each requirement names its `persona` and one
`story` `As <the persona's name>, I want <capability>, so that <outcome>`, whose form only is
checked (`Q-1089-4`). Rule 7: `render` runs `validate` first, prints every conflict under
`Conflicts for the person` and then every open question under `Open questions for the person`, and
writes, as new files only and all or nothing, `docs/plan/scope.md`, `docs/plan/personas.md`,
`docs/plan/milestones.md`, `docs/plan/requirements-proposed.md` (each block with its `Persona:` and
`Story:` lines before its criteria), one Draft spec per area (`new_spec.make_spec`, imported from
the plugin's copy beside this script) and `docs/plan/briefs/M<n>/<key>.md`; it never edits
`docs/requirements.md`. Rules 8 and 25: `publish` exits 2 without `Approve: plan <--head>` by an
account of `spec_approvers` in the saved comments (`reviewers.plan_approvals`), refuses a brief that
`check_brief.py --root .` fails, and prints one `gh api` command per milestone and per brief,
briefs in `depends_on` order, each withheld until `--numbers` gives its milestone's and its
dependences' numbers; it runs none. In personal mode it writes the briefs through
`forge.FilesForge`. Files only: no network, no model; only `render` and personal `publish` write.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_plan
import design_import
from common import ESTIMATE_LINES, repo_root, run

NAME = "plan-intake"
USAGE = (
    "usage: plan_intake.py validate --proposals FILE [--root DIR] | states [--root DIR]"
    " | render --proposals FILE [--root DIR]"
    " | publish --comments FILE --head SHA [--numbers FILE] [--root DIR]"
)
GUARDS = ("scripts/agk/guard.py", ".claude/hooks/data_guard.py")
# The pattern of `playbook.py check-start` (SPEC-0013 rule 5). playbook.py is kit-only, so it is
# kept here and a test holds the two equal (ADR-0456 decision 4).
MEASURABLE = re.compile(r"\d|\b(?:all|every|none|zero)\b", re.IGNORECASE)
VERIFY = "(verify)"
SCOPE = ("in", "out", "assumptions", "constraints", "open_questions")
TOP = ("schema", "scope", "personas", "milestones", "requirements", "areas", "briefs", "conflicts")
LIST, TEXT, LOCS = "list", "text", "locations"
FIELDS = {
    "scope": ("key", "text", "sources"),
    "personas": ("key", "name", "goals", "sources"),
    "milestones": ("id", "title", "exit", "acceptance", "target", "sources"),
    "requirements": ("key", "title", "criteria", "milestone", "persona", "story", "sources"),
    "areas": ("name", "requirements"),
    "briefs": ("key", "milestone", "title", "size", "expected", "advances", "touches")
    + ("depends_on", "sources"),
    "conflicts": ("locations", "description"),
}
KINDS = {"sources": LOCS, "target": "date"} | dict.fromkeys(
    ("criteria", "requirements", "advances", "touches", "depends_on", "locations", "goals"), LIST
)
NON_EMPTY = ("goals",)  # a list that holds at least one item, as `sources` does
OPTIONAL = {"conflicts": ("settled",)}
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


def _items(data: dict) -> list[tuple[str, str, dict]]:
    """(section, name, item) of every item of the proposals, scope by its five lists."""
    out: list[tuple[str, str, dict]] = []
    for section in ("scope", *TOP[2:]):
        groups = [(f"scope.{n}", data["scope"][n]) for n in SCOPE] if section == "scope" else []
        for label, items in groups or [(section, data[section])]:
            kind = label.split(".")[0]
            for n, item in enumerate(items, start=1):
                name = str(n) if kind == "conflicts" else str(item.get(ID.get(kind, "key"), n))
                out.append((label, name, item))
    return out


def shape_problems(data: object) -> list[str]:
    """Rule 4: the top level, then every item's keys and types."""
    if not isinstance(data, dict):
        return ["rule 4: the proposals file is not a JSON object"]
    out = [f"rule 4: proposals: unknown key {k}" for k in data if k not in TOP]
    missing = [f"rule 4: proposals: missing key {k}" for k in TOP if k not in data]
    if missing:
        return out + missing
    if data["schema"] != 1:
        out.append("rule 4: proposals: schema is not 1")
    scope = data["scope"]
    if not isinstance(scope, dict) or sorted(scope) != sorted(SCOPE):
        return [*out, "rule 4: proposals: scope holds exactly " + ", ".join(SCOPE)]
    lists = [scope[n] for n in SCOPE] + [data[k] for k in TOP[2:]]
    if not all(isinstance(x, list) and all(isinstance(i, dict) for i in x) for x in lists):
        return [*out, "rule 4: proposals: every section is a list of objects"]
    for label, name, item in _items(data):
        kind = label.split(".")[0]
        fields, where = FIELDS[kind], f"rule 4: {label} {name}"
        known = (*fields, *OPTIONAL.get(kind, ()))
        out += [f"{where}: unknown key {k}" for k in item if k not in known]
        out += [f"{where}: missing key {k}" for k in fields if k not in item]
        for key in fields:
            kind_of = KINDS.get(key, TEXT)
            if key in item and not _typed(item[key], kind_of):
                out.append(f"{where}: {key} is not {kind_of}")
            elif (kind_of == LOCS or key in NON_EMPTY) and item.get(key) == []:
                out.append(f"{where}: {key} is empty")
        if kind == "conflicts" and isinstance(item.get("locations"), list):
            if len(item["locations"]) != 2:
                out.append(f"{where}: locations is not two locations")
    for n, milestone in enumerate(data["milestones"], start=1):
        if milestone.get("id") != f"M{n}":
            out.append(f"rule 4: milestones {milestone.get('id', n)}: ids run M1, M2, ... in order")
    seen: list[object] = []  # a repeated key is rule 4's `the key is repeated`, said once
    for persona in data["personas"]:
        if (key := persona.get("key")) not in seen:
            seen.append(key)
            if key != f"P{len(seen)}":
                out.append(f"rule 4: personas {key}: keys run P1, P2, ... in order")
    return out


def _typed(value: object, kind: str) -> bool:
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
        if r["milestone"] not in milestones:
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
    return out + conflict_problems(items)


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
    return "\n".join(out) + "\n"


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


def milestones_text(data: dict) -> str:
    out = ["# Milestones"]
    for m in data["milestones"]:
        out += ["", f"### {m['id']} {_one(m['title'])}", ""]
        out += [f"Exit: {_one(m['exit'])}", f"Acceptance: {_one(m['acceptance'])}"]
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
        out += ["", "Criteria:", ""]
        out += [f"- {_one(c)}" for c in r["criteria"]] or [f"- {VERIFY}"]
        out += ["", f"Milestone: {r['milestone']}", "Status: planned", *_sources(r["sources"])]
    return "\n".join(out) + "\n"


def brief_text(data: dict, b: dict) -> str:
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


def cmd_render(root: Path, proposals: Path) -> int:
    data, problems = validation(root, proposals)
    problems = problems or render_problems(data)
    if problems:
        print("\n".join(problems))
        return 1
    if not (Path(__file__).resolve().parent / "new_spec.py").is_file():
        print(f"render needs new_spec.py: {NEW_SPEC}")
        return 2
    import new_spec  # noqa: PLC0415 - kit-only: the plugin's copy, beside this script

    files = {
        f"{PLAN}/scope.md": scope_text(data),
        f"{PLAN}/personas.md": personas_text(data),
        f"{PLAN}/milestones.md": milestones_text(data),
        f"{PLAN}/requirements-proposed.md": requirements_text(data),
    }
    files |= {
        f"{PLAN}/briefs/{b['milestone']}/{b['key']}.md": brief_text(data, b) for b in data["briefs"]
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


def brief_check(root: Path, briefs: list[dict], numbers: dict[str, int]) -> list[str]:
    """Rule 25: every brief not yet published passes `check_brief.py --root .` once numbered."""
    import check_brief  # noqa: PLC0415 - only publish needs it

    out: list[str] = []
    for b in briefs:
        if b["key"] in numbers:
            continue
        problems = check_brief.body_problems(numbered_body(b["body"], numbers), root, None)
        if problems:
            out.append(f"rule 25: briefs {b['key']}: check_brief.py fails: " + "; ".join(problems))
    return out


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
    if not problems:
        briefs = in_order(briefs, ids)
        problems = brief_check(root, briefs, numbers)
    if problems:
        print("\n".join(problems))
        print("nothing was printed to run and nothing was created")
        return 1
    from common import personal_table  # noqa: PLC0415

    if personal_table(root) is not None:
        return publish_files(root, milestones, briefs, dict(numbers))
    return publish_github(milestones, briefs, numbers)


def publish_github(milestones: list[dict], briefs: list[dict], numbers: dict[str, int]) -> int:
    """Rule 25: the commands for the person's own `gh`, printed and never run."""
    counts = dict.fromkeys(("milestones", "briefs", "withheld", "published"), 0)
    for m in milestones:
        if m["id"] in numbers:
            print(f"published {m['id']} milestone {numbers[m['id']]}")
            counts["published"] += 1
        else:
            print(milestone_command(m))
            counts["milestones"] += 1
    for b in briefs:
        if b["key"] in numbers:
            print(f"published {b['key']} #{numbers[b['key']]}")
            counts["published"] += 1
            continue
        waits = [b["milestone"]] if b["milestone"] not in numbers else []
        waits += [d for d in b["depends_on"] if not ISSUE_REF.fullmatch(d) and d not in numbers]
        if waits:
            print(f"withheld {b['key']}: waits for {', '.join(waits)}")
            counts["withheld"] += 1
            continue
        print(brief_command(b, numbered_body(b["body"], numbers), numbers[b["milestone"]]))
        counts["briefs"] += 1
    print(
        f"ok publish: {counts['milestones']} milestone and {counts['briefs']} brief commands"
        f" printed, {counts['withheld']} withheld, {counts['published']} published before;"
        " nothing was run (save each number into --numbers and run publish again)"
    )
    return 0


def publish_files(
    root: Path, milestones: list[dict], briefs: list[dict], numbers: dict[str, int]
) -> int:
    """Rule 25 in personal mode: the briefs as issues of the files forge, in order."""
    import os  # noqa: PLC0415

    from forge import FilesForge  # noqa: PLC0415 - only personal mode writes

    forge = FilesForge(root, env=os.environ)
    for m in milestones:
        print(f"milestone {m['id']}: kept in each brief's Milestone: line (no forge record)")
    made = 0
    for b in briefs:
        if b["key"] in numbers:
            print(f"published {b['key']} #{numbers[b['key']]}")
            continue
        number = forge.create_issue(b["title"], numbered_body(b["body"], numbers), [BRIEF_LABEL])
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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command, rest = (args[0], args[1:]) if args else ("", [])
    options = dict(zip(rest[::2], rest[1::2], strict=False)) if len(rest) % 2 == 0 else None
    allowed = {"validate": {"--proposals", "--root"}, "states": {"--root"}}
    allowed["publish"] = {"--comments", "--head", "--numbers", "--root"}
    allowed = (allowed | {"render": allowed["validate"]}).get(command)
    if allowed is None or options is None or not set(options) <= allowed:
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
    if command == "render":
        return cmd_render(root, Path(options["--proposals"]))
    if command == "publish":
        numbers = Path(options["--numbers"]) if "--numbers" in options else None
        return cmd_publish(root, Path(options["--comments"]), options["--head"], numbers)
    return cmd_validate(root, Path(options["--proposals"]))


if __name__ == "__main__":
    sys.exit(main())
