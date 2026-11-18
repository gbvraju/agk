"""Tests of SPEC-0071 rule 7 (brief #1458, ADR-0616; REQ-078 AC5): `doctor.py` warns
`kit-in-repository` for a kit manifest file in a clean project, naming the path class and never the
content; `doctor.py --paused` warns at start after `[licence] valid_until` and stops nothing; the
steward's guard refuses a write of a manifest path into the product. A stub plugin root with its
own `.claude-plugin/plugin.json` and `kit/manifest.json`; invented data only; no network.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import doctor
import pytest

KIT = Path(__file__).resolve().parents[2]
GUARD = KIT / ".claude" / "hooks" / "steward_guard.py"
CONTENT = "planted-example-content-cb-example-1"
CLEAN = 'version = "9.9.9"\n[kit]\nlayout = "plugin"\nplugin_version = "9.9.9"\n'
VERBATIM = [
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/example.yml",
    ".gitignore",
    "CLAUDE.md",
    "LICENSE-AGK",
    "Makefile",
    "scripts/agk/example_check.py",
]


def stub_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"version": "9.9.9"}\n', "utf-8")
    (plugin / "kit").mkdir()
    manifest = {"kit_version": "9.9.9", "kit_tests": "tests/kit", "verbatim": VERBATIM}
    (plugin / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (plugin / ".claude" / "hooks").mkdir(parents=True)
    shutil.copy(GUARD, plugin / ".claude" / "hooks" / "steward_guard.py")
    return plugin


def sample(tmp_path: Path, toml: str = CLEAN, files: tuple[str, ...] = ()) -> Path:
    root = tmp_path / "product"
    root.mkdir()
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    for rel in files:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(CONTENT + "\n", encoding="utf-8")
    return root


# --- the doctor's warning ---------------------------------------------------------------------


def test_req078_doctor_warns_of_a_planted_kit_file_naming_the_path_class(tmp_path):
    """REQ-078 AC5: a manifest file planted in a clean sample is warned of by its path class."""
    plugin = stub_plugin(tmp_path)
    root = sample(tmp_path, files=("scripts/agk/example_check.py", "Makefile", "tests/kit/t.py"))
    lines = doctor.kit_in_repository_lines(root, plugin)
    assert len(lines) == 1
    line = lines[0]
    assert line.startswith("warn kit-in-repository: ")
    assert "(path class: Makefile, scripts/agk/, tests/kit/)" in line
    assert CONTENT not in line and "example_check" not in line


def test_req078_doctor_is_quiet_for_the_files_a_clean_project_keeps(tmp_path):
    """REQ-078 AC5: rule 2's kept files (`.gitignore`, the templates, `CLAUDE.md`, `LICENSE-AGK`)
    and the project's own files raise no warning."""
    plugin = stub_plugin(tmp_path)
    kept = (".gitignore", "CLAUDE.md", "LICENSE-AGK", ".github/PULL_REQUEST_TEMPLATE.md")
    root = sample(tmp_path, files=(*kept, "src/app.py", "docs/specs/0001-x.md"))
    assert doctor.kit_in_repository_lines(root, plugin) == []


def test_req078_an_installed_sample_behaves_as_today(tmp_path):
    """REQ-078 AC7: an installed project holds the kit's files and gets no warning."""
    plugin = stub_plugin(tmp_path)
    root = sample(tmp_path, 'version = "9.9.9"\n', files=("scripts/agk/example_check.py",))
    assert doctor.kit_in_repository_lines(root, plugin) == []


def test_req078_an_unreadable_manifest_is_said_naming_the_path_class(tmp_path):
    """REQ-078 AC5: a clean project whose plugin manifest cannot be read is not silently clean."""
    plugin = stub_plugin(tmp_path)
    (plugin / "kit" / "manifest.json").write_text("{not json", encoding="utf-8")
    lines = doctor.kit_in_repository_lines(sample(tmp_path), plugin)
    assert lines == [
        "warn kit-in-repository: cannot be checked, the plugin's kit manifest cannot be read "
        "(path class: kit/manifest.json)"
    ]


# --- the grant at start -----------------------------------------------------------------------


def paused_run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT / "scripts" / "agk" / "doctor.py"), "--paused"],
        cwd=root,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(root)},
        check=False,
    )


