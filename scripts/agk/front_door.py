"""The front door's entry and discovery document (SPEC-0048 build (b), rules 3, 5, 14 and 15).

Standard library only, files only, no network: every input is a saved file.

    front_door.py check-issue --issue FILE
        a saved problem issue (the JSON of one GET): the `agk-problem` label, a first line
        `Problem: <words>` of 1 to 1,500 characters up to the first blank line, and no finding of
        `guard.scan_text` in it (rule 3)
    front_door.py discovery-write (--issue FILE | --vision FILE) --answers FILE [--root DIR]
        writes `docs/discovery/<slug>.md` from the problem and a JSON file of the person's answers,
        never over an existing one, and refuses a write in which the guard finds anything (rules 5
        and 14)
    front_door.py check-discovery [FILE ...] [--root DIR]
        checks each discovery document (by default every `docs/discovery/*.md`) (rules 5 and 14)

The answers file: `{"screens": "yes|no|open", "work_type": "<work type>", "answers": [{"id":
"<id>", "answer": "<words>", "where": "<comment link>|in session YYYY-MM-DD"} or {"id": "<id>",
"open": true}], "points": [{"text": "<words>", "where": "..."}]}`; `screens` defaults to `open`
and `work_type` to the issue's `Kind:` line, else `pilot`. Every refusal names the rule and the
file or the setting, never a value, a problem's words or an answer (rule 15). Exit 0 ok, 1 refused,
2 usage.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from guard import scan_text
from playbook_format import WORK_TYPES

NAME = "front-door"
USAGE = (
    "usage: front_door.py check-issue --issue FILE | discovery-write (--issue FILE | --vision FILE)"
    " --answers FILE [--root DIR] | check-discovery [FILE ...] [--root DIR]"
)
LABEL = "agk-problem"
PREFIX = "Problem: "
KIND = "Kind: "
DIR = "docs/discovery"
# front_door.py is installed and `engines.py` and `playbook.py` are not, so the ten common topic ids
# of `engines.py questions` and `/agk:vision`'s limit are mirrored here, never their questions;
# a kit test pins both equal to their source.
TOPICS = (
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
MAX_STATEMENT = 1500
# The five fixed kit questions of rule 4 until amendment 130 adds `[[discovery]]` (build (c)).
FIXED = ("constraints", "success", "data-rules", "environments", "non-functional")
ORDER = (*TOPICS, *FIXED)
SCREENS = ("yes", "no", "open")
START = re.compile(r"^<!-- agk:problem sha256=([0-9a-f]{64}) -->$")
END = "<!-- agk:problem-end -->"
WHERE = re.compile(r"^(?:https://\S+|in session \d{4}-\d{2}-\d{2})$")
ANSWER = re.compile(r'^- ([a-z0-9-]+): (?:(open)|"(.*)" \(given: (.+)\))$')
ANSWER_ID = re.compile(r"^- ([a-z0-9-]+):")
OPEN_POINT = re.compile(r"^- D-\d+: `([a-z0-9-]+)` is open$")


class Refusal(Exception):
    """Exit 1: nothing is written."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def slug(text: str) -> str:
    """The slug rule of SPEC-0012 rule 2: lower case, hyphens, at most 60 characters."""
    out = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return out[:60].strip("-")


def problem_of(body: str) -> str | None:
    """The words after `Problem: ` on the first line, up to the first blank line or `Kind:` line."""
    lines = body.replace("\r\n", "\n").split("\n")
    if not lines[0].startswith(PREFIX.rstrip()):
        return None
    words = [lines[0][len(PREFIX) :] if lines[0].startswith(PREFIX) else ""]
    for line in lines[1:]:
        if not line.strip() or line.startswith(KIND):
            break
        words.append(line)
    return "\n".join(words).strip()


