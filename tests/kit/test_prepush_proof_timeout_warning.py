"""Prepush warns when the full suite takes longer than `proof_timeout` (brief #509, ADR-0258).

After a regression run named `full` ends, when its seconds exceed `proof_timeout`, the `tests` step
of `scripts/agk/prepush.py` prints one line naming the setting, both durations and a value with
headroom (`ceil(n * 1.5 / 60) * 60`), and puts the same line in the record's `notes`. The outcome of
prepush does not change. A selected (non-full) run over the limit prints nothing, and a refused
`proof_timeout` keeps today's refusal.

The runs and the clock are fakes: `execute` is replaced by one that advances a fake clock by the
seconds the test chooses, so no test waits.
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import prepush
import pytest
from impact import Impact, Selected
from test_prepush import LINT_OK, MK_OK, path_with, scanner

TESTING = '[testing]\nprofile = "balanced"\nmap = [ { code = "src/a/**", tests = ["tests/**"] } ]\n'
WARNING = (
    "prepush: warning: the full suite took 1234 s, more than proof_timeout (900 s); "
    "proof will not finish (setting: proof_timeout); a value of about 1860 s leaves headroom"
)


class Clock:
    """A fake monotonic clock that the fake runs advance."""

    def __init__(self) -> None:
        self.now = 1000.0

    def monotonic(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(prepush, "time", types.SimpleNamespace(monotonic=fake.monotonic))
    return fake


def fake_runs(monkeypatch, clock: Clock, seconds: dict[str, float], code: int = 0) -> list[str]:
    """Replace `execute`: each command takes the seconds given for it and exits with `code`."""
    ran: list[str] = []

    def execute(command, cwd, timeout, env=None):
        ran.append(command)
        took = seconds[command]
        clock.now += took
        return code, "", round(took)

    monkeypatch.setattr(prepush, "execute", execute)
    return ran


def toml(timeout: str = "900", proof: bool = False) -> str:
    text = (
        'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
        f"project_tests = 'FULL'\nproof_timeout = {timeout}\n"
    )
    if proof:
        area = 'dirs = ["tests"], patterns = ["test_*.py"], command = \'KIT {files}\''
        text += f"[proof]\nkit = {{ {area} }}\n"
    return text


def full() -> Impact:
    return Impact(table=True, profile="balanced", full=True, reason="profile balanced: 1 unmapped")


def selected() -> Impact:
    item = Selected("src/pay.py", "src/**", ["tests/**"], "tests/test_pay.py")
    return Impact(table=True, profile="fast", full=False, reason=None, selected=[item])


def ran_step() -> prepush.Ran:
    return prepush.Ran(["test_plan.py"], Path("."), 0, "{}")


def gate(root: Path, found: Impact, limit: int, areas=None) -> prepush.Step:
    return prepush.gate(root, [], found, areas, limit, ran_step())


def test_a_full_suite_over_the_limit_prints_the_warning_with_a_suggested_value(
    repo, clock, monkeypatch, capsys
):
    """REQ-016: brief #509 answer 1 (full at 1,234 s with a limit of 900 suggests 1,860)."""
    repo.commit({"agk.toml": toml()}, "base")
    ran = fake_runs(monkeypatch, clock, {"FULL": 1234.0})
    step = gate(repo.root, full(), 900)
    out = capsys.readouterr().out
    assert ran == ["FULL"]
    assert step.outcome == "ok"
    assert out.count(WARNING) == 1
    assert WARNING + "\n" in out
    assert step.notes == [WARNING]


def test_the_warning_does_not_change_a_failing_outcome(repo, clock, monkeypatch, capsys):
    """REQ-016: brief #509 answer 1 (the outcome of prepush does not change)."""
    repo.commit({"agk.toml": toml()}, "base")
    fake_runs(monkeypatch, clock, {"FULL": 1234.0}, code=1)
    step = gate(repo.root, full(), 900)
    assert step.outcome == "FAIL"
    assert WARNING in capsys.readouterr().out
    assert step.notes == [WARNING]


def test_the_suggested_value_rounds_up_to_a_whole_minute(repo, clock, monkeypatch, capsys):
    """REQ-016: brief #509 answer 1 (the value is ceil(n * 1.5 / 60) * 60)."""
    repo.commit({"agk.toml": toml("60")}, "base")
    fake_runs(monkeypatch, clock, {"FULL": 61.0})
    gate(repo.root, full(), 60)
    out = capsys.readouterr().out
    assert "the full suite took 61 s, more than proof_timeout (60 s)" in out
    assert "a value of about 120 s leaves headroom" in out


def test_a_full_suite_under_the_limit_prints_nothing(repo, clock, monkeypatch, capsys):
    """REQ-016: brief #509 answer 3 (full under the limit prints nothing)."""
    repo.commit({"agk.toml": toml()}, "base")
    fake_runs(monkeypatch, clock, {"FULL": 899.0})
    step = gate(repo.root, full(), 900)
    assert step.outcome == "ok"
    assert "warning" not in capsys.readouterr().out
    assert step.notes == []


