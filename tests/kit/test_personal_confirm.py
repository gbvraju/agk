"""SPEC-0041 build (g), part 1: the person confirms each record at a terminal (brief #1502).

Advances REQ-048 (AC2 and AC4).

Rule 15: `personal.py confirm <id>` is refused in an agent session, without a terminal and on a
dirty sidecar; on yes it writes the pull record and the confirmation of rule 8 and makes one
commit, the child of `<C>`, only when the kind's reader passes. Rule 8: the sidecar's readers
accept only that confirmation (`reviewers.terminal_confirmations`), never an agent's, and a
team-mode repository reads exactly as before. Invented repositories and sidecars only; no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import personal  # noqa: E402
import personal_state as ps  # noqa: E402
import reviewers  # noqa: E402

PERSON = "member-example-1"
OTHER = "member-example-2"
AT = "2026-11-18T04:00:00Z"
TERMINAL = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}
REQ_101 = """
### REQ-101 — A customer can empty the cart

- Acceptance: AC1 the cart empties
- Source: observed in code at src/cart.py:10-20
- Status: planned
"""
SPEC = """# SPEC-0001: A customer can empty the cart

- Status: Draft
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-101

Observed in code at src/cart.py:10-20.

## Contexts

- personal: the sidecar holds this spec
- kit, github, local, stacks: not applicable: an invented fixture
"""
ADR = """# ADR-0001: The cart empties in one step

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: SPEC-0001
- Requirements: REQ-101
- Kind: recorded

## Context

Invented.

## Decision

Invented.

## Consequences

Invented.

## Residual

