"""/agk:setup build (a): read the machine and the repository, size the builders, print the plan
(brief #1460, SPEC-0065 rules 2, 3, 5, 6 and 12, ADR-0618; REQ-072).

A fake machine read (`--machine FILE`), saved GitHub answers (`--github FILE`) and a stub runner
for the proof rows; no network, no model, no install. Invented names of example.com only.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("agk_setup", SCRIPTS / "setup.py")
setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(setup)

SKILL = ROOT / "skills" / "setup" / "SKILL.md"
TOOLS = {"python": "3.12.1", "git": "2.43.0", "gh": "2.50.0", "claude": "2.1.0", "node": "20.11.0"}


def machine(**over) -> dict:
    found = {
        "os": "Linux", "os_version": "6.1", "wsl": "absent", "memory_total_gb": 16,
        "memory_available_gb": 12, "cores": 8, "disk_free_gb": 100, "admin": False,
        "tools": dict(TOOLS, podman="4.9.3", docker=None), "winget": "absent",
        "proxy": "none", "remote": "example-org/example-project",
    }  # fmt: skip
    return found | over


def project(tmp_path: Path, toml: str = 'review_mode = "team"\n', files=()) -> Path:
    (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    for name in files:
        (tmp_path / name).write_text("example\n", encoding="utf-8")
    return tmp_path


def run(tmp_path, capsys, monkeypatch, form="plan", fake=None, gh=None, extra=()):
    calls: list[list[str]] = []
    monkeypatch.setattr(setup, "run_cmd", lambda args, cwd: calls.append(list(args)) or 0)
    m, g = tmp_path.parent / "machine.json", tmp_path.parent / "github.json"
    m.write_text(json.dumps(fake or machine()), encoding="utf-8")
    g.write_text(json.dumps(gh or {"lease": "free", "running": 0}), encoding="utf-8")
    args = [form, "--machine", str(m), "--github", str(g), "--root", str(tmp_path), *extra]
    code = setup.main(args)
    return code, capsys.readouterr().out, calls


def files_of(root: Path) -> dict:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_ac1_a_set_up_double_skips_every_check_and_writes_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC1: rule 2: every check row skipped, the proof rows listed, nothing written."""
    root = project(tmp_path)
    before = files_of(root)
    code, out, _ = run(root, capsys, monkeypatch, extra=["--json"])
    table = json.loads(out)
    assert code == 0 and files_of(root) == before
    assert {"steps", "pending", "roles", "builders"} <= set(table)
    checks = [s for s in table["steps"] if s["step"] not in setup.PROOF]
    assert checks and all(s["result"] == "skipped" for s in checks)
    assert table["pending"] == []
    assert {s["step"] for s in table["steps"]} >= set(setup.PROOF)
    assert all(set(s) == {"step", "result", "note"} for s in table["steps"])
    assert all(s["result"] in setup.RESULTS for s in table["steps"])


@pytest.mark.parametrize("k", range(len(TOOLS)))
def test_ac1_a_stopped_run_resumes_at_the_next_step(tmp_path, capsys, monkeypatch, k):
    """REQ-072 AC1: rule 2: the steps done before a stop are skipped; the next one waits."""
    names = list(TOOLS)
    tools = {n: (TOOLS[n] if i < k else None) for i, n in enumerate(names)} | {"podman": None}
    _, out, _ = run(
        project(tmp_path), capsys, monkeypatch, fake=machine(tools=tools), extra=["--json"]
    )
    rows = {s["step"]: s["result"] for s in json.loads(out)["steps"]}
    assert [rows[n] for n in names[:k]] == ["skipped"] * k
    assert rows[names[k]] == "waiting"
    assert names[k] in json.loads(out)["pending"]


def test_ac1_status_prints_the_table_and_changes_nothing(tmp_path, capsys, monkeypatch):
    """REQ-072 AC1: rule 12: `status` runs the checks and the proof again and writes nothing."""
    root = project(tmp_path)
    before = files_of(root)
    code, out, calls = run(root, capsys, monkeypatch, form="status")
    assert code == 0 and files_of(root) == before
    assert "Plan:" not in out and "doctor" in out and "skipped" in out
    assert any("doctor.py" in " ".join(c) for c in calls)


