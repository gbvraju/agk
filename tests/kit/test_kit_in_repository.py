"""Tests of SPEC-0071 rule 7 (brief #1458, ADR-0616; REQ-078 AC5): `doctor.py` warns
`kit-in-repository` for a kit manifest file in a clean project, naming the path class and never the
content; `doctor.py --paused` warns at start after `[licence] valid_until` and stops nothing; the
steward's guard refuses a write of a manifest path into the product and, by brief #1752
(ADR-0732), any write under a kit-only folder of the manifest's `snapshot`, a folder copy and an
unpacked archive.
A stub plugin root with its own `.claude-plugin/plugin.json` and `kit/manifest.json`; invented data
only; no network.
"""

from __future__ import annotations

import importlib.util
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
SNAPSHOT = [
    ".claude-plugin/",
    ".claude/agents/",
    ".claude/hooks/",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".gitignore",
    "CLAUDE.md",
    "Makefile",
    "config/",
    "kit/",
    "scripts/agk/",
    "skills/",
    "tests/kit/",
]
TEMPLATES = {
    "config/example.txt": "kit/templates/example.txt",
    "agk.toml": "kit/templates/agk.toml",
}


def stub_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"version": "9.9.9"}\n', "utf-8")
    (plugin / "kit").mkdir()
    manifest = {
        "kit_version": "9.9.9",
        "kit_tests": "tests/kit",
        "verbatim": VERBATIM,
        "templates": TEMPLATES,
        "snapshot": SNAPSHOT,
    }
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
        ("Bash", {"command": "cat a.py > scripts/agk/example_check.py"}),
        ("Bash", {"command": "git show HEAD:x >scripts/agk/example_check.py"}),
        ("Bash", {"command": "grep -h x a.md 2>&1 >> Makefile"}),
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
        ("Bash", {"command": "cat < Makefile > docs/runs/copy.txt 2>&1"}),
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


