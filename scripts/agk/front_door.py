"""The front door's entry, discovery, research and design (SPEC-0048 builds (b) and (d)).

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
    front_door.py check-research --date YYYY-MM-DD [FILE ...] [--root DIR]
        checks each research record (by default every `docs/research/*.md`): at least two
        `## Option: <name>` sections each with a `- Source: <URL> (accessed YYYY-MM-DD)` line, a
        `## Criteria` table with a row for each of the seven criteria, and a `## Recommendation`
        marked `(proposal)`; a record a design cites is stale when any source was accessed more
        than 180 days before `--date` (rules 6 and 14)
    front_door.py check-design --date YYYY-MM-DD [FILE ...] [--root DIR]
        checks each architecture file (by default every `docs/design/architecture/*.md`): a
        fenced text or Mermaid diagram, no image, and exactly one line
        `Research: docs/research/<its slug>.md` naming a record that passes rule 6 and is fresh
        (rule 7)

The answers file: `{"screens": "yes|no|open", "work_type": "<work type>", "answers": [{"id":
"<id>", "answer": "<words>", "where": "<comment link>|in session YYYY-MM-DD"} or {"id": "<id>",
"open": true}], "points": [{"text": "<words>", "where": "..."}]}`; `screens` defaults to `open`
and `work_type` to the issue's `Kind:` line, else `pilot`. Each answer is written as given, line
endings made `\n`, between `<!-- agk:answer sha256=… -->` and `<!-- agk:answer-end -->` under its
bullet `- <id>: (given: <where>)`, as the problem is under its digest. Every refusal names the rule
and the file or the setting, never a value, a problem's words or an answer (rule 15). Exit 0 ok,
1 refused, 2 usage.
"""

from __future__ import annotations

import datetime
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
    " | (check-research | check-design) --date YYYY-MM-DD [FILE ...] [--root DIR]"
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
ANSWER = re.compile(r"^- ([a-z0-9-]+): (?:(open)|\(given: (.+)\))$")
ANSWER_START = re.compile(r"^<!-- agk:answer sha256=([0-9a-f]{64}) -->$")
ANSWER_END = "<!-- agk:answer-end -->"
MARK = "<!-- agk:"
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
        where = row.get("where")
        if not isinstance(where, str) or not WHERE.fullmatch(where):
            problems.append(f"rule 5: {rel}: `{qid}` is not marked with where it was given")
            where = ""
        words = row["answer"]
        if not isinstance(words, str):
            problems.append(f"rule 5: {rel}: `{qid}` is not text")
            continue
        words = words.replace("\r\n", "\n").replace("\r", "\n")
        if MARK in words:
            problems.append(f"rule 5: {rel}: `{qid}` holds a marker of the document")
            continue
        # The answer as given, between two markers with its digest, as the problem is (rule 5).
        start = f"<!-- agk:answer sha256={digest(words)} -->"
        lines += [f"- {qid}: (given: {where})", start, words, ANSWER_END]
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
    rows = sections.get("Answers", [])
    i = 0
    while i < len(rows):
        ln = rows[i]
        i += 1
        m = ANSWER_ID.match(ln)
        if not m:
            continue
        qid = m.group(1)
        quote = ANSWER_START.match(rows[i]) if i < len(rows) else None
        if quote:
            end = rows.index(ANSWER_END, i + 1) if ANSWER_END in rows[i + 1 :] else -1
            if end < 0:
                out.append(f"rule 5: {rel}: `{qid}` is not quoted between the two markers")
                break
            if digest("\n".join(rows[i + 1 : end])) != quote.group(1):
                out.append(f"rule 5: {rel}: `{qid}` differs from its digest")
            i = end + 1
        if qid in seen:
            out.append(f"rule 5: {rel}: `{qid}` is repeated")
            continue
        seen.append(qid)
        full = ANSWER.match(ln)
        if full and full.group(2) and not quote:
            open_ids.append(qid)
        elif not full or full.group(2) or not WHERE.match(full.group(3)):
            out.append(f"rule 5: {rel}: `{qid}` is not marked with where it was given")
        elif not quote:
            out.append(f"rule 5: {rel}: `{qid}` is not quoted between the two markers")
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


