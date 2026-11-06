"""The rule budget and the rules agents drop (brief 647, ADR-0310). Kit-only: never installed.

    python3 rules.py budget [--root DIR] [--check]
    python3 rules.py dropped --since YYYY-MM-DD [--root DIR] [--repo OWNER/REPO] [--api-dir DIR]

`budget` prints `<path> <words> <rule lines>` for each instruction file an agent reads: the four
core files, every file under `.claude/agents/` and `config/review-checklist.md`. A rule line is a
numbered or bulleted line outside the front matter and fenced code. With `--check` it compares the
counts with `config/rule-budget.txt` and exits 1 on any difference, naming the file.

`dropped` reads, with `gh api` GET only or from recorded responses (`--api-dir`: `pulls.json` and
`comments-<n>.json`), the open and merged pull requests updated since DATE, and counts the numbered
items of the `Verdict: fix list` comments by a listed verdict author posted since DATE: one line
per rule tag, newest first, then the items with no tag as references only (never comment text).
An unreadable pull request list is `unknown` (exit 1); a bad call exits 2.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, agent_apps, fix_items, item_tag, repo_root
from metrics import ApiDir, Gh, author_of, origin_repo
from reviewers import confirmed_comments, solo_person, verdict_authors

CORE = (
    "CLAUDE.md",
    "constitution/principles.md",
    "config/core-rules.md",
    "config/session-rules.md",
)
CHECKLIST = "config/review-checklist.md"
AGENTS = ".claude/agents"
BASELINE = "config/rule-budget.txt"
RULE_LINE = re.compile(r"\s*(?:\d+\.|[-*+])\s+\S")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
ADDED_RULE = "a rule was added: retire one, or make it a check, in the same pull request"
ADDED_WORDS = (
    "words were added: cut words, or move the how-to into a guide, in the same pull request"
)
LOWER = "lower the baseline to the file in the same pull request"
USAGE = (
    "usage: rules.py budget [--root DIR] [--check] | "
    "rules.py dropped --since YYYY-MM-DD [--root DIR] [--repo OWNER/REPO] [--api-dir DIR]"
)


# --- budget (brief 647 answer 1) --------------------------------------------------------------


def counts(text: str) -> tuple[int, int]:
    """(words of the whole file, rule lines outside the front matter and fenced code)."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        start = end + 1 if end is not None else 0
    rules, fenced = 0, False
    for line in lines[start:]:
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and RULE_LINE.match(line):
            rules += 1
    return len(text.split()), rules


def instruction_files(root: Path) -> list[str]:
    """The files an agent reads: the four core files, the agent files, the review checklist."""
    agents = sorted(
        p.relative_to(root).as_posix() for p in (root / AGENTS).glob("*.md") if p.is_file()
    )
    return [*CORE, *agents, CHECKLIST]


def budget_lines(root: Path) -> list[str]:
    out = []
    for rel in instruction_files(root):
        path = root / rel
        if path.is_file():
            words, rules = counts(path.read_text(encoding="utf-8"))
            out.append(f"{rel} {words} {rules}")
    return out


def read_baseline(root: Path) -> tuple[dict[str, tuple[int, int]], list[str]]:
    try:
        text = (root / BASELINE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}, [f"{BASELINE}: cannot be read"]
    found: dict[str, tuple[int, int]] = {}
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
            problems.append(f"{BASELINE}: line {number} is not '<path> <words> <rule lines>'")
            continue
        found[parts[0]] = (int(parts[1]), int(parts[2]))
    return found, problems


def budget_problems(root: Path) -> list[str]:
    """Each difference between the files and `config/rule-budget.txt`, naming the file."""
    baseline, problems = read_baseline(root)
    if problems:
        return problems
    for rel in instruction_files(root):
        path = root / rel
        if not path.is_file():
            if rel in baseline:
                problems.append(f"{rel}: the file is gone; remove its line from {BASELINE}")
            continue
        if rel not in baseline:
            problems.append(f"{rel}: not in the baseline; add its line to {BASELINE}")
            continue
        words, rules = counts(path.read_text(encoding="utf-8"))
        max_words, max_rules = baseline.pop(rel)
        if rules > max_rules:
            problems.append(f"{rel}: {rules} rule lines, baseline {max_rules}; {ADDED_RULE}")
        elif rules < max_rules:
            problems.append(f"{rel}: {rules} rule lines, baseline {max_rules}; {LOWER}")
        if words > max_words:
            problems.append(f"{rel}: {words} words, baseline {max_words}; {ADDED_WORDS}")
        elif words < max_words:
            problems.append(f"{rel}: {words} words, baseline {max_words}; {LOWER}")
    for rel in sorted(set(baseline) - set(instruction_files(root))):
        problems.append(f"{rel}: not an instruction file; remove its line from {BASELINE}")
    return problems


