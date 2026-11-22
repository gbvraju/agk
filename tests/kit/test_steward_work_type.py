"""The kind of product named in discovery becomes the work type on the owner's yes (brief #1757,
ADR-0735, amendment 218 to SPEC-0038 rule 5; REQ-045).

`steward_owner.py work-type --propose` asks the owner one plain question when discovery names a
work type and `agk.toml` declares none; `work-type --yes` writes the `[delivery]` line and its
Proposed ADR on a new branch on the recorded plain yes in solo mode with one person, and prints
only otherwise; `engines.py stack-write` refuses, naming `delivery.work_type`, while discovery
names a work type that is not declared; `doctor.py` warns once, naming the setting.

Local git only, a recorded memory double, no network; invented data only (example.com).
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import doctor  # noqa: E402
import steward_owner  # noqa: E402

ENGINES = KIT_ROOT / "scripts" / "agk" / "engines.py"
NOW = datetime(2026, 11, 22, 18, 40, tzinfo=UTC)
AT = "2026-11-22T18:39Z"
SOLO = 'default_branch = "main"\nreview_mode = "solo"\n'
TEAM = 'default_branch = "main"\nreview_mode = "team"\n'
ONE = "version: 1\nverdict_authors: [boss]\nspec_approvers: [boss]\n"


def discovery(work_type: str, name: str = "booking") -> str:
    return (
        f"# Discovery: A booking site for example.com\n\n- Problem: vision\n"
        f"- Work type: {work_type} (proposed)\n- Screens: yes\n\n## Answers\n\n## Open points\n\n"
        "- none\n"
    )


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


def project(
    tmp: Path, toml: str = SOLO, kinds: tuple[str, ...] = ("web-app",), people: str = ONE
) -> Path:
    root = tmp / "product"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "adr" / "0001-record-architecture-decisions.md").write_text(
        "# ADR-0001: Record decisions\n\n- Status: Accepted\n", encoding="utf-8"
    )
    (root / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    (root / "config" / "reviewers.yaml").write_text(people, encoding="utf-8")
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    for n, kind in enumerate(kinds, 1):
        path = root / "docs" / "discovery" / f"idea-{n}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(discovery(kind), encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "owner@example.com")
    git(root, "config", "user.name", "Owner")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "start")
    return root


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AGK_STEWARD_CACHE", str(tmp_path / "state" / "memory.json"))
    monkeypatch.delenv("AGK_STEWARD_START", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    monkeypatch.setenv("AGK_SESSION", "s1")
    records: list = []
    monkeypatch.setattr(
        steward_owner.steward,
        "record",
        lambda r, kind, text, gh: records.append((kind, text)) or (0, ["recorded"]),
    )
    return tmp_path, records


def said(tmp: Path, words: str) -> Path:
    path = tmp / "words.txt"
    path.write_text(words + "\n", encoding="utf-8")
    return path


def propose(root: Path, minutes: float = 5):
    return steward_owner.work_type_propose(root, NOW - timedelta(minutes=minutes))


def yes(tmp: Path, root: Path, words: str = "Yes"):
    return steward_owner.work_type_yes(root, said(tmp, words), AT, None, NOW)


def stack_write(root: Path):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(ENGINES), "stack-write", "--ref", "main", "--date",
         "2026-11-22", "--root", str(root)],
        cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60,
    )  # fmt: skip


# --- answer 1: the proposal --------------------------------------------------------------------


def test_req045_a_web_app_discovery_asks_one_plain_owner_question(env):
    """REQ-045 AC2: brief #1757 answer 1, one question with no kit term, recorded as the ask."""
    tmp, _ = env
    root = project(tmp)
    code, lines = propose(root)
    assert code == 0, lines
    assert lines[0].startswith("ask the person: Your discovery says this is a web app.")
    sentence = lines[0].removeprefix("ask the person: ")
    assert "web-app checks" in sentence and steward_owner.question_problem(sentence) is None
    (ask,) = [a for a in steward_owner.load_asks(root) if a["open"]]
    assert ask["form"] == "work-type" and ask["work_type"] == "web-app"


@pytest.mark.parametrize("kinds", [(), ("pilot",)])
def test_req045_no_discovery_or_a_pilot_proposes_nothing(env, kinds):
    """REQ-045 AC2: answer 1, only a named work type other than `pilot` is proposed."""
    tmp, _ = env
    root = project(tmp, kinds=kinds)
    code, lines = propose(root)
    assert code == 0 and lines == ["work type: discovery names none; nothing to propose"]
    assert steward_owner.load_asks(root) == []


def test_req045_two_named_work_types_ask_which_and_propose_neither(env):
    """REQ-045 AC2: answer 7, two documents naming different types: a question naming both."""
    tmp, _ = env
    root = project(tmp, kinds=("web-app", "mobile"))
    code, lines = propose(root)
    assert code == 0
    assert "a web app" in lines[0] and "a mobile app" in lines[0]
    assert steward_owner.load_asks(root) == []
    assert yes(tmp, root)[0] == 2  # no proposal stands: a yes writes nothing


def test_req045_a_declared_work_type_is_kept_and_nothing_proposed(env):
    """REQ-045 AC2: answers 5 and 7, the owner's line wins; a difference is noted once."""
    tmp, _ = env
    root = project(tmp, SOLO + '\n[delivery]\nwork_type = "mobile"\n')
    code, lines = propose(root)
    assert code == 0 and len(lines) == 1 and "differs from discovery" in lines[0]
    assert "mobile" not in lines[0] and "web-app" not in lines[0]
    assert doctor.work_type_discovery_lines(root) == [
        "note work type: the declared work type differs from discovery; the declared one is kept"
        " (setting: work_type)"
    ]


