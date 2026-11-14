"""The rule budget, the rules agents drop, and the cut of the rule set (brief 647, ADR-0310,
ADR-0404). Installed in projects.

    python3 rules.py budget [--root DIR] [--check]
    python3 rules.py dropped --since YYYY-MM-DD [--root DIR] [--repo OWNER/REPO] [--api-dir DIR]
    python3 rules.py consolidate --plan [--root DIR] [--since DATE] [--repo O/R] [--api-dir DIR]
    python3 rules.py consolidate --apply --hash HASH [--root DIR]

The instruction files are `[rules] files` in `agk.toml` (paths or globs, in order); without it, the
four core files, every file under `.claude/agents/` and `config/review-checklist.md`.

`budget` prints `<path> <words> <rule lines>` for each instruction file. A rule line is a
numbered or bulleted line outside the front matter and fenced code. With `--check` it compares the
counts with `config/rule-budget.txt` and exits 1 on any difference, naming the file.

`dropped` reads, with `gh api` GET only or from recorded responses (`--api-dir`: `pulls.json` and
`comments-<n>.json`), the open and merged pull requests updated since DATE, and counts the numbered
items of the `Verdict: fix list` comments by a listed verdict author posted since DATE: one line
per rule tag, newest first, then the items with no tag as references only (never comment text).
An unreadable pull request list is `unknown` (exit 1); a bad call exits 2.

`consolidate --plan` changes no file. It prints one row per rule line,
`<file>:<line> <n> <verdict> [<check>] <count>` (`<n>` is `-` for a bullet; the count is `-`
without `--since`), then `before:`, `after:` and `plan: <hash>`. A verdict other than `keep` comes
only from `config/rule-plan.txt` (`<file> <n> retire <check>` or `<file> <n> guide`); a retire
names a check that exists. `consolidate --apply --hash HASH` writes that plan into the working tree
(a pointer line keeps each number, the how-to goes to the guide, a retired rule gets a catch-log
line, the plan's applied lines are cleared and the budget baseline is rewritten), refuses a changed
plan or a dirty tree, and never commits.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    CheckError,
    agent_apps,
    config_source,
    fix_items,
    item_tag,
    repo_root,
    utf8_output,
)
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
PLAN = "config/rule-plan.txt"
GUIDE = "docs/guides/session-how-to.md"
CATCH_LOG = "docs/runs/rules-retired.md"
FILES_SETTING = "[rules] files"
NUMBERED = re.compile(r"(\s*)(\d+)\.\s+(.*)")
POINTER = re.compile(r"\s*\d+\.\s+(?:Merged into|Moved to|Retired:)")
USAGE = (
    "usage: rules.py budget [--root DIR] [--check] | "
    "rules.py dropped --since YYYY-MM-DD [--root DIR] [--repo OWNER/REPO] [--api-dir DIR] | "
    "rules.py consolidate --plan [--root DIR] [--since YYYY-MM-DD] [--repo O/R] [--api-dir DIR] | "
    "rules.py consolidate --apply --hash HASH [--root DIR]"
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


DEFAULT_FILES = (*CORE, f"{AGENTS}/*.md", CHECKLIST)


def instruction_files(root: Path) -> list[str]:
    """The files an agent reads: `[rules] files` of agk.toml (paths or globs, in order), else
    the four core files, the agent files and the review checklist; refusals name the setting."""
    try:
        table = config_source(root).get("rules", {})
    except (OSError, UnicodeDecodeError, ValueError):
        raise CheckError(f"agk.toml cannot be read (setting: {FILES_SETTING})") from None
    entries = table.get("files", DEFAULT_FILES) if isinstance(table, dict) else None
    if not isinstance(entries, (list, tuple)) or not all(
        isinstance(e, str) and e.strip() for e in entries
    ):
        raise CheckError(f"{FILES_SETTING} must be a list of paths or globs")
    out: list[str] = []
    for entry in entries:
        if any(ch in entry for ch in "*?["):
            found = sorted(p.relative_to(root).as_posix() for p in root.glob(entry) if p.is_file())
        else:
            found = [entry]
        out.extend(rel for rel in found if rel not in out)
    return out


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


def tag_counts(root: Path, since: str, repo: str | None, api: str | None) -> dict | None:
    """The fix-list items by a listed verdict author since DATE, by tag; None when the pull
    requests cannot be read (unknown, never 0)."""
    src = ApiDir(Path(api)) if api else Gh(repo or origin_repo())
    pulls = src.get(
        "pulls",
        "repos/{repo}/pulls?state=all&sort=updated&direction=desc",
        lambda chunk: bool(chunk) and str(chunk[-1].get("updated_at") or "")[:10] < since,
    )
    if not isinstance(pulls, list):
        return None
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
    return {"tags": tags, "untagged": untagged, "unread": unread, "verdicts": verdicts, "prs": prs}


def dropped(root: Path, since: str, repo: str | None, api: str | None) -> int:
    found = tag_counts(root, since, repo, api)
    if found is None:
        print("dropped: unknown (the pull requests cannot be read)")
        return 1
    tags, untagged = found["tags"], found["untagged"]
    total = sum(len(v) for v in tags.values()) + len(untagged)
    print(
        f"dropped since {since}: {total} fix-list items in {found['verdicts']} verdicts "
        f"on {len(found['prs'])} pull requests"
    )
    # newest first; on the same time the larger count first
    for tag, ats in sorted(tags.items(), key=lambda kv: (max(kv[1]), len(kv[1])), reverse=True):
        print(f"{len(ats)} {tag} (newest {max(ats)[:10]})")
    print(f"untagged: {len(untagged)}")
    for line in untagged:
        print(line)
    for number in found["unread"]:
        print(f"unread: #{number}")
    return 0


# --- consolidate (brief 647 build (b), ADR-0404) -----------------------------------------------


def rule_rows(text: str) -> list[tuple[int, str | None, int]]:
    """(1-based line, number or None for a bullet, lines in the block) of each rule line; a
    block is the line and the indented lines right after it that are not rule lines."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        start = end + 1 if end is not None else 0
    rows: list[tuple[int, str | None, int]] = []
    fenced = False
    for i in range(start, len(lines)):
        line = lines[i]
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or not RULE_LINE.match(line):
            continue
        size = 1
        while (
            i + size < len(lines)
            and lines[i + size][:1].isspace()
            and lines[i + size].strip()
            and not RULE_LINE.match(lines[i + size])
            and not lines[i + size].lstrip().startswith("```")
        ):
            size += 1
        number = NUMBERED.match(line)
        rows.append((i + 1, number.group(2) if number else None, size))
    return rows