# --- the research record (rule 6) and the design (rule 7) ----------------------------------------

RESEARCH = "docs/research"
DESIGN = "docs/design/architecture"
FRESH_DAYS = 180
# The seven criteria of SPEC-0038 rule 10, as SPEC-0048 rule 6 names them.
CRITERIA = (
    "capability fit",
    "cost",
    "licence",
    "data handling and residency",
    "maturity",
    "integration effort",
    "lock-in",
)
SOURCE = re.compile(r"^- Source: https?://\S+ \(accessed (\d{4}-\d{2}-\d{2})\)$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CITES = re.compile(r"^Research:(.*)$")
FENCE = re.compile(r"^```\s*(mermaid|text|txt|plain)?\s*$")
IMAGE = re.compile(r"!\[[^\]]*\]\(|<img\b", re.IGNORECASE)


def iso_date(text: str) -> datetime.date | None:
    if not ISO.match(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def sections_of(lines: list[str]) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for ln in lines:
        if ln.startswith("## "):
            out.append((ln[3:].strip(), []))
        elif out:
            out[-1][1].append(ln)
    return out


def research_problems(rel: str, text: str) -> tuple[list[str], list[datetime.date]]:
    """Rule 6's form of one record, and the access dates of its source lines."""
    lines = text.split("\n")
    out = guard_problems(14, rel, text)
    if not re.match(r"^# Research: \S", lines[0]):
        out.append(f"rule 6: {rel}: the first line is not `# Research: <title>`")
    dates = []
    for n, ln in enumerate(lines, 1):
        if not ln.startswith("- Source:"):
            continue
        m = SOURCE.match(ln)
        when = iso_date(m.group(1)) if m else None
        if when is None:
            out.append(
                f"rule 6: {rel}: line {n} is a source line without an access date"
                " (`- Source: <URL> (accessed YYYY-MM-DD)`)"
            )
        else:
            dates.append(when)
    sections = sections_of(lines)
    options = [body for head, body in sections if re.match(r"^Option: \S", head)]
    if len(options) < 2:
        out.append(f"rule 6: {rel}: the record has fewer than at least two options (`## Option:`)")
    for n, body in enumerate(options, 1):
        if not any((m := SOURCE.match(ln)) and iso_date(m.group(1)) for ln in body):
            out.append(f"rule 6: {rel}: option {n} has no source line with an access date")
    named = dict(sections)
    if "Criteria" not in named:
        out.append(f"rule 6: {rel}: the `## Criteria` section is missing")
    else:
        rows = {
            ln.strip().strip("|").split("|")[0].strip().lower()
            for ln in named["Criteria"]
            if ln.strip().startswith("|")
        }
        for need in CRITERIA:
            if need not in rows:
                out.append(f"rule 6: {rel}: the criteria table has no `{need}` row")
    if "Recommendation" not in named:
        out.append(f"rule 6: {rel}: the `## Recommendation` section is missing")
    elif not any("(proposal)" in ln for ln in named["Recommendation"]):
        out.append(f"rule 6: {rel}: the recommendation is not marked `(proposal)`")
    return out, dates


def stale(dates: list[datetime.date], today: datetime.date) -> bool:
    return any((today - when).days > FRESH_DAYS for when in dates)


def rel_of(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def read_files(files: list[str], root: Path, folder: str, rule: int, problems: list[str]):
    """(rel, text) of each named file, or of every `<folder>/*.md` when none is named."""
    paths = [Path(f) for f in files] or sorted((root / folder).glob("*.md"))
    out = []
    for path in paths:
        full = path if path.is_absolute() else root / path
        rel = rel_of(full, root)
        try:
            out.append((rel, full.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            problems.append(f"rule {rule}: {rel}: not readable")
    return paths, out


def cited_records(root: Path) -> set[str]:
    """The records every design under `docs/design/architecture/` names on a `Research:` line."""
    cited = set()
    for path in sorted((root / DESIGN).glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        cited |= {m.group(1).strip() for ln in text.split("\n") if (m := CITES.match(ln))}
    return cited


def check_research(files: list[str], root: Path, today: datetime.date) -> int:
    problems: list[str] = []
    paths, records = read_files(files, root, RESEARCH, 6, problems)
    if not paths:
        print(f"ok {NAME}: no research record")
        return 0
    cited = cited_records(root)
    for rel, text in records:
        found, dates = research_problems(rel, text)
        problems += found
        if not stale(dates, today):
            continue
        if rel in cited:
            problems.append(
                f"rule 6: {rel}: a source was accessed more than {FRESH_DAYS} days before the date"
                " given and a design cites the record; read its sources again and change their"
                " access dates"
            )
        else:
            print(
                f"note {NAME}: rule 6: {rel}: a source was accessed more than {FRESH_DAYS} days"
                " before the date given; no design cites it, so it is not stale yet"
            )
    if problems:
        raise Refusal(problems)
    print(f"ok {NAME}: check-research ({len(paths)} records)")
    return 0


def diagram_of(lines: list[str]) -> bool:
    """True when a fenced plain-text or Mermaid block holds at least one non-blank line."""
    i = 0
    while i < len(lines):
        if FENCE.match(lines[i].strip()):
            end = next((j for j in range(i + 1, len(lines)) if lines[j].strip() == "```"), None)
            if end is None:
                return False
            if any(ln.strip() for ln in lines[i + 1 : end]):
                return True
            i = end
        i += 1
    return False


def design_problems(rel: str, text: str, root: Path, today: datetime.date) -> list[str]:
    lines = text.split("\n")
    out = []
    if not diagram_of(lines):
        out.append(
            f"rule 7: {rel}: the design has no text diagram (a fenced Mermaid or plain-text block)"
        )
    if any(IMAGE.search(ln) for ln in lines):
        out.append(f"rule 7: {rel}: the design holds an image; the diagram is text only")
    cites = [m.group(1).strip() for ln in lines if (m := CITES.match(ln))]
    if len(cites) != 1:
        return out + [f"rule 7: {rel}: the design needs exactly one `Research:` line"]
    want = f"{RESEARCH}/{Path(rel).stem}.md"
    if cites[0] != want:
        why = "the `Research:` line does not name the record of its own slug"
        return out + [f"rule 7: {rel}: {why}"]
    target = root / want
    try:
        record = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        why = "the research record it names does not exist or is unreadable"
        return out + [f"rule 7: {rel}: {why}"]
    found, dates = research_problems(want, record)
    if found:
        out.append(f"rule 7: {rel}: its research record fails rule 6")
        out += found
    elif stale(dates, today):
        out.append(
            f"rule 7: {rel}: its research record is stale (rule 6: a source accessed more than"
            f" {FRESH_DAYS} days before the date given)"
        )
    return out


def check_design(files: list[str], root: Path, today: datetime.date) -> int:
    problems: list[str] = []
    paths, designs = read_files(files, root, DESIGN, 7, problems)
    if not paths:
        print(f"ok {NAME}: no design")
        return 0
    for rel, text in designs:
        problems += design_problems(rel, text, root, today)
    if problems:
        raise Refusal(problems)
    print(f"ok {NAME}: check-design ({len(paths)} designs)")
    return 0


COMMANDS = (
    "check-issue",
    "discovery-write",
    "check-discovery",
    "check-research",
    "check-design",
)


def parse(argv: list[str]) -> tuple[str, dict[str, str], list[str]] | None:
    if not argv or argv[0] not in COMMANDS:
        return None
    opts: dict[str, str] = {}
    rest: list[str] = []
    i = 1
    while i < len(argv):
        if argv[i] in ("--issue", "--vision", "--answers", "--root", "--date"):
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
        ok = "--answers" in opts and doors == 1 and not rest and "--date" not in opts
    elif cmd == "check-discovery":
        ok = set(opts) <= {"--root"}
    else:
        today = iso_date(opts.get("--date", ""))
        ok = set(opts) <= {"--root", "--date"} and today is not None
    if not ok:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        if cmd == "check-issue":
            return check_issue(Path(opts["--issue"]))
        if cmd == "discovery-write":
            return discovery_write(opts, root)
        if cmd == "check-discovery":
            return check_discovery(rest, root)
        if cmd == "check-research":
            return check_research(rest, root, today)
        return check_design(rest, root, today)
    except Refusal as refusal:
        for problem in refusal.problems:
            print(f"FAIL {NAME}: {problem}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
