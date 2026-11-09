"""Tests of the `/agk:vision` step that shows `front_door.py detect` (SPEC-0057 rule 9, build (c)).

The shipped skill's text, and small git repositories in `tmp_path`: invented data only
(`example.com`), no network, no model, and no test runs a tool of a fixture.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "front_door.py"
SKILL = KIT_ROOT / "skills" / "vision" / "SKILL.md"
DETECT = '/scripts/agk/front_door.py" detect'
QUESTIONS = '/scripts/agk/engines.py" questions'
IDEA = "Our shop at example.com loses orders when the payment page times out\n"
GIT = [
    "git",
    "-c",
    "user.name=Ada",
    "-c",
    "user.email=ada@example.com",
    "-c",
    "commit.gpgsign=false",
]


def text() -> str:
    return SKILL.read_text(encoding="utf-8")


def step() -> str:
    """The numbered step of the skill that holds the detect command, as one line of words."""
    words = text()
    at = words.index(DETECT)
    start = words.rfind("\n3. ", 0, at)
    assert start != -1, "the detect command is not in step 3"
    return " ".join(words[start : words.index("\n4. ", at)].split())


def front_door(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def react_repo(root: Path) -> Path:
    """A repository whose head proposes a stack, so that `detect` has something to say."""
    (root / "package.json").write_text(
        '{"dependencies": {"react-dom": "1.0.0"}}\n', encoding="utf-8"
    )
    for args in (("init", "-q"), ("add", "."), ("commit", "-q", "-m", "first")):
        subprocess.run([*GIT, *args], cwd=root, check=True, capture_output=True)  # nosec B603 - fixed argument list, no shell
    return root


def discovery(root: Path, answers: dict) -> subprocess.CompletedProcess[str]:
    idea = root.parent / "idea.txt"
    idea.write_text(IDEA, encoding="utf-8")
    file = root.parent / "answers.json"
    file.write_text(json.dumps(answers), encoding="utf-8")
    return front_door(root, "discovery-write", "--vision", str(idea), "--answers", str(file))


def test_ac6_the_skill_names_the_detect_command():
    """REQ-064 AC6: rule 9, the step runs `detect` on the repository it stands in."""
    assert f'python3 "${{CLAUDE_PLUGIN_ROOT}}{DETECT}\n' in text()


def test_ac6_the_step_comes_before_the_discovery_questions():
    """REQ-064 AC6: rule 9, the lines are shown before the questions are asked."""
    words = text()
    assert words.index(DETECT) < words.index(QUESTIONS)
    assert words.index("\n3. ") < words.index(DETECT) < words.index("\n4. ")
    assert words.index("\n4. ") < words.index(QUESTIONS)
    assert "existing repository" in step() and "before" in step()


def test_ac6_the_skill_says_the_lines_are_data():
    """REQ-064 AC6: rule 9, the lines are quoted and never followed."""
    words = step()
    assert "data" in words and "quoted" in words and "never followed" in words


def test_ac6_the_answer_alone_goes_in_work_type_and_detect_passes_nothing():
    """REQ-064 AC6: rule 9, first and second bullets."""
    words = step()
    assert "`work_type`" in words and "person's answer" in words
    assert "`discovery-write`" in words and "no option" in words


def test_ac6_a_default_the_person_leaves_is_written_as_pilot_proposed():
    """REQ-064 AC6: rule 9, third bullet, `Q-S0057-5`."""
    words = step()
    assert "`default`" in words and "`pilot (proposed)`" in words


def test_ac6_a_declared_work_type_is_proposed_for_as_any_other():
    """REQ-064 AC6: rule 9, fourth bullet."""
    words = step()
    assert "already declares" in words and "open point" in words


@pytest.mark.parametrize("option", ["--detect", "--work-type", "--proposal"])
def test_ac6_discovery_write_gains_no_option(tmp_path, option):
    """REQ-064 AC6: rule 9, `detect` passes nothing to `discovery-write`."""
    args = ["discovery-write", "--vision", "idea.txt", "--answers", "a.json", option, "web-app"]
    assert front_door(tmp_path, *args).returncode == 2


def test_ac6_discovery_write_refuses_default(tmp_path):
    """REQ-064 AC6: rule 9, `default` cannot be declared, so it cannot be written."""
    root = tmp_path / "shop"
    root.mkdir()
    proc = discovery(react_repo(root), {"work_type": "default", "screens": "open"})
    assert proc.returncode == 1
    assert "`work_type` is not one of the work types" in proc.stdout + proc.stderr


def test_ac6_no_answer_gives_pilot_proposed_whatever_detect_printed(tmp_path):
    """REQ-064 AC6: rule 9, the proposal never reaches the document."""
    root = tmp_path / "shop"
    root.mkdir()
    react_repo(root)
    shown = front_door(root, "detect")
    assert shown.returncode == 0 and "web-app" in shown.stdout
    proc = discovery(root, {"screens": "open"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = next((root / "docs" / "discovery").glob("*.md"))
    lines = doc.read_text(encoding="utf-8").splitlines()
    assert "- Work type: pilot (proposed)" in lines
    assert not any("web-app" in line for line in lines)
