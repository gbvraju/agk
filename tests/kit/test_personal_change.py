"""SPEC-0041 build (i): a personal change runs start, review, confirm and finish (brief #1507).

Advances REQ-048 (AC5). Rule 17: `personal.py change start` records the files-forge pull of the
branch and, at `spec` and above, drafts the change's spec; `change review` builds the review context
against the sidecar's records and checks the reviewer's report, written as a comment marked as an
agent's (rule 8); `change confirm` is the person's verdict at a terminal naming the head; `change
finish` runs the gate and prints, never runs, the push. Rule 29: the plugin's `personal-reviewer`
agent reads only. Rule 4: nothing is written in the clone or under its `.git/`. Invented
repositories and sidecars in `tmp_path`, a stub gitleaks, no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import personal  # noqa: E402
import personal_state as ps  # noqa: E402

PERSON = "member-example-1"
AGENT = ROOT / ".claude" / "agents" / "personal-reviewer.md"
RUNNER = """import pathlib, runpy, sys
sys.path.insert(0, ".")
bad = 0
for path in sorted(pathlib.Path("tests").glob("test_*.py")):
    try:
        runpy.run_path(str(path))
    except AssertionError:
        bad += 1
sys.exit(1 if bad else 0)
"""
CLEARED = "Verdict: cleared\nContext truncated: no\n\nFindings: none\n"
SKIP = ("AGK_HOME", "AGK_BASE", "GITHUB_BASE_REF", "CI", "PATH", "CLAUDECODE")


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "--no-optional-locks", *args], cwd=root, capture_output=True, text=True,
        check=True,
    ).stdout.strip()  # fmt: skip


def commit(root: Path, subject: str) -> str:
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
        "commit", "-q", "--no-verify", "-m", subject)  # fmt: skip
    return git(root, "rev-parse", "HEAD")


def clone_of(tmp_path: Path) -> Path:
    """`main` (TOTAL = 2, one passing test) is the default branch of `origin`; `work` starts
    there with no commit of its own."""
    clone = tmp_path / "clone"
    (clone / "tests").mkdir(parents=True)
    git(clone, "init", "-q", "-b", "main")
    (clone / "run_tests.py").write_text(RUNNER, encoding="utf-8")
    (clone / "shop.py").write_text("TOTAL = 2\n", encoding="utf-8")
    (clone / "tests" / "test_old.py").write_text("import shop\nassert shop.TOTAL > 0\n", "utf-8")
    base = commit(clone, "base")
    git(clone, "update-ref", "refs/remotes/origin/main", base)
    git(clone, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    git(clone, "checkout", "-q", "-b", "work")
    return clone


def change_code(clone: Path, test: str = "assert shop.TOTAL == 3") -> str:
    (clone / "shop.py").write_text("TOTAL = 3\n", encoding="utf-8")
    (clone / "tests" / "test_total.py").write_text(f"import shop\n{test}\n", "utf-8")
    return commit(clone, "the total counts every item")


def sidecar_of(tmp_path: Path, level: str) -> Path:
    side = tmp_path / "side"
    ps.make_sidecar(side, PERSON)
    toml = side / "agk.toml"
    command = f"{shlex.quote(sys.executable)} run_tests.py"
    text = toml.read_text(encoding="utf-8").replace('level = "light"', f'level = "{level}"')
    toml.write_text(text + f"test_command = {json.dumps(command)}\n", encoding="utf-8")
    commit(side, "settings")
    return side


def scanner(tmp_path: Path) -> str:
    """A PATH with git and a stub gitleaks that finds nothing."""
    folder = tmp_path / "bin"
    folder.mkdir(exist_ok=True)
    found = shutil.which("git")
    assert found
    if not (folder / "git").exists():
        (folder / "git").symlink_to(found)
    stub = folder / "gitleaks"
    stub.write_text(f"#!{sys.executable}\nraise SystemExit(0)\n", encoding="utf-8")
    stub.chmod(0o755)
    return str(folder)


def change(clone: Path, side: Path, *args: str, agent: bool = False, path: str | None = None):
    env = {k: v for k, v in os.environ.items() if k not in SKIP}
    env["PATH"] = path or os.environ.get("PATH", "")
    if agent:
        env["CLAUDECODE"] = "1"
    cmd = [sys.executable, str(SCRIPTS / "personal.py"), "change", *args]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [*cmd, "--clone", str(clone), "--sidecar", str(side)], capture_output=True, text=True,
        env=env,
    )  # fmt: skip


def pulls(side: Path) -> dict[int, dict]:
    folder = side / "forge" / "pulls"
    return {int(p.stem): json.loads(p.read_text("utf-8")) for p in folder.glob("[0-9]*.json")}


def comments(side: Path, number: int) -> list[dict]:
    return json.loads((side / "forge" / f"comments-{number}.json").read_text(encoding="utf-8"))


def snapshot(clone: Path) -> dict[str, str]:
    """Every file of the clone, `.git/` included, by path and SHA-256."""
    return {
        p.relative_to(clone).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(clone.rglob("*"))
        if p.is_file()
    }


def untouched(clone: Path, before: dict[str, str]) -> None:
    assert git(clone, "status", "--porcelain") == ""
    assert snapshot(clone) == before


def clean(side: Path) -> bool:
    return git(side, "status", "--porcelain") == ""


def terminal(env: dict | None = None):
    return {"tty": lambda: True, "env": {"PATH": os.environ.get("PATH", ""), **(env or {})}}


# --- answer 1: start ---------------------------------------------------------------------------


def test_req_048_start_records_the_pull_of_the_branch_and_writes_nothing_in_the_clone(tmp_path):
    """REQ-048 AC5: rules 4, 6 and 17 (the pull record of a local branch, read from git)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "light")
    head = git(clone, "rev-parse", "HEAD")
    before = snapshot(clone)
    done = change(clone, side, "start", "cart-total", "--advances", "REQ-048")
    assert done.returncode == 0, done.stdout + done.stderr
    ((number, pull),) = pulls(side).items()
    assert pull["title"] == "change cart-total" and pull["state"] == "open"
    assert pull["head"] == {"sha": head, "ref": "work"} and pull["base"] == {"ref": "main"}
    assert "Advances: REQ-048" in pull["body"]
    assert f"pull {number}" in done.stdout
    assert not list((side / "docs" / "specs").glob("[0-9]*.md"))  # light: no spec is drafted
    assert clean(side)
    untouched(clone, before)


