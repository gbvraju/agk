"""Parity: every discipline of the kit reaches a project (brief #680, ADR-0326; REQ-020).

`scripts/agk/parity.py report` lists each kit discipline (each `scripts/agk/*.py`, each
`.claude/agents/*.md`, each file directly under `config/`, each `docs/runs/` log that an agent
file names) with how a project gets it: `installed` (kit/manifest.json), `plugin` (a skill runs
it from the plugin root, or a script the plugin runs imports it) or `kit-only (<reason>)` from
`config/kit-only.txt`. `parity.py check` fails naming each discipline in none of the three, and
each line of the list that is stale, unreasoned, duplicated or names nothing. The list may only
shrink. Fixture trees only; no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "parity.py"

# The exception list may only shrink: lower this number in the pull request that removes a line.
KIT_ONLY_CEILING = 15


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def kit(tmp_path: Path, kit_only: str = "") -> Path:
    """A kit tree: one installed script, one the plugin runs, its module, one kit-only script."""
    manifest = {
        "kit_version": "0.0.1",
        "verbatim": [".claude/agents/a.md", "config/rules.md", "scripts/agk/check_x.py"],
        "experimental": [],
        "templates": {"docs/runs/log.md": "kit/templates/log.md", "config/list.txt": "k/l"},
        "rendered": [],
        "adopt": {"templates": {}},
    }
    write(tmp_path, "kit/manifest.json", json.dumps(manifest))
    write(tmp_path, "scripts/agk/check_x.py", 'LOG = "docs/runs/amend-"\n')
    write(tmp_path, "scripts/agk/run.py", "import helper\nfrom common import thing\n")
    write(tmp_path, "scripts/agk/helper.py", "X = 1\n")
    write(tmp_path, "scripts/agk/release.py", "Y = 2\n")
    write(tmp_path, "skills/run/SKILL.md", 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/run.py" .\n')
    write(
        tmp_path,
        ".claude/agents/a.md",
        "Keep `docs/runs/log.md`, `docs/runs/catches-N.md` and "
        "`docs/runs/amend-<n>.md`.\n",
    )
    write(tmp_path, "config/rules.md", "1. One.\n")
    write(tmp_path, "config/list.txt", "x\n")
    write(tmp_path, "config/kit-only.txt", kit_only)
    return tmp_path


FULL = (
    "# the exceptions\n"
    "scripts/agk/release.py builds the kit's own releases\n"
    "docs/runs/catches-*.md the kit's own incident log\n"
    "config/kit-only.txt this list, read only where kit/manifest.json is\n"
)


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_req020_report_names_how_a_project_gets_each_discipline(tmp_path):
    """REQ-020: brief #680 answer 1: installed, plugin (with its imports) or kit-only (reason)."""
    proc = run(kit(tmp_path, FULL), "report")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        ".claude/agents/a.md installed",
        "config/kit-only.txt kit-only (this list, read only where kit/manifest.json is)",
        "config/list.txt installed",
        "config/rules.md installed",
        "docs/runs/amend-*.md installed",
        "docs/runs/catches-*.md kit-only (the kit's own incident log)",
        "docs/runs/log.md installed",
        "scripts/agk/check_x.py installed",
        "scripts/agk/helper.py plugin",
        "scripts/agk/release.py kit-only (builds the kit's own releases)",
        "scripts/agk/run.py plugin",
    ]


def test_req020_check_passes_when_every_discipline_reaches_a_project(tmp_path):
    """REQ-020: brief #680 answer 1."""
    proc = run(kit(tmp_path, FULL), "check")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == "parity: 11 disciplines; 8 reach a project, 3 kit-only"


def test_req020_check_fails_naming_each_discipline_in_none_of_the_three(tmp_path):
    """REQ-020: brief #680 answer 1: a kit discipline in none of the three fails, naming it."""
    root = kit(tmp_path, "config/kit-only.txt this list\n")
    proc = run(root, "check")
    assert proc.returncode == 1
    out = proc.stdout
    assert "scripts/agk/release.py reaches no project" in out
    assert "docs/runs/catches-*.md reaches no project" in out
    assert "config/kit-only.txt" in out  # the fix names the list
    assert "helper.py" not in out and "run.py" not in out


def test_req020_check_fails_on_a_stale_unreasoned_duplicate_or_missing_line(tmp_path):
    """REQ-020: brief #680 answer 2: one line per exception, each with its reason."""
    lines = FULL + (
        "scripts/agk/check_x.py stale: it is installed\n"
        "scripts/agk/run.py stale: the plugin runs it\n"
        "scripts/agk/gone.py names nothing\n"
        "scripts/agk/release.py a second line\n"
        "config/rules.md\n"
    )
    proc = run(kit(tmp_path, lines), "check")
    assert proc.returncode == 1
    out = proc.stdout
    assert "scripts/agk/check_x.py is installed: remove its line" in out
    assert "scripts/agk/run.py reaches a project through the plugin: remove its line" in out
    assert "scripts/agk/gone.py names no kit discipline" in out
    assert "scripts/agk/release.py is listed twice" in out
    assert "config/rules.md has no reason" in out


def test_req020_every_file_under_config_and_every_agent_file_is_a_discipline(tmp_path):
    """REQ-020: brief #680 answer 1: each agent file and each config file the checks read."""
    root = kit(tmp_path, FULL)
    write(root, ".claude/agents/b.md", "No log here.\n")
    write(root, "config/baseline.txt", "1\n")
    out = run(root, "check").stdout
    assert ".claude/agents/b.md reaches no project" in out
    assert "config/baseline.txt reaches no project" in out


def test_req020_a_tree_without_a_manifest_has_nothing_to_check(tmp_path):
    """REQ-020: an installed project has no kit/manifest.json; the check passes and says so."""
    write(tmp_path, "scripts/agk/parity.py", "")
    proc = run(tmp_path, "check")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "parity: no kit/manifest.json; nothing to check"


def test_req020_this_repository_passes_the_check():
    """REQ-020: brief #680 answer 1: every discipline of this kit reaches a project or is listed."""
    proc = run(ROOT, "check")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_req020_the_exception_list_may_only_shrink():
    """REQ-020: brief #680 answer 2 (as the rule budget, ADR-0310): the count only goes down."""
    sys.path.insert(0, str(SCRIPT.parent))
    from parity import read_kit_only

    count = len(read_kit_only(ROOT / "config" / "kit-only.txt"))
    assert count <= KIT_ONLY_CEILING, "an exception was added: install it or ship it instead"
    assert count == KIT_ONLY_CEILING, "an exception was removed: lower KIT_ONLY_CEILING"


def test_req020_parity_is_installed_and_mapped():
    """REQ-020: a new installed script is in the manifest (sorted) and in the testing map."""
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/parity.py" in manifest["verbatim"]
    assert manifest["verbatim"] == sorted(manifest["verbatim"])
    cfg = tomllib.loads((ROOT / "agk.toml").read_text(encoding="utf-8"))
    entry = [e for e in cfg["testing"]["map"] if e["code"] == "scripts/agk/parity.py"]
    assert entry and "tests/kit/test_parity.py" in entry[0]["tests"]
    source = SCRIPT.read_text(encoding="utf-8")
    for word in ("urllib", "socket", "http.client", "requests"):
        assert word not in source, word
