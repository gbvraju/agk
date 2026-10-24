"""Kit-only tests: a project's first requirement is REQ-101 (SPEC-0012 rule 2, amendment 29).

`common.next_free_ids` and every check that compares ids (`intake.py ids`, `stub`, `check`, the
`requirement` form of `new_spec.py`) give a project (agk.toml `mode` init or adopt)
`REQ-max(101, highest + 1)`, because `REQ-001` to `REQ-099` are reserved for the kit. The kit's own
repository, which has no `mode`, still gets the highest id plus one.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo, run_init, without_version_line
from test_adopt import adopt, make_existing
from test_intake import ACCEPTANCE, adr_text, requirement, spec_text

SCRIPTS = KIT_ROOT / "scripts" / "agk"
SENTENCE = "Let a visitor export their saved list as a file."
SECTION = "\n### REQ-{n} — Added\n\n- Acceptance: AC1 given a, when b, then c\n- Status: planned\n"


def commit_all(root: Path) -> None:
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "install")


def script(root: Path, name: str, *args: str):
    return without_version_line(
        subprocess.run(
            [sys.executable, str(SCRIPTS / name), *args, "--root", str(root)],
            capture_output=True,
            text=True,
            env=clean_env(),
        )
    )


def next_req(root: Path) -> str:
    proc = script(root, "intake.py", "ids", "--sentence", SENTENCE, "--ref", "HEAD")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)["req"]


@pytest.fixture
def init_target(target: Path) -> Path:
    proc = run_init(target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    commit_all(target)
    return target


@pytest.fixture
def adopt_target(tmp_path: Path) -> Path:
    root = make_existing(tmp_path / "existing", branch="main")
    proc = adopt(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    commit_all(root)
    return root


def append_requirements(root: Path, *numbers: int) -> None:
    path = root / "docs" / "requirements.md"
    path.write_text(
        path.read_text(encoding="utf-8") + "".join(SECTION.format(n=f"{n:03d}") for n in numbers),
        encoding="utf-8",
    )
    commit_all(root)


@pytest.mark.parametrize("which", ["init_target", "adopt_target"])
def test_ac1_a_new_project_starts_its_requirements_at_101(which, request):
    """REQ-019 AC1: SPEC-0012 rule 2 (REQ-001 to REQ-099 are the kit's; the first of a project)."""
    root = request.getfixturevalue(which)
    assert next_req(root) == "REQ-101"


@pytest.mark.parametrize("which", ["init_target", "adopt_target"])
def test_ac1_the_next_project_id_is_the_highest_plus_one(which, request):
    """REQ-019 AC1: SPEC-0012 rule 2 (101 and 102 exist, so 103; a gap is not filled)."""
    root = request.getfixturevalue(which)
    append_requirements(root, 101, 102)
    assert next_req(root) == "REQ-103"
    append_requirements(root, 150)
    assert next_req(root) == "REQ-151"


@pytest.mark.parametrize("which", ["init_target", "adopt_target"])
def test_ac1_an_empty_requirements_file_of_a_project_still_gives_101(which, request):
    """REQ-019 AC1: SPEC-0012 rule 2 (an empty file is not an excuse to take a kit id)."""
    root = request.getfixturevalue(which)
    (root / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    commit_all(root)
    assert next_req(root) == "REQ-101"


def test_ac1_the_kits_own_repository_is_unchanged(tmp_path):
    """REQ-019 AC1: SPEC-0012 rule 2 (no `mode`: the highest plus one, as before)."""
    root = make_repo(tmp_path / "kit")
    (root / "docs").mkdir()
    (root / "docs" / "requirements.md").write_text(
        "# Requirements\n\n" + SECTION.format(n="003").lstrip("\n"), encoding="utf-8"
    )
    commit_all(root)
    assert next_req(root) == "REQ-004"
    (root / "agk.toml").write_text('mode = ""\n', encoding="utf-8")
    commit_all(root)
    assert next_req(root) == "REQ-004"


@pytest.mark.parametrize("which", ["init_target", "adopt_target"])
def test_ac1_the_requirement_form_of_new_spec_gives_the_same_id(which, request):
    """REQ-019 AC1: SPEC-0012 rule 2 (one function: `new_spec.py requirement` agrees)."""
    root = request.getfixturevalue(which)
    proc = script(root, "new_spec.py", "requirement", "Export a list")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    names = [p.name for p in (root / "docs" / "adr").glob("*add-req-*")]
    assert any("add-req-101" in n for n in names), names


def test_ac1_new_spec_restates_the_rule_with_the_same_constant():
    """REQ-019 AC1: SPEC-0012 rule 2 (new_spec.py is stdlib-only: it restates the rule)."""
    sys.path.insert(0, str(SCRIPTS))
    import common
    import new_spec

    assert new_spec.PROJECT_FIRST_REQ == common.PROJECT_FIRST_REQ == 101


def draft_for(root: Path, req: str) -> None:
    """The three intake files for `req`, numbered as the base's ids say (spec and ADR numbers)."""
    ids = json.loads(
        script(root, "intake.py", "ids", "--sentence", SENTENCE, "--ref", "HEAD").stdout
    )
    swap = {"REQ-004": req, "0014": ids["spec"], "0022": ids["adr"]}

    def apply(text: str) -> str:
        for old, new in swap.items():
            text = text.replace(old, new)
        return text

    git(root, "switch", "-q", "-c", "intake/export")
    with (root / "docs" / "requirements.md").open("a", encoding="utf-8") as fh:
        fh.write(apply(requirement(ACCEPTANCE)))
    (root / "docs" / "specs" / f"{ids['spec']}-export.md").write_text(
        apply(spec_text()), encoding="utf-8"
    )
    (root / "docs" / "adr" / f"{ids['adr']}-add-{req.lower()}-export.md").write_text(
        apply(adr_text()), encoding="utf-8"
    )


@pytest.mark.parametrize("which", ["init_target", "adopt_target"])
def test_ac1_the_check_accepts_101_and_refuses_the_kit_id(which, request):
    """REQ-019 AC1: SPEC-0012 rule 11 C1 (the check uses the same function as `ids`)."""
    root = request.getfixturevalue(which)
    base = git_branch(root)
    draft_for(root, "REQ-101")
    good = script(root, "intake.py", "check", "--base", base, "--date", "2026-10-21")
    assert (good.returncode, good.stdout) == (0, "ok intake\n"), good.stdout + good.stderr


@pytest.mark.parametrize("which", ["init_target", "adopt_target"])
def test_ac1_a_draft_that_takes_a_kit_id_fails_c1(which, request):
    """REQ-019 AC1: SPEC-0012 rule 11 C1 (REQ-004 is not the next free id of a project)."""
    root = request.getfixturevalue(which)
    base = git_branch(root)
    draft_for(root, "REQ-004")
    bad = script(root, "intake.py", "check", "--base", base, "--date", "2026-10-21")
    assert bad.returncode == 1 and "C1" in bad.stdout + bad.stderr, bad.stdout + bad.stderr


def git_branch(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, capture_output=True, text=True
    ).stdout.strip()
