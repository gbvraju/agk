"""Day zero: the steward talks the idea through before a repository exists (brief #1584).

REQ-072 (SPEC-0065 rule 8, amendment 196): in a folder that is not a clone, and whose person has no
repository, `day_zero.py commands` prints the seven commands that create one, one at a time, in a
POSIX and a PowerShell form; the steward never runs them. REQ-069 AC1 (SPEC-0066 rule 4, amendment
197): the person's day-zero answers are kept only on their yes, only in their own Claude folder,
and after the install `write` turns them into `docs/sources/day-zero.md`, which the plan check
accepts, and removes the kept file. A folder that is a git repository with `origin` gets no offer.
Invented data only (`example-bookings`); a local git fixture; no network, no model.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import check_plan
import day_zero
import front_door
import pytest
import steward

NAME = "example-bookings"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=cwd, check=True, capture_output=True
    )


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    claude = tmp_path / "home" / ".claude"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    return claude


@pytest.fixture
def empty(tmp_path) -> Path:
    folder = tmp_path / "idea"
    folder.mkdir()
    return folder


def answer(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "answer.txt"
    path.write_text(text, encoding="utf-8")
    return path


def all_files(path: Path) -> list[Path]:
    return sorted(p for p in path.rglob("*") if p.is_file()) if path.exists() else []


# --- answer 2: keep, only on a yes, only in the person's Claude folder ---------------------------


def test_keep_writes_nothing_before_a_yes(tmp_path, home, empty, capsys):
    """REQ-069 AC1: without the person's yes nothing is kept, anywhere."""
    words = answer(tmp_path, "People who book a table at a small restaurant.")
    code = day_zero.main(
        ["keep", "--folder", str(empty), "--id", "users", "--answer-file", str(words)]
    )
    assert code == 2
    assert "--yes" in capsys.readouterr().err
    assert all_files(home) == [] and all_files(empty) == []


def test_keep_writes_only_to_the_claude_folder_named_by_the_folder_hash(tmp_path, home, empty):
    """REQ-069 AC1: kept only in the person's Claude folder, named by rule 8's folder hash."""
    words = answer(tmp_path, "People who book a table.\nThe restaurant pays.")
    args = ["keep", "--folder", str(empty), "--yes", "--answer-file", str(words)]
    assert day_zero.main([*args, "--id", "users", "--who", "ProductOwner"]) == 0
    assert day_zero.main([*args, "--id", "scale"]) == 0
    assert all_files(empty) == []
    kept = all_files(home)
    assert kept == [home / day_zero.KEPT / f"{steward.folder_key(empty)}.json"]
    rows = json.loads(kept[0].read_text(encoding="utf-8"))["answers"]
    assert [r["id"] for r in rows] == ["users", "scale"]
    assert rows[0]["answer"] == "People who book a table.\nThe restaurant pays."
    assert rows[0]["who"] == "ProductOwner" and rows[0]["at"].endswith("Z")


def test_the_folder_key_is_the_greeting_marks_hash(tmp_path, home, empty):
    """Rule 8: one hash of the folder's path, the same the greeting mark holds."""
    assert steward.first_run(empty, "2026-11-21") == "greet"
    mark = (home / steward.GREETED).read_text(encoding="utf-8").split()[0]
    assert mark == steward.folder_key(empty)


# --- answer 3: the offer and the commands ---------------------------------------------------------


def test_a_folder_that_is_a_repository_with_origin_gets_no_offer(tmp_path, home, empty, capsys):
    assert day_zero.main(["offer", "--folder", str(empty)]) == 0
    assert capsys.readouterr().out.strip() == "offer: github"
    git("init", "-q", "-b", "main", cwd=empty)
    assert day_zero.main(["offer", "--folder", str(empty)]) == 0
    assert capsys.readouterr().out.strip() == "offer: github"  # a repository with no origin yet
    git("remote", "add", "origin", "https://example.com/example-bookings.git", cwd=empty)
    assert day_zero.main(["offer", "--folder", str(empty / ".")]) == 0
    assert capsys.readouterr().out.strip() == "offer: none"


def test_personal_mode_gets_no_offer(tmp_path, home, empty, capsys):
    git("init", "-q", "-b", "main", cwd=empty)
    (empty / "agk.toml").write_text('[personal]\nforge = "files"\n', encoding="utf-8")
    assert day_zero.main(["offer", "--folder", str(empty)]) == 0
    assert capsys.readouterr().out.strip() == "offer: none"


