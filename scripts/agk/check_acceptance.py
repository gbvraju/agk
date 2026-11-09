"""The acceptance record and its check (SPEC-0051 rules 2 to 5 and 7; REQ-058). Installed: a
verbatim entry of `kit/manifest.json`; a step of `agk-governance` after `check_runbooks.py`.

    python3 scripts/agk/check_acceptance.py [--root DIR]
    python3 scripts/agk/check_acceptance.py status [--root DIR]

The check reads every `docs/acceptance/<slug>.md` and prints `ok acceptance (<n> records)`, or one
`FAIL acceptance: rule <n>: <file>: <problem>` line per problem and exits 1, naming the rule of
SPEC-0051 and the file and never a quote, a value or an answer. `status` prints one line per record,
`<slug> accepted`, `<slug> accepted with <n> not met`, `<slug> proposed` or `<slug> stale`, and
writes nothing; a record the check refuses for anything but its status is never shown as accepted.

Files only: no network, and no piece of evidence is ever run or opened beyond parsing a named test
file. The discovery document is read through `front_door.py`. An `accepted` status fails until
build (c) can read the owner's yes (rule 6). Exit 0 ok, 1 refused, 2 usage.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import config_source, repo_root, run
from front_door import (
    ANSWER_END,
    ANSWER_START,
    DIR,
    END,
    RUN_RECORD,
    SLUG,
    START,
    document_problems,
    guard_problems,
    sections_of,
)
from impact import matches

NAME = "acceptance"
FOLDER = "docs/acceptance"
USAGE = "usage: check_acceptance.py [status] [--root DIR]"
NO_GOALS = "not known yet"
NOT_MET = "not met"
DIGEST = re.compile(r"- Success digest: ([0-9a-f]{64})")
STATUS = re.compile(r"- Status: (proposed|accepted)")
GOAL = re.compile(r'- G-([1-9]\d*): "(.+)" -> (.+)')
PATH = r"[A-Za-z0-9_-][A-Za-z0-9._-]*(?:/[A-Za-z0-9_-][A-Za-z0-9._-]*)*"
TEST = re.compile(rf"test ({PATH})::(test\w*)")
WORD = re.compile(r"\w+")

Goal = tuple[int, str, str]


def inside(root: Path, rel: str) -> Path | None:
    """The regular file at `rel` when it is one and does not lead out of the tree, else None."""
    full = root / rel
    try:
        fits = full.resolve().is_relative_to(root.resolve())
    except (OSError, RuntimeError):
        return None
    return full if fits and full.is_file() else None


def read(path: Path | None) -> str | None:
    try:
        return path.read_text(encoding="utf-8") if path is not None else None
    except (OSError, UnicodeDecodeError):
        return None


def success_of(text: str) -> tuple[str | None, str]:
    """The digest and words of the `success` answer of a document `document_problems` passed."""
    lines = text.split("\n")
    if lines.count(END) == 1:
        first = next(i for i, ln in enumerate(lines) if START.match(ln))
        lines = lines[:first] + lines[lines.index(END) + 1 :]
    rows = [ln for name, body in sections_of(lines) if name == "Answers" for ln in body]
    i = 0
    while i < len(rows):
        quote = ANSWER_START.match(rows[i])
        if quote:
            end = rows.index(ANSWER_END, i + 1)
            if rows[i - 1].startswith("- success:"):
                return quote.group(1), "\n".join(rows[i + 1 : end])
            i = end
        i += 1
    return None, ""


def one_line(rule: int, rel: str, what: str) -> str:
    return f"rule {rule}: {rel}: {what}"


def form_of(rel: str, stem: str, lines: list[str]) -> tuple[list[str], list[Goal]]:
    """Rule 3: the lines and the section; the goals as written."""
    out = []
    if not SLUG.fullmatch(stem):
        out.append(one_line(3, rel, "the file name is not a slug"))
    if not re.match(r"# Acceptance: \S", lines[0]):
        out.append(one_line(3, rel, "the first line is not `# Acceptance: <title>`"))
    goals_at = lines.index("## Goals") if "## Goals" in lines else None
    head = lines if goals_at is None else lines[:goals_at]
    for label, shape in (
        ("Discovery", re.compile(rf"- Discovery: {re.escape(DIR)}/{re.escape(stem)}\.md")),
        ("Success digest", DIGEST),
        ("Status", STATUS),
    ):
        named = [ln for ln in head if ln.startswith(f"- {label}:")]
        if len(named) != 1 or not shape.fullmatch(named[0]):
            out.append(one_line(3, rel, f"the `- {label}:` line is missing, wrong or repeated"))
    if goals_at is None:
        return [*out, one_line(3, rel, "the `## Goals` section is missing")], []
    if lines.count("## Goals") > 1:
        out.append(one_line(3, rel, "the `## Goals` section is repeated"))
    goals: list[Goal] = []
    for ln in dict(sections_of(lines)).get("Goals", []):
        found = GOAL.fullmatch(ln)
        if found:
            goals.append((int(found[1]), found[2], found[3]))
        elif ln.strip():
            out.append(one_line(3, rel, "a line of `## Goals` is not a goal of the form"))
    if not goals and not out:
        out.append(one_line(3, rel, "`## Goals` holds no goal"))
    return out, goals


def goal_problems(rel: str, answer: str, goals: list[Goal]) -> list[str]:
    """Rule 2: numbered once from G-1, and the quotes, once each and in order, make the answer."""
    numbers = [n for n, _, _ in goals]
    quotes = [q for _, q, _ in goals]
    out = []
    if len(set(numbers)) != len(numbers):
        out.append(one_line(2, rel, "a goal is repeated"))
    elif numbers != list(range(1, len(numbers) + 1)):
        out.append(one_line(2, rel, "the goals are not numbered G-1 to G-<n> in order"))
    if len(set(quotes)) != len(quotes):
        out.append(one_line(2, rel, "a quote is repeated"))
    if any(q not in answer for q in quotes):
        out.append(one_line(2, rel, "a quote is not in the `success` answer"))
    if any(not WORD.search(q) for q in quotes):
        out.append(one_line(2, rel, "a quote holds no word"))
    if out:
        return out
    spans = []
    at = 0
    for quote in quotes:
        start = answer.find(quote, at)
        if start < 0:
            return [one_line(2, rel, "the quotes are not in the order of the answer")]
        spans.append((start, start + len(quote)))
        at = start + len(quote)
    for word in WORD.finditer(answer):
        held = any(s <= word.start() and word.end() <= e for s, e in spans)
        if not held and word[0] != "and":
            return [one_line(2, rel, "the quotes do not together make the answer")]
    return []


def test_globs(root: Path) -> list[str]:
    """The test globs of the project's `[testing]` map; none when the settings cannot be read."""
    try:
        table = config_source(root).get("testing")
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return []
    entries = table.get("map") if isinstance(table, dict) else None
    globs: list[str] = []
    for entry in entries if isinstance(entries, list) else []:
        tests = entry.get("tests") if isinstance(entry, dict) else None
        globs += [g for g in tests if isinstance(g, str)] if isinstance(tests, list) else []
    return globs


