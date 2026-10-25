"""The router: one label for the state of every pull request (SPEC-0032 rules 1, 2 and 8).

    python3 route.py                         route what the GitHub event of the job names
    python3 route.py --pr N [--dry-run]      route one pull request (a person or a test)
    python3 route.py --all [--dry-run]       route every open pull request
    python3 route.py --branch [--dry-run]    route the default branch: its red-branch brief

It runs in the workflow `agk-route.yml` on `pull_request`, `issue_comment`, `workflow_run` and
`push` to the default branch, with the job's `GITHUB_TOKEN`, from a checkout of the default
branch: it runs no code of a pull request. For each pull request to route it reads the facts
with GET (the head, the check runs and statuses of the head, `mergeable_state`, the comments,
the reviews, the changed files) and sets exactly one of the seven labels `agk:ci-running`,
`agk:ci-red`, `agk:conflict`, `agk:review`, `agk:fix`, `agk:approve`, `agk:ready`, removing the
other six. When more than one state holds, the first of that list in the order conflict,
ci-running, ci-red, approve, fix, ready, review wins. A label set with the job's token starts no
workflow, so the router cannot loop. It writes labels and, for the default branch (SPEC-0032
rule 7), the one issue `The default branch is red`: on a `push` to the default branch or a
finished workflow on it, it reads the checks of the branch's head and, when they fail, opens or
updates that issue as a brief (`Priority: 0`, `Advances: none`) that names the failing check, the
sha and the run and no cause, and closes it when the branch is green; while checks still run it
does nothing. No comment, no review, no merge. Messages name the rule, never a value.
"""

from __future__ import annotations

import base64
import datetime
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path
from urllib.parse import quote

from common import CheckError, load_config, repo_root
from metrics import counted_authors, covered_head, latest_verdict_body, verdicts
from reviewers import person_approvals, spec_approvers, verdict_authors
from session import RED_TITLE, gh, is_red, pages, repo_name

NAME = "route"
USAGE = "usage: route.py [--pr N | --all | --branch] [--dry-run]"
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
    "agk-brief": "1d76db",
}
DESCRIPTIONS = {"agk-brief": "AGK: a brief a builder session can take"}
FAILED_RUN = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"}
FAILED_STATUS = {"failure", "error"}
ASKED = re.compile(r"Approval: (SPEC-\d{4}) (\S+) Draft -> Approved, waiting for a person")
SUMMARY = re.compile(r"Summary: (\S.{0,118}\S|\S)")
PIPELINE_COUNTS = ("review", "fix", "ci-red", "conflict", "approve", "ready")
SPEC_TITLE = re.compile(r"# SPEC-\d{4}: (\S.*)")
SPEC_FILE = re.compile(r"docs/specs/(\d{4})-[^/]+\.md")


class ReadOnly(Exception):
    """The job's token cannot write (a fork's pull request gets a read-only token): skip."""


def write(endpoint: str, *extra: str, method: str, what: str = "rule 2: a label") -> None:
    """One write with `gh api`; a 403 is `ReadOnly`, any other failure a CheckError."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["gh", "api", "--method", method, endpoint, *extra], capture_output=True, text=True
    )
    if proc.returncode == 0 or (method == "DELETE" and "404" in proc.stderr):
        return
    if "403" in proc.stderr:
        raise ReadOnly
    raise CheckError(f"{what} cannot be written")


class Held:
    """The one commit record that `metrics.covered_head` asks its source for."""

    def __init__(self, commit: dict) -> None:
        self.commit = commit

    def get(self, key: str, endpoint: str) -> dict:
        return self.commit


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


approved_by_a_person = person_approvals


def asked_for(body: str) -> set[str]:
    """The specs the conductor's `Approval:` lines of a verdict ask a person to approve."""
    return {m.group(1) for m in map(ASKED.fullmatch, (x.strip() for x in body.splitlines())) if m}


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
    people = approved_by_a_person(comments, f.get("reviews") or [], f.get("approvers") or [])
    if names_head and asked_for(latest_verdict_body(comments, authors)) - people:
        return "agk:approve"
    if names_head and kind in ("fix", "rejected"):
        return "agk:fix"
    covered = covered_head(Held(f.get("commit") or {}), head, comments, authors) == "yes"
    if (names_head and kind == "cleared") or covered:
        waiting = specs_approved_by(f.get("files") or []) - people
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
            write(
                f"repos/{self.repo}/labels",
                "-f",
                f"name={name}",
                "-f",
                f"color={COLORS[name]}",
                "-f",
                "description=" + DESCRIPTIONS.get(name, "AGK: the state of a pull request"),
                method="POST",
            )
            self.known.add(name)


