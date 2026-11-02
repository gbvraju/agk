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


def existing_mockup(root, folder=FOLDER):
    """A mockup folder as the retired writer made it, with its old-format theme (SPEC-0029)."""
    target = mockup(root, folder)
    target.mkdir(parents=True)
    templates = KIT_ROOT / "kit" / "templates"
    (target / "index.html").write_text(
        (templates / "design-index.html").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (target / "README.md").write_text(
        (templates / "design-readme.md").read_text(encoding="utf-8").replace("{{folder}}", folder),
        encoding="utf-8",
    )
    theme = root / "docs" / "design" / "theme.md"
    theme.write_text(
        OLD_THEME.replace("{{evidence}}", f"docs/design/mockups/{folder}/"), encoding="utf-8"
    )
    return target


def mockup(root, folder=FOLDER):
    return root / "docs" / "design" / "mockups" / folder


OLD_THEME = """# Theme

The brand record and the rules of this product's design.

## Brand

- name: [brand name] — source: [where the owner wrote it down]
- font: system-ui — source: the kit's default, a system font with no download

## Tokens

```css
:root {
  --bg: #ffffff;
  --fg: #111111;
  --muted: #555555;
  --accent: #1a56db;
  --accent-fg: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #101418;
    --fg: #f2f2f2;
    --muted: #b0b0b0;
    --accent: #8ab4ff;
    --accent-fg: #101418;
  }
}
```

## Evidence

Evidence: {{evidence}}
"""


# --- write (SPEC-0037 rule 12: no new mockup folder) -------------------------------------------

REFUSAL = "FAIL design: rule 12: a new mockup folder is not written; use /agk:design prototype\n"


@pytest.mark.parametrize(
    "args",
    [
        ("--name", "home", "--date", "2026-10-24"),
        ("--name", "home"),
        ("--name", "Home"),
        ("--name", "home", "--theme-file", "draft.md"),
    ],
)
def test_ac5_write_refuses_a_new_mockup_folder_and_writes_nothing(tmp_path, args):
    """REQ-036 AC5 as SPEC-0037 rule 12 changes it (`Q-S0037-10`; brief #457 answer 6)."""
    proc = design(tmp_path, "write", *args)
    assert (proc.returncode, proc.stdout) == (1, REFUSAL)
    assert not (tmp_path / "docs").exists()


def test_ac5_write_refuses_beside_an_existing_mockup_folder_and_changes_nothing(tmp_path):
    """REQ-036 AC5 as SPEC-0037 rule 12 changes it (existing folders are only read and checked)."""
    existing_mockup(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    proc = design(tmp_path, "write", "--name", "about", "--date", "2026-10-24")
    assert (proc.returncode, proc.stdout) == (1, REFUSAL)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert check(tmp_path).returncode == 0


def test_ac5_the_approval_line_is_the_owners_and_no_template_writes_it():
    """REQ-036 AC5: SPEC-0029 rule 6 (the session never writes the approval line)."""
    for rel in ("design-readme.md", "design-index.html", "design-theme.md"):
        text = (KIT_ROOT / "kit" / "templates" / rel).read_text(encoding="utf-8")
        assert not check_design.APPROVAL.search(text), rel


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
    """REQ-036 AC5: SPEC-0029 rule 6 (four screenshots with a headless browser)."""
    existing_mockup(tmp_path)
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
    # in Blink 0 is dark and 1 is light (measured on Chromium); both are passed explicitly
    assert sum("preferredColorScheme=0" in c for c in calls) == 2
    assert sum("preferredColorScheme=1" in c for c in calls) == 2
    for c in calls:
        dark = "-dark.png" in c
        assert ("preferredColorScheme=0" in c) == dark and ("preferredColorScheme=1" in c) != dark
    assert all(f"file://{mockup(tmp_path)}/index.html" in c for c in calls)
    assert check(tmp_path).returncode == 0  # screenshots are not a page; the check still passes


def test_ac5_without_a_headless_browser_the_screenshots_are_skipped_not_failed(tmp_path):
    """REQ-036 AC5: SPEC-0029 rule 6 (when a headless browser exists; otherwise a note)."""
    existing_mockup(tmp_path)
    empty = tmp_path.parent / (tmp_path.name + "-empty")
    empty.mkdir()
    proc = design(tmp_path, "screenshots", "--folder", FOLDER, path=str(empty))
    assert proc.returncode == 0
    assert proc.stdout == "design: no headless browser found; screenshots skipped\n"
    assert not (mockup(tmp_path) / "screenshots").exists()


@pytest.mark.parametrize("folder", ["missing", "../x", "2026-10-24-home/../.."])
def test_ac5_screenshots_of_a_folder_that_does_not_exist_are_refused(tmp_path, folder):
    """REQ-036 AC5: SPEC-0029 rule 6 (only a mockup folder, never another path)."""
    existing_mockup(tmp_path)
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
    paused = " && steps.paused.outputs.paused != 'true'"  # brief #348
    assert "if: ${{ !cancelled() && github.event.action != 'edited'" + paused + " }}" in block
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
