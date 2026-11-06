"""merge_cleared.py: merge a cleared pull request through one guarded command (SPEC-0039).

Build (a) (brief #528, ADR-0263) gave rules 1 and 3; build (b) (brief #531, ADR-0265) adds rules 2,
4, 5, the pinned merge of rule 6 (its first sentence), 8 and 9. Usage, exactly:

    python3 scripts/agk/merge_cleared.py --pr <n> --sha <the 40-character head sha>

It reads `[flow] auto_merge` and `auto_merge_method`, `paused`, `execution` and `required_checks`
from agk.toml, and `config/reviewers.yaml`, as committed on the default branch of the remote, as
last fetched (never the work tree, never a pull request's head); then, holding the named lock
`merge-cleared` of lock.py, the pull request, its comments, the open issues, the head's check runs
(CI mode) and the pull request's files with `gh api` through the REST API. It re-checks the head,
the verdict, the evidence and the hold list, merges by one `PUT .../merge` pinned to the sha with
the squash method, and prints one line:

    merge-cleared #<n> <sha12>: merged <merge sha12>              exit 0
    merge-cleared #<n> <sha12>: held: <reason>                    exit 3
    merge-cleared #<n> <sha12>: refused: <reason>                 exit 1, or 3 when a later pass
                                                                  may clear it (a moved head)

and exit 4 when GitHub cannot answer one read five times in a row. A reason names a rule, a
setting or a path class, never a value. Standard library only; every `gh` call is an argument list
with no shell and no jq filter, and the JSON is read here. A covered fix list on exactly the head
whose every `Final:` line accepts an ADR clears it too (SPEC-0021 rule 3a, brief 557): each named
ADR must be among the pull request's files and read at the head as `Proposed`, and the squash
message carries one line `ADR-nnnn Accepted (Final <comment id>)` per ADR and the line
`Merged-by: merge_cleared.py`, the mark `common.final_records` reads. Every merge passes its own
squash message (the line `Merged-by: merge_cleared.py` alone when nothing is accepted), and a
pull request whose commits or body already hold either line is held. The governance run after
the merge, the red-branch stop and the record line are build (c).

Build (c) (brief #551, ADR-0273) adds the rest of rule 6 and rule 7. Before the merge the command
needs one record issue (the open local-mode record issue, else the one open issue labelled
`agk-auto-merge`), else `held: no record issue (rule 7)`. After the merge, still under the lock, it
posts one comment `Auto merge: #<n> <merge sha> <UTC time> <verdict link>` there, then fetches the
default branch, adds a detached worktree of the merge commit in a temporary folder outside the
checkout and runs `lock.py run --name heavy --session merge-cleared -- env -i PATH=<PATH>
HOME=<scratch> AGK_PR_BODY=<scratch>/pr-body.md AGK_RECORD_COMMENTS=<scratch>/record-comments.json
make -C <worktree> governance AGK_BASE=<parent of the merge commit>`, the body file holding the pull
request body read before the merge (brief #576, so that a `Covered-by:` build is not reported red)
and the comments file the Final comment of each rule 3a record in the merge commit's history, one
GET each as the workflow's `Record comments` step makes them, an unreadable one left out
(amendment 122, brief #601, so that a `Covered-by:` of an ADR a Final accepted is not reported
red), and removes the worktree in every case. A red
run (or a fetch or worktree that fails) opens or updates the red-branch issue through
`route.write_red`, prints

    merge-cleared: stopped: default branch red after #<n>         exit 1

and that open issue holds every later run. It never reverts, pushes nothing and writes no file
but those two files, which go with the temporary folder.
The heavy-lock wait is bounded by `[flow] after_merge_timeout` (minutes, 30 by default; lock.py's
exit 3 is the step `heavy lock`), and any exception, interrupt or SIGTERM after the merge is the
step `governance not finished`: the red-branch issue is still opened (the fix list on #556).

Build (d) (brief #569) adds rule 10, the CI path. GitHub's own auto-merge is offered only through
GraphQL, which this command never calls (`Q-S0039-12`), so in CI mode it reads the head's check runs
and its commit status over REST and, while a required check is still queued or in progress, merges
nothing, turns nothing on and prints `merge-cleared #<n> <sha12>: held: checks pending` (exit 3);
the conductor's next review pass merges once they are green. A red check holds as before.

Brief #610 (ADR-0297, amendment 123 of SPEC-0039 rules 5 and 6) adds the check before the merge.
After every other hold passes, the command fetches the default branch and the head
(`refs/pull/<n>/head`), builds their merge with `git merge-tree --write-tree` as one commit on the
fetched default branch (`git commit-tree`: an object only, the shape of the squash merge), and runs
the same governance run on it in a detached worktree in a temporary folder outside the checkout,
with `AGK_BASE=<the fetched default branch>`. Green merges; red holds with

    merge-cleared #<n> <sha12>: held: the merge with the default branch fails governance (<step>)

(exit 3), and a conflict holds as `conflict (rule 5)`. While the default branch is red, the one
pull request whose first `Brief:` line names the one open red-branch issue is not held for it, and
when its run after the merge is green the command comments on that issue, naming the merge commit,
and closes it; every other pull request stays held.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
import time
import tomllib
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import lock  # noqa: E402
from common import (  # noqa: E402
    DEFAULT_CONFIG,
    FINAL_ACCEPT,
    MERGED_BY,
    STATUS_LINE,
    CheckError,
    covered_fix_list,
    final_accepts,
    final_records,
    show,
)
from reviewers import CONFIG, approval_shas, approvers_of, conductors_of, parse  # noqa: E402

EXIT_CLEARED, EXIT_REFUSED, EXIT_HELD, EXIT_UNREADABLE = 0, 1, 3, 4
READS = 5  # reads in a row that GitHub cannot answer before the command ends (session rule 21)
PAUSE = 1.0  # seconds between two tries of one read
PAGE = 100
SHA = re.compile(r"[0-9a-f]{40}")
NUMBER = re.compile(r"[1-9][0-9]{0,9}")
ORIGIN = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
USAGE = "usage: merge_cleared.py --pr <n> --sha <40-character sha>"
METHOD = "squash"  # the only accepted merge method (SPEC-0039 rule 1, Q-S0039-11)
SETTING = "setting: {} of the flow table in agk.toml on the default branch"
REMOTE = "refs/remotes/origin/"
LOCK = "merge-cleared"  # the named lock of a run (SPEC-0039 rule 9)
RED_TITLE = "The default branch is red"  # the router's red-branch issue (SPEC-0032 rule 7)
RECORD_TITLE = "Local mode since"  # the one local-mode record issue (docs/guides/local-mode.md)
RECORD_LABEL = "agk-auto-merge"  # the record issue the owner opens once (SPEC-0039 rule 7)
HEAVY = "heavy"  # the heavy-step lock of the governance run (SPEC-0039 rule 6)
WAIT_SETTING = "after_merge_timeout"  # minutes the run waits for the heavy lock (fix list, #556)
WAIT_MINUTES = 30
MINUTE = 60.0  # seconds in a minute of after_merge_timeout
LOCK_TIMEOUT = 3  # lock.py run: the lock was not taken in time (or its folder cannot be written)
NOT_FINISHED = "governance not finished"  # the step of a run cut off after the merge
LOCAL_EVIDENCE = re.compile(r"Local evidence: ([0-9a-f]{12,40})(?![0-9A-Za-z])")
EVIDENCE = re.compile(r"Evidence check: (agrees|differs), head ([0-9a-f]{12})(?![0-9A-Za-z])")
ACCEPT = "Maintainer answer: accept {}"  # the one accepted first line (SPEC-0039 rule 4)
APPROVAL = re.compile(r"Approval: (SPEC-\d{4})(?![0-9])")
DEPENDS = re.compile(r"Depends-on: #(\d+)")
BRIEF = re.compile(r"Brief: #(\d+)")  # the line that names the red-branch issue (brief #610)
FAILS = "the merge with the default branch fails governance"  # the hold of the check (#610)
CHECK_PREFIX = "agk-merge-check-"  # the temporary folder of the check before the merge (#610)
AFTER_PREFIX = "agk-merge-cleared-"  # the temporary folder of the run after the merge (#551)
NAME = ("-c", "user.name=merge-cleared", "-c", "user.email=merge-cleared@example.com")
RELEASE = {  # a release changes the kit's version (SPEC-0039 rule 5)
    "agk.toml": re.compile(r"[+-]\s*version\s*="),
    "kit/manifest.json": re.compile(r'[+-]\s*"kit_version"\s*:'),
}
PROTECTED = (  # (class, a prefix) of SPEC-0039 rule 5; a class without a slash is one file
    "constitution/",
    "config/reviewers.yaml",
    "kit/templates/ruleset.json",
    "scripts/agk/ruleset.py",
    ".github/workflows/",
)
HOLD_LABEL = "agk:hold"
APPROVE_LABEL = "agk:approve"
CONFLICT = ("dirty", "unknown")
HTTP = re.compile(r"HTTP (\d{3})")
PENDING = "checks pending"  # SPEC-0039 rule 10, exactly (brief #569)
RED = ("failure", "error")  # a commit status that failed
ENDED = ("success", *RED)  # a commit status that is no longer `pending`


class Refused(CheckError):
    """A refusal: the one line's reason and its exit code."""

    def __init__(self, reason: str, code: int = EXIT_REFUSED) -> None:
        super().__init__(reason)
        self.code = code