@pytest.mark.parametrize("level", ["spec", "review", "evidence"])
def test_req_048_start_at_spec_and_above_drafts_the_change_spec_for_the_person(tmp_path, level):
    """REQ-048 AC5: rule 17 (a short spec per change, Draft, for `personal.py confirm`)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, level)
    done = change(clone, side, "start", "cart-total", "--advances", "REQ-048")
    assert done.returncode == 0, done.stdout + done.stderr
    (spec,) = (side / "docs" / "specs").glob("[0-9]*.md")
    assert spec.name == "0001-cart-total.md"
    text = spec.read_text(encoding="utf-8")
    assert text.startswith("# SPEC-0001: ") and "- Status: Draft" in text
    assert "personal.py confirm SPEC-0001" in done.stdout
    assert "Spec: SPEC-0001" in pulls(side)[1]["body"]
    assert clean(side)


def test_req_048_the_drafted_spec_passes_the_terminal_confirmation(tmp_path):
    """REQ-048 AC5: rules 15 and 17 (the drafted spec is one the sidecar's reader accepts)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "spec")
    assert change(clone, side, "start", "cart-total", "--advances", "REQ-048").returncode == 0
    code, lines = personal.confirm(side, "SPEC-0001", ask=lambda _q: "yes", **terminal())
    assert code == 0, lines
    assert "- Status: Approved" in (side / "docs/specs/0001-cart-total.md").read_text("utf-8")


def test_req_048_start_on_the_default_branch_is_refused_naming_the_rule(tmp_path):
    """REQ-048 AC5: rule 6 (a pull record is the review record of a local branch)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "light")
    git(clone, "checkout", "-q", "main")
    before = snapshot(clone)
    done = change(clone, side, "start", "cart-total")
    assert done.returncode == 1 and "default branch" in done.stdout
    assert "SPEC-0041 rule 6" in done.stdout and not pulls(side)
    untouched(clone, before)
    git(clone, "checkout", "-q", "--detach", "work")
    done = change(clone, side, "start", "cart-total")
    assert done.returncode == 1 and "SPEC-0041 rule 6" in done.stdout and not pulls(side)


@pytest.mark.parametrize("name", ["Cart", "cart total", "-x", "a/b", ""])
def test_req_048_start_refuses_a_name_that_is_not_a_slug(tmp_path, name):
    """REQ-048 AC5: rule 17 (the change's name is the spec's file name)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "light")
    done = change(clone, side, "start", name)
    assert done.returncode != 0 and not pulls(side)


