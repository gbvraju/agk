"""The front door's entry, discovery, research, design and phase (SPEC-0048 builds (b), (d), (e)).

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
        (rule 7), and its review artifact, chosen by the `- Screens:` line of
        `docs/discovery/<its slug>.md` (`open`, or no such line or document, is read as `yes`):
        with `no`, exactly one line `Demo: docs/runs/<file>` naming a file that exists, which is
        never opened or run; with `yes`, a prototype version folder `docs/design/prototype/v<n>/`
        (checked by `check_design.py`). A `Walkthrough: <where it is kept>` line is judgement: it
        is noted, never opened, never printed and never the artifact (rule 8)
    front_door.py status --date YYYY-MM-DD [SLUG ...] [--root DIR]
        prints one line per problem (by default each `docs/discovery/*.md`), the phase of rule 1
        it is in and what it waits for, from the files only, and writes nothing; past the design
        it prints `waits for the go`, which is read from saved comments (rule 9; build (f))
    front_door.py check-signals
        checks the form of the signal table `config/stack-signals.toml` against `config/playbooks/`,
        both read from this script's own root and never from a repository (SPEC-0057 rule 5)
    front_door.py derive-write --slug SLUG [--modules NAME,NAME] [--root DIR]
        writes one engagement's skeleton `config/playbooks/<slug>.toml` from `default`, the named
        shipped modules and the slug of `docs/research/<slug>.md`, which must pass rule 6; never
        over a file, never in the kit, and only that file: no `agk.toml`, nothing under `kit/`
        (rule 22)
    front_door.py check-playbook --date YYYY-MM-DD [FILE ...] [--root DIR]
        the check of `check_playbooks.py` on each playbook (by default every one), then freshness
        from the gate sources: more than 180 days before `--date` is a `flag` line and exit 0, and
        a failure when a design under `docs/design/architecture/` names the playbook's path. The
        `reviewed` key of amendment 129 (verify) stays refused until it is approved (rule 25)

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
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import playbook_format
from guard import scan_text
from playbook_format import WORK_TYPES

NAME = "front-door"
USAGE = (
    "usage: front_door.py check-issue --issue FILE | discovery-write (--issue FILE | --vision FILE)"
    " --answers FILE [--root DIR] | check-discovery [FILE ...] [--root DIR]"
    " | (check-research | check-design) --date YYYY-MM-DD [FILE ...] [--root DIR]"
    " | status --date YYYY-MM-DD [SLUG ...] [--root DIR] | check-signals"
    " | derive-write --slug SLUG [--modules NAME,NAME] [--root DIR]"
    " | check-playbook --date YYYY-MM-DD [FILE ...] [--root DIR]"
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


# --- the review artifact (rule 8) and the phase (rules 1 and 9) ----------------------------------

RUNS = "docs/runs"
PROTOTYPE = "docs/design/prototype"
DEMO = re.compile(r"^Demo:(.*)$")
WALKTHROUGH = re.compile(r"^Walkthrough:(.*)$")
RUN_RECORD = re.compile(rf"^{RUNS}/[A-Za-z0-9_-][A-Za-z0-9._-]*$")
VERSION = re.compile(r"^v[1-9]\d*$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def screens_of(root: Path, name: str) -> str:
    """The `- Screens:` line of the problem's discovery document; `open` when there is none."""
    try:
        lines = (root / DIR / f"{name}.md").read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeDecodeError):
        return "open"
    quoted = False
    for ln in lines:
        if START.match(ln) or ANSWER_START.match(ln):
            quoted = True
        elif ln in (END, ANSWER_END):
            quoted = False
        elif ln.startswith("## "):
            break
        elif not quoted and (m := re.match(r"^- Screens: (yes|no|open)$", ln)):
            return m.group(1)
    return "open"


