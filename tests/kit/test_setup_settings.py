"""/agk:setup build (b): at most five plain questions with a recommendation, and the project
settings proposed as one change with its ADR on a new branch (brief #1461, SPEC-0065 rules 4, 5,
9, 11 and 16, ADR-0619; REQ-072).

A fake machine read, saved GitHub answers and a scratch git repository with no remote; no network,
no model, no install. Invented names of example.com only.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess  # nosec B404 - the tests' own scratch repository, fixed argument lists
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("agk_setup_b", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(setup)
import steward_owner  # noqa: E402

SKILL = ROOT / "skills" / "setup" / "SKILL.md"
TOOLS = {"python": "3.12.1", "git": "2.43.0", "gh": "2.50.0", "claude": "2.1.0", "node": "20.11.0"}
SECRET = re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}|github_pat_|password\s*[=:]", re.IGNORECASE)
SET = 'execution = "local"\nreview_mode = "solo"\npr_mode = "flow"\n'
SET += '[flow]\nmax_builders = 2\nbuilder_memory_gb = 3\n'
SET += 'launch_adapter = "bash scripts/start-session-local.sh"\n'
SET += '[autopilot]\nmode = "assist"\n'


def machine(**over) -> dict:
    found = {
        "os": "Linux", "os_version": "6.1", "wsl": "absent", "memory_total_gb": 16,
        "memory_available_gb": 12, "cores": 8, "disk_free_gb": 100, "admin": False,
        "tools": dict(TOOLS, podman="4.9.3", docker=None), "winget": "absent",
        "proxy": "none", "remote": "example-org/example-project",
    }  # fmt: skip
    return found | over


def git(root: Path, *args: str) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, the scratch repository
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


WHO = ("-c", "user.email=member-example-1@example.com", "-c", "user.name=member-example-1")


def project(tmp_path: Path, toml: str = "", files=()) -> Path:
    """A scratch clone whose `origin` is a bare repository beside it: no network."""
    root = tmp_path / "project"
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    (root / "docs" / "adr" / "0001-example.md").write_text("# ADR-0001\n", encoding="utf-8")
    for name in files:
        (root / name).write_text("example\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "-c", "user.email=member-example-1@example.com", "-c", "user.name=member-example-1",
        "add", ".")  # fmt: skip
    git(root, "-c", "user.email=member-example-1@example.com", "-c", "user.name=member-example-1",
        "commit", "-q", "-m", "example")  # fmt: skip
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", str(origin))
    git(root, "remote", "add", "origin", str(origin))
    git(root, "push", "-q", "origin", "main")
    git(root, "fetch", "-q", "origin")
    return root


def run(root, capsys, form, fake=None, extra=()):
    m, g = root.parent / "machine.json", root.parent / "github.json"
    m.write_text(json.dumps(fake or machine()), encoding="utf-8")
    g.write_text(json.dumps({"lease": "free", "running": 0}), encoding="utf-8")
    args = [form, "--machine", str(m), "--github", str(g), "--root", str(root), *extra]
    code = setup.main(args)
    return code, capsys.readouterr().out


def asked(root, capsys, fake=None) -> list[dict]:
    code, out = run(root, capsys, "ask", fake, ["--json"])
    assert code == 0
    return json.loads(out)["questions"]


def answers(*pairs: str) -> list[str]:
    return [x for p in pairs for x in ("--answer", p)]


def files_of(root: Path) -> dict:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


def test_ac2_what_the_machine_and_the_project_tell_is_never_asked(tmp_path, capsys):
    """REQ-072 AC2: rules 3 and 4: memory, OS, WSL, engine and settings readable: no question."""
    assert asked(project(tmp_path, SET, ("Containerfile",)), capsys) == []


def test_ac2_an_unset_review_mode_asks_one_plain_question(tmp_path, capsys):
    """REQ-072 AC2: rule 4: one plain question with a recommendation and no kit term."""
    found = asked(project(tmp_path, SET.replace('review_mode = "solo"\n', "")), capsys)
    assert [q["id"] for q in found] == ["team"]
    assert steward_owner.question_problem(found[0]["text"]) is None
    assert found[0]["recommend"] in found[0]["choices"]


def test_ac2_at_most_five_questions_each_plain(tmp_path, capsys):
    """REQ-072 AC2: rule 4: a bare Windows machine of a bare project hears five, no more."""
    fake = machine(os="Windows", os_version="11", wsl="present", admin=True,
                   tools=dict(TOOLS, podman=None, docker=None))  # fmt: skip
    found = asked(project(tmp_path, "", ("Containerfile",)), capsys, fake)
    assert [q["id"] for q in found] == ["where", "team", "autopilot", "engine", "windows"]
    for q in found:
        assert steward_owner.question_problem(q["text"]) is None, q["id"]
        assert q["recommend"] in q["choices"]
    assert next(q for q in found if q["id"] == "windows")["recommend"] == "wsl"
    assert next(q for q in found if q["id"] == "engine")["recommend"] == "podman"


def test_ac2_the_setting_is_named_only_in_the_plans_last_line(tmp_path, capsys):
    """REQ-072 AC2: rules 4 and 5: the plan of at most eight lines ends with the settings."""
    root = project(tmp_path)
    code, out = run(root, capsys, "plan", extra=answers("where=local", "team=solo"))
    plan = out.split("\n\n")[0].splitlines()
    assert code == 0 and plan[0] == "Plan:" and len(plan) - 1 <= 8
    assert 'execution = "local"' in plan[-1] and 'review_mode = "solo"' in plan[-1]
    assert not any("execution = " in line for line in plan[:-1])
    _, out = run(root, capsys, "ask")
    assert "execution" not in out and "review_mode" not in out


def test_ac2_anything_but_a_yes_writes_nothing(tmp_path, capsys):
    """REQ-072 AC2, AC5: rule 5: without the person's yes the settings form changes nothing."""
    root = project(tmp_path)
    before, head = files_of(root), git(root, "rev-parse", "HEAD")
    code, out = run(root, capsys, "settings", extra=answers("where=local"))
    assert code == 1 and "yes" in out
    assert files_of(root) == before and git(root, "branch", "--show-current") == "main"
    assert git(root, "rev-parse", "HEAD") == head