def test_req_048_two_changes_on_two_branches_take_two_numbers_of_one_sequence(tmp_path):
    """REQ-048 AC5: rule 6 (one number sequence; a branch holds one started change)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "light")
    assert change(clone, side, "start", "cart-total").returncode == 0
    again = change(clone, side, "start", "cart-total")
    assert (
        again.returncode == 1 and "already" in again.stdout and "SPEC-0041 rule 17" in again.stdout
    )
    git(clone, "checkout", "-q", "-b", "other", "main")
    assert change(clone, side, "start", "cart-empty").returncode == 0
    found = pulls(side)
    assert sorted(found) == [1, 2]
    assert [found[n]["head"]["ref"] for n in (1, 2)] == ["work", "other"]


# --- answer 2: review --------------------------------------------------------------------------


def test_req_048_review_with_no_change_started_is_refused(tmp_path):
    """REQ-048 AC5: rule 17 (the review belongs to a started change)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "review")
    change_code(clone)
    done = change(clone, side, "review")
    assert done.returncode == 1 and "no change is started" in done.stdout
    assert "SPEC-0041 rule 17" in done.stdout
    assert not (side / "records" / "reviews").exists()


def test_req_048_review_builds_the_context_from_the_clone_and_the_sidecar(tmp_path):
    """REQ-048 AC5: rules 4 and 17 (the diff from the clone, the records from the sidecar)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "review")
    assert change(clone, side, "start", "cart-total", "--advances", "REQ-048").returncode == 0
    head = change_code(clone)
    before = snapshot(clone)
    done = change(clone, side, "review")
    assert done.returncode == 0, done.stdout + done.stderr
    context = (side / "records" / "reviews" / f"{head}.context.md").read_text(encoding="utf-8")
    assert context.startswith("# Review context\n") and "Truncated: no" in context
    assert "### shop.py:H" in context and "+TOTAL = 3" in context
    assert "## Principles" in context and "Advances: REQ-048" in context
    assert "personal-reviewer" in done.stdout and "--report" in done.stdout
    assert clean(side)
    untouched(clone, before)


def test_req_048_a_report_that_holds_is_kept_and_written_as_an_agents_comment(tmp_path):
    """REQ-048 AC5: rules 8 and 17 (`check_review_report`; the comment carries the agent mark)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "review")
    assert change(clone, side, "start", "cart-total").returncode == 0
    head = change_code(clone)
    assert change(clone, side, "review").returncode == 0
    report = tmp_path / "report.md"
    report.write_text(CLEARED, encoding="utf-8")
    done = change(clone, side, "review", "--report", str(report))
    assert done.returncode == 0, done.stdout + done.stderr
    kept = side / "records" / "reviews" / f"{head}.report.md"
    assert kept.read_text(encoding="utf-8") == CLEARED
    (entry,) = comments(side, 1)
    assert entry["body"].strip() == CLEARED.strip()
    assert entry["performed_via_github_app"] == {"slug": "claude"}  # marked even at a terminal
    assert "advisory" in done.stdout and clean(side)