GRANT = '[licence]\ngrant = "G-example-1"\nrepository = "example/product"\nvalid_until = {}\n'


@pytest.mark.parametrize("paused", [False, True])
def test_req078_a_session_warns_at_start_after_valid_until_and_stops_nothing(tmp_path, paused):
    """REQ-078 AC5: after `valid_until` the start check warns, naming the setting, and its one
    stdout line and exit stay as they are."""
    toml = ("paused = true\n" if paused else "") + GRANT.format("2020-01-01")
    proc = paused_run(sample(tmp_path, toml))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ("agk paused\n" if paused else "agk not paused\n")
    assert "warn licence-grant: the grant has ended (setting: [licence] valid_until)" in proc.stderr
    assert "2020-01-01" not in proc.stderr and "G-example-1" not in proc.stderr


@pytest.mark.parametrize("toml", [GRANT.format("2999-12-31"), 'version = "9.9.9"\n'])
def test_req078_a_current_or_absent_grant_says_nothing_at_start(tmp_path, toml):
    """REQ-078 AC5: a current grant, or no `[licence]` table (Q-S0071-3), adds nothing."""
    proc = paused_run(sample(tmp_path, toml))
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "agk not paused\n", "")


# --- the steward's guard ----------------------------------------------------------------------


def guard(plugin: Path, root: Path, tool: str, tool_input: dict) -> str | None:
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(root)}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(plugin / ".claude" / "hooks" / "steward_guard.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    if not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    [
        ("Write", {"file_path": "scripts/agk/example_check.py", "content": CONTENT}),
        ("Edit", {"file_path": "PRODUCT/Makefile", "old_string": "a", "new_string": CONTENT}),
        ("Bash", {"command": "cp /tmp/x.py scripts/agk/example_check.py"}),
        ("Bash", {"command": f"echo {CONTENT} > Makefile"}),
        ("Bash", {"command": "tee -a tests/kit/test_x.py < /tmp/x"}),
    ],
)
def test_req078_the_steward_guard_refuses_a_kit_file_written_into_the_product(
    tmp_path, tool, tool_input
):
    """REQ-078 AC5: a write of a manifest path into a clean product is denied, naming the rule and
    the path class, never the content."""
    plugin = stub_plugin(tmp_path)
    root = sample(tmp_path)
    if "file_path" in tool_input:
        named = tool_input["file_path"].replace("PRODUCT", str(root))
        tool_input = {**tool_input, "file_path": named}
    found = guard(plugin, root, tool, tool_input)
    assert found is not None and found.startswith("steward guard: SPEC-0071 rule 7 denies ")
    assert "(path class: " in found and CONTENT not in found


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    [
        ("Write", {"file_path": "docs/runs/note.md", "content": "x"}),
        ("Write", {"file_path": ".gitignore", "content": "x"}),
        ("Write", {"file_path": "CLAUDE.md", "content": "x"}),
        ("Bash", {"command": "cat scripts/agk/example_check.py"}),
        ("Bash", {"command": "grep -n x Makefile"}),
        ("Bash", {"command": 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/example_check.py"'}),
    ],
)
def test_req078_the_steward_guard_allows_the_projects_own_files_and_reads(
    tmp_path, tool, tool_input
):
    """REQ-078 AC5: the project's records, rule 2's kept files and a read of a kit path pass."""
    plugin = stub_plugin(tmp_path)
    assert guard(plugin, sample(tmp_path), tool, tool_input) is None


def test_req078_an_installed_project_keeps_todays_steward_guard(tmp_path):
    """REQ-078 AC7: in an installed project the kit's files are the project's, as today."""
    plugin = stub_plugin(tmp_path)
    root = sample(tmp_path, 'version = "9.9.9"\n')
    write = {"file_path": "scripts/agk/example_check.py", "content": "x"}
    assert guard(plugin, root, "Write", write) is None


def test_req078_the_steward_prompt_says_it_never_writes_kit_code_into_the_product():
    """REQ-078 AC5: the steward's role file carries rule 7's sentence."""
    text = (KIT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8")
    assert "never paste kit code into an issue, a pull request, a comment or a file" in text
    assert "SPEC-0071 rule 7" in text
