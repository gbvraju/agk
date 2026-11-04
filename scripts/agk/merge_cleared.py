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
with no shell and no jq filter, and the JSON is read here.

Build (c) (brief #551, ADR-0273) adds the rest of rule 6 and rule 7. Before the merge the command
needs one record issue (the open local-mode record issue, else the one open issue labelled
`agk-auto-merge`), else `held: no record issue (rule 7)`. After the merge, still under the lock, it
posts one comment `Auto merge: #<n> <merge sha> <UTC time> <verdict link>` there, then fetches the
default branch, adds a detached worktree of the merge commit in a temporary folder outside the
checkout and runs `lock.py run --name heavy --session merge-cleared -- env -i PATH=<PATH>
HOME=<scratch> make -C <worktree> governance AGK_BASE=<parent of the merge commit>`, and removes
the worktree in every case. A red run (or a fetch or worktree that fails) opens or updates the
red-branch issue through `route.write_red`, prints

    merge-cleared: stopped: default branch red after #<n>         exit 1

and that open issue holds every later run. It never reverts, writes no file and pushes nothing.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
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
from common import DEFAULT_CONFIG, CheckError, show  # noqa: E402
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
LOCAL_EVIDENCE = re.compile(r"Local evidence: ([0-9a-f]{12,40})(?![0-9A-Za-z])")
EVIDENCE = re.compile(r"Evidence check: (agrees|differs), head ([0-9a-f]{12})(?![0-9A-Za-z])")
ACCEPT = "Maintainer answer: accept {}"  # the one accepted first line (SPEC-0039 rule 4)
APPROVAL = re.compile(r"Approval: (SPEC-\d{4})(?![0-9])")
DEPENDS = re.compile(r"Depends-on: #(\d+)")
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
    if first_line(verdict) != f"Verdict: cleared {sha}":
        return "held", "the latest verdict does not clear this head (rule 3)"
    if allowed and login(verdict) not in allowed:
        return "held", (
            "the verdict's author is not listed "
            "(rule 3; setting: conductor_accounts in config/reviewers.yaml)"
        )
    return "cleared", ""


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
    from route import latest_runs  # route imports session; read only when CI mode needs it

    runs = read_pages(f"repos/{repo}/commits/{sha}/check-runs", "the check runs", "check_runs")
    latest = {str(r.get("name") or ""): r for r in latest_runs(runs)}
    found = [latest.get(name) for name in required]
    done = [r for r in found if r is not None and r.get("status") == "completed"]
    if any(r.get("conclusion") != "success" for r in done):
        raise Held("a required check is red (rule 4)")
    if any(r is None for r in found):
        raise Held("a required check is missing (rule 4)")
    if len(done) != len(found):
        raise Held("checks pending (rule 4)")


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


def hold_list(repo: str, number: int, pull: dict, comments: list, approvers: list) -> None:
    """The holds of SPEC-0039 rule 5 after the red branch and paused, in the rule's order."""
    files = read_pages(f"repos/{repo}/pulls/{number}/files", "the files of the pull request")
    count = pull.get("changed_files")
    if not isinstance(count, int) or isinstance(count, bool) or count != len(files):
        raise Held("files not all read (rule 5)")  # GitHub lists at most 3,000 files (rule 2)
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


def merge_pull(repo: str, number: int, sha: str) -> str:
    """The one merge call, pinned to SHA with the squash method; the merge commit's sha."""
    args = ["--method", "PUT", f"repos/{repo}/pulls/{number}/merge"]
    args += ["-f", f"sha={sha}", "-f", f"merge_method={METHOD}"]
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


def governance_argv(tree: Path, home: Path, base: str) -> list[str]:
    """The governance run of SPEC-0039 rule 6 as one argument list: the project's own lock.py,
    the heavy lock, and `env -i` so that only PATH and HOME reach the merged code."""
    lock_py = Path(__file__).resolve().parent / "lock.py"
    return [
        sys.executable,
        str(lock_py),
        "run",
        "--name",
        HEAVY,
        "--session",
        LOCK,
        "--",
        "env",
        "-i",
        f"PATH={os.environ.get('PATH', '')}",
        f"HOME={home}",
        "make",
        "-C",
        str(tree),
        "governance",
        f"AGK_BASE={base}",
    ]


def run_governance(root: Path, tree: Path, home: Path, base: str) -> bool:
    """Run governance once in TREE; its output goes to standard error. Whether it passed."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        governance_argv(tree, home, base),
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    sys.stderr.write(proc.stdout + proc.stderr)
    return proc.returncode == 0


def governance(root: Path, branch: str, merged: str) -> str | None:
    """Fetch the default branch, run governance on the merge commit in a temporary worktree
    outside the checkout, and remove the worktree in every case. None when green, else the
    failing step (`fetch`, `worktree` or `make governance`)."""
    code, _ = git_out(root, "fetch", "-q", "origin", branch)
    if code != 0:
        return "fetch"
    code, _ = git_out(root, "merge-base", "--is-ancestor", merged, f"{REMOTE}{branch}")
    parent_code, parent = git_out(root, "rev-parse", "--verify", "-q", f"{merged}^1")
    if code != 0 or parent_code != 0 or not SHA.fullmatch(parent):
        return "fetch"
    scratch = Path(tempfile.mkdtemp(prefix="agk-merge-cleared-"))
    tree, home = scratch / "tree", scratch / "home"
    try:
        home.mkdir()
        code, _ = git_out(root, "worktree", "add", "--detach", "-q", str(tree), merged)
        if code != 0:
            return "worktree"
        return None if run_governance(root, tree, home, parent) else "make governance"
    finally:
        git_out(root, "worktree", "remove", "--force", str(tree))
        shutil.rmtree(scratch, ignore_errors=True)
        git_out(root, "worktree", "prune")


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
    except (Unreadable, route.ReadOnly, CheckError):
        return False
    return True


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
        issues = read_pages(f"repos/{repo}/issues?state=open", "the open issues")
        if titled(issues, RED_TITLE, exact=True):
            raise Held("the default branch is red (rule 5)")
        record = record_issue(issues)
        if record is None:
            raise Held("no record issue (rule 7)")
        if data.get("execution") == "local" or titled(issues, RECORD_TITLE):
            local_evidence(verdict, comments, sha, approvers)
        else:
            ci_evidence(repo, sha, required)
        hold_list(repo, number, pull, comments, approvers)
        merged = merge_pull(repo, number, sha)
        recorded = post_record(repo, record, number, merged, verdict)
        step = governance(root, str(data.get("default_branch", "main")), merged)
        if step is not None:
            raise Stopped(number, file_red(repo, step, merged))
    if not recorded:
        return f"merged {merged[:12]}", "the record line cannot be posted (rule 7)", EXIT_REFUSED
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