def test_req_048_a_report_that_does_not_hold_is_refused_and_kept_nowhere(tmp_path):
    """REQ-048 AC5: rule 17 (a report that fails `check_review_report` records nothing)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "review")
    assert change(clone, side, "start", "cart-total").returncode == 0
    head = change_code(clone)
    report = tmp_path / "report.md"
    report.write_text("Verdict: approved\n", encoding="utf-8")
    done = change(clone, side, "review", "--report", str(report))
    assert done.returncode == 1 and "no review context" in done.stdout  # context comes first
    assert change(clone, side, "review").returncode == 0
    done = change(clone, side, "review", "--report", str(report))
    assert done.returncode == 1 and "does not hold" in done.stdout
    assert not (side / "records" / "reviews" / f"{head}.report.md").exists()
    assert comments(side, 1) == [] and clean(side)


# --- answer 3: confirm -------------------------------------------------------------------------


def reviewed(tmp_path: Path, level: str = "review") -> tuple[Path, Path, str]:
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, level)
    assert change(clone, side, "start", "cart-total").returncode == 0
    head = change_code(clone)
    assert change(clone, side, "review").returncode == 0
    report = tmp_path / "report.md"
    report.write_text(CLEARED, encoding="utf-8")
    assert change(clone, side, "review", "--report", str(report)).returncode == 0
    return clone, side, head


def test_req_048_an_agent_trying_change_confirm_is_refused(tmp_path):
    """REQ-048 AC5: rule 8 (an agent cannot approve; the person confirms at a terminal)."""
    clone, side, _ = reviewed(tmp_path)
    done = change(clone, side, "confirm", agent=True)
    assert done.returncode == 1 and "CLAUDECODE" in done.stdout
    code, out = personal.change_confirm(clone, side, ask=lambda _q: "yes", tty=lambda: True,
                                        env={"CLAUDECODE": "1"})  # fmt: skip
    assert code == 1 and "CLAUDECODE" in "\n".join(out)
    code, out = personal.change_confirm(clone, side, ask=lambda _q: "yes", tty=lambda: False,
                                        env={})  # fmt: skip
    assert code == 1 and "terminal" in "\n".join(out)
    assert len(comments(side, 1)) == 1  # the report alone


def test_req_048_confirm_needs_the_review_report_of_the_head(tmp_path):
    """REQ-048 AC5: rule 17 (the verdict follows the review of the head it names)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "review")
    assert change(clone, side, "start", "cart-total").returncode == 0
    change_code(clone)
    asked = []
    code, out = personal.change_confirm(clone, side, ask=asked.append, **terminal())
    assert code == 1 and "no review report" in "\n".join(out) and not asked


def test_req_048_confirm_writes_the_verdict_naming_the_head_on_yes_only(tmp_path):
    """REQ-048 AC5: rules 8 and 17 (`Verdict: cleared <head>`, signed at a terminal, unmarked)."""
    clone, side, head = reviewed(tmp_path)
    code, out = personal.change_confirm(clone, side, ask=lambda _q: "no", **terminal())
    assert code == 1 and len(comments(side, 1)) == 1
    code, out = personal.change_confirm(clone, side, ask=lambda _q: "yes", **terminal())
    assert code == 0, out
    entry = comments(side, 1)[-1]
    lines = entry["body"].splitlines()
    assert lines[:3] == [f"Confirmed: {head}", f"Verdict: cleared {head}", "Shown:"]
    assert len(lines) == 7 and lines[-1].startswith(f"confirmed by {PERSON} at a terminal at ")
    assert entry["performed_via_github_app"] is None and entry["user"]["login"] == PERSON
    assert clean(side)


# --- answer 4: finish, and the whole change ------------------------------------------------------


def test_req_048_finish_with_no_change_started_is_refused(tmp_path):
    """REQ-048 AC5: rule 17 (finish belongs to a started change)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "light")
    change_code(clone)
    done = change(clone, side, "finish", "--approve", path=scanner(tmp_path))
    assert done.returncode == 1 and "no change is started" in done.stdout


def test_req_048_finish_with_a_failing_gate_prints_no_push_command(tmp_path):
    """REQ-048 AC5: rules 18 and 20 (the floor fails; no `git push` is printed)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "light")
    assert change(clone, side, "start", "cart-total").returncode == 0
    (clone / "tests" / "test_old.py").write_text("import shop\nassert shop.TOTAL == 9\n", "utf-8")
    commit(clone, "break the old test")
    done = change(clone, side, "finish", "--approve", path=scanner(tmp_path))
    assert done.returncode == 1 and "gate: failed" in done.stdout
    assert "git push" not in done.stdout and "pr-summary" not in done.stdout