def test_ac5_the_settings_go_on_a_new_branch_with_an_adr_never_committed(tmp_path, capsys):
    """REQ-072 AC5: rule 9: one change and its ADR on a new branch; no commit, no push."""
    root = project(tmp_path, 'review_mode = "team"\n')
    head = git(root, "rev-parse", "HEAD")
    extra = ["--yes", "--date", "2026-11-17", *answers("where=local", "autopilot=assist")]
    code, out = run(root, capsys, "settings", extra=extra)
    assert code == 0, out
    assert git(root, "branch", "--show-current") == "agk/setup-settings-2026-11-17"
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "rev-list", "--count", "HEAD") == "1"
    assert git(root, "show", "main:agk.toml") == 'review_mode = "team"'
    config = setup.tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    assert config["execution"] == "local" and config["review_mode"] == "team"
    assert config["pr_mode"] == "flow"  # 2 builders under one login (the study's finding)
    assert config["flow"]["builder_memory_gb"] == 3 and config["autopilot"]["mode"] == "assist"
    assert "max_builders" not in config["flow"]  # a team's cap is not one machine's figure
    assert "# [models.names]" in (root / "agk.toml").read_text(encoding="utf-8")
    adr = sorted((root / "docs" / "adr").glob("0002-*.md"))
    assert len(adr) == 1
    text = adr[0].read_text(encoding="utf-8")
    assert "- Status: Proposed" in text and "`agk.toml`" in text and 'execution = "local"' in text
    status = git(root, "status", "--porcelain")
    assert set(status.split()) >= {"M", "agk.toml", "??"}
    assert "git push" in out and "prepush.py --record" in out