class Held(Exception):
    """A hold of SPEC-0039 rules 3 to 5: the reason, named by rule; exit 3."""


class Stopped(Exception):
    """A red governance run after the merge of pull request NUMBER (SPEC-0039 rule 6); exit 1."""

    def __init__(self, number: int, filed: bool) -> None:
        super().__init__(number)
        self.number = number
        self.filed = filed


class Interrupted(BaseException):
    """A termination signal after the merge, raised so that the red-branch issue is still
    opened."""


class Unreadable(Exception):
    """A read GitHub could not answer five times in a row; the message names what was read."""


# --- rule 1: the setting ------------------------------------------------------------------------


def auto_merge_setting(data: dict) -> str:
    """`on` or `off` for the parsed agk.toml DATA (SPEC-0039 rule 1): on only when `[flow]
    auto_merge` is the boolean true and `auto_merge_method` is "squash"; absent or false is off. A
    value of the wrong kind, another method, or true without a method is refused naming the setting,
    never the value."""
    flow = data.get("flow", {})
    if not isinstance(flow, dict):
        raise CheckError("flow in agk.toml must be a table (setting: flow)")
    value = flow.get("auto_merge", False)
    if not isinstance(value, bool):
        raise CheckError(f"auto_merge must be true or false ({SETTING.format('auto_merge')})")
    if "auto_merge_method" in flow and flow["auto_merge_method"] != METHOD:
        raise CheckError(
            f"auto_merge_method must be squash ({SETTING.format('auto_merge_method')})"
        )
    if value and "auto_merge_method" not in flow:
        raise CheckError(
            "auto_merge_method must be squash when auto_merge is on "
            f"({SETTING.format('auto_merge_method')})"
        )
    return "on" if value else "off"


def git_out(root: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8"
    )
    return proc.returncode, proc.stdout.strip()


