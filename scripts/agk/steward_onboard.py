"""The steward's onboarding at any stage, with its evidence harvest (SPEC-0059 rule 20 and rule 18's
budget; brief #1325, ADR-0562).

Usage: python3 scripts/agk/steward_onboard.py onboard [--again]
       (the same as python3 scripts/agk/steward.py onboard [--again], Q-S0059-14)

A first start (a memory with no `Onboarded:` entry) finds its entry point: day 0 (stage `start`, no
Approved spec and no `agk-brief` issue), execution (an open `agk-conductor` issue, or a locked plan
and a closed brief) or planning (the stage `steward_evidence.py stage` names). Day 0 harvests
nothing. Planning and execution read, by list pages only and never one read per item
(Q-S0059-15): the repository's issue and pull request comments (`Maintainer answer:`, `Answer:`,
`Question:` and `Owner needed:` first lines), the open `agk:parked` issues, and the files: Accepted
ADRs, `docs/runs/decisions/`, Approved specs, the statuses of `docs/requirements.md`, the signed-off
prototype versions and the last line of `check_plan.py --trace`. It writes them as memory notes
marked `harvested`, each line citing its source: `Decision:` notes of at most 50 lines, one `Owner
question:` per open question and per question two answers contradict (never a decision), `Risk:`
for parked work and `Gap:` for each source it could not read. A line the data guard matches is
withheld, naming the class. It ends with `Onboarded: <stage> <date>, <n> decisions, <n> gaps, <n>
open questions` and prints the summary for the owner. A memory already onboarded writes nothing;
`--again` harvests again and writes only lines no note holds. Personal mode reads the files only
and writes the sidecar file. Exit 4: the memory or the stage cannot be read.
"""

from __future__ import annotations

import argparse
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import steward  # noqa: E402
from common import CheckError, personal_table, repo_root, utf8_output  # noqa: E402

ISSUES = "repos/{owner}/{repo}/issues"
COMMENTS = ISSUES + "/comments?per_page=100&page=<page>"
LABELLED = ISSUES + "?labels=<label>&state=<state>&per_page=100"
CHUNK = 50
FIRST = re.compile(r"^(Maintainer answer|Answer|Question): (Q-[\w-]+)\s*(.*)")
STATUS = re.compile(r"^- Status: (\S+)", re.M)
HEADING = re.compile(r"^# ((?:ADR|SPEC)-\d+): (.+)$", re.M)
QROW = re.compile(r"^\|[^|]*\|\s*(Q-[\w-]+[^|]*?)\s*\|", re.M)


def labelled(label: str, state: str) -> str:
    return LABELLED.replace("<label>", label).replace("<state>", state)


def short(text: str) -> str:
    return " ".join(text.split())[:160]


def place(item: dict) -> str:
    number = str(item.get("issue_url", "")).rstrip("/").rsplit("/", 1)[-1]
    return f"#{number} comment {item.get('id')}"


def listed(gh, endpoint: str) -> list | None:
    """Every page of a list, or None when one cannot be read (a gap, never assumed empty)."""
    out, page = [], 1
    while True:
        items = gh("GET", endpoint.replace("<page>", str(page)))
        if items is None:
            return None
        out += items
        if len(items) < 100 or "<page>" not in endpoint:
            return out
        page += 1


def entry_point(root: Path, gh, now: datetime) -> tuple[str, str]:
    """Rule 20: (entry, stage) for day 0, planning or execution."""
    from steward_evidence import conductor_open, stage_of

    stage = stage_of(root, now.date(), conductor_open(root, gh))
    briefs: list = []
    if personal_table(root) is None:
        found = gh("GET", labelled("agk-brief", "all"))
        if found is None:
            raise steward.Unreadable("issues")
        briefs = [i for i in found if "pull_request" not in i]
    locked = (root / "docs" / "plan" / "scope-lock.md").is_file()
    if stage == "build" or (locked and any(i.get("state") == "closed" for i in briefs)):
        return "execution", "build"
    approved = any(_approved(p) for p in (root / "docs" / "specs").glob("*.md"))
    if stage == "start" and not briefs and not approved:
        return "day 0", "start"
    return "planning", stage