def artifact_problems(rel: str, text: str, root: Path) -> tuple[list[str], list[str]]:
    """Rule 8's problems and notes for one design; nothing named is opened or run."""
    lines = text.split("\n")
    out, notes = [], []
    demos = [m.group(1).strip() for ln in lines if (m := DEMO.match(ln))]
    walks = [m.group(1).strip() for ln in lines if (m := WALKTHROUGH.match(ln))]
    for where in walks:
        if where:
            notes.append(
                f"rule 8: {rel}: a `Walkthrough:` line is judgement, read by the conductor and"
                " the owner; no check opens it and it is never committed"
            )
        else:
            out.append(f"rule 8: {rel}: a `Walkthrough:` line names no place")
    if len(demos) > 1:
        out.append(f"rule 8: {rel}: the design names more than one `Demo:` line")
    for demo in demos[:1]:
        if not RUN_RECORD.match(demo) or ".." in demo:
            out.append(f"rule 8: {rel}: the `Demo:` line is not a run record under `{RUNS}/`")
        elif not (root / demo).is_file():
            out.append(f"rule 8: {rel}: the run record its `Demo:` line names does not exist")
    if screens_of(root, Path(rel).stem) == "no":
        if not demos:
            out.append(
                f"rule 8: {rel}: work without screens has no `Demo:` line naming its run record"
            )
        return out, notes
    folder = root / PROTOTYPE
    entries = list(folder.iterdir()) if folder.is_dir() else []
    if not any(p.is_dir() and VERSION.match(p.name) for p in entries):
        out.append(
            f"rule 8: {rel}: work with screens (or `Screens: open`) has no prototype version"
            f" under `{PROTOTYPE}/`"
        )
    return out, notes


def check_design(files: list[str], root: Path, today: datetime.date) -> int:
    problems: list[str] = []
    paths, designs = read_files(files, root, DESIGN, 7, problems)
    if not paths:
        print(f"ok {NAME}: no design")
        return 0
    for rel, text in designs:
        problems += design_problems(rel, text, root, today)
        found, notes = artifact_problems(rel, text, root)
        problems += found
        for note in notes:
            print(f"note {NAME}: {note}")
    if problems:
        raise Refusal(problems)
    print(f"ok {NAME}: check-design ({len(paths)} designs)")
    return 0


def phase_of(root: Path, name: str, today: datetime.date) -> str:
    """Rule 1's phase from the records on disk: each starts when the one before has its record."""
    paths = {k: f"{folder}/{name}.md" for k, folder in (("d", DIR), ("r", RESEARCH), ("a", DESIGN))}
    texts: dict[str, str | None] = {}
    for key, rel in paths.items():
        try:
            texts[key] = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            texts[key] = None
    if texts["d"] is None:
        return f"phase 2 discovery; waits for {paths['d']}"
    if document_problems(paths["d"], texts["d"]):
        return "phase 2 discovery; waits for the discovery document to pass check-discovery"
    if texts["r"] is None:
        return f"phase 3 research; waits for {paths['r']}"
    found, dates = research_problems(paths["r"], texts["r"])
    if found or stale(dates, today):
        return "phase 3 research; waits for the research record to pass check-research, fresh"
    if texts["a"] is None:
        return f"phase 4 design; waits for {paths['a']}"
    if design_problems(paths["a"], texts["a"], root, today):
        return "phase 4 design; waits for the design to pass check-design (rule 7)"
    if artifact_problems(paths["a"], texts["a"], root)[0]:
        return "phase 4 design; waits for its review artifact (rule 8)"
    return "phase 5 the go; waits for the go"


def status(names: list[str], root: Path, today: datetime.date) -> int:
    names = names or sorted(p.stem for p in (root / DIR).glob("*.md"))
    if not names:
        print(f"ok {NAME}: no discovery document")
    for name in names:
        print(f"{name}: {phase_of(root, name, today)}")
    return 0


SIGNALS = "config/stack-signals.toml"
PLAYBOOKS = "config/playbooks"
SIGNAL_SLUG = re.compile(r"^[a-z0-9-]+$")
SIGNAL_ROWS = {
    "stack": ("name", "manifests", "locks"),
    "work_type": ("name", "signal", "file", "contains"),
}


def is_word(value: object) -> bool:
    return isinstance(value, str) and bool(value) and not re.search(r"\s", value)


def is_words(value: object) -> bool:
    return isinstance(value, list) and all(is_word(item) for item in value)


SIGNAL_FORM = {
    "name": is_word,
    "manifests": lambda v: is_words(v) and bool(v),
    "locks": is_words,
    "signal": lambda v: isinstance(v, str) and bool(SIGNAL_SLUG.match(v)),
    "file": is_word,
    "contains": is_word,
}


