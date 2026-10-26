"""Tests of the engines table and its doctor checks (SPEC-0029 rules 1-3 and 8; REQ-036)."""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path

import pytest
from doctor import CHECKS
from test_doctor import checks_of, doctor, prepare, stub_gh

KIT = Path(__file__).resolve().parents[2]
KEYS = ("vision", "stack", "design", "review")
SECRET_NAME = "zq-engine-name"  # nosec B105 - a made-up skill name the test proves is never printed


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """HOME is a directory of the test, so the user's own skills never reach a result."""
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    return path


def run_engines(
    tmp_path: Path,
    engines: str = "",
    project_skills: tuple[str, ...] = (),
    kit_skills: tuple[str, ...] = (),
    kit: bool = True,
):
    """Doctor on the `ok` case with an `[engines]` text appended to agk.toml and skills laid out."""
    dirs = prepare("ok", tmp_path)
    toml = dirs["root"] / "agk.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + engines, encoding="utf-8")
    for name in project_skills:
        skill = dirs["root"] / ".claude" / "skills" / name / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    for name in kit_skills:
        skill = dirs["kit"] / "skills" / name / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    stub = tmp_path / "bin"
    stub_gh(stub)
    dirs["before"] = tree(dirs["root"])
    args = ["--api-dir", str(dirs["api"]), "--repo", "example-owner/example-repo", "--json"]
    if kit:
        args += ["--kit-root", str(dirs["kit"])]
    proc = doctor(*args, str(dirs["root"]), path=f"{stub}{os.pathsep}{os.environ['PATH']}")
    return proc, dirs


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_ac1_without_an_engines_table_every_engine_is_absent_and_the_template_is_used(tmp_path):
    """REQ-036 AC1: SPEC-0029 rules 1 and 2 (absent means the kit's own template)."""
    proc, _ = run_engines(tmp_path)
    report = checks_of(proc.stdout)
    assert proc.returncode == 0, proc.stdout
    for key in KEYS:
        check = report[f"engine-{key}"]
        assert check["status"] == "ok" and "absent" in check["message"]
        assert "template" in check["message"]
    assert report["engines-keys"]["status"] == "ok"


def test_ac1_a_named_skill_of_the_project_or_the_plugin_is_present(tmp_path):
    """REQ-036 AC1: SPEC-0029 rule 2 (present: a skill the session can see)."""
    engines = f'[engines]\nvision = "{SECRET_NAME}"\nstack = "plugin-skill"\n'
    proc, _ = run_engines(tmp_path, engines, (SECRET_NAME,), ("plugin-skill",))
    report = checks_of(proc.stdout)
    assert proc.returncode == 0, proc.stdout
    assert (
        report["engine-vision"]["status"] == "ok"
        and "present" in report["engine-vision"]["message"]
    )
    assert (
        report["engine-stack"]["status"] == "ok" and "present" in report["engine-stack"]["message"]
    )
    assert "absent" in report["engine-design"]["message"]
    assert "absent" in report["engine-review"]["message"]


def test_ac1_a_user_level_skill_is_present_even_with_no_kit_root(tmp_path, home):
    """REQ-036 AC1: SPEC-0029 rule 2 (the ruling on Q-K4-257: `~/.claude/skills` is seen)."""
    skill = home / ".claude" / "skills" / SECRET_NAME / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("zq-file-content\n", encoding="utf-8")
    for kit in (True, False):
        proc, _ = run_engines(tmp_path / str(kit), f'[engines]\nstack = "{SECRET_NAME}"\n', kit=kit)
        check = checks_of(proc.stdout)["engine-stack"]
        assert check["status"] == "ok" and "present" in check["message"]
        assert SECRET_NAME not in proc.stdout and "zq-file-content" not in proc.stdout


def test_ac1_a_user_level_skill_of_another_name_does_not_make_an_engine_present(tmp_path, home):
    """REQ-036 AC1: SPEC-0029 rule 2 (the name must match; the home directory is not listed)."""
    skill = home / ".claude" / "skills" / "other-name" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("x\n", encoding="utf-8")
    proc, _ = run_engines(tmp_path / "run", f'[engines]\nstack = "{SECRET_NAME}"\n')
    assert "missing" in checks_of(proc.stdout)["engine-stack"]["message"]


@pytest.mark.parametrize("key", KEYS)
def test_ac1_a_named_skill_that_is_not_found_is_missing_and_the_name_is_not_printed(tmp_path, key):
    """REQ-036 AC1: SPEC-0029 rule 2 (missing names the setting, never the value)."""
    proc, _ = run_engines(tmp_path, f'[engines]\n{key} = "{SECRET_NAME}"\n')
    check = checks_of(proc.stdout)[f"engine-{key}"]
    assert check["status"] == "fail" and check["severity"] == "warn"
    assert "missing" in check["message"] and f"engines.{key}" in check["message"]
    assert SECRET_NAME not in proc.stdout
    assert proc.returncode == 4