def default_ref(root: Path) -> tuple[str, dict]:
    """The commit of the remote's default branch as last fetched, and its parsed agk.toml.

    The branch is the one `refs/remotes/origin/HEAD` points to, else `main`; agk.toml there must
    name the same `default_branch` (`main` when unset). Nothing is read from the work tree."""
    code, target = git_out(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    branch = target[len(REMOTE) :] if code == 0 and target.startswith(REMOTE) else "main"
    ref = REMOTE + branch
    code, sha = git_out(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}")
    if code != 0 or not SHA.fullmatch(sha):
        raise Refused(
            "the default branch of the remote has not been fetched (setting: default_branch)"
        )
    text = show(root, sha, "agk.toml")
    if text is None:
        raise Refused("agk.toml is missing on the default branch (path class agk.toml)")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        raise Refused(
            "agk.toml on the default branch is not readable TOML (path class agk.toml)"
        ) from None
    if data.get("default_branch", "main") != branch:
        raise Refused(
            "default_branch in agk.toml does not name the remote's default branch "
            "(setting: default_branch)"
        )
    return sha, data


def after_merge_seconds(data: dict) -> float:
    """`[flow] after_merge_timeout` of the default branch in seconds: whole minutes, at least 1,
    30 when absent; anything else is refused before the merge, naming the setting."""
    flow = data.get("flow", {})
    value = flow.get(WAIT_SETTING, WAIT_MINUTES) if isinstance(flow, dict) else WAIT_MINUTES
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise Refused(
            f"{WAIT_SETTING} must be a positive whole number of minutes "
            f"({SETTING.format(WAIT_SETTING)})"
        )
    return value * MINUTE


def setting_on(data: dict) -> None:
    try:
        state = auto_merge_setting(data)
    except CheckError as err:
        raise Refused(str(err)) from None
    if state != "on":
        raise Refused(f"auto-merge is off ({SETTING.format('auto_merge')})")


# --- reads --------------------------------------------------------------------------------------


def gh_api(args: list[str]) -> subprocess.CompletedProcess:
    """`gh api ARGS`: the one way this command calls GitHub, an argument list with no shell."""
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["gh", "api", *args], capture_output=True, text=True, encoding="utf-8"
    )


def read_json(endpoint: str, kind: type, what: str) -> Any:
    """One `gh api` GET of a REST ENDPOINT, parsed here; an answer that fails, is not JSON or is
    not of KIND is tried again, and the fifth failure in a row raises Unreadable."""
    for attempt in range(READS):
        proc = gh_api(["--method", "GET", endpoint])
        if proc.returncode == 0:
            try:
                value = json.loads(proc.stdout)
            except ValueError:
                value = None
            if isinstance(value, kind):
                return value
        if attempt < READS - 1:
            time.sleep(PAUSE)
    raise Unreadable(what)


def read_pages(endpoint: str, what: str, key: str | None = None) -> list[dict]:
    """Every item of a paged REST list (with KEY, the list under that key of each answer)."""
    found: list[dict] = []
    page = 1
    joiner = "&" if "?" in endpoint else "?"
    while True:
        address = f"{endpoint}{joiner}per_page={PAGE}&page={page}"
        if key is None:
            chunk = read_json(address, list, what)
        else:
            chunk = read_json(address, dict, what).get(key)
            if not isinstance(chunk, list):
                raise Unreadable(what)
        found += [c for c in chunk if isinstance(c, dict)]
        if len(chunk) < PAGE:
            return found
        page += 1


def read_comments(repo: str, number: int) -> list[dict]:
    return read_pages(f"repos/{repo}/issues/{number}/comments", "the comments of the pull request")


def repo_of(root: Path) -> str:
    code, url = git_out(root, "remote", "get-url", "origin")
    match = ORIGIN.search(url) if code == 0 else None
    if not match:
        raise Refused("the remote origin is not a GitHub repository (setting: remote origin)")
    if shutil.which("gh") is None:
        raise Refused("gh is not installed (the GitHub CLI reads the pull request)")
    return match.group(1)


# --- rule 3: the verdict ------------------------------------------------------------------------


def login(item: dict) -> str:
    user = item.get("user")
    name = user.get("login") if isinstance(user, dict) else None
    return name.lower() if isinstance(name, str) else ""


def first_line(item: dict) -> str:
    lines = str(item.get("body") or "").splitlines()
    return lines[0] if lines else ""


def latest_verdict(comments: list[dict]) -> dict | None:
    """The comment with the latest time (then the highest id) whose first line starts `Verdict:`."""
    verdicts = [c for c in comments if first_line(c).startswith("Verdict:")]

    def order(item: dict) -> tuple[str, int]:
        cid = item.get("id")
        return str(item.get("created_at") or ""), cid if isinstance(cid, int) else -1

    return max(verdicts, key=order) if verdicts else None


def judge(comments: list[dict], sha: str, allowed: list[str]) -> tuple[str, str]:
    """(`cleared`, "") or (`held`, reason) for the latest verdict (SPEC-0039 rule 3)."""
    verdict = latest_verdict(comments)
    if verdict is None:
        return "held", "no verdict (rule 3)"
    if first_line(verdict) != f"Verdict: cleared {sha}" and accepted_adrs(verdict, sha) is None:
        return "held", "the latest verdict does not clear this head (rule 3)"
    if allowed and login(verdict) not in allowed:
        return "held", (
            "the verdict's author is not listed "
            "(rule 3; setting: conductor_accounts in config/reviewers.yaml)"
        )
    return "cleared", ""


def accepted_adrs(verdict: dict, sha: str) -> list[str] | None:
    """The ADRs a covered fix list on exactly SHA accepts by its `Final:` lines alone (SPEC-0021
    rule 3a, brief 557), or None: such a verdict clears the head like `Verdict: cleared <sha>`."""
    covered = covered_fix_list(str(verdict.get("body") or ""))
    if covered is None or covered[0] != sha:
        return None
    return final_accepts(covered[1])


def adr_status(repo: str, sha: str, path: str) -> str | None:
    """The `- Status:` word of the ADR at PATH in the commit SHA, read with one GET; None when the
    answer is not a base64 file or has no status line."""
    item = read_json(f"repos/{repo}/contents/{path}?ref={sha}", dict, "an ADR a Final line names")
    if item.get("type") != "file" or item.get("encoding") != "base64":
        return None
    try:
        text = base64.b64decode(str(item.get("content") or ""), validate=False).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    found = [m.group(1) for ln in text.splitlines() if (m := STATUS_LINE.match(ln))]
    return found[0] if found else None


