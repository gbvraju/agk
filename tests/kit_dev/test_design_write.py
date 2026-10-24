"""Kit-only tests of `/agk:design`: the writer, the screenshots, the governance step (SPEC-0029).

`design.py write` makes the theme (when absent) and a mockup folder from the kit's templates with
the approval line left to the owner; `design.py screenshots` takes four screenshots when a headless
browser exists; `check_design.py` becomes a step of `make governance`. No network, no model.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import check_design  # noqa: E402

SCRIPT = KIT_ROOT / "scripts" / "agk" / "design.py"
CHECK = KIT_ROOT / "scripts" / "agk" / "check_design.py"
FOLDER = "2026-10-24-home"
OWNER = "Approved by Sam Owner on 2026-10-24"


def design(root, *args, path=None):
    env = clean_env()
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=env,
    )


def check(root):
    return subprocess.run(
        [sys.executable, str(CHECK), "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def write(root, name="home", date="2026-10-24", *extra):
    return design(root, "write", "--name", name, "--date", date, *extra)


def mockup(root, folder=FOLDER):
    return root / "docs" / "design" / "mockups" / folder


# --- write -------------------------------------------------------------------------------------


def test_ac5_write_makes_the_theme_and_the_mockup_folder_from_the_templates(tmp_path):
    """REQ-036 AC5: SPEC-0029 rule 6 (theme.md, index.html and README.md)."""
    proc = write(tmp_path)
    assert proc.returncode == 0, proc.stdout
    theme = (tmp_path / "docs" / "design" / "theme.md").read_text(encoding="utf-8")
    assert f"Evidence: docs/design/mockups/{FOLDER}/" in theme
    for heading in ("## Brand", "## Tokens", "## Contrast", "## Rules", "## Evidence"):
        assert heading in theme
    for rule in (
        "one token block",
        "44 px",
        "360 px",
        "4.5:1",
        "native controls",
        "word plus colour",
    ):
        assert rule in theme.lower(), rule
    page = (mockup(tmp_path) / "index.html").read_text(encoding="utf-8")
    assert "<script" not in page and "://" not in page and "[Product name]" in page
    assert page.count("<style") == 1 and "system-ui" in page
    assert (mockup(tmp_path) / "README.md").is_file()


def test_ac5_what_write_makes_passes_the_check_with_two_notes_and_no_failure(tmp_path):
    """REQ-036 AC5 and AC7: SPEC-0029 rules 6 and 7 (a fresh record: not approved, brand open)."""
    write(tmp_path)
    proc = check(tmp_path)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [
        "design: the theme is not approved yet",
        "at risk design: placeholder brand",
        "ok design",
    ]


def test_ac5_the_approval_line_is_the_owners_and_write_never_writes_it(tmp_path):
    """REQ-036 AC5: SPEC-0029 rule 6 (the session never writes the approval line)."""
    write(tmp_path)
    readme = (mockup(tmp_path) / "README.md").read_text(encoding="utf-8")
    assert not check_design.APPROVAL.search(readme) and "Approved: not yet" in readme
    for rel in ("design-readme.md", "design-index.html", "design-theme.md"):
        text = (KIT_ROOT / "kit" / "templates" / rel).read_text(encoding="utf-8")
        assert not check_design.APPROVAL.search(text), rel
    (mockup(tmp_path) / "README.md").write_text(readme + f"\n{OWNER}\n", encoding="utf-8")
    assert check(tmp_path).stdout == "at risk design: placeholder brand\nok design\n"


def test_ac5_the_date_comes_from_the_clock_when_none_is_given(tmp_path):
    """REQ-036 AC5: principle 10 (dates come from `date -u`)."""
    proc = design(tmp_path, "write", "--name", "home")
    assert proc.returncode == 0, proc.stdout
    today = subprocess.run(["date", "-u", "+%F"], capture_output=True, text=True).stdout.strip()
    assert (mockup(tmp_path, f"{today}-home") / "index.html").is_file()


@pytest.mark.parametrize("name", ["", "Home", "a b", "../x", "-x", "a/b", "x" * 61])
def test_ac5_a_name_that_is_not_a_slug_is_refused_and_nothing_is_written(tmp_path, name):
    """REQ-036 AC5: SPEC-0029 rule 6 (`<date>-<name>`; the refusal names the rule only)."""
    proc = write(tmp_path, name)
    assert proc.returncode == 1 and "rule 6" in proc.stdout
    assert not name or name not in proc.stdout
    assert not (tmp_path / "docs").exists()


@pytest.mark.parametrize("date", ["2026-13-45", "today", "2026-1-1", ""])
def test_ac5_a_date_that_is_not_a_date_is_refused(tmp_path, date):
    """REQ-036 AC5: SPEC-0029 rule 6 (the date is a real YYYY-MM-DD)."""
    proc = write(tmp_path, "home", date)
    assert proc.returncode == 1 and "rule 6" in proc.stdout
    assert not (tmp_path / "docs").exists()


def test_ac5_an_existing_folder_and_an_existing_theme_are_never_overwritten(tmp_path):
    """REQ-036 AC5: SPEC-0029 rule 6 (the theme is the owner's once written)."""
    write(tmp_path)
    theme = tmp_path / "docs" / "design" / "theme.md"
    theme.write_text(theme.read_text(encoding="utf-8") + "\nOwner's line.\n", encoding="utf-8")
    before = theme.read_bytes()
    again = write(tmp_path)
    assert again.returncode == 1 and "rule 6" in again.stdout and "folder" in again.stdout
    second = write(tmp_path, "about")
    assert second.returncode == 0 and theme.read_bytes() == before
    assert (mockup(tmp_path, "2026-10-24-about") / "index.html").is_file()


def test_ac5_a_draft_theme_is_written_as_given_through_the_check(tmp_path):
    """REQ-036 AC5: SPEC-0029 rules 3 and 6 (an engine's draft goes in the theme's place)."""
    write(tmp_path, "first")
    draft = (tmp_path / "docs" / "design" / "theme.md").read_text(encoding="utf-8")
    other = tmp_path.parent / (tmp_path.name + "-draft.md")
    draft = draft.replace("[brand name]", "Reading List")
    draft = draft.replace("[primary colour as a hex value]", "#1a56db")
    other.write_text(draft, encoding="utf-8")
    fresh = tmp_path.parent / (tmp_path.name + "-fresh")
    fresh.mkdir()
    proc = write(fresh, "first", "2026-10-24", "--theme-file", str(other))
    assert proc.returncode == 0, proc.stdout
    assert "Reading List" in (fresh / "docs" / "design" / "theme.md").read_text(encoding="utf-8")
    assert "placeholder brand" not in check(fresh).stdout


# --- screenshots -------------------------------------------------------------------------------


def fake_browser(directory, name="chromium"):
    """A browser on PATH that records its arguments and writes the screenshot it is asked for."""
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / "calls"
    script = directory / name
    script.write_text(
        "#!/bin/sh\n"
        'echo "$@" >> "' + str(log) + '"\n'
        'for a in "$@"; do case "$a" in --screenshot=*) : > "${a#--screenshot=}";; esac; done\n'
    )
    script.chmod(0o755)
    return log


def test_ac5_screenshots_takes_four_with_a_headless_browser(tmp_path):
    """REQ-036 AC5: SPEC-0029 rule 6 (four screenshots with a headless browser) (verify flags)."""
    write(tmp_path)
    log = fake_browser(tmp_path.parent / (tmp_path.name + "-bin"))
    path = f"{log.parent}{os.pathsep}{os.environ['PATH']}"
    proc = design(tmp_path, "screenshots", "--folder", FOLDER, path=path)
    assert proc.returncode == 0, proc.stdout
    shots = sorted(p.name for p in (mockup(tmp_path) / "screenshots").iterdir())
    assert shots == ["1280-dark.png", "1280-light.png", "360-dark.png", "360-light.png"]
    calls = log.read_text(encoding="utf-8").splitlines()
    assert len(calls) == 4 and all("--headless" in c for c in calls)
    assert sum("--window-size=360," in c for c in calls) == 2
    assert sum("--window-size=1280," in c for c in calls) == 2
    assert sum("preferredColorScheme=1" in c for c in calls) == 2
    assert all(f"file://{mockup(tmp_path)}/index.html" in c for c in calls)
    assert check(tmp_path).returncode == 0  # screenshots are not a page; the check still passes


def test_ac5_without_a_headless_browser_the_screenshots_are_skipped_not_failed(tmp_path):
    """REQ-036 AC5: SPEC-0029 rule 6 (when a headless browser exists; otherwise a note)."""
    write(tmp_path)
    empty = tmp_path.parent / (tmp_path.name + "-empty")
    empty.mkdir()
    proc = design(tmp_path, "screenshots", "--folder", FOLDER, path=str(empty))
    assert proc.returncode == 0
    assert proc.stdout == "design: no headless browser found; screenshots skipped\n"
    assert not (mockup(tmp_path) / "screenshots").exists()


@pytest.mark.parametrize("folder", ["missing", "../x", "2026-10-24-home/../.."])
def test_ac5_screenshots_of_a_folder_that_does_not_exist_are_refused(tmp_path, folder):
    """REQ-036 AC5: SPEC-0029 rule 6 (only a mockup folder, never another path)."""
    write(tmp_path)
    proc = design(tmp_path, "screenshots", "--folder", folder)
    assert proc.returncode == 1 and "rule 6" in proc.stdout and folder not in proc.stdout


def test_ac5_the_writer_reads_files_and_runs_only_a_browser(tmp_path):
    """REQ-036 AC5: SPEC-0029 rule 6 (no network, no model; nothing but the browser is run)."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*(?:import|from)\s+(?:socket|urllib|http|requests|ssl)\b", source, re.M
    )
    assert "shell=True" not in source and "os.system" not in source


# --- the governance step -----------------------------------------------------------------------


def test_ac6_check_design_is_a_step_of_make_governance_and_of_the_workflow():
    """REQ-036 AC6: SPEC-0029 rules 7 and 9 (the step is added here; the exemption is removed)."""
    mk = (KIT_ROOT / "agk.mk").read_text(encoding="utf-8")
    recipe = mk.split("agk-governance:\n", 1)[1].split("\n\n", 1)[0]
    assert "\t$(PY) scripts/agk/check_design.py\n" in recipe + "\n"
    workflow = (KIT_ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    block = workflow.split("      - name: check_design\n", 1)[1].split("      - name:", 1)[0]
    assert "if: ${{ !cancelled() }}" in block
    assert "run: python scripts/agk/check_design.py\n" in block
    exempt = (KIT_ROOT / "tests" / "kit" / "test_agk_mk.py").read_text(encoding="utf-8")
    assert "check_design.py" not in exempt


def test_ac6_check_design_is_installed_and_runs_in_a_new_project(installed):
    """REQ-036 AC6: SPEC-0029 rule 7 (a project gets the check; with no design record it passes)."""
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/check_design.py" in manifest["verbatim"]
    script = installed / "scripts" / "agk" / "check_design.py"
    assert script.is_file()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert (proc.returncode, proc.stdout) == (0, "ok design (no design record)\n")
    mk = subprocess.run(
        ["make", "-n", "-f", "agk.mk", "agk-governance"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert "scripts/agk/check_design.py" in mk.stdout


# --- the skill and the guide -------------------------------------------------------------------


def test_ac5_the_skill_names_the_engine_the_template_the_owner_and_the_checks():
    """REQ-036 AC5: SPEC-0029 rules 3 and 6 (an engine drafts; the owner approves, by a line)."""
    text = (KIT_ROOT / "skills" / "design" / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: design\n") and "disable-model-invocation: true" in text
    assert "[engines]" in text and "`design`" in text and "never decides" in text
    assert "design.py" in text and "check_design.py" in text and "screenshots" in text
    assert "approval line" in text and "owner" in text and "protected" in text
    assert "Approved by" in text and "never write" in text
    for verb in ("git push", "git commit", "gh pr", "gh issue"):
        assert verb not in text


def test_ac5_the_guide_lists_the_command_and_the_installed_check():
    """REQ-036 AC5: SPEC-0029 rules 6 and 7 (the check is no longer kit-only)."""
    guide = (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    assert "| `/agk:design` |" in guide
    section = guide.split("## Design check", 1)[1].split("\n## ", 1)[0]
    assert "Kit-only" not in section and "make governance" in section
