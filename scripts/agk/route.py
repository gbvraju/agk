"""The router: one label for the state of every pull request (SPEC-0032 rules 1, 2 and 8).

    python3 route.py                         route what the GitHub event of the job names
    python3 route.py --pr N [--dry-run]      route one pull request (a person or a test)
    python3 route.py --all [--dry-run]       route every open pull request

It runs in the workflow `agk-route.yml` on `pull_request`, `issue_comment`, `workflow_run` and
`push` to the default branch, with the job's `GITHUB_TOKEN`, from a checkout of the default
branch: it runs no code of a pull request. For each pull request to route it reads the facts
with GET (the head, the check runs and statuses of the head, `mergeable_state`, the comments,
the reviews, the changed files) and sets exactly one of the seven labels `agk:ci-running`,
`agk:ci-red`, `agk:conflict`, `agk:review`, `agk:fix`, `agk:approve`, `agk:ready`, removing the
other six. When more than one state holds, the first of that list in the order conflict,
ci-running, ci-red, fix, approve, ready, review wins. A label set with the job's token starts no
workflow, so the router cannot loop. It writes labels and nothing else: no comment, no review,
no merge, no issue. Messages name the rule, never a value.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

from common import CheckError, load_config, repo_root
from metrics import author_of, counted_authors, covered_head, verdicts
from reviewers import parse as parse_reviewers
from reviewers import verdict_authors
from session import gh, pages, repo_name

NAME = "route"
USAGE = "usage: route.py [--pr N | --all] [--dry-run]"
ROUTER_JOB = "agk-route"
LABELS = (
    "agk:ci-running",
    "agk:ci-red",
    "agk:conflict",
    "agk:review",
    "agk:fix",
    "agk:approve",
    "agk:ready",
)
COLORS = {
    "agk:ci-running": "fbca04",
    "agk:ci-red": "d93f0b",
    "agk:conflict": "b60205",
    "agk:review": "0e8a16",
    "agk:fix": "d4c5f9",
    "agk:approve": "5319e7",
    "agk:ready": "0e8a16",
}
FAILED_RUN = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"}
FAILED_STATUS = {"failure", "error"}
APPROVE = re.compile(r"Approve: ([0-9a-f]{7,40}) (SPEC-\d{4})")
SPEC_FILE = re.compile(r"docs/specs/(\d{4})-[^/]+\.md")
CONFIG = "config/reviewers.yaml"


class Held:
    """The one commit record that `metrics.covered_head` asks its source for."""

    def __init__(self, commit: dict) -> None:
        self.commit = commit

    def get(self, key: str, endpoint: str) -> dict:
        return self.commit


def spec_approvers(root: Path) -> list[str]:
    """The people who may approve a spec (`spec_approvers` of the reviewers file), else none."""
    try:
        data = parse_reviewers((root / CONFIG).read_text(encoding="utf-8"))
    except Exception:  # nosec B110 - unreadable or invalid means nobody may approve
        return []
    listed = data.get("spec_approvers") if isinstance(data, dict) else None
    return [str(a).lstrip("@").lower() for a in listed] if isinstance(listed, list) else []


# --- the decision (rule 2) --------------------------------------------------------------------


def specs_approved_by(files: list[dict]) -> set[str]:
    """The specs the pull request sets to `Approved`, from the patches of its changed files."""
    found = set()
    for item in files:
        match = SPEC_FILE.fullmatch(str(item.get("filename") or ""))
        patch = str(item.get("patch") or "")
        if match and "+- Status: Approved" in patch.splitlines():
            found.add(f"SPEC-{match.group(1)}")
    return found


def approved_by_a_person(
    comments: list[dict], reviews: list[dict], approvers: list[str]
) -> set[str]:
    """The specs named by the `Approve: <sha> SPEC-<n>` line of an approver's comment or review."""
    allowed = {a.lstrip("@").lower() for a in approvers}
    found = set()
    for item in [*comments, *reviews]:
        lines = str(item.get("body") or "").splitlines()
        match = APPROVE.fullmatch(lines[0].strip()) if lines else None
        if match and author_of(item) in allowed:
            found.add(match.group(2))
    return found