def acceptance_lines(repo: str, sha: str, verdict: dict) -> list[str]:
    """The squash message lines `ADR-nnnn Accepted (Final <comment id>)` of a Final accept, after
    each named ADR is read as `Proposed` at the head; a held run otherwise (rule 3a)."""
    lines = []
    for path in accepted_adrs(verdict, sha) or []:
        if adr_status(repo, sha, path) != "Proposed":
            raise Held("a Final line accepts an ADR that is not Proposed at the head (rule 3)")
        number = path.split("/")[-1][:4]
        lines.append(f"ADR-{number} Accepted (Final {verdict.get('id')})")
    return lines + [MERGED_BY] if lines else []


# --- the default branch's other settings -----------------------------------------------------


def reviewers_at(root: Path, sha: str) -> dict:
    """config/reviewers.yaml at the default branch's commit SHA; absent is no settings, and one
    that cannot be parsed is refused, never read as empty (SPEC-0039 rules 2 and 3)."""
    text = show(root, sha, CONFIG)
    if text is None:
        return {}
    try:
        return parse(text)
    except CheckError:
        raise Refused(
            "config/reviewers.yaml on the default branch cannot be parsed (setting: "
            "conductor_accounts and spec_approvers in config/reviewers.yaml)"
        ) from None


def conductors_in(data: dict) -> list[str]:
    try:
        return conductors_of(data)
    except CheckError as err:
        raise Refused(str(err)) from None


def required_of(data: dict) -> list[str]:
    """`required_checks` of the default branch's agk.toml (the kit's default when unset)."""
    value = data.get("required_checks", DEFAULT_CONFIG["required_checks"])
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(x, str) and x.strip() for x in value)
    ):
        raise Refused(
            "required_checks must be a list of check names (setting: required_checks in agk.toml "
            "on the default branch)"
        )
    return [x.strip() for x in value]


# --- rule 4: evidence ---------------------------------------------------------------------------


def stamp(item: dict) -> tuple[str, int]:
    cid = item.get("id")
    return str(item.get("created_at") or ""), cid if isinstance(cid, int) else -1


def answered(comments: list[dict], verdict: dict, sha: str, approvers: list[str]) -> bool:
    """A comment by a spec approver, after the verdict, whose first line is exactly
    `Maintainer answer: accept <the 40-character head>` (SPEC-0039 rule 4)."""
    wanted = ACCEPT.format(sha)
    for item in comments:
        if first_line(item) != wanted or login(item) not in approvers:
            continue
        if stamp(item) > stamp(verdict):
            return True
    return False


def local_evidence(verdict: dict, comments: list[dict], sha: str, approvers: list[str]) -> None:
    body = str(verdict.get("body") or "")
    lines = [x.strip() for x in body.splitlines()]
    named = [m for x in lines if (m := LOCAL_EVIDENCE.match(x)) and sha.startswith(m.group(1))]
    checks = [m.group(1) for m in EVIDENCE.finditer(body) if m.group(2) == sha[:12]]
    if not named or not checks:
        raise Held("no local evidence for this head (rule 4)")
    if "differs" in checks and not answered(comments, verdict, sha, approvers):
        raise Held("evidence differs (rule 4)")


def ci_evidence(repo: str, sha: str, required: list[str]) -> None:
    """Rule 4 in CI mode, with rule 10's pending hold (brief #569): every required name must have
    reported, as a check run or a commit status of the head (both read over REST), and ended
    green. A red one holds as red; one still queued or in progress holds with exactly `checks
    pending`, nothing is merged and GitHub's own auto-merge is never turned on (GraphQL only,
    `Q-S0039-12`), so the next review pass merges once they are green."""
    from route import latest_runs, latest_statuses  # route imports session; read in CI mode only

    runs = read_pages(f"repos/{repo}/commits/{sha}/check-runs", "the check runs", "check_runs")
    statuses = read_pages(f"repos/{repo}/commits/{sha}/status", "the commit status", "statuses")
    by_run = {str(r.get("name") or ""): r for r in latest_runs(runs)}
    by_status = {str(s.get("context") or ""): s for s in latest_statuses(statuses)}
    found = [[x for x in (by_run.get(n), by_status.get(n)) if x is not None] for n in required]
    reports = [x for name in found for x in name]
    done = [r for r in reports if r.get("status") == "completed" or r.get("state") in ENDED]
    if any(r.get("state") in RED if "context" in r else r.get("conclusion") != "success"
           for r in done):  # fmt: skip
        raise Held("a required check is red (rule 4)")
    if any(not name for name in found):
        raise Held("a required check is missing (rule 4)")
    if len(done) != len(reports):
        raise Held(PENDING)


# --- rule 5: the hold list ----------------------------------------------------------------------


def titled(issues: list[dict], prefix: str, exact: bool = False) -> bool:
    for item in issues:
        title = str(item.get("title") or "")
        if "pull_request" in item:
            continue
        if title == prefix if exact else title.startswith(prefix):
            return True
    return False


def labels_of(pull: dict) -> set[str]:
    return {str(x.get("name")) for x in pull.get("labels") or [] if isinstance(x, dict)}


def released(files: list[dict]) -> bool:
    for item in files:
        name = item.get("filename")
        if name in RELEASE:
            text = item.get("patch")
            if not isinstance(text, str):
                return True  # a change GitHub does not show could be the version
            if any(RELEASE[name].match(x) for x in text.splitlines()):
                return True
    return False


def protected_class(files: list[dict]) -> str | None:
    for item in files:
        for name in (item.get("filename"), item.get("previous_filename")):
            if not isinstance(name, str):
                continue
            for klass in PROTECTED:
                if name == klass or (klass.endswith("/") and name.startswith(klass)):
                    return klass
    return None