def defines_test(path: Path, name: str) -> bool:
    """Whether the Python file defines `name` in its module or a class; the file is never run."""
    try:
        body = ast.parse(path.read_text(encoding="utf-8")).body
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
        return False
    while body:
        node = body.pop()
        if isinstance(node, ast.ClassDef):
            body += node.body
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return True
    return False


def item_problem(root: Path, globs: list[str], item: str) -> tuple[int, str] | None:
    """Rule 4: one evidence item of the three kinds, naming a file that exists on the tree."""
    kind, _, where = item.partition(" ")
    if kind in ("run", "demo"):
        if not RUN_RECORD.fullmatch(where):
            return 4, f"a `{kind}` item does not name a file directly under docs/runs/"
        return None if inside(root, where) else (4, f"the file of a `{kind}` item does not exist")
    if kind != "test":
        return 4, "an evidence item is of no known kind"
    found = TEST.fullmatch(item)
    if not found:
        return 4, "a `test` item is not `test <path>::<name>`"
    rel, name = found[1], found[2]
    if not rel.startswith("tests/") and not any(matches(rel, g) for g in globs):
        return 4, "the file of a `test` item is not under tests/ or in the `[testing]` map"
    path = inside(root, rel)
    if path is None:
        return 4, "the file of a `test` item does not exist"
    if path.suffix != ".py" or not defines_test(path, name):
        return 4, "the file of a `test` item defines no such Python test function"
    return None