def _approved(path: Path) -> bool:
    found = STATUS.search(path.read_text(encoding="utf-8"))
    return found is not None and found[1] == "Approved"


def from_comments(items: list[dict]) -> tuple[list, list]:
    """(decisions, owner questions) from the first lines of the repository's comments."""
    answers: dict[str, list[tuple[str, str]]] = {}
    asked, needed, decided_on = [], [], set()
    for item in sorted(items, key=lambda c: (c.get("created_at") or "", c.get("id", 0))):
        first = (item.get("body") or "").strip().splitlines()[:1]
        line = first[0] if first else ""
        if line.startswith("Owner needed:"):
            needed.append((short(line), place(item), place(item).split()[0]))
        elif line.startswith("Maintainer answer:"):
            decided_on.add(place(item).split()[0])
        if found := FIRST.match(line):
            word, qid, text = found.groups()
            if word == "Question":
                asked.append((qid, short(text), place(item)))
            else:
                answers.setdefault(qid, []).append(
                    (short(text.split(" (evidence:")[0]), place(item))
                )
    decisions, owner = [], []
    for qid, given in answers.items():
        if len({text for text, _ in given}) > 1:
            where = ", ".join(p for _, p in given)
            owner.append(f"{qid}: two answers disagree (sources: {where})")
        else:
            decisions.append(f"{qid} {given[0][0]} (source: {given[0][1]})")
    owner += [f"{qid} {text} (source: {p})" for qid, text, p in asked if qid not in answers]
    owner += [f"{text} (source: {p})" for text, p, issue in needed if issue not in decided_on]
    return decisions, owner


def from_files(root: Path, gaps: list) -> list:
    out = []
    for folder, prefix in (("docs/adr", "Accepted"), ("docs/specs", "Approved")):
        for path in sorted((root / folder).glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                gaps.append(f"{path.relative_to(root).as_posix()} cannot be read")
                continue
            status, heading = STATUS.search(text), HEADING.search(text)
            if status and status[1] == prefix and heading:
                rel = path.relative_to(root).as_posix()
                out.append(f"{heading[1]} {short(heading[2])} (source: {rel})")
    for path in sorted((root / "docs" / "runs" / "decisions").glob("*.md")):
        for row in QROW.findall(path.read_text(encoding="utf-8")):
            out.append(f"{short(row)} (source: docs/runs/decisions/{path.name})")
    requirements = root / "docs" / "requirements.md"
    if requirements.is_file():
        for block in requirements.read_text(encoding="utf-8").split("\n### ")[1:]:
            status = STATUS.search(block)
            said = status[1] if status else "no status"
            out.append(f"{block.split()[0]} {said} (source: docs/requirements.md)")
    try:
        from design_signoff import rows

        for row in rows(root):
            if row["kind"] == "design":
                signed = f"prototype {row['version']} signed off {row['date']}"
                out.append(f"{signed} (source: docs/design/signoffs.md)")
    except (CheckError, OSError, KeyError):
        gaps.append("the prototype sign-offs cannot be read")
    if (root / "docs" / "plan").is_dir():
        script = Path(__file__).resolve().parent / "check_plan.py"
        found = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(script), "--root", str(root), "--trace"],
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        last = (found.stdout.strip().splitlines() or [""])[-1]
        if found.returncode in (0, 1) and last:
            out.append(f"plan trace: {short(last)} (source: check_plan.py --trace)")
        else:
            gaps.append("the plan's trace cannot be read")
    return out