def decide(f: dict) -> str:
    """The one label of a pull request from its facts; the first state that holds, in order."""
    if f.get("mergeable_state") == "dirty":
        return "agk:conflict"
    checks = [c for c in f.get("checks") or [] if c.get("name") != ROUTER_JOB]
    statuses = f.get("statuses") or []
    if not checks and not statuses:
        return "agk:ci-running"
    if any(c.get("status") != "completed" for c in checks) or any(
        s.get("state") == "pending" for s in statuses
    ):
        return "agk:ci-running"
    if any(c.get("conclusion") in FAILED_RUN for c in checks) or any(
        s.get("state") in FAILED_STATUS for s in statuses
    ):
        return "agk:ci-red"
    head = str(f.get("head") or "")
    comments = f.get("comments") or []
    authors = counted_authors(f.get("authors"), f.get("author"))
    listed = verdicts(comments, authors) or []
    kind, sha = listed[-1] if listed else ("", "")
    names_head = bool(sha) and head.startswith(sha)
    if names_head and kind in ("fix", "rejected"):
        return "agk:fix"
    covered = covered_head(Held(f.get("commit") or {}), head, comments, authors) == "yes"
    if (names_head and kind == "cleared") or covered:
        waiting = specs_approved_by(f.get("files") or []) - approved_by_a_person(
            comments, f.get("reviews") or [], f.get("approvers") or []
        )
        return "agk:approve" if waiting else "agk:ready"
    return "agk:review"


# --- reading the facts and writing the label (rules 1 and 8) ----------------------------------


def listing(endpoint: str, key: str | None = None) -> list | None:
    """A paged GET; `key` names the list inside an object (the check runs)."""
    if key is None:
        return pages(endpoint)
    found: list = []
    page = 1
    sep = "&" if "?" in endpoint else "?"
    while True:
        chunk = gh(f"{endpoint}{sep}per_page=100&page={page}")
        if not isinstance(chunk, dict) or not isinstance(chunk.get(key), list):
            return None
        found += chunk[key]
        if len(chunk[key]) < 100 or len(found) >= int(chunk.get("total_count") or 0):
            return found
        page += 1


def read_facts(repo: str, n: int, root: Path) -> tuple[dict, dict] | None:
    """(the pull request, its facts); None when a fact that must be known cannot be read."""
    pr = gh(f"repos/{repo}/pulls/{n}")
    if not isinstance(pr, dict) or not isinstance(pr.get("head"), dict):
        return None
    head = str(pr["head"].get("sha") or "")
    checks = listing(f"repos/{repo}/commits/{head}/check-runs", "check_runs")
    comments = listing(f"repos/{repo}/issues/{n}/comments")
    files = listing(f"repos/{repo}/pulls/{n}/files")
    if checks is None or comments is None or files is None:
        return None
    status = gh(f"repos/{repo}/commits/{head}/status")
    reviews = listing(f"repos/{repo}/pulls/{n}/reviews")
    commit = gh(f"repos/{repo}/commits/{head}")
    return pr, {
        "head": head,
        "mergeable_state": pr.get("mergeable_state"),
        "checks": checks,
        "statuses": status.get("statuses", []) if isinstance(status, dict) else [],
        "comments": comments,
        "reviews": reviews or [],
        "authors": verdict_authors(root),
        "approvers": spec_approvers(root),
        "author": (pr.get("user") or {}).get("login"),
        "files": files,
        "commit": commit if isinstance(commit, dict) else {},
    }