def apply(repo: str, n: int, current: list[str], wanted: str, labels: Labels) -> None:
    if wanted not in current:
        labels.ensure(wanted)
        write(f"repos/{repo}/issues/{n}/labels", "-f", f"labels[]={wanted}", method="POST")
    for name in current:
        if name in LABELS and name != wanted:
            write(f"repos/{repo}/issues/{n}/labels/{quote(name, safe='')}", method="DELETE")


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


# --- the default branch (rule 7) ---------------------------------------------------------------


def branch_state(checks: list[dict], statuses: list[dict]) -> str:
    """`pending`, `red` or `green` for the checks of the default branch's head."""
    checks = [c for c in checks if c.get("name") != ROUTER_JOB]
    if not checks and not statuses:
        return "pending"
    if any(c.get("status") != "completed" for c in checks) or any(
        s.get("state") == "pending" for s in statuses
    ):
        return "pending"
    failed = any(c.get("conclusion") in FAILED_RUN for c in checks)
    return "red" if failed or any(s.get("state") in FAILED_STATUS for s in statuses) else "green"


def failing(checks: list[dict], statuses: list[dict], repo: str, sha: str) -> tuple[str, str]:
    """(name, link) of the first failing check by name, or status."""
    bad = sorted(
        (str(c.get("name") or ""), str(c.get("html_url") or c.get("details_url") or ""))
        for c in checks
        if c.get("name") != ROUTER_JOB and c.get("conclusion") in FAILED_RUN
    ) + sorted(
        (str(s.get("context") or ""), str(s.get("target_url") or ""))
        for s in statuses
        if s.get("state") in FAILED_STATUS
    )
    name, url = bad[0] if bad else ("", "")
    return name, url or f"https://github.com/{repo}/commit/{sha}/checks"


def one_line(text: str) -> str:
    return " ".join(str(text).split()) or "unnamed"


def red_body(name: str, sha: str, url: str) -> str:
    """The red-branch brief in the shape of a brief; it names the check, the sha and the run."""
    return (
        'Sentence: "The default branch is red: the required checks of its head fail."\n'
        f"Answers:\n1. Failing check: {one_line(name)}\n2. Head: {one_line(sha)}\n"
        f"3. Run: {one_line(url)}\n"
        "Priority: 0\nAdvances: none\nTouches: **\nSize: S\n"
    )


def route_branch(repo: str, default: str, labels: Labels, dry: bool) -> str:
    """Open, update or close the red-branch brief from the checks of the default branch's head."""
    tip = gh(f"repos/{repo}/branches/{default}")
    sha = str(((tip or {}).get("commit") or {}).get("sha") or "") if isinstance(tip, dict) else ""
    checks = listing(f"repos/{repo}/commits/{sha}/check-runs", "check_runs") if sha else None
    status = gh(f"repos/{repo}/commits/{sha}/status") if sha else None
    found = pages(f"repos/{repo}/issues?state=open&labels=agk-brief")
    if checks is None or found is None:
        raise CheckError("rule 7: the checks of the default branch cannot be read")
    statuses = status.get("statuses", []) if isinstance(status, dict) else []
    state = branch_state(checks, statuses)
    open_red = sorted((i for i in found if is_red(i)), key=lambda i: i["number"])
    print(f"default branch {state}")
    if state == "pending" or dry:
        return state
    issues = f"repos/{repo}/issues"
    if state == "green":
        for item in open_red:
            args = ("-f", "state=closed", "-f", "state_reason=completed")
            write(f"{issues}/{item['number']}", *args, method="PATCH", what="rule 7: the issue")
        return state
    name, url = failing(checks, statuses, repo, sha)
    body = red_body(name, sha, url)
    if open_red:
        if str(open_red[0].get("body") or "") != body:
            write(
                f"{issues}/{open_red[0]['number']}",
                "-f",
                f"body={body}",
                method="PATCH",
                what="rule 7: the issue",
            )
    else:
        labels.ensure("agk-brief")
        args = ("-f", f"title={RED_TITLE}", "-f", f"body={body}", "-f", "labels[]=agk-brief")
        write(issues, *args, method="POST", what="rule 7: the issue")
    return state


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


def on_default_branch(name: str, event: dict, default: str) -> bool:
    """A push to the default branch, or a finished workflow run on it (rule 7)."""
    if name == "push":
        return event.get("ref") == f"refs/heads/{default}"
    if name == "workflow_run":
        return (event.get("workflow_run") or {}).get("head_branch") == default
    return False