def kind_of(body: str) -> str | None:
    """The person's guess on a `Kind:` line of the problem's paragraph, a proposal only."""
    for line in body.replace("\r\n", "\n").split("\n")[1:]:
        if not line.strip():
            return None
        if line.startswith(KIND):
            return line[len(KIND) :].strip()
    return None


def guard_problems(rule: int, rel: str, text: str) -> list[str]:
    return [
        f"rule {rule}: {rel}: the data guard finds {f.kind} at line {f.line} column {f.column}"
        for f in scan_text(text)
    ]


def check_problem(rel: str, words: str | None) -> list[str]:
    if words is None:
        return [f"rule 3: {rel}: the body's first line is not `{PREFIX.strip()} <words>`"]
    if not words:
        return [f"rule 3: {rel}: the problem is empty"]
    if len(words) > MAX_STATEMENT:
        return [f"rule 3: {rel}: the problem is over {MAX_STATEMENT} characters"]
    return guard_problems(3, rel, words)


def read_issue(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise Refusal(
            [f"rule 3: {path.name}: not a readable saved issue (the JSON of one GET)"]
        ) from None
    if not isinstance(data, dict):
        raise Refusal([f"rule 3: {path.name}: not a readable saved issue (the JSON of one GET)"])
    return data


def issue_problems(path: Path, data: dict) -> list[str]:
    rel = path.name
    problems = []
    labels = [x.get("name") if isinstance(x, dict) else x for x in data.get("labels") or []]
    if LABEL not in labels:
        problems.append(f"rule 3: {rel}: the issue is not labelled `{LABEL}`")
    body = data.get("body")
    return problems + check_problem(rel, problem_of(body if isinstance(body, str) else ""))


def check_issue(path: Path) -> int:
    problems = issue_problems(path, read_issue(path))
    if problems:
        raise Refusal(problems)
    print(f"ok {NAME}: check-issue {path.name}")
    return 0


# --- the discovery document (rule 5) -------------------------------------------------------------


def digest(words: str) -> str:
    return hashlib.sha256(words.encode("utf-8")).hexdigest()


def one_line(text: str) -> str:
    return " ".join(str(text).split())


def load_answers(path: Path) -> dict:
    rel = path.name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise Refusal([f"rule 5: {rel}: the answers file is not readable JSON"]) from None
    if not isinstance(data, dict) or not isinstance(data.get("answers", []), list):
        raise Refusal([f"rule 5: {rel}: the answers file is not an object with `answers`"])
    return data


def answer_lines(rel: str, rows: list) -> tuple[list[str], list[str], list[str]]:
    """The `## Answers` bullets in rule 4's order, the ids left open, and the problems."""
    by_id: dict[str, dict] = {}
    problems = []
    for row in rows:
        qid = row.get("id") if isinstance(row, dict) else None
        if qid not in ORDER:
            problems.append(f"rule 5: {rel}: an answer names no question of rule 4")
        elif qid in by_id:
            problems.append(f"rule 5: {rel}: `{qid}` is answered twice")
        else:
            by_id[qid] = row
    lines, open_ids = [], []
    for qid in ORDER:
        row = by_id.get(qid, {"open": True})
        if row.get("open") is True or "answer" not in row:
            lines.append(f"- {qid}: open")
            open_ids.append(qid)
            continue
        where = one_line(row.get("where", ""))
        if not WHERE.match(where):
            problems.append(f"rule 5: {rel}: `{qid}` is not marked with where it was given")
        lines.append(f'- {qid}: "{one_line(row["answer"])}" (given: {where})')
    return lines, open_ids, problems


def discovery_write(args: dict[str, str], root: Path) -> int:
    answers_path = Path(args["--answers"])
    data = load_answers(answers_path)
    if "--issue" in args:
        path = Path(args["--issue"])
        issue = read_issue(path)
        problems = issue_problems(path, issue)
        if problems:
            raise Refusal(problems)
        body = issue["body"]
        words, kind = problem_of(body) or "", kind_of(body)
        title = one_line(issue.get("title") or "")
        link = str(issue.get("html_url") or "")
        if not title or not link.startswith("https://"):
            raise Refusal([f"rule 5: {path.name}: the saved issue has no title or no link"])
        name = slug(title)
    else:
        path = Path(args["--vision"])
        try:
            words = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            raise Refusal([f"rule 3: {path.name}: the idea file is not readable"]) from None
        problems = check_problem(path.name, words)
        if problems:
            raise Refusal(problems)
        kind, link, name = None, "vision", slug(words)
        title = words[:60].rsplit(" ", 1)[0] if len(words) > 60 else words
        title = one_line(title)
    rel = f"{DIR}/{name}.md"
    if not name:
        raise Refusal([f"rule 5: {path.name}: the problem gives an empty slug"])
    if END in words or START.match(words.split("\n")[0]):
        raise Refusal([f"rule 5: {path.name}: the problem holds a marker of the document"])
    work_type = data.get("work_type", kind if kind in WORK_TYPES else "pilot")
    screens = data.get("screens", "open")
    problems = []
    if work_type not in WORK_TYPES:
        problems.append(f"rule 5: {answers_path.name}: `work_type` is not one of the work types")
    if screens not in SCREENS:
        problems.append(f"rule 5: {answers_path.name}: `Screens` is not yes, no or open")
    lines, open_ids, more = answer_lines(answers_path.name, data.get("answers", []))
    problems += more
    points = [f"- D-{n}: `{qid}` is open" for n, qid in enumerate(open_ids, 1)]
    for row in data.get("points") or []:
        where = one_line(row.get("where", "")) if isinstance(row, dict) else ""
        if not WHERE.match(where) or not one_line(row.get("text", "")):
            problems.append(f"rule 5: {answers_path.name}: a point is not marked with where given")
            continue
        points.append(f'- D-{len(points) + 1}: "{one_line(row["text"])}" (given: {where})')
    if problems:
        raise Refusal(problems)
    text = "\n".join(
        [
            f"# Discovery: {title}",
            "",
            f"- Problem: {link}",
            f"<!-- agk:problem sha256={digest(words)} -->",
            words,
            END,
            f"- Work type: {work_type} (proposed)",
            f"- Screens: {screens}",
            "",
            "## Answers",
            "",
            *lines,
            "",
            "## Open points",
            "",
            *(points or ["- none"]),
            "",
        ]
    )
    found = guard_problems(14, rel, text)
    if found:
        raise Refusal(found)
    target = root / rel
    if target.exists():
        raise Refusal([f"rule 5: {rel} already exists; one discovery document per problem"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {rel} ({len(open_ids)} open of {len(ORDER)})")
    return 0


def document_problems(rel: str, text: str) -> list[str]:
    lines = text.split("\n")
    out = guard_problems(14, rel, text)
    if not re.match(r"^# Discovery: \S", lines[0]):
        out.append(f"rule 5: {rel}: the first line is not `# Discovery: <title>`")
    starts = [i for i, ln in enumerate(lines) if START.match(ln)]
    ends = [i for i, ln in enumerate(lines) if ln == END]
    body = lines
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        out.append(f"rule 5: {rel}: the problem is not quoted between the two markers")
    else:
        s, e = starts[0], ends[0]
        marker = START.match(lines[s])
        if marker and digest("\n".join(lines[s + 1 : e])) != marker.group(1):
            out.append(f"rule 5: {rel}: the problem differs from its digest")
        body = lines[:s] + lines[e + 1 :]
    if not any(re.match(r"^- Problem: (?:https://\S+|vision)$", ln) for ln in body):
        out.append(f"rule 5: {rel}: the `- Problem:` line is missing")
    types = "|".join(re.escape(t) for t in WORK_TYPES)
    if not any(re.match(rf"^- Work type: (?:{types}) \(proposed\)$", ln) for ln in body):
        out.append(f"rule 5: {rel}: the `- Work type: <type> (proposed)` line is missing")
    if not any(re.match(r"^- Screens: (?:yes|no|open)$", ln) for ln in body):
        out.append(f"rule 5: {rel}: the `- Screens:` line is missing")
    sections: dict[str, list[str]] = {}
    current = None
    for ln in body:
        if ln.startswith("## "):
            current = ln[3:].strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(ln)
    for need in ("Answers", "Open points"):
        if need not in sections:
            out.append(f"rule 5: {rel}: the `## {need}` section is missing")
    seen: list[str] = []
    open_ids = []
    for ln in sections.get("Answers", []):
        m = ANSWER_ID.match(ln)
        if not m:
            continue
        qid = m.group(1)
        if qid in seen:
            out.append(f"rule 5: {rel}: `{qid}` is repeated")
            continue
        seen.append(qid)
        full = ANSWER.match(ln)
        if full and full.group(2):
            open_ids.append(qid)
        elif not full or not WHERE.match(full.group(4)):
            out.append(f"rule 5: {rel}: `{qid}` is not marked with where it was given")
    for qid in ORDER:
        if qid not in seen:
            out.append(f"rule 5: {rel}: `{qid}` is left out")
    for qid in seen:
        if qid not in ORDER:
            out.append(f"rule 5: {rel}: an answer names no question of rule 4")
    known = [q for q in seen if q in ORDER]
    if known != [q for q in ORDER if q in known]:
        out.append(f"rule 5: {rel}: the answers are not in rule 4's order")
    pointed = {m.group(1) for ln in sections.get("Open points", []) if (m := OPEN_POINT.match(ln))}
    for qid in open_ids:
        if qid not in pointed:
            out.append(f"rule 5: {rel}: `{qid}` is open with no D-<n> point")
    return out


def check_discovery(files: list[str], root: Path) -> int:
    paths = [Path(f) for f in files] or sorted((root / DIR).glob("*.md"))
    if not paths:
        print(f"ok {NAME}: no discovery document")
        return 0
    problems = []
    for path in paths:
        full = path if path.is_absolute() else root / path
        try:
            rel = full.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = path.name
        try:
            text = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            problems.append(f"rule 5: {rel}: not readable")
            continue
        problems += document_problems(rel, text)
    if problems:
        raise Refusal(problems)
    print(f"ok {NAME}: check-discovery ({len(paths)} documents)")
    return 0


def parse(argv: list[str]) -> tuple[str, dict[str, str], list[str]] | None:
    if not argv or argv[0] not in ("check-issue", "discovery-write", "check-discovery"):
        return None
    opts: dict[str, str] = {}
    rest: list[str] = []
    i = 1
    while i < len(argv):
        if argv[i] in ("--issue", "--vision", "--answers", "--root"):
            if i + 1 >= len(argv) or argv[i] in opts:
                return None
            opts[argv[i]] = argv[i + 1]
            i += 2
        elif argv[i].startswith("-"):
            return None
        else:
            rest.append(argv[i])
            i += 1
    return argv[0], opts, rest


def main(argv: list[str] | None = None) -> int:
    parsed = parse(list(sys.argv[1:] if argv is None else argv))
    if parsed is None:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, opts, rest = parsed
    root = Path(opts.get("--root", "."))
    if cmd == "check-issue":
        ok = set(opts) <= {"--issue", "--root"} and "--issue" in opts and not rest
    elif cmd == "discovery-write":
        doors = ("--issue" in opts) + ("--vision" in opts)
        ok = "--answers" in opts and doors == 1 and not rest
    else:
        ok = set(opts) <= {"--root"}
    if not ok:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        if cmd == "check-issue":
            return check_issue(Path(opts["--issue"]))
        if cmd == "discovery-write":
            return discovery_write(opts, root)
        return check_discovery(rest, root)
    except Refusal as refusal:
        for problem in refusal.problems:
            print(f"FAIL {NAME}: {problem}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