class Labels:
    """The labels of the repository, read once, created when a label to set is missing."""

    def __init__(self, repo: str) -> None:
        self.repo = repo
        self.known: set[str] | None = None

    def ensure(self, name: str) -> None:
        if self.known is None:
            found = listing(f"repos/{self.repo}/labels")
            self.known = {str(x.get("name")) for x in found or []}
        if name not in self.known:
            gh(
                f"repos/{self.repo}/labels",
                "-f",
                f"name={name}",
                "-f",
                f"color={COLORS[name]}",
                "-f",
                "description=AGK: the state of a pull request, set by the router",
                method="POST",
            )
            self.known.add(name)


def apply(repo: str, n: int, current: list[str], wanted: str, labels: Labels) -> None:
    if wanted not in current:
        labels.ensure(wanted)
        added = gh(f"repos/{repo}/issues/{n}/labels", "-f", f"labels[]={wanted}", method="POST")
        if added is None:
            raise CheckError(f"rule 2: the label of pull request #{n} cannot be written")
    for name in current:
        if name in LABELS and name != wanted:
            gh(f"repos/{repo}/issues/{n}/labels/{quote(name, safe='')}", method="DELETE")


def route_one(repo: str, n: int, root: Path, labels: Labels, dry: bool) -> str | None:
    """Route pull request `n`; its label, or None when it is over; CheckError if unreadable."""
    got = read_facts(repo, n, root)
    if got is None:
        raise CheckError(f"rule 2: the facts of pull request #{n} cannot be read")
    pr, facts = got
    if pr.get("state") != "open" or pr.get("merged_at"):
        return None
    wanted = decide(facts)
    current = [str(x.get("name")) for x in pr.get("labels") or []]
    if not dry:
        apply(repo, n, current, wanted, labels)
    changed = [name for name in current if name in LABELS] != [wanted]
    print(f"#{n} {wanted}" + (" (changed)" if changed and not dry else ""))
    return wanted


# --- which pull requests an event names (rule 1) ----------------------------------------------


def open_numbers(repo: str, head: str | None = None) -> list[int]:
    found = pages(f"repos/{repo}/pulls?state=open") or []
    return [
        int(p["number"])
        for p in found
        if isinstance(p.get("number"), int)
        and (head is None or (p.get("head") or {}).get("sha") == head)
    ]


def targets(name: str, event: dict, repo: str, default: str) -> list[int]:
    if name == "pull_request":
        number = (event.get("pull_request") or {}).get("number")
        return [number] if isinstance(number, int) else []
    if name == "issue_comment":
        issue = event.get("issue") or {}
        return [issue["number"]] if "pull_request" in issue and "number" in issue else []
    if name == "push":
        return open_numbers(repo) if event.get("ref") == f"refs/heads/{default}" else []
    if name == "workflow_run":
        run = event.get("workflow_run") or {}
        if run.get("head_branch") == default:
            return open_numbers(repo)
        listed = [p["number"] for p in run.get("pull_requests") or [] if "number" in p]
        return listed or open_numbers(repo, str(run.get("head_sha") or ""))
    return []


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in args
    rest = [a for a in args if a != "--dry-run"]
    by_number = len(rest) == 2 and rest[0] == "--pr" and rest[1].isdigit()
    if rest not in ([], ["--all"]) and not by_number:
        print(USAGE, file=sys.stderr)
        return 2
    root = repo_root()
    repo = os.environ.get("GITHUB_REPOSITORY") or repo_name(root)
    path = os.environ.get("GITHUB_EVENT_PATH")
    try:
        event = json.loads(Path(path).read_text(encoding="utf-8")) if path else {}
    except (OSError, ValueError):
        event = {}
    default = (event.get("repository") or {}).get("default_branch") or load_config(root)[
        "default_branch"
    ]
    if rest == ["--all"]:
        numbers = open_numbers(repo)
    elif rest:
        numbers = [int(rest[1])]
    else:
        numbers = targets(os.environ.get("GITHUB_EVENT_NAME", ""), event, repo, default)
    labels = Labels(repo)
    failed = False
    for n in dict.fromkeys(numbers):
        try:
            route_one(repo, n, root, labels, dry)
        except CheckError as exc:
            print(f"FAIL {NAME}: {exc}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