def test_ac1_doctor_with_no_kit_root_cannot_tell_a_missing_plugin_skill(tmp_path):
    """REQ-036 AC1: SPEC-0029 rule 2 (cannot-check is never ok)."""
    proc, _ = run_engines(tmp_path, f'[engines]\nvision = "{SECRET_NAME}"\n', kit=False)
    check = checks_of(proc.stdout)["engine-vision"]
    assert (check["status"], check["reason"]) == ("cannot-check", "no-kit-root")


def test_ac1_a_skill_of_another_plugin_cannot_be_read(tmp_path):
    """REQ-036 AC1: SPEC-0029 rule 2 (only the project's and this plugin's skills are read)."""
    proc, _ = run_engines(tmp_path, '[engines]\nreview = "other:thing"\n')
    check = checks_of(proc.stdout)["engine-review"]
    assert (check["status"], check["reason"]) == ("cannot-check", "plugin-unreadable")
    assert "other:thing" not in proc.stdout


@pytest.mark.parametrize("value", ['""', "3", '"../x"', '"a b"'])
def test_ac1_an_invalid_engine_value_fails_without_printing_it(tmp_path, value):
    """REQ-036 AC1: SPEC-0029 rule 1 (a value is the name of a skill)."""
    proc, _ = run_engines(tmp_path, f"[engines]\ndesign = {value}\n")
    check = checks_of(proc.stdout)["engine-design"]
    assert check["status"] == "fail" and "invalid" in check["message"]
    assert "../x" not in proc.stdout and "a b" not in proc.stdout


def test_ac1_a_key_other_than_the_four_fails_and_the_key_is_not_printed(tmp_path):
    """REQ-036 AC1: SPEC-0029 rule 1 (the keys are vision, stack, design and review)."""
    proc, _ = run_engines(tmp_path, f'[engines]\n{SECRET_NAME} = "x"\n')
    check = checks_of(proc.stdout)["engines-keys"]
    assert check["status"] == "fail" and "[engines]" in check["message"]
    assert SECRET_NAME not in proc.stdout


def test_ac1_the_engines_checks_come_last_and_doctor_writes_nothing(tmp_path):
    """REQ-036 AC1: SPEC-0029 rule 2 (read-only, no network, no model)."""
    proc, dirs = run_engines(tmp_path, f'[engines]\nvision = "{SECRET_NAME}"\n')
    assert list(checks_of(proc.stdout))[-5:] == [
        "engines-keys",
        "engine-vision",
        "engine-stack",
        "engine-design",
        "engine-review",
    ]
    assert list(CHECKS)[-5:] == list(checks_of(proc.stdout))[-5:]
    assert tree(dirs["root"]) == dirs["before"]
    assert not (tmp_path / "bin" / "gh-calls").exists()


def test_ac2_a_change_of_the_engines_table_needs_an_adr_that_names_agk_toml(repo):
    """REQ-036 AC2: SPEC-0029 rules 1 and 3 (agk.toml is protected; the check names it)."""
    repo.commit(
        {
            "config/protected-paths.txt": "# c\nconfig/\nagk.toml\n",
            "agk.toml": 'version = "1"\n',
        },
        "base",
    )
    repo.branch()
    repo.commit({"agk.toml": 'version = "1"\n[engines]\nvision = "x"\n'})
    proc = repo.run("check_protected_changes.py", "--base", "main")
    assert proc.returncode == 1 and "agk.toml" in proc.stdout
    repo.commit({"docs/adr/0003-x.md": "# ADR-0003: x\n\n- Status: Accepted\n\nCovers agk.toml.\n"})
    assert repo.run("check_protected_changes.py", "--base", "main").returncode == 0


def test_ac2_the_guide_and_the_skill_say_an_engine_never_decides():
    """REQ-036 AC2: SPEC-0029 rule 3 (an engine's output goes through the template, the checks)."""
    guide = (KIT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    section = guide.split("## Engines", 1)[1].split("\n## ", 1)[0]
    for text in (
        "`[engines]`",
        "vision",
        "stack",
        "design",
        "review",
        "present",
        "absent",
        "missing",
        "never decides",
        "protected",
        "ADR",
        "template",
    ):
        assert text in section, text
    skill = (KIT / "skills" / "doctor" / "SKILL.md").read_text(encoding="utf-8")
    assert "engine" in skill and "missing" in skill


def test_ac8_no_default_engine_is_pinned_anywhere_the_kit_ships():
    """REQ-036 AC8: SPEC-0029 rule 8 (templates only; a commented example, no value)."""
    assert "engines" not in tomllib.loads((KIT / "agk.toml").read_text(encoding="utf-8"))
    for rel in ("kit/templates/agk.toml", "kit/templates/agk.adopt.toml"):  # they hold {{fields}}
        lines = (KIT / rel).read_text(encoding="utf-8").splitlines()
        assert not [ln for ln in lines if ln.startswith(("[engines", "engines", "vision ="))], rel
    template = (KIT / "kit" / "templates" / "agk.toml").read_text(encoding="utf-8")
    assert "# [engines]" in template and "an ADR in the same pull request" in template
    for rel in ("kit/manifest.json", ".claude-plugin/plugin.json"):
        assert "engine" not in json.loads((KIT / rel).read_text(encoding="utf-8")).keys()