def signal_row_problems(kind: str, rows: object) -> list[str]:
    """The form of each `[[stack]]` or `[[work_type]]` row, and what no row may be named."""
    if not isinstance(rows, list) or not rows:
        return [f"rule 5: {SIGNALS}: [[{kind}]] has no row"]
    found: list[str] = []
    for number, row in enumerate(rows, 1):
        where = f"rule 5: {SIGNALS}: [[{kind}]] row {number}"
        if not isinstance(row, dict):
            found.append(f"{where} is not a table")
            continue
        if set(row) - set(SIGNAL_ROWS[kind]):
            found.append(f"{where} has an unknown key")
        for key in SIGNAL_ROWS[kind]:
            if not SIGNAL_FORM[key](row.get(key)):
                found.append(f"{where} `{key}` is missing or malformed")
        if row.get("name") == "default":
            found.append(f"{where} `name` holds the base playbook")
        if row.get("name") == "pilot":
            found.append(f"{where} `name` holds the kind never proposed")
    return found


def signal_problems(root: Path) -> list[str]:
    """Rule 5's form check of the table, naming the setting and never a value."""
    try:
        table = tomllib.loads((root / SIGNALS).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return [f"rule 5: {SIGNALS} cannot be read"]
    head = f"rule 5: {SIGNALS}:"
    found = (
        []
        if set(table) <= {*SIGNAL_ROWS, "no_signal", "ignore"}
        else [f"{head} an unknown top-level key"]
    )
    for kind in SIGNAL_ROWS:
        found += signal_row_problems(kind, table.get(kind))
    for key in ("no_signal", "ignore"):
        if not is_words(table.get(key)):
            found.append(f"{head} `{key}` is not a list of names")
    if found:
        return found
    held = set(table["no_signal"])
    named = {row["name"] for row in table["work_type"]}
    files = {path.stem for path in (root / PLAYBOOKS).glob("*.toml")}
    for number, row in enumerate(table["work_type"], 1):
        if row["name"] not in files:
            found.append(f"{head} [[work_type]] row {number} `name` has no file in {PLAYBOOKS}/")
    if "default" in held:
        found.append(f"{head} `no_signal` holds the base playbook")
    if "pilot" not in held:
        found.append(f"{head} `no_signal` lacks the kind never proposed")
    if held - files - {"pilot"}:
        found.append(f"{head} `no_signal` holds a name with no file in {PLAYBOOKS}/")
    if files - named - held - {"default"}:
        found.append(f"{head} a playbook has no row and is not in `no_signal`")
    if named & held:
        found.append(f"{head} `no_signal` holds a name that has rows")
    return found


def check_signals(root: Path) -> int:
    found = signal_problems(root)
    if found:
        raise Refusal(found)
    print(f"ok {NAME}: {SIGNALS}")
    return 0


def _toml(value: object) -> str:
    """A string or a list of strings as TOML: JSON's escapes are TOML's."""
    return json.dumps(value, ensure_ascii=False)


def skeleton(name: str, modules: list[str], base: dict) -> str:
    """The derived playbook's text: `default`'s discovery, testing profile and milestones, and
    the modules; its gates and evidence come by composition, so they have one home (rule 23)."""
    lines = [
        "# The derived playbook of one engagement. The architect fills its phases, lanes, evidence",
        "# and gates in the design's pull request. Replace `gates = []` with [[gates]] tables,",
        '# each with `source = "<URL> (accessed YYYY-MM-DD)"` or `basis = "expected"`.',
        "format = 1",
        f"work_type = {_toml(name)}",
        'title = "A derived playbook, written for one engagement"',
        "heavy_steps = []",
        "evidence = []",
        "phases = []",
        "lanes = []",
        "claims = []",
        "gates = []",
    ]
    if modules:
        lines.append(f"modules = {_toml(modules)}")
    lines += ["", "[split]", "brief_order = []", "depends_on = []", "", "[testing]"]
    lines += [f"profile = {_toml(base['testing']['profile'])}", "always_full = []", "map = []"]
    milestones = base["milestones"]
    lines += ["", "[milestones]", f"shape = {_toml(milestones['shape'])}"]
    lines.append(f"batch_by = {_toml(milestones['batch_by'])}")
    for row in base["discovery"]:
        lines += ["", "[[discovery]]", f"id = {_toml(row['id'])}", f"text = {_toml(row['text'])}"]
    return "\n".join(lines) + "\n"


def derive_write(opts: dict[str, str], root: Path) -> int:
    """Rule 22: writes the skeleton, or refuses and leaves nothing behind."""
    name = opts["--slug"]
    if not SLUG.match(name):
        raise Refusal(["rule 22: `--slug` is not a slug of rule 5"])
    if name in WORK_TYPES or name == playbook_format.BASE:
        raise Refusal(["rule 22: `--slug` names a shipped playbook"])
    if (root / "kit" / "manifest.json").is_file():
        raise Refusal(["rule 22: a derived playbook is the project's, never the kit's (kit/)"])
    rel = f"{playbook_format.FOLDER}/{name}.toml"
    target = root / rel
    if target.exists():
        raise Refusal([f"rule 22: {rel}: the file exists and is never overwritten"])
    base_path = root / playbook_format.FOLDER / f"{playbook_format.BASE}.toml"
    if not base_path.is_file() or playbook_format.problems(base_path, root):
        raise Refusal([f"rule 22: {playbook_format.FOLDER}/default.toml: missing or not sound"])
    record = root / RESEARCH / f"{name}.md"
    record_rel = f"{RESEARCH}/{name}.md"
    if not record.is_file():
        raise Refusal([f"rule 22: {record_rel}: the research record is missing"])
    try:
        text = record.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise Refusal([f"rule 6: {record_rel}: not readable"]) from None
    found, _ = research_problems(record_rel, text)
    if found:
        raise Refusal(found)
    modules = [m for m in opts.get("--modules", "").split(",") if m]
    base = tomllib.loads(base_path.read_text(encoding="utf-8"))
    import check_playbooks  # here, so a load failure leaves every other command as it is

    target.write_text(skeleton(name, modules, base), encoding="utf-8")
    found = check_playbooks.findings(root, [target])
    if found:
        target.unlink()
        raise Refusal(found)
    print(f"ok {NAME}: wrote {rel}")
    return 0


def design_text(root: Path) -> str:
    """Every design's text, to find which playbooks a design names (rule 25)."""
    texts = []
    for path in sorted((root / DESIGN).glob("*.md")):
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return "\n".join(texts)


def check_playbook(files: list[str], root: Path, today: datetime.date) -> int:
    """Rule 25: the check of `check_playbooks.py`, then the freshness of the gate sources."""
    named = [Path(f) if Path(f).is_absolute() else root / f for f in files]
    missing = [rel_of(path, root) for path in named if not path.is_file()]
    if missing:
        raise Refusal([f"rule 25: {rel}: not readable" for rel in missing])
    import check_playbooks  # here, so a load failure leaves every other command as it is

    paths = named or playbook_format.playbooks(root)
    found = check_playbooks.findings(root, paths)
    designs = design_text(root)
    for path in paths:
        if not stale(playbook_format.source_dates(path), today):
            continue
        rel = rel_of(path, root)
        line = f"rule 25: {rel}: a gate source is more than {FRESH_DAYS} days old"
        if rel in designs:
            found.append(f"{line} and a design names the playbook")
        else:
            print(f"flag {NAME}: {line}")
    if found:
        raise Refusal(found)
    print(f"ok {NAME}: {len(paths)} playbooks")
    return 0


COMMANDS = (
    "check-issue",
    "discovery-write",
    "check-discovery",
    "check-research",
    "check-design",
    "status",
    "check-signals",
    "derive-write",
    "check-playbook",
)


def parse(argv: list[str]) -> tuple[str, dict[str, str], list[str]] | None:
    if not argv or argv[0] not in COMMANDS:
        return None
    opts: dict[str, str] = {}
    rest: list[str] = []
    i = 1
    while i < len(argv):
        if argv[i] in (
            "--issue",
            "--vision",
            "--answers",
            "--root",
            "--date",
            "--slug",
            "--modules",
        ):
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
    elif cmd == "check-signals":
        ok = not opts and not rest
    elif cmd == "derive-write":
        ok = "--slug" in opts and set(opts) <= {"--slug", "--modules", "--root"} and not rest
    else:
        ok = set(opts) <= {"--root", "--date"} and iso_date(opts.get("--date", "")) is not None
        if cmd == "status":
            ok = ok and all(SLUG.match(name) for name in rest)
    today = iso_date(opts.get("--date", "")) or datetime.date.min
    if not ok:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        if cmd == "check-signals":
            return check_signals(Path(__file__).resolve().parents[2])
        if cmd == "check-issue":
            return check_issue(Path(opts["--issue"]))
        if cmd == "discovery-write":
            return discovery_write(opts, root)
        if cmd == "check-discovery":
            return check_discovery(rest, root)
        if cmd == "check-research":
            return check_research(rest, root, today)
        if cmd == "status":
            return status(rest, root, today)
        if cmd == "derive-write":
            return derive_write(opts, root)
        if cmd == "check-playbook":
            return check_playbook(rest, root, today)
        return check_design(rest, root, today)
    except Refusal as refusal:
        for problem in refusal.problems:
            print(f"FAIL {NAME}: {problem}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