# --- the pipeline document (SPEC-0036 rules 2 to 5) --------------------------------------------


def summary_of(body: object) -> str:
    """The sentence of the first `Summary:` line of a pull request body, or `unknown`."""
    for line in str(body or "").splitlines():
        found = SUMMARY.fullmatch(line.strip())
        if found:
            return found.group(1)
    return "unknown"


def spec_title(repo: str, path: str, head: str) -> str:
    """The title of the spec file at the head of a pull request, or `unknown`."""
    if not re.fullmatch(r"docs/specs/\d{4}-[^/]+\.md", path) or not head:
        return "unknown"
    record = gh(f"repos/{repo}/contents/{quote(path)}?ref={head}")
    try:
        text = base64.b64decode(record["content"]).decode("utf-8")
    except (KeyError, TypeError, ValueError):
        return "unknown"
    found = SPEC_TITLE.match(text.splitlines()[0] if text else "")
    return found.group(1).strip() if found else "unknown"


def approve_items(repo: str, pr: dict, root: Path) -> list[dict]:
    n = int(pr["number"])
    url = str(pr.get("html_url") or "")
    unread = [{"number": n, "spec": "unknown", "spec_title": "unknown", "url": url}]
    comments = listing(f"repos/{repo}/issues/{n}/comments")
    if comments is None:
        return unread
    body = latest_verdict_body(comments, counted_authors(verdict_authors(root), None))
    head = str((pr.get("head") or {}).get("sha") or "")
    found = [ASKED.fullmatch(x.strip()) for x in body.splitlines() if ASKED.fullmatch(x.strip())]
    return [
        {
            "number": n,
            "spec": m.group(1),
            "spec_title": spec_title(repo, m.group(2), head),
            "url": url,
        }
        for m in found
    ] or unread


def pipeline_document(repo: str, root: Path) -> dict:
    """What waits for a person, from a fresh read of the open pull requests."""
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    found = pages(f"repos/{repo}/pulls?state=open")
    doc: dict = {"schema": 1, "as_of": now, "ready": [], "approve": []}
    if found is None:
        doc["counts"] = {k: "unknown" for k in PIPELINE_COUNTS}
        return doc
    held = {k: [] for k in PIPELINE_COUNTS}
    for pr in found:
        names = {(x or {}).get("name") for x in pr.get("labels") or []}
        for k in PIPELINE_COUNTS:
            if f"agk:{k}" in names and isinstance(pr.get("number"), int):
                held[k].append(pr)
    doc["counts"] = {k: len(v) for k, v in held.items()}
    doc["ready"] = [
        {
            "number": p["number"],
            "summary": summary_of(p.get("body")),
            "url": str(p.get("html_url") or ""),
        }
        for p in held["ready"]
    ]
    for pr in held["approve"]:
        doc["approve"] += approve_items(repo, pr, root)
    return doc


def write_pipeline(repo: str, root: Path) -> None:
    """Write `pipeline.json` (rule 2); a failure is reported and fails no routing (rule 4)."""
    target = Path(os.environ.get("AGK_PIPELINE_FILE") or "pipeline.json")
    try:
        doc = pipeline_document(repo, root)
        target.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    except (OSError, CheckError, ValueError, KeyError, TypeError):
        print("skipped rule 4: the pipeline document was not written")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in args
    rest = [a for a in args if a != "--dry-run"]
    by_number = len(rest) == 2 and rest[0] == "--pr" and rest[1].isdigit()
    if rest not in ([], ["--all"], ["--branch"]) and not by_number:
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
    name = os.environ.get("GITHUB_EVENT_NAME", "")
    if rest == ["--all"]:
        numbers = open_numbers(repo)
    elif rest == ["--branch"]:
        numbers = []
    elif rest:
        numbers = [int(rest[1])]
    else:
        numbers = targets(os.environ.get("GITHUB_EVENT_NAME", ""), event, repo, default)
    labels = Labels(repo)
    failed = False
    try:
        for n in dict.fromkeys(numbers):
            try:
                route_one(repo, n, root, labels, dry)
            except CheckError as exc:
                print(f"FAIL {NAME}: {exc}")
                failed = True
        if rest == ["--branch"] or (not rest and on_default_branch(name, event, default)):
            try:
                route_branch(repo, default, labels, dry)
            except CheckError as exc:
                print(f"FAIL {NAME}: {exc}")
                failed = True
    except ReadOnly:
        print("skipped (read-only token)")
        failed = False
    if not dry:
        write_pipeline(repo, root)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