def read_plan(root: Path, files: list[str]) -> tuple[dict[tuple[str, str], tuple], list[str]]:
    """The verdicts of `config/rule-plan.txt` by (file, number), and the problems, each naming
    the plan file. A missing plan file is an empty plan."""
    path = root / PLAN
    if not path.is_file():
        return {}, []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}, [f"{PLAN}: cannot be read"]
    plan: dict[tuple[str, str], tuple] = {}
    problems = []
    for at, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        where = f"{PLAN}: line {at}"
        if len(parts) == 4 and parts[2] == "retire":
            if not (root / parts[3]).is_file():
                problems.append(f"{where}: the check {parts[3]} is not found")
                continue
            entry: tuple = ("retire", parts[3])
        elif len(parts) == 3 and parts[2] == "guide":
            entry = ("guide",)
        else:
            problems.append(f"{where} is not '<file> <n> retire <check>' or '<file> <n> guide'")
            continue
        if parts[0] not in files or not (root / parts[0]).is_file():
            problems.append(f"{where}: {parts[0]} is not an instruction file")
            continue
        numbers = [n for _, n, _ in rule_rows((root / parts[0]).read_text(encoding="utf-8"))]
        if numbers.count(parts[1]) != 1:
            problems.append(f"{where}: {parts[0]} has no one numbered rule {parts[1]}")
            continue
        if (parts[0], parts[1]) in plan:
            problems.append(f"{where}: {parts[0]} {parts[1]} is planned twice")
            continue
        plan[(parts[0], parts[1])] = entry
    return plan, problems