POSIX = [
    "gh auth status",
    "git init -b main",
    f"printf '# {NAME}\\n' > README.md",
    f"git add README.md && git commit -m 'Start {NAME}'",
    f"gh repo create {NAME} --private --source . --remote origin --push",
    "git remote set-head origin --auto",
    "gh repo edit --enable-issues",
]
POWERSHELL = [
    *POSIX[:2],
    f"Set-Content -Encoding utf8 -Path README.md -Value '# {NAME}'",
    f"git add README.md; git commit -m 'Start {NAME}'",
    *POSIX[4:],
]


@pytest.mark.parametrize(("shell", "want"), [("posix", POSIX), ("powershell", POWERSHELL)])
def test_commands_prints_the_seven_steps_one_at_a_time_in_order(shell, want, capsys):
    """REQ-072: one command per call, each shown only after the one before it exited 0."""
    for step, command in enumerate(want, start=1):
        args = ["commands", "--name", NAME, "--shell", shell, "--step", str(step)]
        assert day_zero.main(args) == 0
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == f"step {step}/7: {command}"
        assert len(lines) == 2 and "exit" in lines[1]
    assert day_zero.main(["commands", "--name", NAME, "--shell", shell, "--step", "8"]) == 0
    assert capsys.readouterr().out.startswith("done:")


def test_the_repository_is_private_unless_the_person_chooses_public():
    """Q-1584-3: `--private` by default; `--public` only on the person's own choice."""
    assert "--private" in day_zero.steps(NAME, "posix")[4]
    assert "--public " in day_zero.steps(NAME, "posix", public=True)[4]


def test_powershell_never_redirects_with_echo():
    """Windows: `echo >` writes UTF-16 in Windows PowerShell; the README is written as UTF-8."""
    assert not any(">" in line for line in day_zero.steps(NAME, "powershell"))


@pytest.mark.parametrize("bad", ["", "two words", "../x", "a;b", "-flag", "x" * 101])
def test_a_name_that_is_not_a_repository_name_is_refused_naming_the_setting(bad, capsys):
    assert day_zero.main(["commands", f"--name={bad}", "--shell", "posix"]) == 2
    err = capsys.readouterr().err
    assert "--name" in err and (not bad or bad not in err)


# --- answer 4: the answers become the first source ------------------------------------------------


def test_write_makes_a_source_the_plan_check_accepts_and_removes_the_kept_file(
    tmp_path, home, empty
):
    """REQ-069 AC1, SPEC-0043 rule 1: `Kind: other`, the person's words quoted, never rewritten."""
    words = "People who book a table.\n## not a heading\nThe restaurant pays."
    path = answer(tmp_path, words)
    args = ["keep", "--folder", str(empty), "--yes", "--answer-file", str(path)]
    assert day_zero.main([*args, "--id", "users"]) == 0
    assert day_zero.main([*args, "--id", "colour-of-the-logo"]) == 0
    git("init", "-q", "-b", "main", cwd=empty)
    out = tmp_path / "answers.json"
    code = day_zero.main(
        ["write", "--root", str(empty), "--folder", str(empty), "--answers", str(out)]
    )
    assert code == 0
    source = empty / "docs" / "sources" / "day-zero.md"
    text = source.read_text(encoding="utf-8")
    head = text.splitlines()[:5]
    assert head[:3] == ["Source: Day-zero conversation", "Kind: other", "Version: 1"]
    assert head[3].startswith("Date: 20") and head[4] == ""
    assert check_plan.header_problems(text) == []
    assert check_plan.source_problems(empty) == []
    assert "> ## not a heading" in text and "> The restaurant pays." in text
    assert all_files(home) == []  # the kept file is removed
    rows = json.loads(out.read_text(encoding="utf-8"))["answers"]
    assert [r["id"] for r in rows] == ["users"]  # only the ids the vision's answers file knows
    assert rows[0]["answer"] == words
    lines, open_ids, problems = front_door.answer_lines("answers.json", rows)
    assert problems == [] and "users" not in open_ids


def test_write_never_overwrites_a_source_and_keeps_the_kept_file(tmp_path, home, empty, capsys):
    path = answer(tmp_path, "Restaurants.")
    day_zero.main(
        ["keep", "--folder", str(empty), "--yes", "--id", "users", "--answer-file", str(path)]
    )
    source = empty / "docs" / "sources" / "day-zero.md"
    source.parent.mkdir(parents=True)
    source.write_text("kept by the person\n", encoding="utf-8")
    assert day_zero.main(["write", "--root", str(empty), "--folder", str(empty)]) == 1
    assert source.read_text(encoding="utf-8") == "kept by the person\n"
    assert len(all_files(home)) == 1


def test_write_with_nothing_kept_writes_nothing(tmp_path, home, empty, capsys):
    assert day_zero.main(["write", "--root", str(empty), "--folder", str(empty)]) == 0
    assert capsys.readouterr().out.strip() == "write: nothing kept"
    assert all_files(empty) == []
