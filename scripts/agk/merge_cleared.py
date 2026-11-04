"""merge_cleared.py: judge whether a pull request is cleared for the guarded merge (SPEC-0039).

Build (a) of SPEC-0039 rule 12 (brief #528, ADR-0263): rules 1 and 3. Usage, exactly:

    python3 scripts/agk/merge_cleared.py --pr <n> --sha <the 40-character head sha>

It reads `[flow] auto_merge` and `auto_merge_method` from agk.toml as committed on the default
branch of the remote, as last fetched (never the work tree, never a pull request's head), then the
pull request and its comments with `gh api` through the REST API, and prints one line:

    merge-cleared #<n> <sha12>: cleared (merge not yet built)     exit 0
    merge-cleared #<n> <sha12>: held: <reason>                    exit 3
    merge-cleared #<n> <sha12>: refused: <reason>                 exit 1 (3 for a moved head)

and exit 4 when GitHub cannot answer one read five times in a row. A reason names a rule, a
setting or a path class, never a value. Standard library only; every `gh` call is an argument list
with no shell and no jq filter, and the JSON is read here. In this build the command makes no merge
call, takes no lock and writes nothing: builds (b) to (e) add the rest of SPEC-0039.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, show  # noqa: E402
from reviewers import CONFIG, conductors_of, parse  # noqa: E402

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


class Refused(CheckError):
    """A refusal: the one line's reason and its exit code."""

    def __init__(self, reason: str, code: int = EXIT_REFUSED) -> None:
        super().__init__(reason)
        self.code = code


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


def conductors(root: Path, sha: str) -> list[str]:
    """`conductor_accounts` of config/reviewers.yaml at the default branch's commit SHA."""
    text = show(root, sha, CONFIG)
    if text is None:
        return []
    try:
        return conductors_of(parse(text))
    except CheckError as err:
        raise Refused(str(err)) from None


# --- reads --------------------------------------------------------------------------------------


def read_json(endpoint: str, kind: type, what: str) -> Any:
    """One `gh api` GET of a REST ENDPOINT, parsed here; an answer that fails, is not JSON or is
    not of KIND is tried again, and the fifth failure in a row raises Unreadable."""
    for attempt in range(READS):
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["gh", "api", "--method", "GET", endpoint],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
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


def read_comments(repo: str, number: int) -> list[dict]:
    found: list[dict] = []
    page = 1
    while True:
        endpoint = f"repos/{repo}/issues/{number}/comments?per_page={PAGE}&page={page}"
        chunk = read_json(endpoint, list, "the comments of the pull request")
        found += [c for c in chunk if isinstance(c, dict)]
        if len(chunk) < PAGE:
            return found
        page += 1


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
    allowed = conductors(root, base)
    repo = repo_of(root)
    pull = read_json(f"repos/{repo}/pulls/{number}", dict, "the pull request")
    head = pull.get("head")
    head_sha = head.get("sha") if isinstance(head, dict) else None
    if not isinstance(head_sha, str) or not SHA.fullmatch(head_sha):
        raise Unreadable("the pull request")
    if head_sha != sha:
        raise Refused("head moved (rule 3: --sha is not the pull request's head)", EXIT_HELD)
    state, reason = judge(read_comments(repo, number), sha, allowed)
    if state == "cleared":
        return "cleared (merge not yet built)", "", EXIT_CLEARED
    return "held", reason, EXIT_HELD


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args is None:
        print(f"merge-cleared #? ?: refused: {USAGE}")
        return EXIT_REFUSED
    number, sha = args
    prefix = f"merge-cleared #{number} {sha[:12]}:"
    try:
        word, reason, code = outcome(Path.cwd() if root is None else root, number, sha)
    except Refused as err:
        print(f"{prefix} refused: {err}")
        return err.code
    except Unreadable as err:
        print(f"{prefix} refused: GitHub cannot be read ({err}, {READS} reads in a row)")
        return EXIT_UNREADABLE
    print(f"{prefix} {word}: {reason}" if reason else f"{prefix} {word}")
    return code


if __name__ == "__main__":
    sys.exit(main())