def unapproved(pull: dict, comments: list[dict], sha: str, approvers: list[str]) -> bool:
    if APPROVE_LABEL in labels_of(pull):
        return True
    asked = set(APPROVAL.findall(str(pull.get("body") or "")))
    if not asked:
        return False
    approved = approval_shas(comments, [], approvers)
    return any(not any(sha.startswith(s) for s in approved.get(spec, [])) for spec in asked)


def dependence_unmet(repo: str, pull: dict) -> bool:
    for number in dict.fromkeys(DEPENDS.findall(str(pull.get("body") or ""))):
        item = read_json(f"repos/{repo}/issues/{number}", dict, "a Depends-on issue")
        if "pull_request" in item:
            other = read_json(f"repos/{repo}/pulls/{number}", dict, "a Depends-on pull request")
            if not other.get("merged_at"):
                return True
        elif item.get("state") != "closed" or item.get("state_reason") != "completed":
            return True
    return False


def holds_record(text: str) -> bool:
    """Whether TEXT has a line that `common.final_records` would read as a record: an
    `ADR-nnnn Accepted (Final <id>)` line or the line `MERGED_BY` (rule 3a). Only this command
    writes them, so a pull request that carries one is held (brief 557)."""
    lines = [ln.strip() for ln in text.splitlines()]
    return any(ln == MERGED_BY or FINAL_ACCEPT.fullmatch(ln) for ln in lines)


def hold_list(
    repo: str, number: int, pull: dict, comments: list, approvers: list, accepts: list[str]
) -> None:
    """The holds of SPEC-0039 rule 5 after the red branch and paused, in the rule's order; first,
    each ADR a Final line ACCEPTS must be one the pull request adds or changes (rule 3)."""
    files = read_pages(f"repos/{repo}/pulls/{number}/files", "the files of the pull request")
    count = pull.get("changed_files")
    if not isinstance(count, int) or isinstance(count, bool) or count != len(files):
        raise Held("files not all read (rule 5)")  # GitHub lists at most 3,000 files (rule 2)
    touched = {
        item.get("filename") for item in files if item.get("status") in ("added", "modified")
    }
    if any(path not in touched for path in accepts):
        raise Held("a Final line accepts an ADR that this pull request does not change (rule 3)")
    commits = read_pages(f"repos/{repo}/pulls/{number}/commits", "the commits of the pull request")
    count = pull.get("commits")
    if not isinstance(count, int) or isinstance(count, bool) or count != len(commits):
        raise Held("commits not all read (rule 5)")  # GitHub lists at most 250 commits
    texts = [str(pull.get("body") or "")]
    texts += [str((c.get("commit") or {}).get("message") or "") for c in commits]
    if any(holds_record(text) for text in texts):
        raise Held("a commit or the body already holds a record line (rule 3)")
    sha = str(pull["head"]["sha"])
    if released(files):
        raise Held("release (rule 5)")
    if unapproved(pull, comments, sha, approvers):
        raise Held("spec approval (rule 5)")
    if (klass := protected_class(files)) is not None:
        raise Held(f"protected class {klass} (rule 5)")
    if HOLD_LABEL in labels_of(pull):
        raise Held("hold label (rule 5)")
    if pull.get("draft") is not False:
        raise Held("draft (rule 5)")
    if dependence_unmet(repo, pull):
        raise Held("depends-on (rule 5)")
    state = pull.get("mergeable_state")
    if not isinstance(state, str) or state in CONFLICT:
        raise Held("conflict (rule 5)")


# --- rule 6: the pinned merge -------------------------------------------------------------------


def write_once(args: list[str]) -> tuple[int, str, str]:
    """One `gh` call that writes: never retried (SPEC-0039 rule 6)."""
    proc = gh_api(args)
    return proc.returncode, proc.stdout, proc.stderr


def current_head(repo: str, number: int) -> str:
    pull = read_json(f"repos/{repo}/pulls/{number}", dict, "the pull request")
    head = pull.get("head")
    return str(head.get("sha") if isinstance(head, dict) else "")


def merge_pull(repo: str, number: int, sha: str, message: list[str] | None = None) -> str:
    """The one merge call, pinned to SHA with the squash method; the merge commit's sha. The
    squash commit message is always this command's own: MESSAGE (the acceptance lines of rule 3a)
    or the line `MERGED_BY` alone, never GitHub's default, which copies the commit bodies."""
    args = ["--method", "PUT", f"repos/{repo}/pulls/{number}/merge"]
    args += ["-f", f"sha={sha}", "-f", f"merge_method={METHOD}"]
    args += ["-f", "commit_message=" + "\n".join(message or [MERGED_BY])]
    code, out, err = write_once(args)
    if code != 0:
        found = HTTP.search(err)
        status = int(found.group(1)) if found else 0
        if status == 409:
            raise Refused("head moved (rule 6: GitHub refused the pinned sha)", EXIT_HELD)
        if status == 405:
            if current_head(repo, number) != sha:
                raise Refused("head moved (rule 6: GitHub refused the pinned sha)", EXIT_HELD)
            raise Refused("GitHub did not merge: not mergeable (rule 6)", EXIT_HELD)
        if status == 0 or status >= 500:
            raise Refused("GitHub cannot be reached for the merge (rule 6)", EXIT_HELD)
        raise Refused("GitHub refused the merge (rule 6)")
    try:
        answer = json.loads(out)
    except ValueError:
        answer = None
    merged = answer.get("sha") if isinstance(answer, dict) else None
    if not (isinstance(answer, dict) and answer.get("merged") is True and isinstance(merged, str)):
        raise Refused("GitHub did not report a merge (rule 6)")
    if not SHA.fullmatch(merged):
        raise Refused("GitHub did not report a merge (rule 6)")
    return merged


# --- rule 7: the record -------------------------------------------------------------------------