def test_req078_the_doctor_and_the_guard_keep_the_same_files():
    """REQ-078 AC5: rule 2's kept files are written twice; the two lists cannot drift apart."""
    spec = importlib.util.spec_from_file_location("steward_guard_kept", GUARD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.KEEPS == doctor.CLEAN_KEEPS
    assert module.KEEPS_UNDER == doctor.CLEAN_KEEPS_UNDER


# --- brief #1752: every kit folder, a folder copy and an unpacked archive (ADR-0732) -------------

KIT_ONLY = ("scripts/agk/", ".claude/agents/", "skills/", "tests/kit/", "kit/")


def load_guard():
    spec = importlib.util.spec_from_file_location("steward_guard_folders", GUARD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def kit_case(plugin: Path, case: tuple[str, dict]) -> tuple[str, dict]:
    tool, tool_input = case
    return tool, {k: v.replace("PLUGIN", str(plugin)) for k, v in tool_input.items()}


FOUND_ALLOWED = [
    ("Bash", {"command": "cp -r PLUGIN/scripts/agk scripts/"}),
    ("Bash", {"command": "cp -R PLUGIN/scripts/agk scripts"}),
    ("Bash", {"command": "cp -a PLUGIN/scripts/agk ./scripts/"}),
    ("Bash", {"command": "rsync -a PLUGIN/scripts/ scripts/"}),
    ("Bash", {"command": "tar -C PLUGIN -cf - scripts/agk | tar -xf -"}),
    ("Bash", {"command": "mkdir -p scripts/agk && cp PLUGIN/scripts/agk/common.py scripts/agk/"}),
    ("Bash", {"command": "cp -r PLUGIN/.claude/agents .claude/"}),
    ("Write", {"file_path": "scripts/agk/x.py", "content": CONTENT}),
    ("Write", {"file_path": "scripts/agk/gates/new.py", "content": CONTENT}),
    ("Write", {"file_path": "skills/brief/SKILL.md", "content": CONTENT}),
]


@pytest.mark.parametrize("case", FOUND_ALLOWED)
def test_req078_the_guard_refuses_kit_code_the_test_report_found_allowed(tmp_path, case):
    """REQ-078 AC5 (brief #1752 answers 2 and 3): each of the test report's 10 allowed cases is
    denied, naming the rule and a kit-only folder as the path class, never the content."""
    plugin = stub_plugin(tmp_path)
    found = guard(plugin, sample(tmp_path), *kit_case(plugin, case))
    assert found is not None and found.startswith("steward guard: SPEC-0071 rule 7 denies ")
    assert "(path class: " in found and CONTENT not in found
    named = found.split("(path class: ", 1)[1].rstrip(")").split(", ")
    assert named and all(
        n in KIT_ONLY or n == ".claude/hooks/" or n == ".claude-plugin/" for n in named
    )


@pytest.mark.parametrize(
    "case",
    [
        ("Bash", {"command": "cp -r /tmp/x ."}),
        ("Bash", {"command": "mkdir -p scripts/agk"}),
        ("Bash", {"command": "curl -o scripts/agk/x.py https://example.com/x.py"}),
        ("Bash", {"command": "touch scripts\\\\agk\\\\x.py"}),
        ("Write", {"file_path": "scripts\\agk\\x.py", "content": CONTENT}),
        ("Bash", {"command": "unzip -q /tmp/k.zip -d skills"}),
        ("Bash", {"command": "unzip /tmp/k.zip"}),
        ("Bash", {"command": "tar xzf /tmp/k.tgz -C scripts"}),
        ("Bash", {"command": "7z x /tmp/k.7z -o."}),
        ("Bash", {"command": "cpio -idm < /tmp/k.cpio"}),
        ("Bash", {"command": "cp -t scripts/ -r PLUGIN/scripts/agk"}),
        ("Bash", {"command": "cp PLUGIN/scripts/agk/common.py PLUGIN/kit/x.json kit"}),
        ("Bash", {"command": "git checkout HEAD~1 -- scripts/agk"}),
        ("Bash", {"command": "git restore --source=HEAD~1 skills/brief"}),
        ("Bash", {"command": "gh release download v1 -D scripts/agk"}),
    ],
)
def test_req078_the_guard_refuses_the_brief_edge_cases(tmp_path, case):
    """REQ-078 AC5 (brief #1752 answers 2, 3 and 7, Q-A-1's conservative reading): a recursive
    copy into a folder that holds a kit folder, a word under one, a back slash path, an unpack and
    the three git and gh forms are denied."""
    plugin = stub_plugin(tmp_path)
    root = sample(tmp_path)
    found = guard(plugin, root, *kit_case(plugin, case))
    assert found is not None and found.startswith("steward guard: SPEC-0071 rule 7 denies ")


@pytest.mark.parametrize(
    "case",
    [
        ("Bash", {"command": "cp /tmp/notes.md docs/"}),
        ("Bash", {"command": "cp notes.md ."}),
        ("Bash", {"command": "cp -r docs/a docs/b"}),
        ("Bash", {"command": 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/steward.py" status'}),
        ("Bash", {"command": "cp -r PLUGIN/scripts/agk /tmp/copy-example"}),
        ("Bash", {"command": "tar -xf /tmp/k.tar -C docs/runs"}),
        ("Bash", {"command": "git checkout -- docs/a.md && git status"}),
    ],
)
def test_req078_the_guard_still_allows_the_projects_own_copies(tmp_path, case):
    """REQ-078 AC5 (brief #1752 answer 4): a single file to `docs/` or the root, a recursive copy
    between the project's own folders, the steward's scripts from the plugin and a copy out of the
    project pass."""
    plugin = stub_plugin(tmp_path)
    assert guard(plugin, sample(tmp_path), *kit_case(plugin, case)) is None


@pytest.mark.parametrize(
    "command", ["cp -r /tmp/x .", "rsync -a /tmp/x/ scripts/", "tar -xf /tmp/k.tar"]
)
def test_req078_a_manifest_without_snapshot_denies_a_recursive_copy(tmp_path, command):
    """REQ-078 AC5 (brief #1752 answer 5): with no `snapshot` list the guard cannot check, so a
    recursive copy or an unpack into the project is denied naming `kit/manifest.json`."""
    plugin = stub_plugin(tmp_path)
    manifest = {"kit_version": "9.9.9", "kit_tests": "tests/kit", "verbatim": VERBATIM}
    (plugin / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    found = guard(plugin, sample(tmp_path), "Bash", {"command": command})
    assert found == (
        "steward guard: SPEC-0071 rule 7 denies a write it cannot check "
        "(path class: kit/manifest.json)"
    )


@pytest.mark.parametrize("case", FOUND_ALLOWED[:3] + FOUND_ALLOWED[7:8])
def test_req078_an_installed_project_keeps_todays_guard_for_folder_copies(tmp_path, case):
    """REQ-078 AC7 (brief #1752 answer 5): without `[kit] layout = "plugin"` nothing changes."""
    plugin = stub_plugin(tmp_path)
    root = sample(tmp_path, 'version = "9.9.9"\n')
    assert guard(plugin, root, *kit_case(plugin, case)) is None


def test_req078_the_kit_only_folders_of_the_kits_own_manifest():
    """REQ-078 AC5 (brief #1752 answer 1): derived from `snapshot`, never a fixed list; a manifest
    change that moves a folder shows here."""
    manifest = json.loads((KIT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(load_guard().kit_only_folders(manifest)) == [
        ".claude-plugin/",
        ".claude/agents/",
        ".claude/hooks/",
        "kit/",
        "scripts/agk/",
        "skills/",
        "tests/kit/",
    ]
