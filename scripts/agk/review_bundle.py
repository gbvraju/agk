# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Print the review bundle of one pull request head (brief #1013 answer 1, ADR-0431; REQ-046).

    python3 scripts/agk/review_bundle.py --pr <n> --sha <40-hex head> [--base REF]

One document on stdout, for a reviewer slot that never saw the build (ADR-0430 decision 2): the
output of `review_context.py` for the head, the `## Parts` section (each direct dependency the
change adds, removes or moves, with its `docs/parts.md` row or `no row`; SPEC-0076 rule 8, brief
#2073, ADR-0863), the brief's body (the pull request's `Brief: #n`), the
ruling comments of the brief and the pull request (`Answer:`, `Correction:`, `Maintainer answer:`,
`Approve:`, and `Verdict:` on the pull request), each with its author and time, and the conclusions
of the head's check runs. It reads REST with GET only (`gh api`), and of the issues only the brief
and the two comment lists. It refuses a sha that is not the pull request's head and a checkout that
is not at it. The same replies and the same checkout give the same bytes. Exit 0, 1 on a refusal
or a failed read, 2 on a usage error.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import session  # noqa: E402
from common import (  # noqa: E402
    CheckError,
    changed_files,
    git,
    merge_base,
    repo_root,
    resolve_base,
    run,
    show,
    utf8_output,
)
from gates import parts, pins  # noqa: E402
from parts_record import COLUMNS, RECORD  # noqa: E402
from review_context import Budget, assemble, caps, fenced  # noqa: E402

NAME = "review-bundle"
USAGE = "usage: review_bundle.py --pr N --sha <40-hex head> [--base REF]"
RULE = "(ADR-0431 decision 1)"
SHA = re.compile(r"[0-9a-f]{40}")
NUMBER = re.compile(r"[1-9]\d{0,9}")
BRIEF_RULINGS = ("Answer:", "Correction:", "Maintainer answer:", "Approve:")
PULL_RULINGS = (*BRIEF_RULINGS, "Verdict:")


def parse_args(args: list[str]) -> tuple[int, str, str | None] | None:
    values: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i] in ("--pr", "--sha", "--base") and i + 1 < len(args) and args[i] not in values:
            values[args[i]] = args[i + 1]
            i += 2
        else:
            return None
    pr, sha = values.get("--pr", ""), values.get("--sha", "")
    if not NUMBER.fullmatch(pr) or not SHA.fullmatch(sha):
        return None
    return int(pr), sha, values.get("--base")


def read(endpoint: str, what: str) -> dict:
    found = session.gh(endpoint)
    if not isinstance(found, dict):
        raise CheckError(f"{what} cannot be read")
    return found


def comments(endpoint: str, what: str) -> list:
    found = session.pages(endpoint)
    if found is None:
        raise CheckError(f"{what} cannot be read")
    return found


def rulings(found: list, kinds: tuple[str, ...]) -> list[dict]:
    """The comments whose first line starts with one of `kinds`, oldest first."""
    said = [c for c in found if isinstance(c, dict) and session.first_line(c).startswith(kinds)]
    return sorted(said, key=lambda c: (str(c.get("created_at") or ""), c.get("id") or 0))


def ruling_lines(where: str, found: list[dict]) -> list[str]:
    if not found:
        return [f"- none on {where}"]
    out: list[str] = []
    for c in found:
        body = session.FOOTER.sub("", str(c.get("body") or "")).rstrip()
        out += [
            f"- on {where} by {session.author_of(c)} at {c.get('created_at')}:",
            *fenced(body.splitlines()),
        ]
    return out


def check_lines(runs: list) -> list[str]:
    named = sorted(
        (str(r.get("name")), str(r.get("conclusion") or r.get("status") or "unknown"))
        for r in runs
        if isinstance(r, dict)
    )
    return [f"- {name}: {state}" for name, state in named] or ["- none reported"]


def entries(reader: str, build: str, text: str | None) -> dict[str, tuple[str, str]]:
    """name -> (version or `unpinned`, group) of each direct dependency of the build file
    (`pins.direct`, one group at a time for npm so that a move between groups shows; a root
    `requirements.txt` through `pins.requirement_lines`); empty for an absent file."""
    if text is None:
        return {}
    out: dict[str, tuple[str, str]] = {}
    if reader == "npm":
        data = json.loads(text)
        for group in pins.NPM_GROUPS:
            one = json.dumps({group: data.get(group) or {}})
            for name, version in pins.direct(reader, one):
                out.setdefault(name, (version or "unpinned", group))
        return out
    found = pins.requirement_lines(text)[0] if build.endswith(".txt") else pins.direct(reader, text)
    for name, version in found:
        out.setdefault(pins.norm(name), (version or "unpinned", ""))
    return out


def row_text(row: dict[str, str]) -> list[str]:
    head = "| " + " | ".join(COLUMNS) + " |"
    return fenced([head, "| " + " | ".join(row[c] for c in COLUMNS) + " |"])


def record_rows(text: str | None) -> dict[str, list[dict[str, str]]] | None:
    """Rows by section of the record (build (d)'s reader, `Q-PF-1`); None absent or unread."""
    found = parts.sections(text) if text is not None else None
    return None if found is None else found[0]