def record_issue(issues: list[dict]) -> int | None:
    """The number of the issue the record line goes to: the one open local-mode record issue while
    one is open, else the one open issue labelled `agk-auto-merge`; None with neither, or with more
    than one of the kind it would use (SPEC-0039 rule 7)."""
    plain = [i for i in issues if "pull_request" not in i and isinstance(i.get("number"), int)]
    local = [i for i in plain if str(i.get("title") or "").startswith(RECORD_TITLE)]
    found = local or [i for i in plain if RECORD_LABEL in labels_of(i)]
    return int(found[0]["number"]) if len(found) == 1 else None


def verdict_link(repo: str, number: int, verdict: dict) -> str:
    url = verdict.get("html_url")
    if isinstance(url, str) and url.startswith("https://"):
        return url
    return f"https://github.com/{repo}/pull/{number}#issuecomment-{verdict.get('id')}"


def post_record(repo: str, issue: int, number: int, merged: str, verdict: dict) -> bool:
    """The one record line of SPEC-0039 rule 7, posted once; whether GitHub took it."""
    when = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"Auto merge: #{number} {merged} {when} {verdict_link(repo, number, verdict)}"
    args = ["--method", "POST", f"repos/{repo}/issues/{issue}/comments", "-f", f"body={line}"]
    code, _, _ = write_once(args)
    return code == 0


# --- rule 6: governance after the merge, and the red-branch stop -------------------------------


RECORD_COMMENTS = "record-comments.json"  # in the run's home (amendment 122, brief #601)


def governance_argv(tree: Path, home: Path, body: Path, base: str, wait: float) -> list[str]:
    """The governance run of SPEC-0039 rule 6 as one argument list: the project's own lock.py,
    the heavy lock waited for at most WAIT seconds, and `env -i` so that only PATH, HOME,
    AGK_PR_BODY (the file BODY holding the merged pull request's body, brief #576) and
    AGK_RECORD_COMMENTS (HOME's file of the records' Final comments, amendment 122, brief #601)
    reach the merged code."""
    lock_py = Path(__file__).resolve().parent / "lock.py"
    return [
        sys.executable,
        str(lock_py),
        "run",
        "--name",
        HEAVY,
        "--session",
        LOCK,
        "--timeout",
        f"{wait:g}",
        "--",
        "env",
        "-i",
        f"PATH={os.environ.get('PATH', '')}",
        f"HOME={home}",
        f"AGK_PR_BODY={body}",
        f"AGK_RECORD_COMMENTS={home / RECORD_COMMENTS}",
        "make",
        "-C",
        str(tree),
        "governance",
        f"AGK_BASE={base}",
    ]