def build_plan(root: Path) -> tuple[list[dict], dict[str, str], dict[str, str], list[str]]:
    """The rows, the texts before, the texts after and the problems."""
    files = [rel for rel in instruction_files(root) if (root / rel).is_file()]
    plan, problems = read_plan(root, files)
    rows: list[dict] = []
    before: dict[str, str] = {}
    after: dict[str, str] = {}
    guide: list[str] = []
    log: list[str] = []
    today = datetime.now(UTC).date().isoformat()
    for rel in files:
        text = (root / rel).read_text(encoding="utf-8")
        before[rel] = text
        lines = text.splitlines()
        changed = False
        for at, number, size in reversed(rule_rows(text)):
            entry = plan.get((rel, number)) if number else None
            verdict = entry or ("keep",)
            rows.append(
                {
                    "file": rel,
                    "line": at,
                    "n": number or "-",
                    "verdict": list(verdict),
                    "text": "\n".join(lines[at - 1 : at - 1 + size]),
                }
            )
            if entry is None:
                continue
            match = NUMBERED.match(lines[at - 1])
            if match is None:  # a planned rule is a numbered one (read_plan)
                continue
            indent, body = match.group(1), [match.group(3)]
            body += [x.strip() for x in lines[at : at - 1 + size]]
            if entry[0] == "retire":
                pointer = f"Retired: enforced by `{entry[1]}` (rules.py consolidate)."
                log.append(f"- {today} {rel} {number}: retired, enforced by `{entry[1]}`")
            else:
                pointer = f"Moved to `{GUIDE}` (rules.py consolidate)."
                guide.append(f"## {rel} rule {number}\n\n{' '.join(body)}\n")
            lines[at - 1 : at - 1 + size] = [f"{indent}{number}. {pointer}"]
            changed = True
        if changed:
            after[rel] = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    rows.sort(key=lambda r: (files.index(r["file"]), r["line"]))
    if guide:
        old = read_or(root / GUIDE, GUIDE_HEAD)
        after[GUIDE] = old + "".join(f"\n{g}" for g in reversed(guide))
    if log:
        after[CATCH_LOG] = read_or(root / CATCH_LOG, LOG_HEAD) + "".join(
            f"{x}\n" for x in reversed(log)
        )
    if plan:
        after[PLAN] = "".join(
            f"{x}\n"
            for x in (root / PLAN).read_text(encoding="utf-8").splitlines()
            if not x.strip() or x.lstrip().startswith("#")
        )
    baseline = budget_after(root, files, {**before, **after})
    if baseline is not None:
        after[BASELINE] = baseline
    return rows, before, after, problems


GUIDE_HEAD = (
    "# Session how-to\n\nThe how-to that `rules.py consolidate` moved out of the rule files. Each "
    "section names the file and the rule number it came from; the rule file keeps the number with "
    "a pointer here.\n"
)
LOG_HEAD = (
    "# Rules retired\n\nOne line per rule that `rules.py consolidate` retired, naming the check "
    "that enforces it. The rule file keeps the number with a pointer.\n\n"
)


def read_or(path: Path, default: str) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else default


def budget_after(root: Path, files: list[str], texts: dict[str, str]) -> str | None:
    """`config/rule-budget.txt` with each line rewritten to the counts of the texts; None when
    there is no baseline or nothing changes."""
    path = root / BASELINE
    if not path.is_file():
        return None
    old = path.read_text(encoding="utf-8")
    out = []
    for line in old.splitlines():
        parts = line.split()
        if line.strip() and not line.startswith("#") and len(parts) == 3 and parts[0] in texts:
            words, rules = counts(texts[parts[0]])
            line = f"{parts[0]} {words} {rules}"
        out.append(line)
    new = "\n".join(out) + ("\n" if old.endswith("\n") else "")
    return None if new == old else new