def budget(root: Path, check: bool) -> int:
    if not check:
        for line in budget_lines(root):
            print(line)
        return 0
    problems = budget_problems(root)
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print("ok rule-budget")
    return 0


# --- dropped (brief 647 answer 2) -------------------------------------------------------------


def dropped(root: Path, since: str, repo: str | None, api: str | None) -> int:
    src = ApiDir(Path(api)) if api else Gh(repo or origin_repo())
    pulls = src.get(
        "pulls",
        "repos/{repo}/pulls?state=all&sort=updated&direction=desc",
        lambda chunk: bool(chunk) and str(chunk[-1].get("updated_at") or "")[:10] < since,
    )
    if not isinstance(pulls, list):
        print("dropped: unknown (the pull requests cannot be read)")
        return 1
    authors = {a.lstrip("@").lower() for a in verdict_authors(root) or []}
    tags: dict[str, list[str]] = {}
    untagged: list[str] = []
    unread: list[int] = []
    verdicts, prs = 0, set()
    for pull in pulls:
        number = pull.get("number")
        if not isinstance(number, int) or str(pull.get("updated_at") or "")[:10] < since:
            continue
        if pull.get("state") != "open" and not pull.get("merged_at"):
            continue
        notes = src.get(f"comments-{number}", f"repos/{{repo}}/issues/{number}/comments")
        if not isinstance(notes, list):
            unread.append(number)
            continue
        notes = confirmed_comments(notes, agent_apps(root), solo_person(root))
        for note in notes:
            at = str(note.get("created_at") or "")
            if author_of(note) not in authors or at[:10] < since:
                continue
            items = fix_items(str(note.get("body") or ""))
            if not items:
                continue
            verdicts += 1
            prs.add(number)
            for n, item in enumerate(items, 1):
                tag = item_tag(item)
                if tag is None:
                    untagged.append(f"untagged #{number} comment {note.get('id')} item {n}")
                else:
                    tags.setdefault(tag, []).append(at)
    total = sum(len(v) for v in tags.values()) + len(untagged)
    print(
        f"dropped since {since}: {total} fix-list items in {verdicts} verdicts "
        f"on {len(prs)} pull requests"
    )
    # newest first; on the same time the larger count first
    for tag, ats in sorted(tags.items(), key=lambda kv: (max(kv[1]), len(kv[1])), reverse=True):
        print(f"{len(ats)} {tag} (newest {max(ats)[:10]})")
    print(f"untagged: {len(untagged)}")
    for line in untagged:
        print(line)
    for number in unread:
        print(f"unread: #{number}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in ("budget", "dropped"):
        print(USAGE)
        return 2
    command, rest = args[0], args[1:]
    flags = {"--check"} if command == "budget" else set()
    valued = {"--root"} | ({"--since", "--repo", "--api-dir"} if command == "dropped" else set())
    opts: dict[str, str] = {}
    i = 0
    while i < len(rest):
        if rest[i] in flags:
            opts[rest[i]] = ""
            i += 1
        elif rest[i] in valued and i + 1 < len(rest):
            opts[rest[i]] = rest[i + 1]
            i += 2
        else:
            print(USAGE)
            return 2
    root = Path(opts["--root"]).resolve() if "--root" in opts else repo_root()
    if command == "budget":
        return budget(root, "--check" in opts)
    if not DATE.fullmatch(opts.get("--since", "")):
        print(USAGE)
        return 2
    try:
        return dropped(root, opts["--since"], opts.get("--repo"), opts.get("--api-dir"))
    except CheckError as exc:
        print(f"dropped: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