def runtime_rows(rows: dict, key: str, many: bool) -> list[dict[str, str]]:
    names = [n for n in rows if not many or pins.RUNTIME_NAMES.get(n.casefold()) == key]
    return [r for n in names for r in rows[n]]


def parts_lines(root: Path, base: str | None) -> list[str]:
    """SPEC-0076 rule 8 (brief #2073 answer 1): each direct dependency the change adds, removes
    or moves, with its `docs/parts.md` row at the head fenced or `no row in docs/parts.md`, then
    each record row the change adds or edits whose part no build file changes; cut at
    `review_other_cap` as `assemble` cuts."""
    head = ["## Parts", ""]
    found = parts.settings(root)
    if isinstance(found, str):
        return [*head, f"- not run parts: {found}", ""]
    stack = pins.runtimes_of(root)
    if stack is None:
        return [*head, f"- not run parts: {pins.NO_STACK}", ""]
    resolved = resolve_base(root, base)
    if resolved is None:
        raise CheckError("no base ref resolves; pass --base")
    mb = merge_base(root, resolved)
    changed = changed_files(root, mb)
    try:
        now = record_rows((root / RECORD).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        now = None  # absent or not UTF-8: each line ends `no parts record`
    before = record_rows(show(root, mb, RECORD)) or {}
    many = len(stack) > 1
    out: list[str] = []
    shown: set[tuple[str, str]] = set()
    for one in stack:
        key = next(k for k, v in pins.STACKS.items() if v == one.row)
        build, reader = one.at(one.build), one.row[3]
        if build not in changed:
            continue
        try:
            at = root / build
            new_text = at.read_text(encoding="utf-8") if at.is_file() else None
            old = entries(reader, build, show(root, mb, build))
            new = entries(reader, build, new_text)
        except (ValueError, AttributeError, TypeError, UnicodeDecodeError):
            out.append(f"- {build}: cannot be read")
            continue
        mine = runtime_rows(now or {}, key, many)
        for name in sorted(set(old) | set(new)):
            a, b = old.get(name, ("none", "")), new.get(name, ("none", ""))
            if a == b:
                continue
            moved = f" ({a[1]} -> {b[1]})" if a[0] == b[0] and a[1] and b[1] else ""
            line = f"- {build}: {name} {a[0]} -> {b[0]}{moved}"
            if now is None:
                out.append(f"{line}: no parts record")
                continue
            named = [r for r in mine if pins.norm(r["Part"]) == name]
            if named:
                shown.add((key, name))
            out += [line, *([x for r in named for x in row_text(r)] or [f"- no row in {RECORD}"])]
    for one in stack:
        key = next(k for k, v in pins.STACKS.items() if v == one.row)
        old_rows = runtime_rows(before, key, many)
        for r in runtime_rows(now or {}, key, many):
            if r in old_rows or (key, pins.norm(r["Part"])) in shown:
                continue
            shown.add((key, pins.norm(r["Part"])))
            out += [f"- {RECORD}: {r['Part']} {r['Version']}", *row_text(r)]
    budget = Budget(caps(root)["review_other_cap"])
    kept = budget.take(out or ["- no build file or parts record changed"])
    return [*head, *kept, *budget.marker(), ""]


def bundle(root: Path, number: int, sha: str, base: str | None) -> str:
    repo = session.repo_name(root)
    pull = read(f"repos/{repo}/pulls/{number}", "the pull request")
    head = str((pull.get("head") or {}).get("sha") or "")
    if head != sha:
        raise CheckError(f"refused: the sha is not the head of the pull request {RULE}")
    if git(root, "rev-parse", "HEAD").strip() != sha:
        raise CheckError(f"refused: the checkout is not at the head {RULE}")
    body = str(pull.get("body") or "")
    brief = session.BRIEF_LINE.search(body)
    out = [f"# Review bundle: #{number} {sha}", "", assemble(root, base, body), ""]
    out += parts_lines(root, base)
    if brief is None:
        out += ["## Brief", "", "- the pull request body names no `Brief: #n`", ""]
        brief_rulings: list[dict] = []
    else:
        n = brief.group(1)
        issue = read(f"repos/{repo}/issues/{n}", f"brief #{n}")
        text = session.FOOTER.sub("", str(issue.get("body") or "")).rstrip()
        out += [f"## Brief #{n}", "", *fenced(text.splitlines()), ""]
        brief_rulings = rulings(
            comments(f"repos/{repo}/issues/{n}/comments", f"#{n}"), BRIEF_RULINGS
        )
    pull_rulings = rulings(
        comments(f"repos/{repo}/issues/{number}/comments", f"#{number}"), PULL_RULINGS
    )
    out += ["## Rulings", ""]
    if brief is not None:
        out += ruling_lines(f"brief #{brief.group(1)}", brief_rulings)
    out += [*ruling_lines(f"#{number}", pull_rulings), ""]
    checks = read(f"repos/{repo}/commits/{sha}/check-runs?per_page=100", "the head's checks")
    runs = checks.get("check_runs")
    if not isinstance(runs, list):
        raise CheckError("the head's checks cannot be read")
    out += ["## Checks", "", *check_lines(runs), ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    parsed = parse_args(list(sys.argv[1:] if argv is None else argv))
    if parsed is None:
        print(USAGE, file=sys.stderr)
        return 2
    sys.stdout.write(bundle(repo_root(), *parsed))
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