def test_ac1_plan_runs_no_proof_and_lists_the_proof_rows_as_not_yet_run(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC1: rules 5 and 12: the proofs run after the yes and in `status`, not in `plan`."""
    root = project(tmp_path, files=("Containerfile",))
    for extra in ((), ("--json",)):
        code, out, calls = run(root, capsys, monkeypatch, extra=extra)
        assert code == 0 and calls == []
    rows = {s["step"]: s for s in json.loads(out)["steps"]}
    assert all(rows[p]["result"] == "skipped" for p in setup.PROOF)
    assert all(rows[p]["note"] == setup.NOT_YET for p in setup.PROOF)
    _, _, calls = run(root, capsys, monkeypatch, form="status")
    assert any(c[1:3] == ["run", "--rm"] for c in calls)


def test_ac2_reads_first_asks_nothing_and_the_plan_has_at_most_eight_lines(
    tmp_path, capsys, monkeypatch
):
    """REQ-072 AC2: rules 3 and 5: what the double tells is named, never asked; no install."""
    _, out, calls = run(project(tmp_path), capsys, monkeypatch)
    plan = out.split("\n\n")[0].splitlines()
    assert plan[0] == "Plan:" and 2 <= len(plan) - 1 <= 8
    text = "\n".join(plan)
    for read in ("Linux 6.1", "16 GB", "8 cores", "podman", "example-org/example-project"):
        assert read in text, read
    assert "?" not in out
    assert not [c for c in calls if c and c[0] in ("winget", "apt", "apt-get", "dnf")]


@pytest.mark.parametrize("total", [8, 16, 32])
@pytest.mark.parametrize("heavy", [False, True])
def test_ac3_the_figure_follows_the_formula(total, heavy):
    """REQ-072 AC3: rule 6: (available less a 25 percent reserve) / 4 GB or 3 GB, rounded down."""
    available = total * 0.75
    per = 4 if heavy else 3
    got = setup.size(available, total, cores=64, per_gb=per, reserve=0.25, max_builders=99)
    assert got["figure"] == int((available - 0.25 * total) // per)
    assert got["limit"] == "memory" and str(per) in got["reason"]


@pytest.mark.parametrize(
    ("cores", "most", "live", "figure", "limit"),
    [(4, 99, 0, 2, "cores"), (64, 1, 0, 1, "max_builders"), (64, 6, 4, 2, "team")],
)
def test_ac3_the_caps_apply_and_are_named(cores, most, live, figure, limit):
    """REQ-072 AC3: rule 6: capped by cores, `max_builders` and the team's live builders."""
    got = setup.size(24, 32, cores=cores, per_gb=3, reserve=0.25, max_builders=most, live=live)
    assert (got["figure"], got["limit"]) == (figure, limit)
    assert limit.split("_")[0] in got["reason"]


def test_ac3_unreadable_memory_gives_one_and_says_unknown():
    """REQ-072 AC3: rule 6: memory that cannot be read is unknown, never 0."""
    got = setup.size(None, None, cores=8, per_gb=3, reserve=0.25, max_builders=4)
    assert got["figure"] == 1 and "unknown" in got["reason"]


@pytest.mark.parametrize(
    ("toml", "files", "per"),
    [
        ("", (), 3),
        ("", ("playwright.config.ts",), 4),
        ("", ("Containerfile",), 4),
        ("[flow]\nbuilder_memory_gb = 6\n", ("Dockerfile",), 6),
    ],
)
def test_ac3_memory_per_builder_comes_from_the_project(
    tmp_path, capsys, monkeypatch, toml, files, per
):
    """REQ-072 AC3: rule 6: the project's value, else 4 GB with browsers or containers, else 3."""
    _, out, _ = run(project(tmp_path, toml, files), capsys, monkeypatch, extra=["--json"])
    assert json.loads(out)["builders"]["per_builder_gb"] == per


def test_ac3_the_person_may_lower_the_figure_never_raise_it(tmp_path, capsys, monkeypatch):
    """REQ-072 AC3: rule 6: `--builders` below the figure is kept; above it is refused."""
    code, out, _ = run(project(tmp_path), capsys, monkeypatch, extra=["--json", "--builders", "1"])
    assert code == 0 and json.loads(out)["builders"]["figure"] == 1
    code, out, _ = run(project(tmp_path), capsys, monkeypatch, extra=["--builders", "9"])
    assert code == 1 and "cap" in out


def test_ac3_team_live_builders_cap_the_machine(tmp_path, capsys, monkeypatch):
    """REQ-072 AC3: rule 6: in a team, `max_builders` less the builders already live."""
    toml = 'review_mode = "team"\n[flow]\nmax_builders = 3\n'
    gh = {"lease": "held by cb-example-1 until 2026-11-17T18:00Z", "running": 2}
    _, out, _ = run(project(tmp_path, toml), capsys, monkeypatch, gh=gh, extra=["--json"])
    got = json.loads(out)["builders"]
    assert (got["figure"], got["limit"]) == (1, "team")


def test_ac5_no_secret_reaches_the_output():
    """REQ-072 AC5: rule 11: a remote's or a proxy's credentials are never read back."""
    url = "https://member-example-1:example-secret-1@github.com/example-org/example-project.git"
    assert setup.remote_name(url) == "example-org/example-project"
    state = setup.proxy_state({"HTTPS_PROXY": "http://u:example-secret-2@proxy.example.com:8080"})
    assert state == "configured" and "secret" not in state
    assert setup.proxy_state({}) == "none"


def test_ac2_unknown_memory_is_said_in_the_plan(tmp_path, capsys, monkeypatch):
    """REQ-072 AC2, AC3: a figure that cannot be read is named unknown in the plan."""
    fake = machine(memory_total_gb=None, memory_available_gb=None)
    _, out, _ = run(project(tmp_path), capsys, monkeypatch, fake=fake)
    assert "memory unknown" in out and "1 builder" in out


def test_ac1_the_skill_has_its_first_form_and_status():
    """REQ-072 AC1: rule 2: the skill runs the plugin's `setup.py`, with `status`, never pushing."""
    text = SKILL.read_text(encoding="utf-8")
    assert "## /agk:setup status" in text and "## /agk:setup\n" in text
    assert '${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" status' in text
    for verb in ("git push", "git commit", "gh pr"):
        assert verb not in text
