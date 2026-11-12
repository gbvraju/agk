"""The plan's proposals, validated (SPEC-0043 rules 3 to 6). Installed: `kit/manifest.json` lists it
in `verbatim`. Build (c1) of SPEC-0043 rule 27 (amendment 163, ADR-0456); `render` is build (c2).

    python3 plan_intake.py validate --proposals FILE [--root DIR]
    python3 plan_intake.py states [--root DIR]

Rule 3: every command exits 2 with `data guard not installed: <path>` when `scripts/agk/guard.py`
or `.claude/hooks/data_guard.py` is absent, and runs `guard.scan_text` on the whole text of every
source before it reads a line of one; a finding refuses with exit 1, naming the file, the kind and
`line <l>, column <c>`, never the matched text. Rules 4 to 6: `validate` prints `ok proposals` or
one line per problem naming the rule and the item's `key` or `id`, never its text. `states` prints
the inventory's `yes` states that no `<screen>/<state>` heading of a `Kind: design` source covers
(amendment 163 item 5). Files only: no network, no model, nothing written.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_plan
import design_import
from common import ESTIMATE_LINES, repo_root, run

NAME = "plan-intake"
USAGE = "usage: plan_intake.py validate --proposals FILE [--root DIR] | states [--root DIR]"
GUARDS = ("scripts/agk/guard.py", ".claude/hooks/data_guard.py")
# The pattern of `playbook.py check-start` (SPEC-0013 rule 5). playbook.py is kit-only, so it is
# kept here and a test holds the two equal (ADR-0456 decision 4).
MEASURABLE = re.compile(r"\d|\b(?:all|every|none|zero)\b", re.IGNORECASE)
VERIFY = "(verify)"
SCOPE = ("in", "out", "assumptions", "constraints", "open_questions")
TOP = ("schema", "scope", "milestones", "requirements", "areas", "briefs", "conflicts")
LIST, TEXT, LOCS = "list", "text", "locations"
FIELDS = {
    "scope": ("key", "text", "sources"),
    "milestones": ("id", "title", "exit", "acceptance", "target", "sources"),
    "requirements": ("key", "title", "criteria", "milestone", "sources"),
    "areas": ("name", "requirements"),
    "briefs": ("key", "milestone", "title", "size", "expected", "advances", "touches")
    + ("depends_on", "sources"),
    "conflicts": ("locations", "description"),
}
KINDS = {"sources": LOCS, "target": "date"} | dict.fromkeys(
    ("criteria", "requirements", "advances", "touches", "depends_on", "locations"), LIST
)
OPTIONAL = {"conflicts": ("settled",)}
ID = {"milestones": "id", "areas": "name"}
SETTLED = "Settled: "
STATE_HEADING = re.compile(r"^([^/]+)/([^/]+)$")


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
            elif kind_of == LOCS and item.get(key) == []:
                out.append(f"{where}: {key} is empty")
        if kind == "conflicts" and isinstance(item.get("locations"), list):
            if len(item["locations"]) != 2:
                out.append(f"{where}: locations is not two locations")
    for n, milestone in enumerate(data["milestones"], start=1):
        if milestone.get("id") != f"M{n}":
            out.append(f"rule 4: milestones {milestone.get('id', n)}: ids run M1, M2, ... in order")
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


def cmd_validate(root: Path, proposals: Path) -> int:
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
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print("ok proposals")
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
    allowed = {"validate": {"--proposals", "--root"}, "states": {"--root"}}.get(command)
    if allowed is None or options is None or not set(options) <= allowed:
        print(USAGE, file=sys.stderr)
        return 2
    if command == "validate" and "--proposals" not in options:
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
    return cmd_validate(root, Path(options["--proposals"]))


if __name__ == "__main__":
    sys.exit(main())