def evidence_problems(root: Path, rel: str, goals: list[Goal]) -> list[str]:
    globs = test_globs(root)
    out: list[str] = []
    for _, _, evidence in goals:
        items = evidence.split(", ")
        if NOT_MET in items and len(items) > 1:
            out.append(one_line(3, rel, "a goal is both `not met` and has evidence"))
            continue
        for item in items:
            problem = None if item == NOT_MET else item_problem(root, globs, item)
            if problem and one_line(problem[0], rel, problem[1]) not in out:
                out.append(one_line(problem[0], rel, problem[1]))
    return out


def inspect(root: Path, path: Path) -> tuple[list[str], str]:
    """The problems of one record and its state of rule 7."""
    rel = f"{FOLDER}/{path.name}"
    text = read(inside(root, rel))
    if text is None:
        return [one_line(3, rel, "not readable")], "stale"
    found = guard_problems(5, rel, text)
    lines = text.split("\n")
    stem = path.stem
    form, goals = form_of(rel, stem, lines)
    if form:
        return found + form, "proposed"
    doc_rel = f"{DIR}/{stem}.md"
    doc = read(inside(root, doc_rel))
    if doc is None:
        return [*found, one_line(3, rel, "the discovery document does not exist")], "stale"
    if document_problems(doc_rel, doc):
        return [*found, one_line(2, rel, "the discovery document fails its own check")], "stale"
    if lines[0].removeprefix("# Acceptance: ") != doc.split("\n")[0].removeprefix("# Discovery: "):
        return [*found, one_line(3, rel, "the title is not the discovery document's")], "proposed"
    digest, answer = success_of(doc)
    if digest is None or answer.strip().rstrip(".").casefold() == NO_GOALS:
        return [*found, one_line(2, rel, "the `success` answer is open: no goals")], "stale"
    named = next(m for ln in lines if (m := DIGEST.fullmatch(ln)))
    if named[1] != digest:
        return [*found, one_line(2, rel, "stale: the digest is not the answer's")], "stale"
    out = found + goal_problems(rel, answer, goals) + evidence_problems(root, rel, goals)
    accepted = next(m for ln in lines if (m := STATUS.fullmatch(ln)))[1] == "accepted"
    if out or not accepted:
        state = "proposed"
    else:
        unmet = sum(1 for _, _, evidence in goals if evidence == NOT_MET)
        state = f"accepted with {unmet} not met" if unmet else "accepted"
    if accepted:
        out.append(one_line(6, rel, "`accepted` needs the owner's yes, not readable yet"))
    return out, state


def records(root: Path) -> list[Path]:
    return sorted((root / FOLDER).glob("*.md"))


def cmd_check(root: Path) -> int:
    paths = records(root)
    problems = [p for path in paths for p in inspect(root, path)[0]]
    if problems:
        for problem in problems:
            print(f"FAIL {NAME}: {problem}")
        return 1
    print(f"ok {NAME} ({len(paths)} records)")
    return 0


def cmd_status(root: Path) -> int:
    for path in records(root):
        print(f"{path.stem} {inspect(root, path)[1]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    status = args[:1] == ["status"]
    args = args[1:] if status else args
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if (root is None and args) or (root is not None and not root.is_dir()):
        print(USAGE, file=sys.stderr)
        return 2
    return run(NAME, lambda: (cmd_status if status else cmd_check)(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
