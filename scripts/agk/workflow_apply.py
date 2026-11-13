"""Apply a builder's proposed workflow file to its pull request's branch (brief #1189, ADR-0505).

    python3 scripts/agk/workflow_apply.py --pr N [--yes --head SHA] [--repo OWNER/REPO]
                                          [--remote NAME]

The owner's command `/agk:workflow-apply <pr>`, run on the owner's machine with the owner's own
`git` and `gh`. A session never changes `.github/workflows/`; a builder commits the whole proposed
file at `.agk/workflow-proposals/<name>.yml` on its branch and asks `for the maintainers`.

It reads the pull request (GET), refuses one that is not open, comes from a fork or whose head is
the default branch, fetches the head branch into a temporary worktree (removed when it ends), lists
each proposal with its target `.github/workflows/<name>.yml`, refuses a proposal that does not
parse or names no `jobs`, prints the diff against the branch's current workflow and stops: a dry
run, which changes nothing, and ends with the head it showed and the `--yes --head <sha>` command.
A proposal that is not a regular file, or a target path any part of which is a symbolic link, is
refused before anything is read through it or written.

`--yes` needs `--head <sha>`, the head the dry run printed, and refuses any other head, so a push
between the two runs is never applied unseen. With `--yes` it needs the newest
`Question: Q-... for the maintainers` comment that names the command (its Q id), moves each
proposal into place, deletes the proposals folder, commits `workflow: apply the proposal of #<n>
(<Q id>)`, checks the committed files byte for byte, pushes a fast-forward of the fetched head
to the head branch (never a force-push, never the default branch) and posts one comment
`Answer: <Q id> done: <commit> applied by /agk:workflow-apply`. What it cannot do it prints and
never does. Personal mode (a `[personal]` table) has no pull requests.

The parse check is a structural check of the YAML subset a workflow uses, standard library only
(ADR-0001 decision 4): block mappings and lists, quoted and flow scalars, block scalars, no tab in
an indent, balanced quotes and brackets, and a top-level `jobs:` with at least one job.

Exit 0 after a dry run or an applied proposal, 1 when it refused or could not finish, 2 for a usage
error.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

PROPOSALS = ".agk/workflow-proposals"
WORKFLOWS = ".github/workflows"
COMMAND = "/agk:workflow-apply"
PROPOSAL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.yml")
ORIGIN = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
QUESTION = re.compile(r"Question: (Q-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\b")
MAINTAINERS = "for the maintainers"
WORKFLOW_SCOPE = re.compile(r"workflow.{0,40}scope|scope.{0,40}workflow", re.IGNORECASE | re.S)
PAGE = 100


class Refused(Exception):
    """A step the command will not take; the message says what and why."""


# --- the YAML structure check --------------------------------------------------------------------

KEY = re.compile(
    r"""(?:"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^\s#'"\[\]{},&*!|>%@`-][^#]*?|-[^\s#]*?)"""
    r"""\s*:(?=\s|$)"""
)
BLOCK_HEADER = re.compile(r"[|>][0-9+-]*\s*(#.*)?$")
PROPERTY = re.compile(r"(?:[&!][^\s]*\s+)+")


def _scan(text: str, i: int, quote: str | None, depth: int) -> tuple[int, str | None, int]:
    """Scan TEXT from I in the given quote and flow state; the end index of the content (before a
    comment) and the state after it."""
    n = len(text)
    while i < n:
        ch = text[i]
        if quote == '"':
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                quote = None
        elif quote == "'":
            if ch == "'":
                if i + 1 < n and text[i + 1] == "'":
                    i += 2
                    continue
                quote = None
        elif depth > 0:
            if ch in "\"'":
                quote = ch
            elif ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
            elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
                return i, quote, depth
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return i, quote, depth
        i += 1
    return n, quote, depth


def _value_state(value: str) -> tuple[str | None, int, bool]:
    """The quote and flow state after one value, and whether it opens a block scalar."""
    value = value.strip()
    prop = PROPERTY.match(value + " ")
    if prop and not value.startswith(("[", "{")):
        value = (value + " ")[prop.end() :].strip()
    if not value:
        return None, 0, False
    if BLOCK_HEADER.match(value):
        return None, 0, True
    if value[0] in "\"'":
        _, quote, _ = _scan(value, 1, value[0], 0)
        return quote, 0, False
    if value[0] in "[{":
        _, quote, depth = _scan(value, 1, None, 1)
        return quote, depth, False
    return None, 0, False


def yaml_problem(text: str) -> str | None:
    """None when TEXT has the structure of a workflow file; else why not (`does not parse ...` or
    `names no jobs`)."""
    lines = text.splitlines()
    quote: str | None = None
    depth = 0
    block: int | None = None  # the indent a block scalar's content must exceed
    stack = [0]
    in_jobs = False  # inside the top-level `jobs:` mapping
    has_jobs = False
    for number, line in enumerate(lines, start=1):
        if quote is not None or depth > 0:  # the continuation of a quoted or flow value
            _, quote, depth = _scan(line, 0, quote, depth)
            if depth < 0:
                return f"does not parse (an unopened bracket, line {number})"
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" \t"))
        if block is not None:
            if not stripped or len(line) - len(line.lstrip(" ")) > block:
                continue
            block = None
        if not stripped or stripped.startswith("#"):
            continue
        if "\t" in line[:indent]:
            return f"does not parse (a tab in an indent, line {number})"
        if indent == 0 and (stripped in ("---", "...") or stripped.startswith("--- ")):
            continue
        if stripped.startswith("%"):
            continue
        popped = False
        while stack[-1] > indent:
            stack.pop()
            popped = True
        if popped and stack[-1] != indent:
            return f"does not parse (an indent that matches no level above it, line {number})"
        if stack[-1] < indent:
            stack.append(indent)
        content = stripped
        offset = indent
        while content == "-" or content.startswith("- "):
            rest = content[1:]
            gap = len(rest) - len(rest.lstrip(" "))
            offset += 1 + gap
            content = rest.lstrip(" ")
            if content:
                stack.append(offset)
        if not content:
            continue
        key = KEY.match(content)
        if key:
            value = content[key.end() :]
            if indent == 0:
                in_jobs = key.group(0)[:-1].strip().strip("\"'") == "jobs"
                tail = value.strip()
                if in_jobs and tail.startswith("{") and not re.match(r"\{\s*\}", tail):
                    has_jobs = True
            elif in_jobs and offset == indent:
                has_jobs = True
            q, d, opens = _value_state(value)
        else:
            if indent == 0:
                return f"does not parse (line {number} is not a key of the top-level mapping)"
            q, d, opens = _value_state(content)
        if opens:
            block = indent
        quote, depth = q, d
        if depth < 0:
            return f"does not parse (an unopened bracket, line {number})"
    if quote is not None:
        return "does not parse (a quote that is never closed)"
    if depth > 0:
        return "does not parse (a bracket that is never closed)"
    if not has_jobs:
        return "names no jobs (a top-level `jobs:` with at least one job)"
    return None


# --- git and gh -----------------------------------------------------------------------------------


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError:
        raise Refused("git is not installed") from None
    if check and proc.returncode != 0:
        said = proc.stderr.strip().splitlines()
        raise Refused(f"git {args[0]} failed" + (f": {said[-1]}" if said else ""))
    return proc


def git_bytes(cwd: Path, *args: str) -> bytes:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=cwd, capture_output=True
    )
    if proc.returncode != 0:
        raise Refused(f"git {args[0]} failed")
    return proc.stdout


def gh(endpoint: str, *extra: str, method: str = "GET") -> Any:
    """One `gh api` call with the owner's own `gh`; None when it failed."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["gh", "api", "--method", method, endpoint, *extra],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        raise Refused("gh is not installed: install the GitHub CLI, then `gh auth login`") from None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout) if proc.stdout.strip() else {}
    except ValueError:
        return None


def comments(repo: str, number: int) -> list[dict]:
    found: list[dict] = []
    page = 1
    while True:
        chunk = gh(f"repos/{repo}/issues/{number}/comments?per_page={PAGE}&page={page}")
        if not isinstance(chunk, list):
            raise Refused(f"the comments of pull request #{number} cannot be read")
        found += chunk
        if len(chunk) < PAGE:
            return found
        page += 1


def question_id(items: list[dict]) -> str | None:
    """The Q id of the newest `Question: ... for the maintainers` comment that names the command."""
    for item in reversed(items):
        body = str(item.get("body") or "")
        first = body.splitlines()[0] if body else ""
        match = QUESTION.match(first)
        if match and MAINTAINERS in first and COMMAND in body:
            return match.group(1)
    return None


def personal(root: Path) -> bool:
    path = root / "agk.toml"
    if not path.is_file():
        return False
    try:
        return isinstance(tomllib.loads(path.read_text(encoding="utf-8")).get("personal"), dict)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False


def repo_of(root: Path, remote: str) -> str:
    url = git(root, "remote", "get-url", remote, check=False).stdout.strip()
    match = ORIGIN.search(url)
    if not match:
        raise Refused(f"the remote {remote} is not a GitHub repository: pass --repo OWNER/REPO")
    return match.group(1)


# --- the command ---------------------------------------------------------------------------------


def read_pull(repo: str, number: int) -> tuple[str, str]:
    """(head branch, head sha) of an open pull request of REPO whose head may be pushed to."""
    pull = gh(f"repos/{repo}/pulls/{number}")
    if not isinstance(pull, dict) or not isinstance(pull.get("head"), dict):
        raise Refused(f"pull request #{number} cannot be read")
    if pull.get("state") != "open":
        raise Refused(f"pull request #{number} is not open")
    head, base = pull["head"], pull.get("base") or {}
    ref, sha = str(head.get("ref") or ""), str(head.get("sha") or "")
    if (head.get("repo") or {}).get("full_name") != repo:
        raise Refused(f"pull request #{number} comes from a fork: its branch is not pushed here")
    default = (base.get("repo") or {}).get("default_branch") or ""
    if not ref or not sha or not default:
        raise Refused(f"pull request #{number} names no head branch or default branch")
    if ref == default:
        raise Refused(f"the head of pull request #{number} is the default branch: never pushed to")
    return ref, sha


def link_in(tree: Path, rel: str) -> str | None:
    """The first part of REL under TREE that is a symbolic link, else None."""
    path = tree
    for part in Path(rel).parts:
        path = path / part
        if path.is_symlink():
            return path.relative_to(tree).as_posix()
    return None


def proposals(tree: Path) -> list[tuple[str, str, bytes]]:
    """(proposal path, target path, bytes) of each proposal; refuses a bad name, a file that is
    not a regular file, a target path through a symbolic link and a file that does not parse."""
    linked = link_in(tree, PROPOSALS)
    if linked:
        raise Refused(f"{linked}: a symbolic link, not a folder; nothing was changed")
    folder = tree / PROPOSALS
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.iterdir()):
        rel = path.relative_to(tree).as_posix()
        if path.is_symlink() or not path.is_file():
            raise Refused(f"{rel}: not a regular file (a link or a folder); nothing was changed")
        if not PROPOSAL_NAME.fullmatch(path.name):
            raise Refused(f"{rel}: not a {PROPOSALS}/<name>.yml file")
        target = f"{WORKFLOWS}/{path.name}"
        linked = link_in(tree, target)
        if linked:
            raise Refused(
                f"{target}: its path holds a symbolic link ({linked}); nothing was changed"
            )
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise Refused(f"{rel}: does not parse (not UTF-8)") from None
        problem = yaml_problem(text)
        if problem:
            raise Refused(f"{rel}: {problem}")
        found.append((rel, target, data))
    return found


def show_diff(tree: Path, target: str, data: bytes) -> None:
    current = tree / target
    old = current.read_text(encoding="utf-8").splitlines() if current.is_file() else []
    new = data.decode("utf-8").splitlines()
    source = f"a/{target}" if current.is_file() else "/dev/null"
    for line in difflib.unified_diff(old, new, source, f"b/{target}", lineterm=""):
        print(line)


def apply(tree: Path, found: list[tuple[str, str, bytes]], number: int, qid: str) -> str:
    """Move each proposal into place, remove the folder and commit; the new commit."""
    for _rel, target, data in found:
        if link_in(tree, target):
            raise Refused(f"{target}: its path holds a symbolic link; nothing was changed")
        path = tree / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        git(tree, "add", "--", target)
    git(tree, "rm", "-q", "-r", "--", PROPOSALS)
    git(tree, "commit", "-q", "-m", f"workflow: apply the proposal of #{number} ({qid})")
    for _rel, target, data in found:
        if git_bytes(tree, "cat-file", "blob", f"HEAD:{target}") != data:
            raise Refused(f"{target}: the commit does not match the proposal byte for byte")
    print(f"byte-for-byte: ok ({len(found)} file(s))")
    return git(tree, "rev-parse", "HEAD").stdout.strip()


def push(tree: Path, remote: str, ref: str) -> None:
    proc = git(tree, "push", "--quiet", remote, f"HEAD:refs/heads/{ref}", check=False)
    if proc.returncode == 0:
        return
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if WORKFLOW_SCOPE.search(proc.stderr):
        raise Refused(
            "the push was refused: your token lacks the workflow permission; run "
            "`gh auth refresh -s workflow`, then run this command again (nothing was posted)"
        )
    raise Refused("the push was refused by the remote (git's message is above; nothing was posted)")


def work(args: argparse.Namespace, root: Path) -> int:
    if personal(root):
        print(
            "refused: personal mode (setting: personal) has no pull requests; "
            f"{COMMAND} needs one, so nothing was done"
        )
        return 1
    repo = args.repo or repo_of(root, args.remote)
    ref, sha = read_pull(repo, args.pr)
    git(root, "fetch", "--quiet", args.remote, f"refs/heads/{ref}")
    fetched = git(root, "rev-parse", "FETCH_HEAD").stdout.strip()
    if fetched != sha:
        raise Refused(
            f"the branch of pull request #{args.pr} moved since it was read: run the command again"
        )
    if args.yes and fetched != args.head:
        raise Refused(
            f"the branch of pull request #{args.pr} moved since the dry run you read: run the "
            "dry run again and read its diff; nothing was changed"
        )
    temp = Path(tempfile.mkdtemp(prefix="agk-workflow-apply-"))
    tree = temp / "tree"
    try:
        git(root, "worktree", "add", "--quiet", "--detach", str(tree), fetched)
        found = proposals(tree)
        if not found:
            raise Refused(f"no proposal under {PROPOSALS}/ on {ref}")
        for rel, target, data in found:
            print(f"{rel} -> {target}")
            show_diff(tree, target, data)
        qid = question_id(comments(repo, args.pr))
        if qid is None:
            missing = (
                f"no `Question: Q-... {MAINTAINERS}` comment on #{args.pr} names {COMMAND}; "
                "the builder posts it first"
            )
            if not args.yes:
                print(f"note: {missing}")
            else:
                raise Refused(f"{missing}; nothing was changed")
        else:
            print(f"answers: {qid}")
        if not args.yes:
            print(f"head: {fetched}")
            print(
                f"dry run: nothing changed; to apply exactly this diff to {ref}, run again with "
                f"--yes --head {fetched}"
            )
            return 0
        commit = apply(tree, found, args.pr, qid or "")
        push(tree, args.remote, ref)
        print(f"pushed {commit} to {ref}")
        line = f"Answer: {qid} done: {commit} applied by {COMMAND}"
        endpoint = f"repos/{repo}/issues/{args.pr}/comments"
        posted = gh(endpoint, "--raw-field", f"body={line}", method="POST")
        if posted is None:
            print(f"the comment could not be posted; post it on #{args.pr} yourself:\n{line}")
            return 1
        print(f"posted on #{args.pr}: {line}")
        return 0
    finally:
        git(root, "worktree", "remove", "--force", str(tree), check=False)
        git(root, "worktree", "prune", check=False)
        shutil.rmtree(temp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a proposed workflow file (ADR-0505).")
    parser.add_argument("--pr", type=int, required=True, help="the pull request number")
    parser.add_argument("--yes", action="store_true", help="apply, commit, push and answer")
    parser.add_argument("--repo", help="OWNER/REPO (default: read from the remote)")
    parser.add_argument("--remote", default="origin", help="the remote to fetch and push")
    parser.add_argument(
        "--head", help="with --yes: the full head commit the dry run printed; any other is refused"
    )
    args = parser.parse_args(argv)
    if args.yes and not (args.head and re.fullmatch(r"[0-9a-f]{40}", args.head)):
        parser.error("--yes needs --head <the 40-character head commit the dry run printed>")
    top = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8"
    ) if shutil.which("git") else None
    if top is None or top.returncode != 0:
        print("refused: run it inside the repository's checkout (git is needed)")
        return 1
    try:
        return work(args, Path(top.stdout.strip()))
    except Refused as exc:
        print(f"refused: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
