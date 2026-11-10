"""The smoke run after a merge, chosen by what changed (SPEC-0044 rule 8, brief #923, build (c) of
REQ-051).

`smoke.py [--base REF] [--head REF] [--run]` reads the changed paths (by default of the last merge
on the default branch) and prints one line with its choice and the reason: one kind of
`[testing] smoke` when every changed file outside documentation matches that kind's `code`, the
full smoke (`project_tests`) for anything else, and nothing for documentation only. `--run` runs the
choice under the heavy-step lock. Small git repositories in `tmp_path`, stub commands, invented
data only (example.com), no network.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import impact
import pytest
import smoke
from common import CheckError

SMOKE = (
    "[testing]\n"
    'always_full = ["web/vite.config.ts"]\n'
    "smoke = [\n"
    '  { kind = "frontend", code = ["web/**"], command = "echo frontend-smoke" },\n'
    '  { kind = "contract", code = ["contracts/**", "mocks/**"], command = "echo contract" },\n'
    "]\n"
)


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def project(tmp_path: Path, testing: str | None = SMOKE, extra: str = "") -> Path:
    """An invented project on `main` with one commit; returns its root."""
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    text = 'default_branch = "main"\nproject_tests = "echo full-smoke"\n' + extra
    if testing is not None:
        text += testing
    (root / "agk.toml").write_text(text, encoding="utf-8")
    (root / "README.md").write_text("Invented project, see https://example.com\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "builder@example.com")
    git(root, "config", "user.name", "Builder")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def merge(root: Path, *paths: str) -> str:
    """Commit PATHS on `main` as one merge would land; returns the commit before it."""
    before = git(root, "rev-parse", "HEAD")
    for rel in paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"invented {rel}\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "an invented change (#1)")
    return before


def choose(root: Path, monkeypatch, capsys, *args: str) -> tuple[int, str]:
    monkeypatch.chdir(root)
    code = smoke.main(list(args))
    return code, capsys.readouterr().out


@pytest.mark.parametrize(
    ("paths", "kind"),
    [
        (("web/src/App.tsx", "web/src/App.test.tsx"), "frontend"),
        (("contracts/orders.json",), "contract"),
        (("mocks/orders.json",), "contract"),
        (("web/src/App.tsx", "docs/guide.md"), "frontend"),
    ],
)
def test_one_kind_picks_that_kind(tmp_path, monkeypatch, capsys, paths, kind):
    """REQ-051 AC4: SPEC-0044 rule 8 (front-end only, contract only and mock only pick one kind)."""
    root = project(tmp_path)
    base = merge(root, *paths)
    code, out = choose(root, monkeypatch, capsys, "--base", base, "--head", "HEAD")
    assert code == 0
    lines = out.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith(f"smoke: {kind}: ")


@pytest.mark.parametrize(
    ("paths", "reason"),
    [
        (("web/src/App.tsx", "contracts/orders.json"), "two kinds"),
        (("app/orders.py",), "app/orders.py"),
        (("web/src/App.tsx", "web/vite.config.ts"), "always_full"),
    ],
)
def test_other_changes_pick_the_full_smoke(tmp_path, monkeypatch, capsys, paths, reason):
    """REQ-051 AC4: SPEC-0044 rule 8 (two kinds, a back-end file, an always_full file: full)."""
    root = project(tmp_path)
    base = merge(root, *paths)
    code, out = choose(root, monkeypatch, capsys, "--base", base, "--head", "HEAD")
    assert code == 0
    assert out.splitlines()[0].startswith("smoke: full: ")
    assert reason in out


def test_documentation_only_picks_nothing(tmp_path, monkeypatch, capsys):
    """REQ-051 AC4: SPEC-0044 rule 8 and Q-S0044-3 (documentation only: nothing runs)."""
    root = project(tmp_path)
    base = merge(root, "docs/guide.md", "NOTES.md")
    code, out = choose(root, monkeypatch, capsys, "--base", base, "--head", "HEAD", "--run")
    assert code == 0
    assert out.splitlines() == ["smoke: none: only documentation changed (2 files)"]


def test_without_a_smoke_list_the_full_smoke_is_chosen(tmp_path, monkeypatch, capsys):
    """REQ-051 AC4: SPEC-0044 rules 1 and 8 (no `[testing] smoke`: the full smoke, as today)."""
    root = project(tmp_path, testing=None)
    base = merge(root, "web/src/App.tsx")
    code, out = choose(root, monkeypatch, capsys, "--base", base, "--head", "HEAD")
    assert code == 0
    assert out.splitlines() == ["smoke: full: no [testing] smoke list (setting: testing.smoke)"]


def test_the_default_range_is_the_last_merge_on_the_default_branch(tmp_path, monkeypatch, capsys):
    """REQ-051 AC4: SPEC-0044 rule 8 (without --base and --head: the last merge, from local git)."""
    root = project(tmp_path)
    merge(root, "app/orders.py")
    merge(root, "contracts/orders.json")
    git(root, "checkout", "-q", "-b", "elsewhere")
    merge(root, "app/other.py")
    code, out = choose(root, monkeypatch, capsys)
    assert code == 0
    assert out.splitlines()[0].startswith("smoke: contract: ")


@pytest.mark.parametrize(
    "value",
    [
        '"web/**"',
        '[{ kind = "backend", code = ["web/**"], command = "echo invented" }]',
        '[{ kind = "frontend", code = [], command = "echo invented" }]',
        '[{ kind = "frontend", code = ["web/**"], command = " " }]',
        '[{ kind = "frontend", code = ["web/**"] }]',
        '[{ kind = "frontend", code = ["web/**"], command = "echo invented", extra = 1 }]',
        '[{ kind = "frontend", code = ["/web/**"], command = "echo invented" }]',
    ],
)
def test_a_bad_smoke_value_is_refused_naming_the_setting(tmp_path, monkeypatch, capsys, value):
    """REQ-051 AC4: brief #923 answer 3 (a bad `smoke` is refused naming the setting, never the
    value)."""
    root = project(tmp_path, testing=f"[testing]\nsmoke = {value}\n")
    with pytest.raises(CheckError) as caught:
        impact.testing_table(root)
    assert "setting: testing.smoke" in str(caught.value)
    assert "invented" not in str(caught.value) and "backend" not in str(caught.value)
    base = merge(root, "web/src/App.tsx")
    code, out = choose(root, monkeypatch, capsys, "--base", base, "--head", "HEAD")
    assert code == 2
    assert "setting: testing.smoke" in out and "invented" not in out


def test_a_good_smoke_list_is_accepted_by_the_testing_reader(tmp_path):
    """REQ-051 AC4: brief #923 answer 3 (the `[testing]` reader accepts the `smoke` key)."""
    root = project(tmp_path)
    assert impact.testing_table(root) is not None
    assert [e["kind"] for e in impact.smoke_entries(root)] == ["frontend", "contract"]


