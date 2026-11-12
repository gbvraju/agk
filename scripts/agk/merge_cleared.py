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

Brief #628 (ADR-0304, amendment 124 of SPEC-0039 rule 5) keeps a spec approval on a later head: an
`Approve: <sha> SPEC-<n>` counts for the head when the spec's text there is its text at `<sha>`
apart from the status flip from `Draft` to `Approved`, read with local `git` (the head fetched
from `refs/pull/<n>/head` only when missing); anything unreadable holds as `spec approval`.

Brief #667 (ADR-0320, amendment 132 of SPEC-0039 rule 6) adds the kit tests that read the whole
tree to the check before the merge. After governance passes on the would-be merge, in the same
worktree, the command runs the test files of `[testing] pre_merge_tests` (agk.toml on the default
branch; without the key, none) under the heavy lock: `lock.py run --name heavy ... -- env -i
PATH=<PATH> HOME=<scratch> AGK_KIT_TESTS=1 PYTHONDONTWRITEBYTECODE=1 <python> -m pytest -q
--rootdir <worktree> ... <worktree>/<file>...`; pytest reads the configuration file it finds
above the listed files. A failure, or a listed name that is not a file of the merge, holds with

    merge-cleared #<n> <sha12>: held: the merge with the default branch fails pre-merge tests
        (<file>::<test>)                                          (one line)

(exit 3), nothing merged; a bad setting is refused before anything runs, naming the setting.

Brief #643 build (b) (ADR-0329) changes no behaviour: the settings read before any GitHub read are
`ruled`, the holds that merge nothing are `holds` (a verdict that does not clear the head raises
`NotCleared`, a `Held`) and local mode is `local_mode`, so that `conductor.py merge-queue` judges
each open pull request with the same functions and copies no rule.