def test_a_full_suite_exactly_at_the_limit_prints_nothing(repo, clock, monkeypatch, capsys):
    """REQ-016: brief #509 answer 1 (only seconds that exceed the limit warn)."""
    repo.commit({"agk.toml": toml()}, "base")
    fake_runs(monkeypatch, clock, {"FULL": 900.0})
    gate(repo.root, full(), 900)
    assert "warning" not in capsys.readouterr().out


def test_a_selected_run_over_the_limit_prints_nothing(repo, clock, monkeypatch, capsys):
    """REQ-016: brief #509 answer 3 (a selected run over the limit prints nothing)."""
    repo.commit({"agk.toml": toml(proof=True)}, "base")
    areas = prepush.proof_areas(repo.root)
    fake_runs(monkeypatch, clock, {"KIT tests/test_pay.py": 1234.0})
    step = gate(repo.root, selected(), 900, areas)
    assert step.outcome == "ok"
    assert "warning" not in capsys.readouterr().out
    assert step.notes == []


def test_a_proof_plan_run_over_the_limit_prints_nothing(repo, clock, monkeypatch, capsys):
    """REQ-016: brief #509 answer 1 (only the regression run named `full` warns)."""
    repo.commit({"agk.toml": toml()}, "base")
    fake_runs(monkeypatch, clock, {"OWN": 1234.0})
    nothing = Impact(table=True, profile="fast", full=False, reason=None)
    runs = [{"name": "full", "command": "OWN", "cwd": "."}]
    step = prepush.gate(repo.root, runs, nothing, None, 900, ran_step())
    assert "warning" not in capsys.readouterr().out
    assert step.notes == []


def test_a_refused_proof_timeout_keeps_todays_refusal(repo):
    """REQ-016: brief #509 answer 3 (a refused `proof_timeout` setting keeps today's refusal)."""
    text = toml("0").replace("project_tests = 'FULL'", "project_tests = 'echo full'")
    text += TESTING
    repo.commit({"agk.toml": text, "agk.mk": MK_OK, "Makefile": LINT_OK, "src/b.py": "x\n"})
    repo.branch("feature")
    repo.commit({"src/b.py": "y\n"})
    bin_dir = scanner(repo.root / ".." / "bin-509", 0)
    proc = repo.run("prepush.py", "--no-lock", PATH=path_with(bin_dir))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "proof_timeout must be a positive integer (setting: proof_timeout)" in proc.stdout
    assert "prepush: stopped at tests" in proc.stdout
    assert "warning" not in proc.stdout


def test_the_warning_is_in_the_records_notes(repo, clock, monkeypatch, tmp_path_factory, capsys):
    """REQ-016: brief #509 answer 1 (the line is in the record's notes)."""
    outside = tmp_path_factory.mktemp("outside")
    text = toml() + TESTING
    repo.commit({"agk.toml": text, "agk.mk": MK_OK, "Makefile": LINT_OK, "src/b.py": "x\n"})
    repo.branch("feature")
    repo.commit({"src/b.py": "y\n"})
    fake_runs(monkeypatch, clock, {"FULL": 1234.0})
    monkeypatch.chdir(repo.root)
    monkeypatch.setenv("PATH", path_with(scanner(outside / "bin", 0)))
    for name in ("GITHUB_BASE_REF", "AGK_BASE", "CI"):
        monkeypatch.delenv(name, raising=False)
    record = outside / "record.json"
    code = prepush.main(["--no-lock", "--record", str(record)])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "prepush: all steps passed" in out
    assert out.count(WARNING) == 1
    data = json.loads(record.read_text(encoding="utf-8"))
    assert data["notes"] == [WARNING]
    assert data["result"] == "passed"


def test_a_record_without_a_warning_has_empty_notes(
    repo, clock, monkeypatch, tmp_path_factory, capsys
):
    """REQ-016: brief #509 answer 1 (no warning, no note)."""
    outside = tmp_path_factory.mktemp("outside")
    text = toml() + TESTING
    repo.commit({"agk.toml": text, "agk.mk": MK_OK, "Makefile": LINT_OK, "src/b.py": "x\n"})
    repo.branch("feature")
    repo.commit({"src/b.py": "y\n"})
    fake_runs(monkeypatch, clock, {"FULL": 10.0})
    monkeypatch.chdir(repo.root)
    monkeypatch.setenv("PATH", path_with(scanner(outside / "bin", 0)))
    for name in ("GITHUB_BASE_REF", "AGK_BASE", "CI"):
        monkeypatch.delenv(name, raising=False)
    record = outside / "record.json"
    assert prepush.main(["--no-lock", "--record", str(record)]) == 0
    assert json.loads(record.read_text(encoding="utf-8"))["notes"] == []


def test_the_testing_guide_says_to_set_proof_timeout_above_the_full_suite():
    """REQ-016: brief #509 answer 2 (the guide's proof section gains one sentence)."""
    root = Path(__file__).resolve().parents[2]
    text = " ".join((root / "docs/guides/testing.md").read_text(encoding="utf-8").split())
    assert "set `proof_timeout` above the full suite's time with headroom" in text
    assert "prepush warns when it is not" in text