def test_the_regression_selection_does_not_change(tmp_path):
    """REQ-051 AC4: SPEC-0044 rules 1 and 8 (a smoke list changes no regression selection)."""
    listed = '[testing]\nsmoke = [{ kind = "frontend", code = ["web/**"], command = "echo f" }]\n'
    found = []
    for name, testing in (("plain", "[testing]\n"), ("listed", listed)):
        root = project(tmp_path / name, testing=testing)
        base = merge(root, "web/src/App.tsx", "app/orders.py")
        found.append(impact.select(root, base, "HEAD").data())
    assert found[0] == found[1]


def stub(tmp_path: Path) -> str:
    """A stub command that writes the lock it ran under; no real suite runs."""
    script = tmp_path / "stub.py"
    out = tmp_path / "ran.json"
    script.write_text(
        "import json, os, sys\n"
        f"open({str(out)!r}, 'w').write(json.dumps({{'argv': sys.argv[1:], "
        "'lock': os.environ.get('AGK_LOCK_NAME'), "
        "'slot': bool(os.environ.get('AGK_LOCK_TOKEN'))}))\n",
        encoding="utf-8",
    )
    return f"{sys.executable} {script}"


def test_run_takes_the_heavy_lock(tmp_path, monkeypatch, capsys):
    """REQ-051 AC4: SPEC-0044 rule 8 (`--run` runs the choice under the heavy-step lock)."""
    locks = tmp_path / "locks"
    command = stub(tmp_path)
    testing = (
        "[testing]\nsmoke = [\n"
        f'  {{ kind = "contract", code = ["contracts/**"], command = "{command} contract" }},\n'
        "]\n"
    )
    root = project(tmp_path, testing=testing, extra=f"lock_dir = '{locks.as_posix()}'\n")
    base = merge(root, "contracts/orders.json")
    code, out = choose(root, monkeypatch, capsys, "--base", base, "--head", "HEAD", "--run")
    assert code == 0, out
    assert out.splitlines()[0].startswith("smoke: contract: ")
    ran = json.loads((tmp_path / "ran.json").read_text(encoding="utf-8"))
    assert ran == {"argv": ["contract"], "lock": "heavy", "slot": True}


def test_run_returns_the_command_exit_code(tmp_path, monkeypatch, capsys):
    """REQ-051 AC4: SPEC-0044 rule 8 (`--run` ends with the chosen command's exit code)."""
    locks = tmp_path / "locks"
    testing = '[testing]\nsmoke = [{ kind = "frontend", code = ["web/**"], command = "exit 3" }]\n'
    root = project(tmp_path, testing=testing, extra=f"lock_dir = '{locks.as_posix()}'\n")
    base = merge(root, "web/src/App.tsx")
    code, _ = choose(root, monkeypatch, capsys, "--base", base, "--head", "HEAD", "--run")
    assert code == 3


def test_a_usage_error_exits_two(tmp_path, monkeypatch, capsys):
    """REQ-051 AC4: brief #923 answer 1 (the options are --base, --head and --run)."""
    root = project(tmp_path)
    code, out = choose(root, monkeypatch, capsys, "--everything")
    assert code == 2
    assert "usage: smoke.py" in out