SPEC-0050 build (b) (brief #727, ADR-0339, rules 6 and 8) adds two holds after every hold above
passes and before the governance run of the check before the merge: once the would-be merge is
built (so a fetch that fails and a conflict hold as before), it reads the fetched default branch
and the head with local `git` only (`session_plan.reprove_files`, `behind_merges`):

    merge-cleared #<n> <sha12>: held: re-prove (rule 6 of SPEC-0050)
    merge-cleared #<n> <sha12>: held: behind the default branch (setting flow.max_behind_merges)
    merge-cleared #<n> <sha12>: held: re-prove (unknown)

(exit 3, nothing merged, recorded or filed): the first when a file the head changes since its
merge base was also changed on the default branch after it; the second only when `[flow]
max_behind_merges` (opt-in, an integer of at least 0; anything else refused naming the setting)
is set and the first-parent commits of the default branch after the merge base are above it; the
third when either read fails. A line names the rule or the setting, never a file, count or sha.

`--sweep` (brief #797, ADR-0373; brief #836, ADR-0383) is the merger's pass after every finished
check and on its schedule: the open, non-draft pull requests, oldest first, the guarded merge above
on at most five whose latest verdict clears the current head, one line each, `MERGED #<n> <m> min
after cleared` for each it merged, and `UNMERGED #<n> cleared <m> min <reason>` for a cleared one
older than 20 minutes it could not merge (in local mode it only reports). The label is never an
input: a cleared pull request labelled `agk:fix` or `agk:review` prints `LABEL #<n> <label> but
cleared`, and the router runs for it when it is left unmerged. `--sweep-gate` prints `on` or `off`
for the workflow.

`--status --pr <n> --sha <head>` (brief #853, ADR-0387) sets the commit status `agk/verdict` by the
reading of the merge: `success` when the head is cleared, no hold of rule 5 stands and it is not in
the re-prove state; else `pending` with the reason. It prints `merge-cleared #<n> <sha12>: status
<state>` and sets nothing in local mode or on a `--sha` that is not the head. `--status --event FILE
--event-name NAME` is the job's form, for a comment; the merger also starts on that status with
`success`, and only the guarded command merges.

Brief #972 (ADR-0417, amendment 158 of SPEC-0039 rule 2a) changes what `[flow] merge_queue = true`
does in GitHub mode (not local mode, not personal mode): every hold above still runs first, in the
same order, the check before the merge included (`Q-S0039-18`); then, instead of merging, the
command adds the head to GitHub's merge queue, pinned to the cleared sha:

    merge-cleared #<n> <sha12>: queued                            exit 0
    merge-cleared #<n> <sha12>: already queued                    exit 0
    merge-cleared #<n> <sha12>: refused: head moved (rule 2a: ...)  exit 3

The queue is offered only through GraphQL (`enqueuePullRequest` with `expectedHeadOid`, verify), so
that one read and one write are made only inside GitHub Actions (`GITHUB_ACTIONS=true`, the merger
job, with `AGK_MERGE_TOKEN` set); anywhere else, or without that token, the command is refused with
a line naming rule 2a before any GraphQL call, and a session stays REST-only (`Q-S0039-12`,
`Q-S0039-19`). A head with a `Removed from the merge queue:` line newer than its clearing verdict is
held (`removed from the merge queue since the verdict (rule 2c)`) until a new verdict, so a sweep
never queues a removed head again. A head already in the queue is read before the check before the
merge, so a sweep never re-runs it for a queued head. `--queue-removed --event FILE` is the
merger's job on a failed `governance` or `proof` run of the `merge_group` event: one comment
`Removed from the merge queue: <check> failed on <queue sha12>` on the pull request the queue's
branch names (`gh-readonly-queue/<base>/pr-<n>-<sha>`, verify), only when GitHub removed it (open,
not merged and not in the queue, read with the merger's token), never twice for one queue sha
(rule 2c).
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
from typing import Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import impact  # noqa: E402
import lock  # noqa: E402
import session_plan  # noqa: E402
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
    status_flip_only,
)
from reviewers import (  # noqa: E402
    CONFIG,
    approval_shas,
    approvers_of,
    conductors_of,
    parse,
    specs_named_approved,
)

EXIT_CLEARED, EXIT_REFUSED, EXIT_HELD, EXIT_UNREADABLE = 0, 1, 3, 4
READS = 5  # reads in a row that GitHub cannot answer before the command ends (session rule 21)
PAUSE = 1.0  # seconds between two tries of one read
PAGE = 100
SHA = re.compile(r"[0-9a-f]{40}")
FALLBACK = " (conductor fallback)"  # a verdict's first-line ending (ADR-0431 decision 3)
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
REPROVE = "re-prove (rule 6 of SPEC-0050)"  # brief #727, SPEC-0050 rule 8
REPROVE_UNKNOWN = "re-prove (unknown)"
BEHIND_SETTING = "max_behind_merges"
BEHIND = f"behind the default branch (setting flow.{BEHIND_SETTING})"
TESTS_FAIL = "the merge with the default branch fails pre-merge tests"  # brief #667
FAILED_LINE = re.compile(r"^(?:FAILED|ERROR) (\S+?)(?: - .*)?$")  # pytest's short summary line
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
HOLD_LABELS = (HOLD_LABEL, "agk:parked")  # a person's hold, on a brief or a pull request (Q-846-1)
APPROVE_LABEL = "agk:approve"
CONFLICT = ("dirty", "unknown")
HTTP = re.compile(r"HTTP (\d{3})")
RULESET = "rule violation"  # GitHub's words for a merge its ruleset refuses (brief #765, verify)
JOB_LINE = re.compile(
    r"merge-cleared #([1-9][0-9]{0,9}) ([0-9a-f]{12}): "
    r"(merged|queued|already queued|held|refused)(?:\s|:|$)"
)
CREATED_STARTS = ("Verdict:", "Approve:")  # first lines of a new comment that may clear a head
EDITED_STARTS = (*CREATED_STARTS, "Final:")  # and of an edited one (brief #836 answer 1)
STALE_LABELS = (
    "agk:build",
    "agk:fix",
    "agk:review",
)  # a cleared head's label contradicts these (brief #836)
SWEEP_MAX = 5  # guarded merges a run (brief #797 answer 3)
UNMERGED_MINUTES = 20  # brief #797 answer 5
STOPPED = "merge-cleared: stopped:"
SPEC_FILE = re.compile(r"docs/specs/(\d{4})-[^/]+\.md")
DRAFT_HOLD = "an approved spec still reads Draft (rule 5)"  # brief #797 answer 4
JOB_PREFIX = "merger: "  # the one comment of a hold or a refusal (brief #765)
MERGE_ENV = "AGK_MERGE_TOKEN"  # the one variable the merge call reads; only the job sets it
NO_MERGE_LINE = f"merge needs {MERGE_ENV} or the owner's tap"  # the `Correction:` on brief #765
PENDING = "checks pending"  # SPEC-0039 rule 10, exactly (brief #569)
RED = ("failure", "error")  # a commit status that failed
ENDED = ("success", *RED)  # a commit status that is no longer `pending`
STATUS_CONTEXT = "agk/verdict"  # the commit status of a verdict (brief #853)
STATUS_LIMIT = 140  # characters GitHub takes in a status description (verify)
OWNER_MERGE = "owner merge"
QUEUE_SETTING = "merge_queue"
QUEUE_OUTSIDE = (
    f"the merge queue is joined only by the merger job on GitHub Actions with {MERGE_ENV} "
    "(rule 2a; a session stays REST-only)"
)
QUEUE_MOVED = "head moved (rule 2a: GitHub refused the pinned sha)"
QUEUE_FAILED = "GitHub did not add the head to the merge queue (rule 2a)"
QUEUE_BRANCH = re.compile(r"gh-readonly-queue/.+/pr-([1-9][0-9]{0,9})-[0-9a-f]{40}")
QUEUE_REMOVED = "Removed from the merge queue: {check} failed on {sha12}"
REMOVED_START = "Removed from the merge queue:"
REMOVED_HOLD = "removed from the merge queue since the verdict (rule 2c)"
QUEUE_READ = (
    "query($owner: String!, $name: String!, $number: Int!) { repository(owner: $owner, "
    "name: $name) { pullRequest(number: $number) { id headRefOid isInMergeQueue } } }"
)
QUEUE_WRITE = (
    "mutation($pullRequestId: ID!, $expectedHeadOid: GitObjectID!) { enqueuePullRequest(input: "
    "{pullRequestId: $pullRequestId, expectedHeadOid: $expectedHeadOid}) "
    "{ mergeQueueEntry { state position } } }"
)


class Refused(CheckError):
    """A refusal: the one line's reason and its exit code."""

    def __init__(self, reason: str, code: int = EXIT_REFUSED) -> None:
        super().__init__(reason)
        self.code = code


class Held(Exception):
    """A hold of SPEC-0039 rules 3 to 5: the reason, named by rule; exit 3."""


class NotCleared(Held):
    """The hold of rule 3 alone: the latest verdict does not clear this head. The merge queue
    (`conductor.py merge-queue`, brief #643, ADR-0329) leaves such a pull request out silently."""


class Rules(NamedTuple):
    """What a run reads from the default branch before any GitHub read (`ruled`)."""

    data: dict  # agk.toml
    people: dict  # config/reviewers.yaml
    allowed: list[str]  # conductor_accounts
    approvers: list[str]  # spec_approvers
    required: list[str]  # required_checks
    pre: dict | None = None  # [testing] pre_merge_tests, checked (brief #667)
    behind: int | None = None  # [flow] max_behind_merges, checked (brief #727)
    queue: bool = False  # [flow] merge_queue, checked (brief #853)


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


def default_branch(root: Path) -> str:
    """The name of the remote's default branch: the one `refs/remotes/origin/HEAD` points to,
    else `main`."""
    code, target = git_out(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    return target[len(REMOTE) :] if code == 0 and target.startswith(REMOTE) else "main"


def default_ref(root: Path) -> tuple[str, dict]:
    """The commit of the remote's default branch as last fetched, and its parsed agk.toml.

    The branch is the one `refs/remotes/origin/HEAD` points to, else `main`; agk.toml there must
    name the same `default_branch` (`main` when unset). Nothing is read from the work tree."""
    branch = default_branch(root)
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


def max_behind_setting(data: dict) -> int | None:
    """`[flow] max_behind_merges` of the default branch (SPEC-0050 rule 8): None when absent, else
    an integer of at least 0; anything else is refused before any read, naming the setting."""
    flow = data.get("flow", {})
    if not isinstance(flow, dict) or BEHIND_SETTING not in flow:
        return None
    value = flow[BEHIND_SETTING]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Refused(
            f"{BEHIND_SETTING} must be a whole number of at least 0 "
            f"({SETTING.format(BEHIND_SETTING)})"
        )
    return value


def merge_queue_setting(data: dict) -> bool:
    """`[flow] merge_queue` (brief #853 answer 4): a boolean, false when absent; anything else is
    refused naming the setting, never the value."""
    flow = data.get("flow", {})
    value = flow.get(QUEUE_SETTING, False) if isinstance(flow, dict) else False
    if not isinstance(value, bool):
        raise Refused(f"{QUEUE_SETTING} must be true or false ({SETTING.format(QUEUE_SETTING)})")
    return value


def setting_on(data: dict) -> None:
    try:
        state = auto_merge_setting(data)
    except CheckError as err:
        raise Refused(str(err)) from None
    if state != "on":
        raise Refused(f"auto-merge is off ({SETTING.format('auto_merge')})")


# --- reads --------------------------------------------------------------------------------------


def gh_api(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """`gh api ARGS`: the one way this command calls GitHub, an argument list with no shell."""
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["gh", "api", *args], capture_output=True, text=True, encoding="utf-8", env=env
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
    first = first_line(verdict).removesuffix(FALLBACK)  # ADR-0431 decision 3: read as the same
    if first != f"Verdict: cleared {sha}" and accepted_adrs(verdict, sha) is None:
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


def adr_status(
    repo: str, sha: str, path: str, what: str = "an ADR a Final line names"
) -> str | None:
    """The `- Status:` word of the ADR (or spec) at PATH in the commit SHA, read with one GET; None
    when the answer is not a base64 file or has no status line."""
    item = read_json(f"repos/{repo}/contents/{path}?ref={sha}", dict, what)
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


def held_label(pull: dict) -> str | None:
    """The first hold label on PULL, or None (SPEC-0039 rule 5, ADR-0385)."""
    return next((name for name in HOLD_LABELS if name in labels_of(pull)), None)


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


def git_bytes(root: Path, *args: str) -> bytes | None:
    """The output of one local `git` read as bytes, or None when it fails."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True
    )
    return proc.stdout if proc.returncode == 0 else None


def head_present(root: Path, number: int, sha: str) -> bool:
    """Whether the commit SHA is in the checkout, fetching `refs/pull/<n>/head` once when it is
    not: the ref the check before the merge fetches anyway (amendment 123)."""
    if git_out(root, "cat-file", "-e", f"{sha}^{{commit}}")[0] == 0:
        return True
    git_out(root, "fetch", "-q", "origin", f"refs/pull/{number}/head")
    return git_out(root, "cat-file", "-e", f"{sha}^{{commit}}")[0] == 0


def same_text(root: Path, sha: str, spec: str, approved: str) -> bool:
    """Whether the spec SPEC-nnnn at the head SHA is its text at the APPROVED commit apart from the
    status flip (amendment 124, brief 628). The approved commit must be the head or an ancestor of
    it, and the spec the one `docs/specs/<nnnn>-*.md` at the head, at the same path at the
    approved commit; anything unreadable is False (fail closed)."""
    code, full = git_out(root, "rev-parse", "--verify", "-q", f"{approved}^{{commit}}")
    if code != 0 or not SHA.fullmatch(full):
        return False
    if git_out(root, "merge-base", "--is-ancestor", full, sha)[0] != 0:
        return False
    code, names = git_out(root, "ls-tree", "--name-only", sha, "docs/specs/")
    pattern = re.compile(rf"docs/specs/{spec[5:]}-[^/]*\.md")
    found = [n for n in names.splitlines() if pattern.fullmatch(n)] if code == 0 else []
    if len(found) != 1:
        return False
    texts = [git_bytes(root, "cat-file", "blob", f"{rev}:{found[0]}") for rev in (full, sha)]
    if texts[0] is None or texts[1] is None:
        return False
    try:
        return status_flip_only(texts[0].decode("utf-8"), texts[1].decode("utf-8"))
    except UnicodeDecodeError:
        return False


def unapproved(
    pull: dict,
    comments: list[dict],
    sha: str,
    approvers: list[str],
    root: Path | None = None,
    number: int = 0,
) -> bool:
    """SPEC-0039 rule 5 (`spec approval`): an `Approval:` line whose spec has no approval by an
    account in `spec_approvers` for the head SHA, or for an earlier commit of its history whose
    spec text the head keeps apart from the status flip (amendment 124, brief 628)."""
    if APPROVE_LABEL in labels_of(pull):
        return True
    asked = set(APPROVAL.findall(str(pull.get("body") or "")))
    if not asked:
        return False
    approved = approval_shas(comments, [], approvers)
    for spec in sorted(asked):
        shas = approved.get(spec, [])
        if any(sha.startswith(s) for s in shas):
            continue
        if root is None or not shas or not head_present(root, number, sha):
            return True
        if not any(same_text(root, sha, spec, s) for s in shas):
            return True
    return False


def approved_still_draft(
    repo: str, files: list[dict], comments: list[dict], approvers: list[str], sha: str
) -> bool:
    """Brief #797 answer 4: whether the pull request adds or changes a spec a listed approver has
    approved and that still reads `Draft` on the head; the status is read only for such a spec."""
    approved = specs_named_approved(comments, approvers)
    for item in files:
        name = str(item.get("filename") or "")
        match = SPEC_FILE.fullmatch(name)
        if not match or item.get("status") not in ("added", "modified"):
            continue
        if f"SPEC-{match.group(1)}" not in approved:
            continue
        if adr_status(repo, sha, name, "a spec the pull request changes") == "Draft":
            return True
    return False


def depends_on(body: str) -> list[str]:
    """The numbers of BODY's `Depends-on: #n` lines, in order, once each: only a stripped line that
    is exactly that line, the reading of `check_pr_mode.py` rule 5 (brief #991); a mention inside a
    sentence or backticks is not a dependence."""
    found = [m.group(1) for ln in body.splitlines() if (m := DEPENDS.fullmatch(ln.strip()))]
    return list(dict.fromkeys(found))


def dependence_unmet(repo: str, pull: dict) -> bool:
    for number in depends_on(str(pull.get("body") or "")):
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
    repo: str,
    number: int,
    pull: dict,
    comments: list,
    approvers: list,
    accepts: list[str],
    root: Path | None = None,
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
    if unapproved(pull, comments, sha, approvers, root, number):
        raise Held("spec approval (rule 5)")
    if approved_still_draft(repo, files, comments, approvers, sha):
        raise Held(DRAFT_HOLD)
    if (klass := protected_class(files)) is not None:
        raise Held(f"protected class {klass} (rule 5)")
    if held_label(pull):
        raise Held("hold label (rule 5)")
    if pull.get("draft") is not False:
        raise Held("draft (rule 5)")
    if dependence_unmet(repo, pull):
        raise Held("depends-on (rule 5)")
    state = pull.get("mergeable_state")
    if not isinstance(state, str) or state in CONFLICT:
        raise Held("conflict (rule 5)")


# --- rule 6: the pinned merge -------------------------------------------------------------------


def write_once(args: list[str], env: dict[str, str] | None = None) -> tuple[int, str, str]:
    """One `gh` call that writes: never retried (SPEC-0039 rule 6)."""
    proc = gh_api(args, env)
    return proc.returncode, proc.stdout, proc.stderr


def merge_env() -> dict[str, str] | None:
    """The environment of the one merge call: with `AGK_MERGE_TOKEN` set (the merger job), `gh`
    authenticates with it for this call alone; else None, the caller's own login (brief #765)."""
    value = os.environ.get(MERGE_ENV)
    return {**os.environ, "GH_TOKEN": value} if value else None


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
    code, out, err = write_once(args, merge_env())
    if code != 0:
        found = HTTP.search(err)
        status = int(found.group(1)) if found else 0
        if status == 409:
            raise Refused("head moved (rule 6: GitHub refused the pinned sha)", EXIT_HELD)
        if status == 405 and RULESET in err.lower():  # the default branch's ruleset (brief #765)
            raise Held("merge refused by the ruleset (rule 6)")
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


# --- after the record line: the issues the body closes and the brief it builds (brief #959) -----

# GitHub's closing keywords (close, closes, closed, fix, fixes, fixed, resolve, resolves, resolved,
# any case, an optional colon) before `#n`; `Fixes-failure: #n` and `Brief: #n` are not among them.
CLOSING = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b:?\s+#(\d+)\b", re.IGNORECASE)
BRIEF_LINE = re.compile(r"Brief: #(\d+)")
FINISHES_LINE = re.compile(r"Finishes: #(\d+)")  # session rule 28: the last pull request of a brief
CLOSE_WAIT = 5.0  # seconds GitHub is given to close the issues a merged body closes
TIMELINE_PAGES = 10  # pages of the brief's timeline read at most
BRIEF_LABEL = "agk-brief"


def closed_by(text: str) -> list[int]:
    """The issues a pull request body closes, as GitHub reads its closing keywords, in order."""
    out: list[int] = []
    for found in CLOSING.finditer(text or ""):
        number = int(found.group(1))
        if number not in out:
            out.append(number)
    return out


def brief_of(text: str) -> int | None:
    for line in (text or "").splitlines():
        found = BRIEF_LINE.fullmatch(line.strip())
        if found:
            return int(found.group(1))
    return None


def finishes(text: str, brief: int) -> bool:
    """The body says it finishes BRIEF: a whole stripped line `Finishes: #<brief>` (brief #992),
    read as `brief_of` reads `Brief: #n`; a mention inside a sentence is not that line."""
    for line in (text or "").splitlines():
        found = FINISHES_LINE.fullmatch(line.strip())
        if found and int(found.group(1)) == brief:
            return True
    return False


def read_once(endpoint: str, kind: type) -> Any:
    """One GET, never retried: this step holds nothing, so a read GitHub refuses is skipped."""
    proc = gh_api(["--method", "GET", endpoint])
    if proc.returncode != 0:
        return None
    try:
        value = json.loads(proc.stdout)
    except ValueError:
        return None
    return value if isinstance(value, kind) else None


def merged_titles(repo: str, brief: int) -> list[str] | None:
    """The titles of the merged pull requests that name BRIEF, from its timeline; None when GitHub
    cannot answer."""
    titles: list[str] = []
    for page in range(1, TIMELINE_PAGES + 1):
        chunk = read_once(f"repos/{repo}/issues/{brief}/timeline?per_page={PAGE}&page={page}", list)
        if chunk is None:
            return None
        for event in chunk:
            source = event.get("source") if isinstance(event, dict) else None
            item = source.get("issue") if isinstance(source, dict) else None
            pull = item.get("pull_request") if isinstance(item, dict) else None
            if isinstance(pull, dict) and pull.get("merged_at"):
                titles.append(str(item.get("title") or ""))
        if len(chunk) < PAGE:
            return titles
    return titles


def brief_built(repo: str, brief: dict, title: str, text: str) -> bool:
    """Every build the brief names is named by a merged pull request's title, as `session.py
    plan` reads builds (this one's TITLE among them); a brief that names no builds is built only
    when the merged body TEXT says `Finishes: #<brief>` on a line of its own (brief #992)."""
    number = int(brief.get("number") or 0)
    builds = session_plan.builds_of(str(brief.get("body") or ""))
    if not builds:
        return finishes(text, number)
    titles = merged_titles(repo, number)
    if titles is None:
        return False
    pulls = [{"title": t} for t in [title, *titles]]
    return all(any(session_plan.names_build(p, number, n) for p in pulls) for n, _ in builds)


def open_issue(item: dict | None) -> bool:
    return isinstance(item, dict) and item.get("state") == "open" and "pull_request" not in item


def close_brief(repo: str, brief: int, number: int, merged: str, title: str, text: str) -> bool:
    """Close the brief the body TEXT builds when every build has merged (brief #959 answer 2), or,
    for a brief that names no builds, when TEXT finishes it (brief #992); whether it was closed.
    An open brief with a build unmerged, or not finished, gets nothing."""
    item = read_once(f"repos/{repo}/issues/{brief}", dict)
    if not open_issue(item):
        return False
    labels = {str(x.get("name")) for x in item.get("labels") or [] if isinstance(x, dict)}
    if BRIEF_LABEL not in labels or not brief_built(repo, item, title, text):
        return False
    endpoint = f"repos/{repo}/issues/{brief}"
    line = f"All builds merged; last #{number} {merged[:12]}"
    code, _, _ = write_once(["--method", "POST", f"{endpoint}/comments", "-f", f"body={line}"])
    if code != 0:
        return False
    args = ["--method", "PATCH", endpoint, "-f", "state=closed", "-f", "state_reason=completed"]
    return write_once(args)[0] == 0


def close_after_merge(repo: str, number: int, merged: str, text: str, title: str) -> None:
    """After the record line (brief #959): the brief of the body's `Brief: #N` is closed when every
    build has merged (a brief with no `Builds:` line only on the body's `Finishes: #N`, brief
    #992), and each issue the body closes that is still open after a short wait gets one note.
    The merge stands and nothing is held."""
    closes = closed_by(text)
    brief = brief_of(text)
    if not closes and brief is None:
        return
    if closes:
        time.sleep(CLOSE_WAIT)  # GitHub closes them itself, a moment after the merge
    if brief is not None and close_brief(repo, brief, number, merged, title, text):
        closes = [n for n in closes if n != brief]
    line = f"Not closed by merge {merged[:12]} of #{number}; close it if the work is done"
    for issue in closes:
        if open_issue(read_once(f"repos/{repo}/issues/{issue}", dict)):
            write_once(
                ["--method", "POST", f"repos/{repo}/issues/{issue}/comments", "-f", f"body={line}"]
            )


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


def tests_argv(tree: Path, home: Path, names: list[str], wait: float) -> list[str]:
    """The pre-merge test run of brief #667 as one argument list: the heavy lock as governance
    takes it, `env -i` with PATH, HOME and AGK_KIT_TESTS=1 only, and pytest on the files NAMES of
    TREE, rooted at TREE, so that no token reaches the merged code and nothing is cached."""
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
        "AGK_KIT_TESTS=1",
        "PYTHONDONTWRITEBYTECODE=1",
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-rfE",
        "-p",
        "no:cacheprovider",
        "--rootdir",
        str(tree),
        *(str(tree / name) for name in names),
    ]


def first_failure(out: str, names: list[str]) -> str:
    """The first `<file>::<test>` (or `<file>`) that pytest's short summary names as failed or
    in error, its file given as the listed name of NAMES that it ends with (pytest prints it
    relative to where it ran); `pytest` when it names none."""
    for line in out.splitlines():
        found = FAILED_LINE.match(line.strip())
        if found:
            file, sep, test = found.group(1).partition("::")
            file = file.replace("\\", "/")
            listed = [n for n in names if file == n or file.endswith(f"/{n}")]
            return f"{listed[0] if listed else file}{sep}{test}"
    return "pytest"


def run_tests(root: Path, tree: Path, home: Path, names: list[str], wait: float) -> str | None:
    """Run the pre-merge tests NAMES once in TREE (brief #667); output to standard error. None
    when they passed, else what failed: the first failing test, `heavy lock` when lock.py did not
    take the lock in WAIT seconds and pytest named no test, or `pytest`. An interrupt ends
    lock.py and is raised again."""
    child = subprocess.Popen(  # nosec B603 - fixed argument list, no shell
        tests_argv(tree, home, names, wait),
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
    failed = first_failure(out or "", names)
    if failed == "pytest" and child.returncode == LOCK_TIMEOUT:
        return "heavy lock"
    return failed


def pre_merge_setting(data: dict) -> dict | None:
    """The `[testing]` table of the default branch for the pre-merge tests (brief #667), its
    `pre_merge_tests` checked here so that a bad setting is refused before anything runs."""
    table = data.get("testing")
    if table is None:
        return None
    if not isinstance(table, dict):
        raise Refused("[testing] must be a table (setting: testing)")
    if impact.PRE_MERGE in table:
        try:
            impact.check_pre_merge_tests(table[impact.PRE_MERGE])
        except CheckError as err:
            raise Refused(str(err)) from None
    return table


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
    root: Path,
    commit: str,
    base: str,
    wait: float,
    text: str,
    prefix: str,
    repo: str = "",
    pre: dict | None | bool = False,
) -> str | None:
    """The governance run on COMMIT against BASE in a detached worktree of a new temporary folder
    outside the checkout (named with PREFIX), with TEXT in the body file of its temporary home and
    the Final comments of COMMIT's records (read from REPO, amendment 122) in its record-comments
    file; both are removed in every case. The one run of rule 6, after the merge and before it
    (brief #610). None when green, else the failing step. With PRE (the default branch's
    `[testing]` table, None without one; False after the merge), the pre-merge tests run after a
    green governance and a failure raises Held (brief #667)."""
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
        step = run_governance(root, tree, home, body, base, wait)
        if step is not None or pre is False:
            return step
        try:
            names = impact.pre_merge_names(pre if isinstance(pre, dict) else None, tree)
        except CheckError:
            raise Held(f"{TESTS_FAIL} (setting: testing.{impact.PRE_MERGE})") from None
        failed = run_tests(root, tree, home, names, wait) if names else None
        if failed is not None:
            raise Held(f"{TESTS_FAIL} ({failed})")
        return None
    finally:
        git_out(root, "worktree", "remove", "--force", str(tree))
        shutil.rmtree(scratch, ignore_errors=True)
        git_out(root, "worktree", "prune")


def fetched_base(root: Path, branch: str, number: int, sha: str) -> str | None:
    """Fetch the default branch and the pull request's head: the default branch's commit, or None
    when either cannot be read."""
    code, _ = git_out(root, "fetch", "-q", "origin", branch, f"refs/pull/{number}/head")
    base_code, base = git_out(root, "rev-parse", "--verify", "-q", f"{REMOTE}{branch}^{{commit}}")
    head_code, _ = git_out(root, "cat-file", "-e", f"{sha}^{{commit}}")
    if code != 0 or base_code != 0 or head_code != 0 or not SHA.fullmatch(base):
        return None
    return base


def would_be_merge(root: Path, branch: str, number: int, sha: str) -> tuple[str | None, str]:
    """Fetch the default branch and the pull request's head, and make their merge one commit on
    the fetched default branch, as the squash merge will be: (the commit, the default branch's
    commit), or (None, the failing step). A conflict holds, as rule 5 holds one (brief #610)."""
    base = fetched_base(root, branch, number, sha)
    if base is None:
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


def reprove_check(root: Path, base: str, sha: str, limit: int | None) -> None:
    """The holds of SPEC-0050 rule 8 (brief #727) on the fetched default branch BASE and the head
    SHA, read with local git, before the governance run of the check before the merge: hold when
    the head is in the re-prove state of rule 6, or, with LIMIT set, more first-parent commits
    behind BASE than LIMIT. A read that fails holds as unknown. Each hold names the rule or the
    setting only."""
    files = session_plan.reprove_files(root, base, sha)
    if files is None:
        raise Held(REPROVE_UNKNOWN)
    if files:
        raise Held(REPROVE)
    if limit is None:
        return
    count = session_plan.behind_merges(root, base, sha)
    if count is None:
        raise Held(REPROVE_UNKNOWN)
    if count > limit:
        raise Held(BEHIND)


def merge_check(
    root: Path,
    branch: str,
    number: int,
    sha: str,
    wait: float,
    text: str,
    repo: str = "",
    pre: dict | None = None,
    limit: int | None = None,
) -> str | None:
    """Governance on the would-be merge of SHA with the default branch, before the merge (brief
    #610, amendment 123): the run of rule 6 on it, then the pre-merge tests of PRE (the default
    branch's `[testing]` table, brief #667). Between the would-be merge and the run, the holds of
    SPEC-0050 rule 8 with LIMIT, `[flow] max_behind_merges` (brief #727). None when green, else
    the failing step; any exception, interrupt or termination is `governance not finished`,
    nothing having merged."""
    with after_merge_signals():
        try:
            commit, base = would_be_merge(root, branch, number, sha)
            if commit is None:
                return base
            reprove_check(root, base, sha, limit)
            return in_worktree(root, commit, base, wait, text, CHECK_PREFIX, repo, pre)
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
    title: str = "",
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
            with contextlib.suppress(Exception):  # the merge stands, nothing is held (#959)
                close_after_merge(repo, number, merged, text, title)
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


# --- the merger job of GitHub mode (brief #765, ADR-0354, amendment 139) ------------------------


class Nothing(Exception):
    """The merger job has nothing to try: the message is its one line on stderr."""


def github_mode(data: dict) -> None:
    """Nothing unless `auto_merge` is on (squash), `execution` is not `local` and `forge` is not
    `files`, all in agk.toml of the default branch: local mode keeps the conductor's run and
    personal mode never merges (SPEC-0039 rule 4, SPEC-0041 rule 9)."""
    try:
        state = auto_merge_setting(data)
    except CheckError as err:
        raise Nothing(str(err)) from None
    if state != "on":
        raise Nothing(f"auto-merge is off ({SETTING.format('auto_merge')})")
    if data.get("execution") == "local":
        raise Nothing("local mode: the conductor merges (setting: execution in agk.toml)")
    if data.get("forge") == "files":
        raise Nothing("personal mode merges nothing (setting: forge in agk.toml)")


def event_target(name: str, payload: dict) -> tuple[int, str | None] | None:
    """(the pull request, its head sha or None) that event NAME's PAYLOAD may clear, or None: a
    `Verdict:` or `Approve:` comment on a pull request, one edited to start `Verdict:`, `Final:`
    or `Approve:` (brief #836 answer 1), a green run of `governance` or `proof` on a pull request's
    head (the workflow's `workflow_run` start names which), or the router's `workflow_dispatch`
    with the input `pr` (brief #1116, ADR-0476). Nothing here reads GitHub."""
    if name == "issue_comment":
        issue = payload.get("issue")
        note = payload.get("comment")
        if not (isinstance(issue, dict) and isinstance(note, dict) and issue.get("pull_request")):
            return None
        starts = EDITED_STARTS if payload.get("action") == "edited" else CREATED_STARTS
        if not first_line(note).startswith(starts):
            return None
        number = issue.get("number")
        return (number, None) if isinstance(number, int) and number > 0 else None
    if name == "workflow_run":
        done = payload.get("workflow_run")
        if not isinstance(done, dict) or done.get("event") != "pull_request":
            return None
        if done.get("conclusion") != "success":
            return None
        pulls = done.get("pull_requests")
        sha = done.get("head_sha")
        if not (isinstance(pulls, list) and len(pulls) == 1 and isinstance(pulls[0], dict)):
            return None
        number = pulls[0].get("number")
        if not (isinstance(number, int) and number > 0 and isinstance(sha, str)):
            return None
        return (number, sha) if SHA.fullmatch(sha) else None
    if name == "workflow_dispatch":  # the router's start with the input `pr` (brief #1116)
        inputs = payload.get("inputs")
        value = inputs.get("pr") if isinstance(inputs, dict) else None
        if isinstance(value, str) and NUMBER.fullmatch(value):
            return int(value), None
        return None
    if name == "status":  # the number is read from GitHub by the caller (brief #853 answer 2)
        if payload.get("context") != STATUS_CONTEXT or payload.get("state") != "success":
            return None
        sha = payload.get("sha")
        return (0, sha) if isinstance(sha, str) and SHA.fullmatch(sha) else None
    return None


def pull_of_head(repo: str, sha: str, branch: str) -> int:
    """The one open pull request into BRANCH whose head is SHA; Nothing unless there is exactly
    one (brief #853 answer 2)."""
    pulls = read_json(f"repos/{repo}/commits/{sha}/pulls", list, "the pull requests of the head")
    found = [
        p["number"]
        for p in pulls
        if isinstance(p, dict)
        and p.get("state") == "open"
        and isinstance(p.get("number"), int)
        and (p.get("head") or {}).get("sha") == sha
        and (p.get("base") or {}).get("ref") == branch
    ]
    if len(found) != 1:
        raise Nothing(f"not one open pull request has this head (event status, {len(found)} found)")
    return found[0]


def event_main(path: str, name: str, root: Path) -> int:
    """`--event FILE --event-name NAME`: print `<n> <sha>` when the job should run the command of
    rule 2 on that pull request and head, else one line on stderr and nothing on stdout."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = None
    if not isinstance(payload, dict):
        print("merger: refused: the event payload cannot be read (input: --event)", file=sys.stderr)
        return 2
    try:
        target = event_target(name, payload)
        if target is None:
            raise Nothing(f"not a verdict, an approval or a green run of a head (event {name})")
        _, data = default_ref(root)
        github_mode(data)
        merge_queue_setting(data)  # a bad setting is refused; the command queues or merges (#972)
        repo = repo_of(root)
        number, sha = target
        if number == 0 and sha is not None:
            number = pull_of_head(repo, sha, str(data.get("default_branch", "main")))
        if sha is None:
            sha = current_head(repo, number)
        if not SHA.fullmatch(sha):
            raise Unreadable("the pull request")
        issues = read_pages(f"repos/{repo}/issues?state=open", "the open issues")
        if titled(issues, RECORD_TITLE):
            raise Nothing("local mode: the conductor merges (the local-mode record issue is open)")
        state, reason = judge(read_comments(repo, number), sha, [])
        if state != "cleared":
            raise Nothing(f"#{number} not cleared: {reason}")
    except Nothing as err:
        print(f"merger: nothing to do: {err}", file=sys.stderr)
        return EXIT_CLEARED
    except Refused as err:
        print(f"merger: nothing to do: {err}", file=sys.stderr)
        return EXIT_CLEARED
    except Unreadable as err:
        print(f"merger: nothing to do: GitHub cannot be read ({err})", file=sys.stderr)
        return EXIT_CLEARED
    print(f"{number} {sha}")
    return EXIT_CLEARED


def clock() -> datetime:
    return datetime.now(UTC)


def sweep_allows(data: dict) -> bool:
    """Brief #797 answers 3 and 6: True when a sweep may merge, False when it only reports (local
    mode); Nothing when this project has no sweep (auto-merge off, personal mode, paused)."""
    if data.get("paused") is True:
        raise Nothing("paused (setting: paused in agk.toml on the default branch)")
    if data.get("execution") == "local":
        github_mode({**data, "execution": ""})  # the other settings still decide
        return False
    github_mode(data)
    return True


def sweep_list(pulls: list[dict]) -> list[dict]:
    """The open, non-draft pull requests, oldest first; the label is never read (brief #836)."""
    kept = [p for p in pulls if p.get("state") == "open" and p.get("draft") is False]
    return sorted(kept, key=lambda p: (str(p.get("created_at") or ""), p.get("number") or 0))


def minutes_since(item: dict, now: datetime) -> int | None:
    """Whole minutes from ITEM's last edit (else its `created_at`) to NOW, or None when it cannot
    be read: a verdict corrected in place cleared the head when it was edited (brief #836)."""
    try:
        stamp = item.get("updated_at") or item.get("created_at")
        made = datetime.strptime(str(stamp), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return int((now - made.replace(tzinfo=UTC)).total_seconds() // 60)


def report_unmerged(number: int, verdict: dict | None, reason: str) -> None:
    """Brief #797 answer 5: one line for a cleared pull request left unmerged over 20 minutes."""
    minutes = minutes_since(verdict or {}, clock())
    if minutes is not None and minutes > UNMERGED_MINUTES:
        print(f"UNMERGED #{number} cleared {minutes} min {reason}")


def report_merged(number: int, verdict: dict | None) -> None:
    """Brief #836 `Measured:`: the minutes from the clearing verdict to this merge."""
    minutes = minutes_since(verdict or {}, clock())
    print(f"MERGED #{number} {'unknown' if minutes is None else minutes} min after cleared")


def reroute(root: Path, repo: str, number: int) -> None:
    """Brief #836 answer 2: the router's one pass over a pull request whose label is stale; a
    failure ends nothing, as every step of the job ends green."""
    import route  # route imports session; read only when a label is stale

    try:
        route.route_one(repo, number, root, route.Labels(repo), False)
    except CheckError:
        print(f"LABEL #{number} router not re-run")


def sweep_one(root: Path, repo: str, pull: dict, merging: bool, tried: int) -> tuple[int, bool]:
    """One pull request of a sweep and its line: (the guarded merges so far, whether to stop)."""
    number = int(pull.get("number") or 0)
    head = pull.get("head")
    sha = str(head.get("sha") if isinstance(head, dict) else "")
    prefix = f"merge-cleared #{number} {sha[:12]}:"
    try:
        comments = read_comments(repo, number)
        state, why = judge(comments, sha, [])
    except Unreadable as err:
        print(f"{prefix} not read: GitHub cannot be read ({err})")
        return tried, False
    if state != "cleared":
        print(f"{prefix} not cleared: {why}")
        return tried, False
    verdict = latest_verdict(comments)
    refresh_status(root, number, sha)
    stale = next((name for name in STALE_LABELS if name in labels_of(pull)), None)
    if stale:
        print(f"LABEL #{number} {stale} but cleared")
    if not merging:
        reason = "local mode: the conductor merges"
    elif tried >= SWEEP_MAX:
        reason = f"not tried: at most {SWEEP_MAX} a run"
    else:
        line, _ = guarded(root, number, sha)
        print(line)
        tried += 1
        if line.startswith(STOPPED):
            return tried, True
        if ": merged " in line:
            report_merged(number, verdict)
            return tried, False
        report_unmerged(number, verdict, line.split(": ", 1)[-1])
        if stale:
            reroute(root, repo, number)
        return tried, False
    print(f"{prefix} {reason}")
    report_unmerged(number, verdict, reason)
    if stale and merging:
        reroute(root, repo, number)
    return tried, False


def sweep_main(root: Path) -> int:
    """`--sweep` (brief #797 answers 3, 5 and 6, brief #836): one line per open pull request, oldest
    first, the guarded merge on at most five cleared heads; always exit 0, as every step does."""
    try:
        _, data = default_ref(root)
        merging = sweep_allows(data)
        repo = repo_of(root)
        issues = read_pages(f"repos/{repo}/issues?state=open", "the open issues")
        merging = merging and not titled(issues, RECORD_TITLE)
        endpoint = f"repos/{repo}/pulls?state=open&sort=created&direction=asc"
        pulls = sweep_list(read_pages(endpoint, "the open pull requests"))
    except (Nothing, Refused) as err:
        print(f"merger: nothing to do: {err}", file=sys.stderr)
        return EXIT_CLEARED
    except Unreadable as err:
        print(f"merger: nothing to do: GitHub cannot be read ({err})", file=sys.stderr)
        return EXIT_CLEARED
    tried = 0
    for pull in pulls:
        tried, stop = sweep_one(root, repo, pull, merging, tried)
        if stop:
            break
    return EXIT_CLEARED


def sweep_gate_main(root: Path) -> int:
    """`--sweep-gate`: `on` when this project gets the sweep job, else `off` (brief #797)."""
    try:
        _, data = default_ref(root)
        github_mode(data)
    except (Nothing, Refused):
        print("off")
        return EXIT_CLEARED
    print("on")
    return EXIT_CLEARED


def post_once(repo: str, number: int, body: str) -> None:
    """One comment BODY on the pull request, unless the same first line is there already."""
    if any(first_line(c) == body for c in read_comments(repo, number)):
        print("merger: already said")
        return
    endpoint = f"repos/{repo}/issues/{number}/comments"
    code, _, _ = write_once(["--method", "POST", endpoint, "-f", f"body={body}"])
    print("merger: commented" if code == 0 else "merger: the comment cannot be posted")


def queue_removed(payload: dict) -> tuple[int, str] | None:
    """Brief #972 answer 4: (the pull request, its one line) for a failed `governance` or `proof`
    run of the `merge_group` event on a queue branch, else None."""
    run = payload.get("workflow_run")
    if not isinstance(run, dict) or run.get("event") != "merge_group":
        return None
    if run.get("conclusion") != "failure" or run.get("name") not in ("governance", "proof"):
        return None
    found = QUEUE_BRANCH.fullmatch(str(run.get("head_branch") or ""))
    sha = str(run.get("head_sha") or "")
    if not found or not SHA.fullmatch(sha):
        return None
    return int(found.group(1)), QUEUE_REMOVED.format(check=run["name"], sha12=sha[:12])


def queue_removed_main(path: str, root: Path) -> int:
    """`--queue-removed --event FILE`: one removal line, never twice for one queue sha; exit 0."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = None
    target = queue_removed(payload) if isinstance(payload, dict) else None
    if target is None:
        print("merger: nothing to do: not a failed merge queue run", file=sys.stderr)
        return EXIT_CLEARED
    try:
        repo = repo_of(root)
        if not github_removed(repo, target[0]):
            print("merger: nothing posted: GitHub did not remove the pull request (rule 2c)")
            return EXIT_CLEARED
        post_once(repo, *target)
    except (Refused, Unreadable) as err:
        print(f"merger: nothing posted: {err}")
    return EXIT_CLEARED


def github_removed(repo: str, number: int) -> bool:
    """Verdict item 4 on #993: whether GitHub removed pull request NUMBER from the queue: it is
    open and not merged (REST), and not in the queue (one GraphQL read, only in the merger job
    with its own token). A failed batch requeues the members it did not remove (verify)."""
    if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get(MERGE_ENV):
        raise Refused(QUEUE_OUTSIDE)
    pull = read_json(f"repos/{repo}/pulls/{number}", dict, "the pull request")
    if pull.get("state") != "open" or pull.get("merged") is True or pull.get("merged_at"):
        return False
    found = queue_read(repo, number)
    if not isinstance(found.get("isInMergeQueue"), bool):
        raise Unreadable("the merge queue state of the pull request")
    return found["isInMergeQueue"] is False


def no_secret_main(number: int, root: Path) -> int:
    """`--report --pr N --no-secret`: the job has no merge secret, so one line and nothing else."""
    try:
        post_once(repo_of(root), number, NO_MERGE_LINE)
    except (Refused, Unreadable) as err:
        print(f"merger: nothing posted: {err}")
    return EXIT_CLEARED


def report_main(number: int, sha: str, line: str, root: Path) -> int:
    """`--report --pr N --sha SHA --line LINE`: after LINE, the command's own line for N and SHA,
    nothing on a merge (the merge's push starts the default branch's run, verify), else post one
    comment `merger: <line>` on the pull request unless the same comment is there already. Exit
    0, or 2 for a line that is not the command's own."""
    found = JOB_LINE.match(line)
    if not found or int(found.group(1)) != number or found.group(2) != sha[:12]:
        print("merger: refused: the line is not merge_cleared.py's own (input: --line)")
        return 2
    try:
        repo = repo_of(root)
        if found.group(3) == "merged":
            print("merger: the merge's own push starts governance")
            return EXIT_CLEARED
        if found.group(3) in ("queued", "already queued"):  # the queue's run is the gate (#972)
            print("merger: in the merge queue; nothing posted")
            return EXIT_CLEARED
        if line.endswith(f": held: {PENDING}"):  # the other required run ends and tries again
            print("merger: checks pending; nothing posted")
            return EXIT_CLEARED
        post_once(repo, number, JOB_PREFIX + line)
    except (Refused, Unreadable) as err:
        print(f"merger: nothing posted: {err}")
    return EXIT_CLEARED


# --- the verdict as a commit status (brief #853, ADR-0387) ----------------------------------------


def verdict_reason(comments: list[dict], sha: str, reason: str) -> str:
    """The `pending` reason of a head the latest verdict does not clear; REASON is `judge`'s."""
    verdict = latest_verdict(comments)
    if verdict is None:
        return "no verdict"
    line = first_line(verdict)
    if line == f"Verdict: fix list {sha}":
        return "fix list"
    if line == f"Verdict: rejected {sha}":
        return "rejected"
    if "not listed" in reason:
        return "the verdict's author is not listed"
    return "no verdict for this head"


def spec_waiting(
    root: Path, number: int, pull: dict, comments: list[dict], sha: str, approvers: list[str]
) -> str:
    """The first spec of an `Approval:` line that has no approval for the head; `the spec` for a
    pull request held by its `agk:approve` label alone."""
    asked = sorted(set(APPROVAL.findall(str(pull.get("body") or ""))))
    for spec in asked:
        alone = {**pull, "body": f"Approval: {spec}", "labels": []}
        if unapproved(alone, comments, sha, approvers, root, number):
            return spec
    return asked[0] if asked else "the spec"


def verdict_state(root: Path, repo: str, number: int, sha: str, rules: Rules) -> tuple[str, str]:
    """(`success`, "") or (`pending`, the reason) for the head SHA, by the reading of the merge
    (`judge`, `hold_list`, the re-prove state); a moved head is Refused, so nothing is set."""
    pull = read_json(f"repos/{repo}/pulls/{number}", dict, "the pull request")
    head = pull.get("head")
    if not isinstance(head, dict) or head.get("sha") != sha:
        raise Refused("head moved (rule 3: --sha is not the pull request's head)", EXIT_HELD)
    comments = read_comments(repo, number)
    state, reason = judge(comments, sha, rules.allowed)
    if state != "cleared":
        return "pending", verdict_reason(comments, sha, reason)
    accepts = accepted_adrs(latest_verdict(comments) or {}, sha) or []
    try:
        hold_list(repo, number, pull, comments, rules.approvers, accepts, root)
    except Held as err:
        text = str(err)
        if text.startswith(("release", "protected class")):
            return "pending", OWNER_MERGE
        if text.startswith("spec approval"):
            return "pending", "approve " + spec_waiting(
                root, number, pull, comments, sha, rules.approvers
            )
        return "pending", text
    if rules.queue:  # the queue tests it with the default branch (brief #853 answer 4)
        return "success", ""
    branch = str(rules.data.get("default_branch", "main"))
    base = fetched_base(root, branch, number, sha)
    files = None if base is None else session_plan.reprove_files(root, base, sha)
    if files is None:
        return "pending", "re-prove unknown"
    return ("pending", f"re-prove {files[0]}") if files else ("success", "")


def set_status(repo: str, sha: str, state: str, reason: str) -> bool:
    """Set the status unless its newest entry says the same; False when the write fails."""
    description = (reason or "cleared")[:STATUS_LIMIT]
    seen = read_pages(f"repos/{repo}/commits/{sha}/statuses", "the statuses of the head")
    newest = next((s for s in seen if s.get("context") == STATUS_CONTEXT), None)
    if newest and (newest.get("state"), newest.get("description")) == (state, description):
        return True
    fields = [f"state={state}", f"context={STATUS_CONTEXT}", f"description={description}"]
    args = ["--method", "POST", f"repos/{repo}/statuses/{sha}"]
    for field in fields:
        args += ["-f", field]
    return write_once(args)[0] == 0


def status_line(root: Path, number: int, sha: str) -> tuple[str, int]:
    """Compute and set the status of one head: (the one line, the exit code)."""
    prefix = f"merge-cleared #{number} {sha[:12]}:"
    try:
        rules = ruled(root)
        repo = repo_of(root)
        state, reason = verdict_state(root, repo, number, sha, rules)
        shown = f"{prefix} status {state}{' ' + reason if reason else ''}"
        issues = read_pages(f"repos/{repo}/issues?state=open", "the open issues")
        if local_mode(rules.data, issues) or rules.data.get("forge") == "files":
            return f"{shown} (local mode: not set)", EXIT_CLEARED
        if not set_status(repo, sha, state, reason):
            return f"{shown}: the status cannot be set", EXIT_REFUSED
    except Held as err:
        return f"{prefix} held: {err}", EXIT_HELD
    except Refused as err:
        return f"{prefix} refused: {err}", err.code
    except CheckError as err:
        return f"{prefix} refused: {err}", EXIT_REFUSED
    except Unreadable as err:
        return f"{prefix} refused: GitHub cannot be read ({err}, {READS} reads in a row)", (
            EXIT_UNREADABLE
        )
    return shown, EXIT_CLEARED


def refresh_status(root: Path, number: int, sha: str) -> None:
    """The sweep's refresh of a cleared head when main moves: one line, and a failure ends
    nothing (brief #853 answer 1)."""
    print(status_line(root, number, sha)[0])


def status_event_main(path: str, name: str, root: Path) -> int:
    """`--status --event FILE --event-name NAME`: the job's step, on a comment alone, so that no
    status write answers a status event; every outcome ends green."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = None
    if name != "issue_comment" or not isinstance(payload, dict):
        return EXIT_CLEARED
    target = event_target(name, payload)
    if target is None:
        return EXIT_CLEARED
    try:
        _, data = default_ref(root)
        github_mode(data)
        sha = current_head(repo_of(root), target[0])
    except (Nothing, Refused, Unreadable) as err:
        print(f"merger: no status: {err}", file=sys.stderr)
        return EXIT_CLEARED
    print(status_line(root, target[0], sha)[0])
    return EXIT_CLEARED


def job_args(argv: list[str]) -> tuple[str, list[str]] | None:
    """The merger job's modes: (`event`, [file, name]), (`report`, [n, sha, line]),
    (`no-secret`, [n]), (`sweep`, []), (`sweep-gate`, []), (`status`, [n, sha]) or
    (`status-event`, [file, name])."""
    if argv in (["--sweep"], ["--sweep-gate"]):
        return argv[0][2:], []
    if len(argv) == 5 and argv[:2] == ["--status", "--pr"] and argv[3] == "--sha":
        if NUMBER.fullmatch(argv[2]) and SHA.fullmatch(argv[4]):
            return "status", [argv[2], argv[4]]
    if len(argv) == 5 and argv[:2] == ["--status", "--event"] and argv[3] == "--event-name":
        return "status-event", [argv[2], argv[4]]
    if len(argv) == 3 and argv[:2] == ["--queue-removed", "--event"]:
        return "queue-removed", [argv[2]]
    if len(argv) == 4 and argv[0] == "--event" and argv[2] == "--event-name":
        return "event", [argv[1], argv[3]]
    if len(argv) == 4 and argv[:2] == ["--report", "--pr"] and argv[3] == "--no-secret":
        return ("no-secret", [argv[2]]) if NUMBER.fullmatch(argv[2]) else None
    if len(argv) == 7 and argv[0] == "--report" and argv[1] == "--pr" and argv[3] == "--sha":
        if argv[5] == "--line" and NUMBER.fullmatch(argv[2]) and SHA.fullmatch(argv[4]):
            return "report", [argv[2], argv[4], argv[6]]
    return None


def parse_args(argv: list[str]) -> tuple[int, str] | None:
    if len(argv) != 4 or argv[0] != "--pr" or argv[2] != "--sha":
        return None
    if not NUMBER.fullmatch(argv[1]) or not SHA.fullmatch(argv[3]):
        return None
    return int(argv[1]), argv[3]


def ruled(root: Path) -> Rules:
    """The settings of the default branch of the remote as last fetched, refused or held before
    any GitHub read (SPEC-0039 rules 1, 3 and 5): auto-merge on, not paused, the reviewers file,
    `conductor_accounts`, `spec_approvers`, `required_checks` and `after_merge_timeout`. The merge
    queue reads them the same way (brief #643, ADR-0329)."""
    base, data = default_ref(root)
    setting_on(data)
    if data.get("paused") is True:
        raise Held("paused (rule 5; setting: paused in agk.toml on the default branch)")
    people = reviewers_at(root, base)
    allowed = conductors_in(people)
    approvers = approvers_of(people)
    required = required_of(data)
    after_merge_seconds(data)  # a bad setting is refused before anything is merged
    pre = pre_merge_setting(data)  # likewise the pre-merge tests (brief #667)
    behind = max_behind_setting(data)  # and the behind limit (brief #727)
    queue = merge_queue_setting(data)  # and the merge queue (brief #853)
    return Rules(data, people, allowed, approvers, required, pre, behind, queue)


def local_mode(data: dict, issues: list[dict]) -> bool:
    """Local mode (SPEC-0039 rule 4): `execution = "local"` on the default branch, or the one open
    local-mode record issue (docs/guides/local-mode.md)."""
    return data.get("execution") == "local" or titled(issues, RECORD_TITLE)


def holds(
    root: Path, repo: str, number: int, sha: str, rules: Rules
) -> tuple[dict, dict, list[str], int, int | None]:
    """Every hold of SPEC-0039 rules 3, 4, 5 and 7 that reads GitHub and merges nothing, in the
    order of a run: (the pull request, its clearing verdict, the acceptance lines of rule 3a, the
    record issue, the red-branch issue the pull request fixes or None). A verdict that does not
    clear the head raises NotCleared; any other hold raises Held, a moved head Refused (exit 3).
    The merge queue judges each open pull request with it (brief #643, ADR-0329)."""
    pull = read_json(f"repos/{repo}/pulls/{number}", dict, "the pull request")
    head = pull.get("head")
    head_sha = head.get("sha") if isinstance(head, dict) else None
    if not isinstance(head_sha, str) or not SHA.fullmatch(head_sha):
        raise Unreadable("the pull request")
    if head_sha != sha:
        raise Refused("head moved (rule 3: --sha is not the pull request's head)", EXIT_HELD)
    comments = read_comments(repo, number)
    state, reason = judge(comments, sha, rules.allowed)
    if state != "cleared":
        raise NotCleared(reason)
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
    if local_mode(rules.data, issues):
        local_evidence(verdict, comments, sha, rules.approvers)
    else:
        ci_evidence(repo, sha, rules.required)
    accepts = accepted_adrs(verdict, sha) or []
    hold_list(repo, number, pull, comments, rules.approvers, accepts, root)
    return pull, verdict, accepted, record, fixing


def queue_mode(repo: str, rules: Rules) -> bool:
    """Brief #972: True when the head joins the merge queue instead of being merged: `[flow]
    merge_queue = true`, GitHub mode (`execution` not `local`, `forge` not `files`) and no open
    local-mode record issue (rule 4); one more read of the open issues, only with the setting on."""
    data = rules.data
    if not rules.queue or data.get("execution") == "local" or data.get("forge") == "files":
        return False
    issues = read_pages(f"repos/{repo}/issues?state=open", "the open issues")
    return not titled(issues, RECORD_TITLE)


def queue_call(fields: list[str]) -> tuple[int, dict | None, str]:
    """One GraphQL call of the merger job (brief #972, `Q-S0039-19`): (exit code, the answer's
    `data` or None, the error text); an answer that carries `errors` counts as a failure."""
    proc = gh_api(["graphql", *fields], merge_env())
    try:
        answer = json.loads(proc.stdout) if proc.returncode == 0 else None
    except ValueError:
        answer = None
    if isinstance(answer, dict) and answer.get("errors"):
        text = " ".join(str(e.get("message", "")) for e in answer["errors"] if isinstance(e, dict))
        return 1, None, text
    data = answer.get("data") if isinstance(answer, dict) else None
    return proc.returncode, data if isinstance(data, dict) else None, proc.stderr


def queue_read(repo: str, number: int) -> dict:
    """The one GraphQL read of the merger job: the pull request's id, head and queue state."""
    owner, _, name = repo.partition("/")
    fields = ["-f", f"query={QUEUE_READ}", "-f", f"owner={owner}", "-f", f"name={name}"]
    _, data, _ = queue_call([*fields, "-F", f"number={number}"])
    pull = ((data or {}).get("repository") or {}).get("pullRequest")
    if not isinstance(pull, dict):
        raise Unreadable("the merge queue state of the pull request")
    return pull


def queue_state(repo: str, number: int, sha: str) -> tuple[str, bool]:
    """The pull request's GraphQL id and whether it is in the merge queue; a head that is no longer
    SHA is refused as moved, an unreadable answer is Unreadable."""
    pull = queue_read(repo, number)
    if not isinstance(pull.get("id"), str):
        raise Unreadable("the merge queue state of the pull request")
    if pull.get("headRefOid") != sha:
        raise Refused(QUEUE_MOVED, EXIT_HELD)
    return pull["id"], pull.get("isInMergeQueue") is True


def enqueue(node: str, sha: str) -> None:
    """The one write of rule 2a: add the pull request NODE to the merge queue, pinned to SHA."""
    fields = ["-f", f"query={QUEUE_WRITE}", "-f", f"pullRequestId={node}"]
    code, data, err = queue_call([*fields, "-f", f"expectedHeadOid={sha}"])
    entry = ((data or {}).get("enqueuePullRequest") or {}).get("mergeQueueEntry")
    if code == 0 and isinstance(entry, dict):
        return
    words = err.lower()
    if "head" in words and ("oid" in words or "moved" in words or "sha" in words):
        raise Refused(QUEUE_MOVED, EXIT_HELD)
    raise Refused(QUEUE_FAILED)


def removed_since(comments: list[dict], verdict: dict) -> bool:
    """Verdict item 3 on #993 (amendment 158 item 4): a `Removed from the merge queue:` line
    newer than the clearing VERDICT holds the head, so a sweep never queues it again; a new head
    needs a new verdict anyway, and a new verdict on the head lifts the hold."""

    def order(item: dict) -> tuple[str, int]:
        cid = item.get("id")
        return str(item.get("created_at") or ""), cid if isinstance(cid, int) else -1

    removals = [c for c in comments if first_line(c).startswith(REMOVED_START)]
    return any(order(c) > order(verdict) for c in removals)


def outcome(root: Path, number: int, sha: str) -> tuple[str, str, int]:
    rules = ruled(root)
    data = rules.data
    repo = repo_of(root)
    with merge_lock(root):
        pull, verdict, accepted, record, fixing = holds(root, repo, number, sha, rules)
        queue = queue_mode(repo, rules)
        if queue and (os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get(MERGE_ENV)):
            raise Refused(QUEUE_OUTSIDE)  # before any GraphQL call: never a session's own login
        node = ""
        if queue and removed_since(read_comments(repo, number), verdict):
            raise Held(REMOVED_HOLD)
        if queue:
            node, queued = queue_state(repo, number, sha)
            if queued:
                return "already queued", "", EXIT_CLEARED
        text = str(pull.get("body") or "")  # the body read above, for governance (brief #576)
        branch = str(data.get("default_branch", "main"))
        wait = after_merge_seconds(data)
        step = merge_check(root, branch, number, sha, wait, text, repo, rules.pre, rules.behind)
        if step is not None:
            raise Held(f"{FAILS} ({step})")
        if queue:
            enqueue(node, sha)
            return "queued", "", EXIT_CLEARED
        merged = merge_pull(repo, number, sha, accepted)
        recorded, closed = after_merge(
            root,
            repo,
            number,
            merged,
            record,
            verdict,
            data,
            text,
            fixing,
            str(pull.get("title") or ""),
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


def guarded(root: Path, number: int, sha: str) -> tuple[str, int]:
    """The one guarded merge of pull request NUMBER at SHA: (its one line, its exit code)."""
    prefix = f"merge-cleared #{number} {sha[:12]}:"
    try:
        word, reason, code = outcome(root, number, sha)
    except Held as err:
        return f"{prefix} held: {err}", EXIT_HELD
    except Refused as err:
        return f"{prefix} refused: {err}", err.code
    except Unreadable as err:
        return f"{prefix} refused: GitHub cannot be read ({err}, {READS} reads in a row)", (
            EXIT_UNREADABLE
        )
    except Stopped as stop:
        missing = "" if stop.filed else " (the red-branch issue cannot be written)"
        return f"{STOPPED} default branch red after #{stop.number}{missing}", EXIT_REFUSED
    return (f"{prefix} {word}: {reason}" if reason else f"{prefix} {word}"), code


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    job = job_args(argv)
    if job is not None:  # the merger job of GitHub mode (brief #765)
        here = Path.cwd() if root is None else root
        if job[0] == "sweep":
            return sweep_main(here)
        if job[0] == "sweep-gate":
            return sweep_gate_main(here)
        if job[0] == "event":
            return event_main(job[1][0], job[1][1], here)
        if job[0] == "status":
            line, code = status_line(here, int(job[1][0]), job[1][1])
            print(line)
            return code
        if job[0] == "status-event":
            return status_event_main(job[1][0], job[1][1], here)
        if job[0] == "queue-removed":
            return queue_removed_main(job[1][0], here)
        if job[0] == "no-secret":
            return no_secret_main(int(job[1][0]), here)
        return report_main(int(job[1][0]), job[1][1], job[1][2], here)
    args = parse_args(argv)
    if args is None:
        print(f"merge-cleared #? ?: refused: {USAGE}")
        return EXIT_REFUSED
    line, code = guarded(Path.cwd() if root is None else root, *args)
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