def test_ac5_a_setting_already_equal_is_not_proposed(tmp_path, capsys):
    """REQ-072 AC5: rule 9: equal settings are left out; all equal, no branch and no change."""
    root = project(tmp_path, SET)
    before = files_of(root)
    extra = ["--yes", *answers("where=local", "team=solo", "autopilot=on")]
    code, out = run(root, capsys, "settings", extra=extra)
    assert code == 0 and "no pull request" in out
    assert files_of(root) == before and git(root, "branch", "--show-current") == "main"
    root2 = project(tmp_path / "two", SET.replace('pr_mode = "flow"\n', ""))
    _, out = run(root2, capsys, "settings", extra=["--yes", *answers("where=local")])
    config = setup.tomllib.loads((root2 / "agk.toml").read_text(encoding="utf-8"))
    assert config["pr_mode"] == "flow"
    adr = next((root2 / "docs" / "adr").glob("0002-*.md")).read_text(encoding="utf-8")
    assert "execution" not in adr and "review_mode" not in adr and "max_builders" not in adr


def test_ac5_hybrid_and_pool_are_kept(tmp_path, capsys):
    """REQ-072 AC5: Q-S0065-6: `hybrid` and `pool` are never replaced."""
    root = project(tmp_path, SET.replace('"local"\nreview', '"hybrid"\nreview'))
    assert "where" not in [q["id"] for q in asked(root, capsys)]
    code, out = run(root, capsys, "settings", extra=["--yes", *answers("where=local")])
    assert code == 0 and "no pull request" in out
    assert 'execution = "hybrid"' in (root / "agk.toml").read_text(encoding="utf-8")


def test_ac6_personal_mode_makes_no_project_change(tmp_path, capsys):
    """REQ-072 AC6: rule 16: for me only: nothing is proposed to the project."""
    root = project(tmp_path)
    before = files_of(root)
    code, out = run(root, capsys, "settings", extra=["--yes", *answers("where=personal")])
    assert code == 0 and "nothing" in out
    assert files_of(root) == before and git(root, "branch", "--show-current") == "main"


def test_ac5_the_windows_answer_maps_to_the_adapter(tmp_path, capsys):
    """REQ-072 AC5: rules 4 and 9: native or WSL 2 is proposed as the launch adapter."""
    fake = machine(os="Windows", os_version="11", wsl="present", admin=True)
    for pick, kind in (("wsl", "wsl"), ("native", "windows")):
        root = project(tmp_path / pick, 'review_mode = "solo"\n')
        extra = ["--yes", *answers("where=local", f"windows={pick}")]
        code, _ = run(root, capsys, "settings", fake, extra)
        config = setup.tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
        assert code == 0 and config["flow"]["launch_adapter"] == setup.wsl.ADAPTERS[kind]
        assert config["flow"]["max_builders"] == 2  # one person: this machine's figure


def test_usage_an_unknown_answer_is_refused(tmp_path, capsys):
    """REQ-072 AC2: an answer outside the choices is a usage error and changes nothing."""
    root = project(tmp_path)
    before = files_of(root)
    for bad in ("where=pool", "colour=blue", "where"):
        code, _ = run(root, capsys, "settings", extra=["--yes", "--answer", bad])
        assert code == 2 and files_of(root) == before


def test_ac5_no_output_or_file_holds_a_token_or_password(tmp_path, capsys):
    """REQ-072 AC5: rule 11: no run's output or written file holds a token-shaped value."""
    root = project(tmp_path)
    outs = [run(root, capsys, f, extra=x)[1] for f, x in (("ask", ["--json"]), ("plan", []))]
    outs.append(run(root, capsys, "settings", extra=["--yes", *answers("where=local")])[1])
    written = [p.read_text(encoding="utf-8") for p in files_of(root)]
    body = root / ".git" / "agk" / "pr-body-setup.md"
    assert body.is_file(), outs[2]
    assert "Advances: REQ-001" in body.read_text(encoding="utf-8")
    assert not any(SECRET.search(t) for t in [*outs, *written, body.read_text(encoding="utf-8")])


def test_ac2_the_skill_asks_then_proposes_and_never_pushes(tmp_path):
    """REQ-072 AC2, AC5: the skill asks the questions, acts on one yes and never commits."""
    text = SKILL.read_text(encoding="utf-8")
    assert '${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" ask --json' in text
    assert "settings --yes" in text
    for verb in ("git push", "git commit", "gh pr"):
        assert verb not in text


