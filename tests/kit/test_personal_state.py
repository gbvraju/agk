"""SPEC-0041 build (c): personal mode's private state (brief #584).

`personal_state.py` gives one developer a private state folder under `AGK_HOME`, with an id, a
registry, `attach` and `detach`, and nothing written into the product repository: rules 1 to 4,
rule 27 (detach without the hook, the product-untouched test), rule 28 (the modes, no network
module) and rule 29 (the product's history and refs stay unchanged). Invented data only.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import personal_state as ps  # noqa: E402
import reviewers  # noqa: E402

PERSON = "demo-dev"
ORIGIN = "https://someone@Example.com/Team/Demo-App.git"
LAYOUT = {
    ".gitignore",
    "agk.toml",
    "constitution/principles.md",
    "config/core-rules.md",
    "config/review-checklist.md",
    "config/reviewers.yaml",
    "config/session-rules.md",
    "docs/requirements.md",
    "docs/adr/.gitkeep",
    "docs/briefs/.gitkeep",
    "docs/runs/decisions-log.md",
    "docs/specs/.gitkeep",
    "forge/.gitkeep",
    "metrics/.gitkeep",
    "records/.gitkeep",
    "test-map.toml",
}


def run_git(root: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout


def make_clone(path: Path, origin: str | None = ORIGIN) -> Path:
    path.mkdir(parents=True)
    run_git(path, "init", "-q", "-b", "main")
    run_git(path, "config", "user.email", "t@example.com")
    run_git(path, "config", "user.name", "t")
    run_git(path, "config", "commit.gpgsign", "false")
    (path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    run_git(path, "add", "-A")
    run_git(path, "commit", "-q", "-m", "initial")
    if origin:
        run_git(path, "remote", "add", "origin", origin)
    return path


def env_for(home: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "AGK_HOME")}
    env.update({"AGK_HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1"}, **extra)
    return env


def cli(clone: Path, home: Path, *args: str, env: dict | None = None, stdin: str | None = None):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "personal_state.py"), *args, "--clone", str(clone)],
        capture_output=True,
        text=True,
        input=stdin,
        env=env or env_for(home),
    )


def attach(clone: Path, home: Path, *extra: str, env: dict | None = None):
    return cli(clone, home, "attach", "--person", PERSON, *extra, env=env)


def git_files(clone: Path) -> dict[str, tuple[int, str]]:
    out = {}
    for path in sorted((clone / ".git").rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            out[path.relative_to(clone).as_posix()] = (len(data), hashlib.sha256(data).hexdigest())
    return out


def product_state(clone: Path) -> tuple:
    return (
        git_files(clone),
        run_git(clone, "status", "--porcelain"),
        run_git(clone, "for-each-ref"),
        run_git(clone, "log", "--all", "--format=%H"),
        sorted(p.relative_to(clone).as_posix() for p in clone.rglob("*") if ".git" not in p.parts),
    )


def sidecar_of(home: Path) -> Path:
    (sidecar,) = (home / "projects").iterdir()
    return sidecar


# Rule 1: the name and the setting.


def write_toml(root: Path, text: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "agk.toml").write_text(text, encoding="utf-8")
    return root


def test_rule1_only_forge_files_is_accepted_in_a_sidecar(tmp_path):
    """REQ-048 AC1: rule 1 (`files` accepted; `github`, absent and malformed refused)."""
    ok = write_toml(tmp_path / "ok", '[personal]\nforge = "files"\n')
    assert common.personal_table(ok) == {
        "forge": "files",
        "level": "light",
        "ai_disclosure": "both",
    }
    for name, text in (
        ("github", '[personal]\nforge = "github"\n'),
        ("absent", '[personal]\nlevel = "light"\n'),
        ("malformed", 'personal = "files-forge"\n'),
        ("number", "[personal]\nforge = 7\n"),
        ("unknown", '[personal]\nforge = "files"\nskip_floor = true\n'),
        ("level", '[personal]\nforge = "files"\nlevel = "lightest"\n'),
        ("disclosure", '[personal]\nforge = "files"\nai_disclosure = "none"\n'),
    ):
        with pytest.raises(common.CheckError) as err:
            common.personal_table(write_toml(tmp_path / name, text))
        message = str(err.value)
        assert "setting" in message, name
        for value in ("github", "files-forge", "lightest", "none", "7"):
            assert f"'{value}'" not in message and f'"{value}"' not in message, name


def test_rule1_a_repository_without_the_table_is_in_team_mode(tmp_path):
    """REQ-048 AC1: rule 1 (no `[personal]` table reads exactly as today)."""
    root = write_toml(tmp_path / "team", 'default_branch = "main"\n')
    assert common.personal_table(root) is None
    assert common.personal_table(tmp_path / "missing") is None
    assert common.load_config(root)["default_branch"] == "main"


def test_rule1_no_name_of_the_mode_or_the_setting_contains_local():
    """REQ-048 AC1: rule 1 ("local" means GitHub Actions is blocked)."""
    for name in (common.PERSONAL_TABLE, common.FORGE_SETTING, common.FORGE_FILES, "personal mode"):
        assert "local" not in name


def test_rule1_doctor_prints_the_personal_mode_line(tmp_path):
    """REQ-048 AC1: rule 1 (`doctor.py` on a sidecar; a malformed table names the setting)."""
    root = tmp_path / "side"
    make_clone(root, origin=None)
    write_toml(root, '[personal]\nforge = "files"\nlevel = "spec"\n')
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "doctor.py"), str(root)],
        capture_output=True,
        text=True,
        env=env_for(tmp_path / "home"),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "personal mode: forge files, level spec, disclosure both\n"
    write_toml(root, '[personal]\nforge = "github"\n')
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "doctor.py"), str(root)],
        capture_output=True,
        text=True,
        env=env_for(tmp_path / "home"),
    )
    assert proc.returncode == 1
    assert "forge" in proc.stdout and "github" not in proc.stdout


# Rule 2: the state outside the product.


def test_rule2_agk_home_from_the_setting_the_home_and_the_windows_profile(tmp_path):
    """REQ-048 AC1: rule 2 (`AGK_HOME`, else `~/.agk`, else `%USERPROFILE%\\.agk`)."""
    assert ps.agk_home({"AGK_HOME": str(tmp_path / "s")}, "posix") == tmp_path / "s"
    assert ps.agk_home({"HOME": str(tmp_path / "h")}, "posix") == tmp_path / "h" / ".agk"
    win = ps.agk_home({"USERPROFILE": str(tmp_path / "w")}, "nt")
    assert win == tmp_path / "w" / ".agk"
    with pytest.raises(common.CheckError, match="AGK_HOME"):
        ps.agk_home({}, "posix")


def test_rule2_attach_makes_the_sidecar_with_the_kit_layout(tmp_path):
    """REQ-048 AC1: rule 2 (the layout, `cache/` ignored, solo mode, one listed person)."""
    clone = make_clone(tmp_path / "Demo App")
    home = tmp_path / "state"
    proc = attach(clone, home)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    sidecar = sidecar_of(home)
    assert set(run_git(sidecar, "ls-files").split()) == LAYOUT
    assert (sidecar / "cache").is_dir()
    (sidecar / "cache" / "inventory.json").write_text("{}\n", encoding="utf-8")
    assert run_git(sidecar, "status", "--porcelain") == ""
    assert common.load_config(sidecar)["review_mode"] == "solo"
    assert common.personal_table(sidecar)["forge"] == "files"
    assert reviewers.solo_person(sidecar) == PERSON
    assert run_git(sidecar, "rev-list", "--count", "HEAD").strip() == "1"
    for rel in ("constitution/principles.md", "config/session-rules.md"):
        assert (sidecar / rel).read_bytes() == (SCRIPTS.parents[1] / rel).read_bytes()


def test_rule2_attach_with_agk_home_unset_uses_the_home(tmp_path):
    """REQ-048 AC1: rule 2 (`AGK_HOME` unset: a fake home)."""
    clone = make_clone(tmp_path / "demo")
    env = env_for(tmp_path / "unused")
    del env["AGK_HOME"]
    env["HOME"] = str(tmp_path / "fakehome")
    proc = attach(clone, tmp_path, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert sidecar_of(tmp_path / "fakehome" / ".agk").is_dir()


def test_rule2_the_five_file_checks_pass_in_the_sidecar(tmp_path):
    """REQ-048 AC1: rule 2 (the file checks run unchanged with the sidecar as their root)."""
    clone = make_clone(tmp_path / "demo")
    home = tmp_path / "state"
    assert attach(clone, home).returncode == 0
    sidecar = sidecar_of(home)
    brief = tmp_path / "brief.md"
    brief.write_text(
        'Sentence: "The demo app greets a visitor."\n\nAnswers:\n1. None.\n\n'
        "Advances: REQ-001\nTouches: app.py\nSize: S\n",
        encoding="utf-8",
    )
    runs = [
        ["check_requirements.py"],
        ["check_specs.py"],
        ["check_adrs.py"],
        ["check_numbers.py"],
        ["check_brief.py", str(brief), "--root", str(sidecar)],
    ]
    for args in runs:
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(SCRIPTS / args[0]), *args[1:]],
            cwd=sidecar,
            capture_output=True,
            text=True,
            env=env_for(home, AGK_BASE="HEAD"),
        )
        assert proc.returncode == 0, args[0] + proc.stdout + proc.stderr


# Rule 3: the project id and the registry.


def test_rule3_url_normalisation_and_slug():
    """REQ-048 AC1: rule 3 (scheme, credentials, `.git` and `/` removed, host lower-cased)."""
    assert ps.normalise_url(ORIGIN) == "example.com/Team/Demo-App"
    assert ps.normalise_url("git@Example.com:Team/demo.git/") == "example.com/Team/demo"
    assert ps.normalise_url("ssh://git@Example.com:22/Team/demo") == "example.com:22/Team/demo"
    assert ps.slug("example.com/Team/Demo_App.v2") == "demo-app-v2"
    assert ps.slug("Ünïcode !") == "n-code"
    assert ps.slug("___") == "project"


def test_rule3_the_id_of_a_clone_and_of_its_worktree(tmp_path):
    """REQ-048 AC1: rule 3 (`<slug>-<12 hex>` of the root commits; a worktree has the same id)."""
    clone = make_clone(tmp_path / "demo")
    root = run_git(clone, "rev-list", "--max-parents=0", "HEAD").strip()
    hex12 = hashlib.sha256(f"{root}\n".encode()).hexdigest()[:12]
    assert ps.project_id(clone) == f"demo-app-{hex12}"
    run_git(clone, "worktree", "add", "-q", str(tmp_path / "wt"), "-b", "other")
    assert ps.project_id(tmp_path / "wt") == ps.project_id(clone)
    assert ps.common_dir(tmp_path / "wt") == ps.common_dir(clone)
    bare = make_clone(tmp_path / "No Origin", origin=None)
    assert ps.project_id(bare).startswith("no-origin-")


def test_rule3_a_shallow_clone_takes_its_hex_from_the_normalised_url(tmp_path):
    """REQ-048 AC1: rule 3 (shallow: the hex over the normalised `origin`)."""
    source = make_clone(tmp_path / "source", origin=None)
    (source / "two.py").write_text("x = 2\n", encoding="utf-8")
    run_git(source, "add", "-A")
    run_git(source, "commit", "-q", "-m", "two")
    run_git(tmp_path, "clone", "-q", "--depth", "1", source.as_uri(), "shallow")
    shallow = tmp_path / "shallow"
    run_git(shallow, "remote", "set-url", "origin", ORIGIN)
    hex12 = hashlib.sha256(b"example.com/Team/Demo-App").hexdigest()[:12]
    assert ps.project_id(shallow) == f"demo-app-{hex12}"


def test_rule3_a_clone_with_no_commit_and_no_origin_is_refused(tmp_path):
    """REQ-048 AC1: rule 3 (refused naming the rule)."""
    empty = tmp_path / "empty"
    empty.mkdir()
    run_git(empty, "init", "-q")
    proc = attach(empty, tmp_path / "state")
    assert proc.returncode == 1
    assert "rule 3" in proc.stdout
    assert not (tmp_path / "state").exists()


def test_rule3_a_second_clone_with_the_same_id_asks_and_writes_nothing(tmp_path):
    """REQ-048 AC1: rule 3 and `Q-S0041-12` (share or a `-2` state, chosen by the person)."""
    home = tmp_path / "state"
    first = make_clone(tmp_path / "one")
    assert attach(first, home).returncode == 0
    second = tmp_path / "two"
    run_git(tmp_path, "clone", "-q", first.as_uri(), "two")
    run_git(second, "remote", "set-url", "origin", ORIGIN)
    registry = (home / "registry.toml").read_bytes()
    proc = attach(second, home)
    assert proc.returncode == 1
    assert "--share" in proc.stdout and "--new" in proc.stdout
    assert (home / "registry.toml").read_bytes() == registry
    assert len(list((home / "projects").iterdir())) == 1
    proc = attach(second, home, "--new")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ids = sorted(p.name for p in (home / "projects").iterdir())
    assert ids == [ps.project_id(first), ps.project_id(first) + "-2"]
    third = tmp_path / "three"
    run_git(tmp_path, "clone", "-q", first.as_uri(), "three")
    run_git(third, "remote", "set-url", "origin", ORIGIN)
    assert attach(third, home, "--share").returncode == 0
    assert ps.registry(home)[ps.common_dir(third)] == ps.project_id(first)
    assert len(list((home / "projects").iterdir())) == 2


def test_rule3_a_clone_with_agk_installed_is_refused(tmp_path):
    """REQ-048 AC1: rule 3 and `Q-S0041-18` (pointed to team mode)."""
    clone = make_clone(tmp_path / "demo")
    (clone / "agk.toml").write_text('version = "0.63.0"\n', encoding="utf-8")
    proc = attach(clone, tmp_path / "state")
    assert proc.returncode == 1
    assert "team mode" in proc.stdout
    assert not (tmp_path / "state").exists()


def test_rule3_attach_twice_is_one_state(tmp_path):
    """REQ-048 AC1: rule 3 (the registry maps the common dir once)."""
    clone = make_clone(tmp_path / "demo")
    home = tmp_path / "state"
    assert attach(clone, home).returncode == 0
    proc = attach(clone, home)
    assert proc.returncode == 0
    assert "already attached" in proc.stdout
    assert ps.registry(home) == {ps.common_dir(clone): ps.project_id(clone)}


# Rule 4: nothing in the clone.


def fake_git(tmp_path: Path) -> tuple[dict[str, str], Path]:
    """A `git` first on PATH that records its arguments and runs the real one."""
    real = shutil.which("git")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "git-calls.jsonl"
    script = bindir / "git"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        f"with open({str(log)!r}, 'a', encoding='utf-8') as f:\n"
        "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        f"os.execv({real!r}, [{real!r}, *sys.argv[1:]])\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return {"PATH": f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}"}, log


@pytest.mark.skipif(os.name == "nt", reason="the fake git is a POSIX script")
def test_rule4_every_git_call_on_the_clone_is_read_only(tmp_path):
    """REQ-048 AC1: rule 4 (`--no-optional-locks`, read-only, no `worktree add`)."""
    clone = make_clone(tmp_path / "demo")
    home = tmp_path / "state"
    extra, log = fake_git(tmp_path)
    env = env_for(home, **extra)
    assert attach(clone, home, env=env).returncode == 0
    assert cli(clone, home, "id", env=env).returncode == 0
    assert cli(clone, home, "detach", env=env).returncode == 0
    calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    on_clone = [c for c in calls if c[:2] == ["-C", str(clone)]]
    assert on_clone
    for call in on_clone:
        assert call[2] == "--no-optional-locks", call
        assert call[3] in ps.READ_ONLY, call
    assert not [c for c in calls if "worktree" in c]
    assert not [c for c in calls if c[:2] != ["-C", str(clone)] and str(clone) in " ".join(c)]


# Rule 27 in part: detach without the hook, and the product-untouched test.


def test_rule27_the_product_is_untouched_by_attach_and_detach(tmp_path):
    """REQ-048 AC1 AC8: rule 27 (status, every file under `.git/`, refs and history unchanged)."""
    clone = make_clone(tmp_path / "demo")
    home = tmp_path / "state"
    before = product_state(clone)
    assert attach(clone, home).returncode == 0
    assert product_state(clone) == before
    assert cli(clone, home, "id").returncode == 0
    assert cli(clone, home, "detach").returncode == 0
    assert product_state(clone) == before
    assert before[1] == ""


def test_rule27_detach_prints_export_first_and_removes_the_registry_entry(tmp_path):
    """REQ-048 AC1: rule 27 (the export line first; the state is kept without `--delete-state`)."""
    clone = make_clone(tmp_path / "demo")
    home = tmp_path / "state"
    assert attach(clone, home).returncode == 0
    proc = cli(clone, home, "detach")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines()[0] == ps.EXPORT_LINE
    assert ps.registry(home) == {}
    assert sidecar_of(home).is_dir()
    proc = cli(clone, home, "detach")
    assert proc.returncode == 1 and "not attached" in proc.stdout


class FakeTerminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_rule27_delete_state_needs_the_typed_id_at_a_terminal(tmp_path, monkeypatch, capsys):
    """REQ-048 AC1: rule 27 (refused in an agent session, without a terminal, on a wrong id)."""
    clone = make_clone(tmp_path / "demo")
    home = tmp_path / "state"
    assert attach(clone, home).returncode == 0
    pid = ps.project_id(clone)
    monkeypatch.setenv("AGK_HOME", str(home))
    args = ["detach", "--delete-state", "--clone", str(clone)]
    monkeypatch.setenv("CLAUDECODE", "1")
    assert ps.main(args, stdin=FakeTerminal(pid + "\n")) == 1
    assert "CLAUDECODE" in capsys.readouterr().out
    monkeypatch.delenv("CLAUDECODE")
    assert ps.main(args, stdin=io.StringIO(pid + "\n")) == 1
    assert "terminal" in capsys.readouterr().out
    assert ps.main(args, stdin=FakeTerminal("wrong-id\n")) == 1
    assert (home / "projects" / pid).is_dir() and ps.registry(home)
    assert ps.main(args, stdin=FakeTerminal(pid + "\n")) == 0
    assert not (home / "projects" / pid).exists()
    assert ps.registry(home) == {}


# Rule 28 in part: the modes and no network module.


@pytest.mark.skipif(os.name == "nt", reason="POSIX modes")
def test_rule28_the_state_is_0700_and_its_files_0600(tmp_path):
    """REQ-048 AC8: rule 28 (on POSIX `AGK_HOME` is 0700 and every file it writes 0600)."""
    clone = make_clone(tmp_path / "demo")
    home = tmp_path / "state"
    assert attach(clone, home).returncode == 0
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    for path in home.rglob("*"):
        if path.is_symlink():
            continue
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode & 0o077 == 0, path
        if path.is_file() and ".git" not in path.relative_to(home).parts:
            assert mode == 0o600, path


def test_rule28_personal_state_imports_no_network_module():
    """REQ-048 AC8: rule 28 (standard library only; no network module)."""
    tree = ast.parse((SCRIPTS / "personal_state.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    assert not names & {"socket", "http", "urllib", "ssl", "ftplib", "smtplib", "requests"}
    assert "CLAUDECODE" == ps.SESSION_SETTING


# Rule 29 in part: only the sidecar gains commits.


def test_rule29_only_the_sidecar_gains_commits(tmp_path):
    """REQ-048 AC4: rule 29 (the product's history and refs are unchanged; the sidecar commits)."""
    clone = make_clone(tmp_path / "demo")
    home = tmp_path / "state"
    refs = run_git(clone, "for-each-ref")
    history = run_git(clone, "log", "--all", "--format=%H %T")
    assert attach(clone, home).returncode == 0
    sidecar = sidecar_of(home)
    assert run_git(sidecar, "log", "--format=%s").strip() == ps.ATTACH_SUBJECT
    assert run_git(clone, "for-each-ref") == refs
    assert run_git(clone, "log", "--all", "--format=%H %T") == history