def harvest(root: Path, gh) -> dict:
    """Rule 20's one read of the facts, by list pages only."""
    gaps: list = []
    decisions: list = []
    owner: list = []
    risks: list = []
    if personal_table(root) is None:
        items = listed(gh, COMMENTS)
        if items is None:
            gaps.append("the comments of issues and pull requests cannot be read")
        else:
            decisions, owner = from_comments(items)
        parked = gh("GET", labelled("agk:parked", "open"))
        if parked is None:
            gaps.append("parked work cannot be read (source: issues labelled agk:parked)")
        else:
            risks = [
                f"parked: #{i['number']} {short(i.get('title', ''))} (source: #{i['number']})"
                for i in parked
            ]
    decisions += from_files(root, gaps)
    return {"Decision": decisions, "Owner question": owner, "Risk": risks, "Gap": gaps}


def guarded(root: Path, line: str) -> str:
    from guard import scan_text

    from config import guard_patterns

    findings = scan_text(line, guard_patterns(root))
    if not findings:
        return line
    source = line.rsplit(" (source: ", 1)[-1] if " (source: " in line else "unknown)"
    classes = ", ".join(sorted({f.kind for f in findings}))
    return f"a line withheld by the data guard ({classes}) (source: {source}"


def onboard(root: Path, gh, now: datetime, again: bool = False) -> tuple[int, list[str]]:
    personal = personal_table(root) is not None
    cache: dict = {}
    if personal:
        memory = steward.personal_entries(root)
    else:
        cache = steward.load_cache(root)
        steward.memory_issue(gh, root, cache)
        memory = cache["comments"]
    done = [c for c in memory if steward.entry_kind(c.get("body", "")) == "Onboarded"]
    if done and not again:
        return 0, [f"onboarded: {done[-1]['body'].strip().splitlines()[0]}"]
    entry, stage = entry_point(root, gh, now)
    found: dict[str, list] = {"Decision": [], "Owner question": [], "Risk": [], "Gap": []}
    if entry != "day 0":
        found = harvest(root, gh)
    held = {line.strip() for c in memory for line in c.get("body", "").splitlines()}
    texts, counts = [], {}
    for kind, lines in found.items():
        lines = [guarded(root, line) for line in dict.fromkeys(lines)]
        if kind == "Owner question":
            new = [x for x in lines if f"Owner question: harvested {x}" not in held]
            texts += [f"Owner question: harvested {x}" for x in new]
        else:
            new = [x for x in lines if f"- {x}" not in held]
            for at in range(0, len(new), CHUNK):
                part = new[at : at + CHUNK]
                texts.append(
                    f"{kind}: harvested, {len(part)} notes\n" + "\n".join(f"- {x}" for x in part)
                )
        counts[kind] = len(new)
    texts.append(
        f"Onboarded: {stage} {now.date().isoformat()}, {counts.get('Decision', 0)} decisions, "
        f"{counts.get('Gap', 0)} gaps, {counts.get('Owner question', 0)} open questions"
    )
    for text in texts:
        if personal:
            steward.personal_append(root, text)
        else:
            steward.post(gh, cache, text)
    if not personal:
        steward.save_cache(root, cache)
    rely = [x.split(" (source: ")[0] for x in found["Decision"][:5]]
    more = len(found["Decision"]) - len(rely)
    return 0, [
        f"entry: {entry}",
        f"stage: {stage}",
        texts[-1],
        *([f"rely on: {'; '.join(rely)}" + (f"; and {more} more" if more else "")] if rely else []),
        *(f"gap: {g}" for g in found["Gap"]),
    ]


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(
        prog="steward_onboard.py", description=__doc__.split("\n\n")[0]
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("onboard").add_argument("--again", action="store_true")
    opts = parser.parse_args(argv)
    return run(repo_root(), opts.again)


def run(root: Path, again: bool) -> int:
    try:
        code, lines = onboard(root, steward.gh_api, datetime.now(UTC), again=again)
    except steward.Unreadable as exc:
        print(f"error: {exc} cannot be read", file=sys.stderr)
        return 4
    except (CheckError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