@pytest.mark.parametrize("figure", [0, 1])
def test_ac5_one_builder_keeps_strict(tmp_path, capsys, figure):
    """REQ-072 AC5: `pr_mode` becomes flow only when more than one builder runs."""
    root = project(tmp_path, 'review_mode = "solo"\nexecution = "local"\n')
    extra = ["--yes", "--builders", str(figure), *answers("autopilot=off")]
    code, _ = run(root, capsys, "settings", extra=extra)
    assert code == 0
    assert "pr_mode" not in setup.tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))


def test_ac6_ci_mode_proposes_execution_only(tmp_path, capsys):
    """REQ-072 AC6: rule 16: on GitHub's machines nothing is sized from this machine."""
    root = project(tmp_path, 'review_mode = "solo"\n')
    code, _ = run(root, capsys, "settings", extra=["--yes", *answers("where=hosted")])
    config = setup.tomllib.loads((root / "agk.toml").read_text(encoding="utf-8"))
    assert code == 0 and config["execution"] == "hosted"
    assert "pr_mode" not in config and "flow" not in config and "autopilot" not in config


def test_ac6_personal_mode_names_no_setting_in_the_plan(tmp_path, capsys):
    """REQ-072 AC6: rule 16: for me only, the plan proposes nothing to the project."""
    _, out = run(project(tmp_path), capsys, "plan", extra=answers("where=personal"))
    last = out.split("\n\n")[0].splitlines()[-1]
    assert "nothing is proposed" in last and " = " not in last


def test_ac5_the_branch_starts_from_the_default_branch(tmp_path, capsys):
    """REQ-072 AC5: rule 9: a feature branch's own commits stay out; a dirty tree refuses."""
    root = project(tmp_path, 'review_mode = "solo"\n')
    git(root, "checkout", "-q", "-b", "feature-example")
    (root / "example.txt").write_text("example\n", encoding="utf-8")
    git(root, "add", "example.txt")
    git(root, *WHO, "commit", "-q", "-m", "feature")
    (root / "example.txt").write_text("changed\n", encoding="utf-8")
    code, out = run(root, capsys, "settings", extra=["--yes", *answers("where=local")])
    assert code == 1 and "working tree" in out
    assert git(root, "branch", "--show-current") == "feature-example"
    git(root, "checkout", "-q", "--", "example.txt")
    code, out = run(root, capsys, "settings", extra=["--yes", *answers("where=local")])
    assert code == 0, out
    assert git(root, "rev-parse", "HEAD") == git(root, "rev-parse", "origin/main")
    assert not (root / "example.txt").exists()


def test_ac5_a_table_line_with_a_comment_is_the_same_table(tmp_path, capsys):
    """REQ-072 AC5: rule 9: `[flow]  # ...` is found, never doubled; the text parses first."""
    toml = 'review_mode = "solo"\n[flow]  # the flow table\nmax_builders = 2\n'
    root = project(tmp_path, toml)
    code, out = run(root, capsys, "settings", extra=["--yes", *answers("where=local")])
    text = (root / "agk.toml").read_text(encoding="utf-8")
    assert code == 0, out
    assert text.count("[flow]") == 1 and setup.tomllib.loads(text)["flow"]["builder_memory_gb"] == 3
    assert setup.set_key("[a]\nx = 1\n", "a", "y", 2) == "[a]\nx = 1\ny = 2\n"


def test_ac5_a_change_that_would_not_parse_makes_no_branch(tmp_path, capsys, monkeypatch):
    """REQ-072 AC5: rule 9: the text is checked before the branch; nothing is left behind."""
    root = project(tmp_path, 'review_mode = "solo"\n')
    monkeypatch.setattr(setup, "set_key", lambda text, *item: text + "[broken\n")
    code, out = run(root, capsys, "settings", extra=["--yes", *answers("where=local")])
    assert code == 1 and "would not parse" in out
    assert git(root, "branch", "--show-current") == "main"
    assert git(root, "branch", "--list", "agk/*") == ""