def test_req045_doctor_warns_once_naming_the_setting_never_the_value(env):
    """REQ-045 AC2: answer 1, one warning naming `work_type`; none without a discovery type."""
    tmp, _ = env
    lines = doctor.work_type_discovery_lines(project(tmp / "one"))
    assert len(lines) == 1 and lines[0].startswith("warn work type:")
    assert "(setting: work_type)" in lines[0] and "web-app" not in lines[0]
    assert doctor.work_type_discovery_lines(project(tmp / "two", kinds=("pilot",))) == []


# --- answer 2: the write on a yes --------------------------------------------------------------


def test_req045_a_recorded_yes_in_solo_mode_writes_the_line_and_its_adr(env):
    """REQ-045 AC2: answer 2, on a new branch: the line and a Proposed ADR quoting the owner;
    the commands are printed, nothing is committed or pushed."""
    tmp, records = env
    root = project(tmp)
    propose(root)
    code, lines = yes(tmp, root, "Yes, go ahead.")
    assert code == 0, lines
    assert git(root, "branch", "--show-current").strip() == steward_owner.WORK_TYPE_BRANCH
    assert git(root, "rev-list", "--count", "HEAD").strip() == "1"  # nothing committed
    data = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    assert data["delivery"] == {"work_type": "web-app"} and data["review_mode"] == "solo"
    (adr,) = (root / "docs" / "adr").glob("0002-work-type.md")
    text = adr.read_text(encoding="utf-8")
    assert "- Status: Proposed" in text and "agk.toml" in text
    assert f'Owner said ({AT}): "Yes, go ahead."' in text
    assert any(ln.startswith("git commit") for ln in lines)
    assert not any(ln.startswith("git push") and "main" in ln.split()[-1] for ln in lines)
    assert records[-1][0] == "Decision" and "work-type" in records[-1][1]
    assert yes(tmp, root)[0] == 2  # the ask is answered: a second yes writes nothing


def test_req045_an_existing_delivery_table_takes_the_line(env):
    """REQ-045 AC2: answer 2, a `[delivery]` table without the line keeps its other keys."""
    tmp, _ = env
    root = project(tmp, SOLO + "\n[delivery]\n# the owner's line goes here\n")
    propose(root)
    assert yes(tmp, root)[0] == 0
    data = tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    assert data["delivery"] == {"work_type": "web-app"}


@pytest.mark.parametrize(
    ("toml", "people"),
    [(TEAM, ONE), (SOLO, "version: 1\nverdict_authors: [boss, ann]\nspec_approvers: [boss]\n")],
)
def test_req045_team_mode_or_two_people_prints_only(env, toml, people):
    """REQ-045 AC2: answers 2 and 5, a team chooses by its own pull request: printed only."""
    tmp, _ = env
    root = project(tmp, toml, people=people)
    before = (root / "agk.toml").read_text(encoding="utf-8")
    propose(root)
    code, lines = yes(tmp, root)
    assert code == 0 and any('work_type = "web-app"' in ln for ln in lines)
    assert (root / "agk.toml").read_text(encoding="utf-8") == before
    assert git(root, "branch", "--show-current").strip() == "main"
    assert not (root / "docs" / "adr" / "0002-work-type.md").exists()


@pytest.mark.parametrize(("words", "code"), [("Yes, but later", 2), ("not yet", 1)])
def test_req045_a_condition_or_not_yet_writes_nothing(env, words, code):
    """REQ-045 AC2: answers 2 and 7, `yes but` is no yes; `not yet` is recorded, nothing written."""
    tmp, records = env
    root = project(tmp)
    before = (root / "agk.toml").read_text(encoding="utf-8")
    propose(root)
    assert yes(tmp, root, words)[0] == code
    assert (root / "agk.toml").read_text(encoding="utf-8") == before
    assert git(root, "branch", "--show-current").strip() == "main"
    if words == "not yet":
        assert records[-1][0] == "Decision" and "not yet" in records[-1][1]


def test_req045_a_stale_yes_or_a_supervisor_steward_writes_nothing(env, monkeypatch):
    """REQ-045 AC2: answer 5, the yes is no older than four times the wait; a steward the
    supervisor started writes nothing."""
    tmp, _ = env
    root = project(tmp)
    propose(root, minutes=60 * 25)
    assert yes(tmp, root)[0] == 2
    propose(root)
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    assert yes(tmp, root)[0] == 2
    assert "delivery" not in tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))


# --- answer 3: the stack after the work type ---------------------------------------------------


def test_req045_stack_write_refuses_a_named_but_undeclared_work_type(env):
    """REQ-045 AC2: answer 3, refused naming `delivery.work_type`, never the value."""
    tmp, _ = env
    proc = stack_write(project(tmp))
    assert proc.returncode == 1
    assert "(setting: delivery.work_type)" in proc.stdout and "web-app" not in proc.stdout
    assert not list((tmp / "product" / "docs" / "adr").glob("*-stack-options.md"))


@pytest.mark.parametrize(
    ("toml", "kinds"),
    [(SOLO, ()), (SOLO, ("pilot",)), (SOLO + '\n[delivery]\nwork_type = "web-app"\n', ("web-app",))],
)
def test_req045_stack_write_is_unchanged_otherwise(env, toml, kinds):
    """REQ-045 AC2: answers 3 and 5, no discovery, a pilot or a declared type: writes as today."""
    tmp, _ = env
    root = project(tmp, toml, kinds=kinds)
    proc = stack_write(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert list((root / "docs" / "adr").glob("*-stack-options.md"))
