"""Print the review bundle of one pull request head (brief #1013 answer 1, ADR-0431; REQ-046).

    python3 scripts/agk/review_bundle.py --pr <n> --sha <40-hex head> [--base REF]

One document on stdout, for a reviewer slot that never saw the build (ADR-0430 decision 2): the
output of `review_context.py` for the head, the brief's body (the pull request's `Brief: #n`), the
ruling comments of the brief and the pull request (`Answer:`, `Correction:`, `Maintainer answer:`,
`Approve:`, and `Verdict:` on the pull request), each with its author and time, and the conclusions
of the head's check runs. It reads REST with GET only (`gh api`), and of the issues only the brief
and the two comment lists. It refuses a sha that is not the pull request's head and a checkout that
is not at it. The same replies and the same checkout give the same bytes. Exit 0, 1 on a refusal
or a failed read, 2 on a usage error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import session  # noqa: E402
from common import CheckError, git, repo_root, run, utf8_output  # noqa: E402
from review_context import assemble, fenced  # noqa: E402

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