def run_governance(
    root: Path, tree: Path, home: Path, body: Path, base: str, wait: float
) -> str | None:
    """Run governance once in TREE; its output goes to standard error. None when it passed, else
    the failing step: `heavy lock` when lock.py did not take the lock in WAIT seconds (its exit
    3), otherwise `make governance`. An interrupt ends lock.py (which ends its command and frees
    the heavy lock) and is raised again."""
    child = subprocess.Popen(  # nosec B603 - fixed argument list, no shell
        governance_argv(tree, home, body, base, wait),
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        out, _ = child.communicate()
    except BaseException:
        end_child(child)
        raise
    sys.stderr.write(out or "")
    if child.returncode == 0:
        return None
    return "heavy lock" if child.returncode == LOCK_TIMEOUT else "make governance"


def end_child(child: subprocess.Popen) -> None:
    if child.poll() is None:
        child.terminate()
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def record_comments(repo: str, root: Path, merged: str) -> list[dict]:
    """The Final comment of each SPEC-0021 rule 3a record in the history of the merge commit
    MERGED (the ids `check_adrs.py --record-ids` prints there, read here by the command's own
    `common.final_records`), one GET each, the GETs of the workflow's `Record comments` step; a
    comment that cannot be read is left out, so its record counts for nothing (amendment 122,
    brief #601)."""
    found: list[dict] = []
    for cid in sorted({record[1] for record in final_records(root, merged).values()}):
        try:
            found.append(read_json(f"repos/{repo}/issues/comments/{cid}", dict, "a Final comment"))
        except Unreadable:
            continue
    return found


def governance(
    root: Path, branch: str, merged: str, wait: float, text: str, repo: str = ""
) -> str | None:
    """Fetch the default branch, run governance on the merge commit in a temporary worktree
    outside the checkout, with TEXT (the pull request body read before the merge) and the Final
    comments of the merge commit's records (read from REPO) in files of the run's temporary home,
    and remove all of them in every case. None when green, else the failing step (`fetch`,
    `worktree`, `heavy lock` or `make governance`)."""
    code, _ = git_out(root, "fetch", "-q", "origin", branch)
    if code != 0:
        return "fetch"
    code, _ = git_out(root, "merge-base", "--is-ancestor", merged, f"{REMOTE}{branch}")
    parent_code, parent = git_out(root, "rev-parse", "--verify", "-q", f"{merged}^1")
    if code != 0 or parent_code != 0 or not SHA.fullmatch(parent):
        return "fetch"
    return in_worktree(root, merged, parent, wait, text, AFTER_PREFIX, repo)


def in_worktree(
    root: Path, commit: str, base: str, wait: float, text: str, prefix: str, repo: str = ""
) -> str | None:
    """The governance run on COMMIT against BASE in a detached worktree of a new temporary folder
    outside the checkout (named with PREFIX), with TEXT in the body file of its temporary home and
    the Final comments of COMMIT's records (read from REPO, amendment 122) in its record-comments
    file; both are removed in every case. The one run of rule 6, after the merge and before it
    (brief #610). None when green, else the failing step."""
    scratch = Path(tempfile.mkdtemp(prefix=prefix))
    tree, home = scratch / "tree", scratch / "home"
    body = home / "pr-body.md"
    try:
        home.mkdir()
        body.write_text(text, encoding="utf-8")
        found = record_comments(repo, root, commit) if repo else []
        (home / RECORD_COMMENTS).write_text(json.dumps(found), encoding="utf-8")
        code, _ = git_out(root, "worktree", "add", "--detach", "-q", str(tree), commit)
        if code != 0:
            return "worktree"
        return run_governance(root, tree, home, body, base, wait)
    finally:
        git_out(root, "worktree", "remove", "--force", str(tree))
        shutil.rmtree(scratch, ignore_errors=True)
        git_out(root, "worktree", "prune")


def would_be_merge(root: Path, branch: str, number: int, sha: str) -> tuple[str | None, str]:
    """Fetch the default branch and the pull request's head, and make their merge one commit on
    the fetched default branch, as the squash merge will be: (the commit, the default branch's
    commit), or (None, the failing step). A conflict holds, as rule 5 holds one (brief #610)."""
    code, _ = git_out(root, "fetch", "-q", "origin", branch, f"refs/pull/{number}/head")
    base_code, base = git_out(root, "rev-parse", "--verify", "-q", f"{REMOTE}{branch}^{{commit}}")
    head_code, _ = git_out(root, "cat-file", "-e", f"{sha}^{{commit}}")
    if code != 0 or base_code != 0 or head_code != 0 or not SHA.fullmatch(base):
        return None, "fetch"
    code, out = git_out(root, "merge-tree", "--write-tree", "--no-messages", base, sha)
    if code == 1:
        raise Held("conflict (rule 5)")
    tree = out.splitlines()[0] if out else ""
    if code != 0 or not SHA.fullmatch(tree):
        return None, "merge-tree"
    message = f"merge-cleared: the would-be merge of #{number}"
    code, commit = git_out(root, *NAME, "commit-tree", tree, "-p", base, "-m", message)
    if code != 0 or not SHA.fullmatch(commit):
        return None, "merge-tree"
    return commit, base


def merge_check(
    root: Path, branch: str, number: int, sha: str, wait: float, text: str, repo: str = ""
) -> str | None:
    """Governance on the would-be merge of SHA with the default branch, before the merge (brief
    #610, amendment 123): the run of rule 6 on it. None when green, else the failing step; any
    exception, interrupt or termination is `governance not finished`, nothing having merged."""
    with after_merge_signals():
        try:
            commit, base = would_be_merge(root, branch, number, sha)
            if commit is None:
                return base
            return in_worktree(root, commit, base, wait, text, CHECK_PREFIX, repo)
        except Held:
            raise
        except BaseException:  # a run that cannot finish is not green; nothing has merged
            return NOT_FINISHED


def commit_url(repo: str, sha: str) -> str:
    return f"https://github.com/{repo}/commit/{sha}"


def file_red(repo: str, step: str, merged: str) -> bool:
    """Open or update the red-branch issue through the router's writer (SPEC-0039 rule 6,
    Q-S0039-6), naming the failing step and the merge commit and no cause; whether it was
    written."""
    import route  # route imports session; read only after a red run

    try:
        found = read_pages(f"repos/{repo}/issues?state=open&labels=agk-brief", "the open briefs")
        open_red = sorted((i for i in found if route.is_red(i)), key=lambda i: i["number"])
        body = route.red_body(step, merged, commit_url(repo, merged))
        route.write_red(repo, open_red, body, route.Labels(repo))
    except Exception:  # any failure to write it is said on the stop line (fix list, #556)
        return False
    return True


def red_issues(issues: list[dict]) -> list[dict]:
    """The open issues titled exactly `The default branch is red`, whoever wrote them."""
    return [i for i in issues if "pull_request" not in i and i.get("title") == RED_TITLE]


def red_fix(pull: dict, reds: list[dict]) -> int | None:
    """The number of the one open red-branch issue that the first `Brief:` line of the pull
    request's body names exactly (`Brief: #<n>`), else None (brief #610, amendment 123)."""
    if len(reds) != 1 or not isinstance(reds[0].get("number"), int):
        return None
    lines = [x.rstrip() for x in str(pull.get("body") or "").splitlines()]
    first = next((x for x in lines if x.startswith("Brief:")), "")
    found = BRIEF.fullmatch(first)
    return reds[0]["number"] if found and int(found.group(1)) == reds[0]["number"] else None


def close_red(repo: str, issue: int, number: int, merged: str) -> bool:
    """After a green run after the merge of the red-branch fix: one comment on ISSUE naming the
    merge commit, then the issue closed as completed (brief #610); whether both were written."""
    line = (
        f"The default branch is green again: governance passed on the merge commit {merged} "
        f"of #{number} ({commit_url(repo, merged)}), merged by merge_cleared.py."
    )
    endpoint = f"repos/{repo}/issues/{issue}"
    code, _, _ = write_once(["--method", "POST", f"{endpoint}/comments", "-f", f"body={line}"])
    if code != 0:
        return False
    args = ["--method", "PATCH", endpoint, "-f", "state=closed", "-f", "state_reason=completed"]
    code, _, _ = write_once(args)
    return code == 0


def on_signal(signum: int, frame: object) -> None:
    raise Interrupted(signum)


@contextlib.contextmanager
def after_merge_signals() -> Iterator[None]:
    """After the merge, SIGTERM and SIGHUP raise Interrupted instead of ending the process, so
    the red-branch issue is still opened; the handlers before are put back afterwards."""
    before: dict[int, Any] = {}
    for name in ("SIGTERM", "SIGHUP"):
        signum = getattr(signal, name, None)
        if signum is not None:
            before[signum] = signal.signal(signum, on_signal)
    try:
        yield
    finally:
        for signum, handler in before.items():
            signal.signal(signum, handler)


def after_merge(
    root: Path,
    repo: str,
    number: int,
    merged: str,
    record: int,
    verdict: dict,
    data: dict,
    text: str,
    fixing: int | None = None,
) -> tuple[bool, bool]:
    """Everything after the merge (SPEC-0039 rules 6 and 7): the record line, then governance.
    Any exception, interrupt or termination counts as red (`governance not finished`): the
    red-branch issue is opened or updated and Stopped is raised. When green and the merge was the
    fix of the red-branch issue FIXING, that issue is closed (brief #610). Whether the record was
    posted, and whether the issue to close was closed."""
    wait = after_merge_seconds(data)
    recorded = False
    with after_merge_signals():
        try:
            recorded = post_record(repo, record, number, merged, verdict)
            branch = str(data.get("default_branch", "main"))
            step = governance(root, branch, merged, wait, text, repo)
        except BaseException:  # the merge stands; the run cannot show green (fix list, #556)
            step = NOT_FINISHED
        if step is not None:
            try:
                filed = file_red(repo, step, merged)
            except BaseException:  # an interrupt while it is written: said on the stop line
                filed = False
            raise Stopped(number, filed)
    closed = fixing is None or close_red(repo, fixing, number, merged)
    return recorded, closed


# --- rule 9: the lock ---------------------------------------------------------------------------


@contextlib.contextmanager
def merge_lock(root: Path) -> Iterator[None]:
    """Hold the named lock `merge-cleared` (one slot) for the rest of the run; lock.py's wait
    lines go to standard error, so that standard output keeps its one line."""
    try:
        held = lock.lock_folder(root, LOCK)
        limit = lock.stale_minutes(root)
    except lock.Usage as err:
        raise Refused(f"the lock {LOCK} cannot be read ({err})") from None
    token = uuid.uuid4().hex
    owner = {
        "session": os.environ.get("AGK_SESSION") or LOCK,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": token,
    }
    try:
        with contextlib.redirect_stdout(sys.stderr):
            taken = lock.take(held, LOCK, owner, limit, None)
    except OSError:
        lock.clear_if_same(held, token)
        raise Refused(f"the lock {LOCK} cannot be written (setting: lock_dir)") from None
    try:
        yield
    finally:
        lock.clear_if_same(taken or held, token)


# --- the command --------------------------------------------------------------------------------


def parse_args(argv: list[str]) -> tuple[int, str] | None:
    if len(argv) != 4 or argv[0] != "--pr" or argv[2] != "--sha":
        return None
    if not NUMBER.fullmatch(argv[1]) or not SHA.fullmatch(argv[3]):
        return None
    return int(argv[1]), argv[3]


def outcome(root: Path, number: int, sha: str) -> tuple[str, str, int]:
    base, data = default_ref(root)
    setting_on(data)
    if data.get("paused") is True:
        raise Held("paused (rule 5; setting: paused in agk.toml on the default branch)")
    people = reviewers_at(root, base)
    allowed = conductors_in(people)
    approvers = approvers_of(people)
    required = required_of(data)
    after_merge_seconds(data)  # a bad setting is refused before anything is merged
    repo = repo_of(root)
    with merge_lock(root):
        pull = read_json(f"repos/{repo}/pulls/{number}", dict, "the pull request")
        head = pull.get("head")
        head_sha = head.get("sha") if isinstance(head, dict) else None
        if not isinstance(head_sha, str) or not SHA.fullmatch(head_sha):
            raise Unreadable("the pull request")
        if head_sha != sha:
            raise Refused("head moved (rule 3: --sha is not the pull request's head)", EXIT_HELD)
        comments = read_comments(repo, number)
        state, reason = judge(comments, sha, allowed)
        if state != "cleared":
            return "held", reason, EXIT_HELD
        verdict = latest_verdict(comments) or {}
        accepted = acceptance_lines(repo, sha, verdict)
        issues = read_pages(f"repos/{repo}/issues?state=open", "the open issues")
        reds = red_issues(issues)
        fixing = red_fix(pull, reds) if reds else None
        if reds and fixing is None:  # only the red-branch fix may merge (brief #610)
            raise Held("the default branch is red (rule 5)")
        record = record_issue(issues)
        if record is None:
            raise Held("no record issue (rule 7)")
        if data.get("execution") == "local" or titled(issues, RECORD_TITLE):
            local_evidence(verdict, comments, sha, approvers)
        else:
            ci_evidence(repo, sha, required)
        hold_list(repo, number, pull, comments, approvers, accepted_adrs(verdict, sha) or [])
        text = str(pull.get("body") or "")  # the body read above, for governance (brief #576)
        branch = str(data.get("default_branch", "main"))
        step = merge_check(root, branch, number, sha, after_merge_seconds(data), text, repo)
        if step is not None:
            raise Held(f"{FAILS} ({step})")
        merged = merge_pull(repo, number, sha, accepted)
        recorded, closed = after_merge(
            root, repo, number, merged, record, verdict, data, text, fixing
        )
    if not recorded:
        return f"merged {merged[:12]}", "the record line cannot be posted (rule 7)", EXIT_REFUSED
    if not closed:
        return (
            f"merged {merged[:12]}",
            "the red-branch issue cannot be closed (rule 6)",
            EXIT_REFUSED,
        )
    return f"merged {merged[:12]}", "", EXIT_CLEARED


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args is None:
        print(f"merge-cleared #? ?: refused: {USAGE}")
        return EXIT_REFUSED
    number, sha = args
    prefix = f"merge-cleared #{number} {sha[:12]}:"
    try:
        word, reason, code = outcome(Path.cwd() if root is None else root, number, sha)
    except Held as err:
        print(f"{prefix} held: {err}")
        return EXIT_HELD
    except Refused as err:
        print(f"{prefix} refused: {err}")
        return err.code
    except Unreadable as err:
        print(f"{prefix} refused: GitHub cannot be read ({err}, {READS} reads in a row)")
        return EXIT_UNREADABLE
    except Stopped as stop:
        missing = "" if stop.filed else " (the red-branch issue cannot be written)"
        print(f"merge-cleared: stopped: default branch red after #{stop.number}{missing}")
        return EXIT_REFUSED
    print(f"{prefix} {word}: {reason}" if reason else f"{prefix} {word}")
    return code


if __name__ == "__main__":
    sys.exit(main())