def test_req_048_finish_without_approve_runs_nothing(tmp_path):
    """REQ-048 AC5: rule 19 (the gate runs the test command only with the person's yes)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "light")
    assert change(clone, side, "start", "cart-total").returncode == 0
    change_code(clone)
    done = change(clone, side, "finish", path=scanner(tmp_path))
    assert done.returncode == 1 and "nothing ran" in done.stdout and "git push" not in done.stdout
    assert not (side / "records" / "gates").exists()


def test_req_048_an_invented_change_goes_start_review_confirm_finish_in_the_sidecar(tmp_path):
    """REQ-048 AC5: rules 4, 15, 17 and 20 (the brief's Measured line, at the `review` level)."""
    clone, side = clone_of(tmp_path), sidecar_of(tmp_path, "review")
    path = scanner(tmp_path)
    before = snapshot(clone)
    assert change(clone, side, "start", "cart-total", "--advances", "REQ-048").returncode == 0
    code, lines = personal.confirm(side, "SPEC-0001", ask=lambda _q: "yes", **terminal())
    assert code == 0, lines
    untouched(clone, before)
    head = change_code(clone)
    before = snapshot(clone)
    assert change(clone, side, "review").returncode == 0
    report = tmp_path / "report.md"
    report.write_text(CLEARED, encoding="utf-8")
    assert change(clone, side, "review", "--report", str(report)).returncode == 0
    code, out = personal.change_confirm(clone, side, ask=lambda _q: "yes", **terminal())
    assert code == 0, out
    done = change(clone, side, "finish", "--approve", path=path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "gate: passed" in done.stdout and "git push origin work" in done.stdout
    assert "pr-summary" in done.stdout
    assert (side / "records" / "gates" / f"{head}.json").is_file()
    assert clean(side)
    untouched(clone, before)


# --- answer 5: the plugin's personal reviewer --------------------------------------------------


def front(text: str) -> dict[str, str]:
    head = text.split("\n---", 1)[0].removeprefix("---\n")
    return dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)


def test_req_048_the_personal_reviewer_reads_only_and_never_confirms():
    """REQ-048 AC5: rule 29 (the plugin's reviewer for personal mode: read tools, the sidecar)."""
    text = AGENT.read_text(encoding="utf-8")
    meta = front(text)
    assert meta["name"] == "personal-reviewer"
    assert [t.strip() for t in meta["tools"].split(",")] == ["Read", "Grep", "Glob"]
    body = " ".join(text.split())
    for said in ("sidecar", "never write", "never confirm", "product clone", "advisory",
                 "check_review_report.py", "personal.py change review --report"):  # fmt: skip
        assert said in body, said
    reviewer = (ROOT / ".claude" / "agents" / "reviewer.md").read_text(encoding="utf-8")
    assert front(reviewer)["name"] == "reviewer"  # the team-mode reviewer is unchanged


def test_req_048_the_plugin_ships_the_personal_reviewer():
    """REQ-048 AC5: rule 29 (listed in the manifest and in the plugin's agents)."""
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert ".claude/agents/personal-reviewer.md" in manifest["verbatim"]
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "./.claude/agents/personal-reviewer.md" in plugin["agents"]
    assert "./.claude/agents/reviewer.md" not in plugin["agents"]


@pytest.mark.parametrize("missing", ["review_context", "check_review_report"])
def test_req_048_a_default_install_without_the_experimental_review_files_fails_by_name(
    tmp_path, monkeypatch, missing
):
    """REQ-048 AC5: rule 17 (an absent experimental review file is named, ADR-0649)."""
    clone, side, _ = reviewed(tmp_path)
    monkeypatch.setitem(sys.modules, missing, None)
    path = f"scripts/agk/{missing}.py"
    if missing == "review_context":
        with pytest.raises(personal.CheckError, match=path):
            personal.change_review(clone, side, None, None)
        return
    report = tmp_path / "report.md"
    with pytest.raises(personal.CheckError, match=path):
        personal.change_review(clone, side, None, str(report))
    code, out = personal.change_confirm(clone, side, ask=lambda _q: "yes", **terminal())
    assert code == 1 and path in "\n".join(out)