None.
"""
SPEC_PATH = "docs/specs/0001-empty-cart.md"
ADR_PATH = "docs/adr/0001-empty-cart.md"
SHOWN = (
    "SPEC-0001: A customer can empty the cart",
    f"{SPEC_PATH} at abc",
    "status: Draft -> Approved",
)


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def commit(root: Path, subject: str) -> str:
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
        "commit", "-q", "--no-verify", "-m", subject)  # fmt: skip
    return git(root, "rev-parse", "HEAD")


def holding(path: Path, toml_extra: str = "") -> Path:
    """A sidecar with one observed requirement, one Draft spec and one Proposed ADR, committed."""
    ps.make_sidecar(path, PERSON)
    req = path / "docs" / "requirements.md"
    req.write_text(req.read_text(encoding="utf-8") + REQ_101, encoding="utf-8")
    (path / SPEC_PATH).write_text(SPEC, encoding="utf-8")
    (path / ADR_PATH).write_text(ADR, encoding="utf-8")
    (path / "test-map.toml").write_text('"REQ-101 AC1" = ["tests/test_cart.py::t"]\n', "utf-8")
    if toml_extra:
        toml = path / "agk.toml"
        toml.write_text(toml.read_text(encoding="utf-8") + toml_extra, encoding="utf-8")
    commit(path, "records")
    return path


def team_repo(path: Path) -> Path:
    """The same records in a team-mode repository: no `[personal]` table."""
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    (path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    (path / "docs" / "specs").mkdir(parents=True)
    (path / "docs" / "adr").mkdir(parents=True)
    (path / "docs" / "requirements.md").write_text("# Requirements\n" + REQ_101, "utf-8")
    (path / SPEC_PATH).write_text(SPEC, encoding="utf-8")
    (path / ADR_PATH).write_text(ADR, encoding="utf-8")
    (path / "tests").mkdir()
    (path / "tests" / "test_cart.py").write_text(
        "def test_t():  # REQ-101 AC1\n    pass\n", "utf-8"
    )
    commit(path, "records")
    return path


def run_check(root: Path, name: str, *args: str) -> subprocess.CompletedProcess:
    drop = ("GITHUB_BASE_REF", "AGK_BASE", "CI", "CLAUDECODE")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / f"{name}.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k not in drop},
    )


def confirm(root: Path, rid: str, answer="yes", env=None, tty=True):
    asked = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return answer(root) if callable(answer) else answer

    code, lines = personal.confirm(
        root, rid, ask=ask, tty=lambda: tty, env=TERMINAL if env is None else env
    )
    return code, "\n".join(lines), asked


def set_status(root: Path, rel: str, old: str, new: str) -> None:
    """Replace the last OLD of the file (REQ-101 is the last entry of the requirements)."""
    path = root / rel
    text = path.read_text(encoding="utf-8")
    at = text.rindex(old)
    path.write_text(text[:at] + new + text[at + len(old) :], encoding="utf-8")


def terminal(sha: str, rid: str, line: str, login=PERSON, last=None, verdict="cleared") -> dict:
    body = "\n".join(
        [
            f"Confirmed: {sha}",
            f"Verdict: {verdict} {sha}",
            f"Record: {rid}",
            line,
            "Shown:",
            *SHOWN,
            last or f"confirmed by {login} at a terminal at {AT}",
        ]  # fmt: skip
    )
    return {"id": 1, "body": body, "user": {"login": login}, "created_at": AT,
            "performed_via_github_app": None}  # fmt: skip


def comments_file(root: Path, items: list[dict]) -> str:
    path = root / "cache" / "comments.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    return str(path)


def snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# --- rule 15: the refusals ----------------------------------------------------------------------


def test_req_048_confirm_in_an_agent_session_is_refused(tmp_path):
    """REQ-048 AC4: rule 15 and rule 8 (`CLAUDECODE` set: refused, nothing written)."""
    root = holding(tmp_path / "s")
    head = git(root, "rev-parse", "HEAD")
    code, out, asked = confirm(root, "SPEC-0001", env={**TERMINAL, "CLAUDECODE": "1"})
    assert code == 1 and "setting: CLAUDECODE" in out and not asked
    assert git(root, "rev-parse", "HEAD") == head and git(root, "status", "--porcelain") == ""


def test_req_048_confirm_without_a_terminal_is_refused(tmp_path):
    """REQ-048 AC4: rule 15 (standard input not a terminal: the command line refuses)."""
    root = holding(tmp_path / "s")
    head = git(root, "rev-parse", "HEAD")
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "personal.py"), "confirm", "SPEC-0001", "--sidecar",
         str(root)],
        cwd=root, input="yes\n", capture_output=True, text=True, env=TERMINAL,
    )  # fmt: skip
    assert done.returncode == 1 and "terminal" in done.stdout and "SPEC-0041 rule 15" in done.stdout
    code, out, asked = confirm(root, "SPEC-0001", tty=False)
    assert code == 1 and "terminal" in out and not asked
    assert git(root, "rev-parse", "HEAD") == head


def test_req_048_confirm_on_a_dirty_sidecar_is_refused(tmp_path):
    """REQ-048 AC4: rule 8 (`<C>` is the head of a clean work tree, else refused)."""
    root = holding(tmp_path / "s")
    (root / "records" / "note.txt").write_text("x", encoding="utf-8")
    code, out, asked = confirm(root, "SPEC-0001")
    assert code == 1 and "SPEC-0041 rule 8" in out and "clean" in out and not asked


@pytest.mark.parametrize("rid", ["SPEC-0009", "ADR-0009", "REQ-109", "spec-1"])
def test_req_048_an_unknown_record_is_refused(tmp_path, rid):
    """REQ-048 AC4: rule 15 (only a record of the sidecar can be confirmed)."""
    root = holding(tmp_path / "s")
    code, out, asked = confirm(root, rid)
    assert code == 1 and out.startswith("refused:") and not asked


def test_req_048_answering_no_writes_nothing(tmp_path):
    """REQ-048 AC4: rule 15 (the three lines are shown; no writes nothing)."""
    root = holding(tmp_path / "s")
    head, before = git(root, "rev-parse", "HEAD"), snapshot(root)
    code, out, asked = confirm(root, "SPEC-0001", answer="no")
    assert code == 1 and len(asked) == 1
    shown = out.splitlines()
    assert shown[:3] == [
        "SPEC-0001: A customer can empty the cart",
        f"{SPEC_PATH} at {head}",
        "status: Draft -> Approved",
    ]
    assert git(root, "rev-parse", "HEAD") == head and git(root, "status", "--porcelain") == ""
    assert {k: v for k, v in snapshot(root).items() if not k.startswith(".git/")} == {
        k: v for k, v in before.items() if not k.startswith(".git/")
    }


# --- rule 15: yes ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rid", "rel", "moved", "line"),
    [
        ("SPEC-0001", SPEC_PATH, "- Status: Approved", "Approve: SPEC-0001"),
        ("ADR-0001", ADR_PATH, "- Status: Accepted", "Accept: ADR-0001"),
        ("REQ-101", "docs/requirements.md", "- Status: planned", "Confirm: REQ-101"),
    ],
)
def test_req_048_yes_writes_the_records_and_one_commit_child_of_c(tmp_path, rid, rel, moved, line):
    """REQ-048 AC4: rules 8 and 15 (the pull record, the confirmation, one commit)."""
    root = holding(tmp_path / "s")
    c = git(root, "rev-parse", "HEAD")
    code, out, asked = confirm(root, rid)
    assert code == 0, out
    assert len(asked) == 1 and git(root, "status", "--porcelain") == ""
    assert (
        git(root, "rev-parse", "HEAD^") == c
        and git(root, "rev-list", "--count", f"{c}..HEAD") == "1"
    )
    changed = set(git(root, "diff", "--name-only", c, "HEAD").splitlines())
    number = json.loads(git(root, "show", f"HEAD:forge/pulls/{max(_pulls(root))}.json"))["number"]
    forge = {f"forge/pulls/{number}.json", f"forge/comments-{number}.json"}
    assert changed == (forge if rid.startswith("REQ") else forge | {rel})
    assert moved in (root / rel).read_text(encoding="utf-8")
    pull = json.loads((root / f"forge/pulls/{number}.json").read_text(encoding="utf-8"))
    assert pull["head"]["sha"] == c and pull["title"] == f"confirm {rid}"
    assert "typed at a terminal with no agent session's mark" in pull["body"]
    [entry] = json.loads((root / f"forge/comments-{number}.json").read_text(encoding="utf-8"))
    lines = entry["body"].splitlines()
    assert lines[:4] == [f"Confirmed: {c}", f"Verdict: cleared {c}", f"Record: {rid}", line]
    assert lines[4] == "Shown:" and lines[5:8] == out.splitlines()[:3] and len(lines) == 9
    assert lines[8].startswith(f"confirmed by {PERSON} at a terminal at 20")
    assert entry["user"]["login"] == PERSON and entry["performed_via_github_app"] is None
    derived = reviewers.terminal_confirmations([entry], ["claude"], PERSON)
    assert [d["body"] for d in derived[1:]] == [line.replace(": ", f": {c} ", 1)]


def _pulls(root: Path) -> list[int]:
    return [int(p.stem) for p in (root / "forge" / "pulls").glob("*.json")]


def test_req_048_a_reader_failure_restores_c_and_commits_nothing(tmp_path):
    """REQ-048 AC4: rule 15 (the record edited before the yes: exit 1, at `<C>`)."""
    root = holding(tmp_path / "s")
    c = git(root, "rev-parse", "HEAD")

    def edit(where: Path) -> str:
        set_status(where, SPEC_PATH, "Observed in code", "Edited after the summary; observed")
        return "yes"

    code, out, _ = confirm(root, "SPEC-0001", answer=edit)
    assert code == 1 and "check_specs" in out
    assert git(root, "rev-parse", "HEAD") == c and git(root, "status", "--porcelain") == ""
    assert not list((root / "forge").glob("comments-*.json"))


def test_req_048_sign_is_off_by_default_and_signs_when_set(tmp_path):
    """REQ-048 AC4: rule 15 (`[personal] sign = true` signs the commit with the person's key)."""
    assert "-S" not in personal.commit_options(holding(tmp_path / "a"))
    signed = personal.commit_options(holding(tmp_path / "b", "sign = true\n"))
    assert "-S" in signed and "commit.gpgsign=false" not in signed


def test_req_048_confirm_writes_nothing_in_the_product_clone(tmp_path):
    """REQ-048 AC4: rule 4 (the clone and its `.git/` are unchanged by a confirmation)."""
    root = holding(tmp_path / "s")
    clone = team_repo(tmp_path / "clone")
    before = snapshot(clone)
    code, out, _ = confirm(root, "ADR-0001")
    assert code == 0, out
    assert snapshot(clone) == before


# --- rule 8: the reader ---------------------------------------------------------------------------

C = "c" * 40


@pytest.mark.parametrize(
    ("rid", "line", "derived"),
    [
        ("SPEC-0001", "Approve: SPEC-0001", f"Approve: {C} SPEC-0001"),
        ("ADR-0001", "Accept: ADR-0001", f"Accept: {C} ADR-0001"),
        ("REQ-101", "Confirm: REQ-101", f"Confirm: {C} REQ-101"),
    ],
)
def test_req_048_terminal_confirmations_give_one_line_of_each_kind(rid, line, derived):
    """REQ-048 AC2: rule 8 (`terminal_confirmations` adds the one derived line, same author)."""
    item = terminal(C, rid, line)
    found = reviewers.terminal_confirmations([item], ["claude"], PERSON)
    assert found[0] is item and [x["body"] for x in found[1:]] == [derived]
    assert found[1]["user"] == item["user"] and found[1]["created_at"] == AT
    assert reviewers.confirmed_comments([item], ["claude"], PERSON) == [item]


@pytest.mark.parametrize(
    "item",
    [
        terminal(
            C, "SPEC-0001", "Approve: SPEC-0001", last=f"confirmed by {PERSON} in a session at {AT}"
        ),
        terminal(C, "SPEC-0001", "Approve: SPEC-0002"),
        terminal(C, "SPEC-0001", "Accept: SPEC-0001"),
        terminal(C, "ADR-0001", "Approve: ADR-0001"),
        terminal(C, "SPEC-0001", "Approve: SPEC-0001", login=OTHER),
        {
            **terminal(C, "SPEC-0001", "Approve: SPEC-0001"),
            "performed_via_github_app": {"slug": "claude"},
        },
        terminal(C, "SPEC-0001", "Approve: SPEC-0001", verdict="fix list"),
        terminal(
            C, "SPEC-0001", "Approve: SPEC-0001", last=f"confirmed by {OTHER} at a terminal at {AT}"
        ),
        {**terminal(C, "SPEC-0001", "Approve: SPEC-0001"), "user": {"login": OTHER}},
    ],
    ids=[
        "session",
        "other-id",
        "wrong-word",
        "adr-approve",
        "other-login",
        "agent",
        "fix-list",
        "signed-other",
        "author-other",
    ],  # fmt: skip
)
def test_req_048_any_other_comment_gives_nothing(item):
    """REQ-048 AC2: rule 8 (another shape, person, id pair, agent mark or verdict gives nothing)."""
    assert reviewers.terminal_confirmations([item], ["claude"], PERSON) == [item]
    assert reviewers.terminal_confirmations([item], ["claude"], None) == [item]


def test_req_048_a_session_confirmation_is_not_read_as_a_terminal_one():
    """REQ-048 AC2: rule 8 (the two readers never read each other's confirmation)."""
    session = terminal(
        C, "SPEC-0001", "Approve: SPEC-0001", last=f"confirmed by {PERSON} in a session at {AT}"
    )
    assert reviewers.terminal_confirmations([session], ["claude"], PERSON) == [session]


# --- rule 8: the three sidecar readings ---------------------------------------------------


def flipped(root: Path, kind: str) -> tuple[str, str]:
    """Commit `<C>`, then move the record in the work tree as `confirm` does; the base is `<C>`."""
    c = git(root, "rev-parse", "HEAD")
    if kind == "spec":
        set_status(root, SPEC_PATH, "- Status: Draft", "- Status: Approved")
    elif kind == "adr":
        set_status(root, ADR_PATH, "- Status: Proposed", "- Status: Accepted")
    else:
        set_status(root, "docs/requirements.md", "- Status: planned", "- Status: done")
    return c, c


@pytest.mark.parametrize(
    ("kind", "check", "rid", "line"),
    [
        ("spec", "check_specs", "SPEC-0001", "Approve: SPEC-0001"),
        ("adr", "check_adrs", "ADR-0001", "Accept: ADR-0001"),
        ("req", "check_requirements", "REQ-101", "Confirm: REQ-101"),
    ],
)
def test_req_048_each_sidecar_reading_needs_the_terminal_confirmation(
    tmp_path, kind, check, rid, line
):
    """REQ-048 AC2: rule 8 (passes with it; fails without it, with an agent's or a plain line)."""
    root = holding(tmp_path / "s")
    c, base = flipped(root, kind)
    good = comments_file(root, [terminal(c, rid, line)])
    done = run_check(root, check, "--base", base, "--comments", good)
    assert done.returncode == 0, done.stdout + done.stderr
    agent = {**terminal(c, rid, line), "performed_via_github_app": {"slug": "claude"}}
    plain = {**terminal(c, rid, line), "body": line.replace(": ", f": {c} ", 1)}
    for items in ([], [agent], [plain]):
        done = run_check(root, check, "--base", base, "--comments", comments_file(root, items))
        assert done.returncode == 1 and rid in done.stdout, (items, done.stdout)


@pytest.mark.parametrize(
    ("kind", "check", "rid", "line", "rel"),
    [
        ("spec", "check_specs", "SPEC-0001", "Approve: SPEC-0001", SPEC_PATH),
        ("adr", "check_adrs", "ADR-0001", "Accept: ADR-0001", ADR_PATH),
        ("req", "check_requirements", "REQ-101", "Confirm: REQ-101", "docs/requirements.md"),
    ],
)
def test_req_048_a_record_changed_after_c_fails(tmp_path, kind, check, rid, line, rel):
    """REQ-048 AC2: rule 8 (the record equals its text at `<C>` apart from its status line)."""
    root = holding(tmp_path / "s")
    c, base = flipped(root, kind)
    path = root / rel
    text = path.read_text(encoding="utf-8")
    edited = text.replace("src/cart.py:10-20", "src/cart.py:11-20").replace("Invented.", "Edited.")
    assert edited != text
    path.write_text(edited, "utf-8")
    done = run_check(
        root, check, "--base", base, "--comments", comments_file(root, [terminal(c, rid, line)])
    )
    assert done.returncode == 1 and rid in done.stdout, done.stdout


@pytest.mark.parametrize("check", ["check_adrs", "check_requirements"])
def test_req_048_a_team_mode_repository_takes_neither_new_reading(tmp_path, check):
    """REQ-048 AC2: rule 8 (the same records in team mode read exactly as before)."""
    root = team_repo(tmp_path / "t")
    base = git(root, "rev-parse", "HEAD")
    set_status(root, ADR_PATH, "- Status: Proposed", "- Status: Accepted")
    set_status(root, "docs/requirements.md", "- Status: planned", "- Status: done")
    empty = root / "comments.json"
    empty.write_text("[]", encoding="utf-8")
    with_comments = run_check(root, check, "--base", base, "--comments", str(empty))
    without = run_check(root, check, "--base", base)
    assert with_comments.returncode == without.returncode == 0, with_comments.stdout
    assert with_comments.stdout == without.stdout


def test_req_048_without_comments_a_sidecar_reads_as_before(tmp_path):
    """REQ-048 AC2: rule 8 (a local run has no comments: the confirmation is not checked)."""
    root = holding(tmp_path / "s")
    _, base = flipped(root, "adr")
    assert run_check(root, "check_adrs", "--base", base).returncode == 0