def plan_hash(rows: list[dict], after: dict[str, str]) -> str:
    """The rows and the texts the apply would write, ignoring the catch-log date."""
    data = {
        "rows": rows,
        "after": {k: v for k, v in after.items() if k != CATCH_LOG},
        "log": [x.split(" ", 2)[2] for x in after.get(CATCH_LOG, "").splitlines() if x[:2] == "- "],
    }
    blob = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def totals(texts: dict[str, str], files: list[str]) -> tuple[int, int]:
    words = rules = 0
    for rel in files:
        w, r = counts(texts[rel])
        words, rules = words + w, rules + r
    return words, rules


def in_force(texts: dict[str, str], files: list[str]) -> int:
    count = 0
    for rel in files:
        lines = texts[rel].splitlines()
        count += sum(1 for at, _, _ in rule_rows(texts[rel]) if not POINTER.match(lines[at - 1]))
    return count


def consolidate_plan(root: Path, since: str | None, repo: str | None, api: str | None) -> int:
    rows, before, after, problems = build_plan(root)
    for problem in problems:
        print(f"consolidate: {problem}")
    if problems:
        return 1
    found = tag_counts(root, since, repo, api) if since else None
    if since and found is None:
        print("consolidate: counts unknown (the pull requests cannot be read)")
    for row in rows:
        if found is None:
            count = "-"
        else:
            count = str(len(found["tags"].get(f"{row['file']} {row['n']}", [])))
        print(f"{row['file']}:{row['line']} {row['n']} {' '.join(row['verdict'])} {count}")
    files = list(before)
    new = {**before, **{k: v for k, v in after.items() if k in before}}
    w0, r0 = totals(before, files)
    w1, r1 = totals(new, files)
    print(f"before: {w0} words, {r0} rule lines, {in_force(before, files)} in force")
    print(f"after: {w1} words, {r1} rule lines, {in_force(new, files)} in force")
    print(f"plan: {plan_hash(rows, after)}")
    return 0


def dirty(root: Path) -> str | None:
    """None for a clean git work tree, else the refusal."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return "git cannot be run"
    if proc.returncode != 0:
        return "the root is not a git work tree"
    if proc.stdout.strip():
        return "the working tree is dirty; commit or stash first"
    return None


def consolidate_apply(root: Path, wanted: str) -> int:
    rows, _before, after, problems = build_plan(root)
    for problem in problems:
        print(f"consolidate: {problem}")
    if problems:
        return 1
    refusal = dirty(root)
    if refusal is None and plan_hash(rows, after) != wanted:
        refusal = "the plan has changed since --plan; run --plan again and pass its hash"
    if refusal is not None:
        print(f"consolidate: refused: {refusal}")
        return 1
    for rel, text in sorted(after.items()):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {rel}")
    print("consolidate: applied; nothing is committed")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in ("budget", "dropped", "consolidate"):
        print(USAGE)
        return 2
    command, rest = args[0], args[1:]
    flags = {
        "budget": {"--check"},
        "dropped": set(),
        "consolidate": {"--plan", "--apply"},
    }[command]
    valued = {"--root"} | {
        "budget": set(),
        "dropped": {"--since", "--repo", "--api-dir"},
        "consolidate": {"--since", "--repo", "--api-dir", "--hash"},
    }[command]
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
    try:
        if command == "budget":
            return budget(root, "--check" in opts)
        if command == "consolidate":
            return consolidate(root, opts)
        if not DATE.fullmatch(opts.get("--since", "")):
            print(USAGE)
            return 2
        return dropped(root, opts["--since"], opts.get("--repo"), opts.get("--api-dir"))
    except CheckError as exc:
        print(f"{command}: {exc}")
        return 1


def consolidate(root: Path, opts: dict[str, str]) -> int:
    plan, apply = "--plan" in opts, "--apply" in opts
    since = opts.get("--since")
    if plan == apply or (since is not None and not DATE.fullmatch(since)):
        print(USAGE)
        return 2
    if plan:
        if "--hash" in opts:
            print(USAGE)
            return 2
        return consolidate_plan(root, since, opts.get("--repo"), opts.get("--api-dir"))
    if not opts.get("--hash") or {"--since", "--repo", "--api-dir"} & set(opts):
        print(USAGE)
        return 2
    return consolidate_apply(root, opts["--hash"])


if __name__ == "__main__":
    sys.exit(main())
