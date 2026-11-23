"""Tests of an adopted project's first gates run (SPEC-0072 rules 6, 7 and 8; REQ-079; brief #1837,
ADR-0766).

On the Node and Python samples of `test_node_pack.py` and `test_python_pack.py` in `mode = "adopt"`,
the first run holds the rule 8 floors (a pinned rule off, `strict` false, no ESLint configuration,
a ruff table missing `E`) in `config/agk-baseline/`, prints `held` and no `ok standards`, and exits
0; a later run that turns one more rule off fails naming rule 7, and turning one on prints that a
count fell, which `--baseline` lowers. The same trees in `mode = "init"` fail as before. A lint tool
that did not run is never held, in either mode, with or without a baseline. A pack with no product
file in scope is `not run`, named in the last line. `doctor.py` names a held floor and a pack that
reads no file, never a file, a rule or a value. One table test keeps the class closed: every pack
step is tallied or has a reason. Stand-in tools, no network; invented data only (example.com).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import doctor  # noqa: E402
import run_gates  # noqa: E402
import test_node_pack as node  # noqa: E402
import test_python_pack as py  # noqa: E402
from gates import baseline, bom, node_pack, python_pack  # noqa: E402

BASE = "config/agk-baseline"
NODE_FLOOR = f"{BASE}/standards-node-floor.txt"
TYPE_FLOOR = f"{BASE}/standards-node-type-floor.txt"
PY_FLOOR = f"{BASE}/standards-python-pyproject-floor.txt"
PLANTED = ("greet.ts", "no-debugger", "example.com", "app.py")
# The one reason table: a pack step that is not tallied (held to a baseline) is one of these.
REASONS = {
    "tools": "a missing tool fails in every mode (it counts no file)",
    "paths": "a refused project_lint_paths fails in every mode (it counts no file)",
    "note": "information, never a failure",
    "no-file": "no product file in scope: the pack is not run (python_pack.NO_FILE)",
}


@pytest.fixture(autouse=True)
def _no_bill(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bom, "applies", lambda _root: False)


def adopt(root: Path, mode: str = "adopt") -> Path:
    path = root / "agk.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('mode = "init"', f'mode = "{mode}"'),
        encoding="utf-8",
    )
    return root


def node_sample(tmp: Path, mode: str = "adopt", **kw: object) -> Path:
    return adopt(node.sample(tmp, **kw), mode)


def py_sample(tmp: Path, mode: str = "adopt", select: str = '["F"]', **kw: object) -> Path:
    root = py.sample(tmp, **kw)
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace('select = ["E", "F", "I", "B", "UP"]', f"select = {select}"), encoding="utf-8"
    )
    return adopt(root, mode)


def gates(root: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> tuple[int, str]:
    code = run_gates.main([*extra, "--root", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def rules_off(*off: str) -> dict:
    return dict(node.floor_rules(), **{r: "off" for r in off})


def last(out: str) -> str:
    return out.strip().splitlines()[-1]


def broken_lint(root: Path) -> None:
    """A stand-in eslint whose lint run exits 2 with no report; `--print-config` still works."""
    tool = root / "node_modules" / ".bin" / "eslint"
    body = tool.read_text(encoding="utf-8")
    tool.write_text(body.replace("out, bad = [], False", "sys.exit(2)\nout, bad = []"), "utf-8")


# Answer 1: the floors are held on the adopted first run.


def test_a_pinned_rule_off_is_held_on_the_first_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answer 1 and its Measured line."""
    root = node_sample(tmp_path, rules=rules_off("no-debugger"))
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "standards node floor (baseline): 1 held (setting: standards.config)" in out
    assert "ok standards" not in out and "FAIL" not in out
    assert (root / NODE_FLOOR).read_text(encoding="utf-8") == "package.json 1\n"
    for word in ("greet.ts", "no-debugger"):
        assert word not in out


def test_strict_false_is_held_on_the_first_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answer 1 (`type-floor`, named by its path class)."""
    root = node_sample(tmp_path, tsconfig='{"compilerOptions": {"strict": false}}')
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "standards node type-floor (baseline): 1 held (path class: tsconfig.json)" in out
    assert (root / TYPE_FLOOR).read_text(encoding="utf-8") == "tsconfig.json 1\n"
    assert "ok standards" not in out and "false" not in out


def test_no_eslint_configuration_is_held_and_lint_is_not_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answers 1 and 2 (the one exception, Q-1837-3)."""
    root = node_sample(tmp_path)
    (root / "eslint-rules.json").unlink()  # the stand-in then finds no configuration
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "standards node floor (baseline): 1 held (setting: standards.config)" in out
    assert (
        "not run standards node lint: the pack's configuration is held (setting: standards.config)"
        in out
    )
    assert "standards node lint" in last(out) and "not run:" in last(out)
    assert "ok standards" not in out


def test_a_ruff_table_missing_rules_is_held_on_the_first_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answer 1 (the Python floor: E, I, B and UP off)."""
    root = py_sample(tmp_path)
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "standards python-pyproject floor (baseline): 4 held (setting: standards.config)" in out
    assert (root / PY_FLOOR).read_text(encoding="utf-8") == "pyproject.toml 4\n"
    assert "ok standards" not in out


def test_a_rule_turned_off_later_fails_and_one_turned_on_is_lowered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answers 1 and 7 (a held floor can only fall)."""
    root = node_sample(tmp_path, rules=rules_off("no-debugger"))
    assert gates(root, capsys)[0] == 0
    conf = root / "eslint-rules.json"
    text = conf.read_text(encoding="utf-8")
    conf.write_text(text.replace('"no-empty": "error"', '"no-empty": "off"'), encoding="utf-8")
    code, out = gates(root, capsys)
    assert code == 1
    assert "standards node floor: SPEC-0072 rule 7" in out
    assert "(path class: config/agk-baseline/)" in out
    assert "pack's rule no-empty (setting: standards.config)" in out
    conf.write_text(text.replace('"no-debugger": "off"', '"no-debugger": "error"'), "utf-8")
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "baseline standards node floor: a count fell in 1 file" in out
    assert (root / NODE_FLOOR).read_text(encoding="utf-8") == "package.json 1\n"
    assert gates(root, capsys, "--baseline")[0] == 0
    assert (root / NODE_FLOOR).read_text(encoding="utf-8") == ""


@pytest.mark.parametrize("case", ["rule-off", "strict-false", "python"])
def test_the_same_trees_in_init_mode_fail_as_before(
    case: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answers 1 and 6 (a team's own configuration must pass in init)."""
    if case == "python":
        root = py_sample(tmp_path, mode="init")
    elif case == "rule-off":
        root = node_sample(tmp_path, mode="init", rules=rules_off("no-debugger"))
    else:
        root = node_sample(tmp_path, mode="init", tsconfig='{"compilerOptions": {}}')
    code, out = gates(root, capsys)
    assert code == 1
    assert "floor: SPEC-0072 rule 8" in out
    assert not (root / BASE).exists()


@pytest.mark.parametrize("mode", ["init", "none", "other"])
def test_baseline_writes_a_missing_floor_file_in_any_mode(
    mode: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answer 6 (`--baseline`, the upgrade's yes, Q-S0072-5); a project that is
    not adopted writes nothing on a plain run, and its floor fails until it holds a file."""
    root = node_sample(tmp_path, mode="init", rules=rules_off("no-debugger"))
    toml = root / "agk.toml"
    text = toml.read_text(encoding="utf-8")
    if mode != "init":
        new = "" if mode == "none" else 'mode = "x"\n'
        toml.write_text(text.replace('mode = "init"\n', new), encoding="utf-8")
    assert gates(root, capsys)[0] == 1 and not (root / NODE_FLOOR).exists()
    code, out = gates(root, capsys, "--baseline")
    assert code == 0, out
    assert (root / NODE_FLOOR).read_text(encoding="utf-8") == "package.json 1\n"


# Answer 2: a step that did not run is never held.


@pytest.mark.parametrize("mode", ["adopt", "init"])
@pytest.mark.parametrize("held", [False, True])
def test_a_lint_tool_that_did_not_run_fails_in_every_mode(
    mode: str, held: bool, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answer 2 (red on main: adopt held it as `ok standards node`)."""
    root = node_sample(tmp_path, mode=mode)
    if held:
        assert gates(root, capsys, "--baseline")[0] == 0
    broken_lint(root)
    for _ in range(2):  # the first run and the next one
        code, out = gates(root, capsys)
        assert code == 1, out
        assert (
            "FAIL gates: standards node lint: SPEC-0072 rule 6: the lint tool did not run "
            "(setting: standards.lint)" in out
        )
        assert "ok standards node" not in out
    lint = root / BASE / "standards-node-lint.txt"
    assert lint.is_file() == held


# Answer 3: no file in scope is `not run`.


@pytest.mark.parametrize("stack", ["node", "python-pyproject"])
def test_no_product_file_in_scope_is_not_run(
    stack: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answer 3 (red on main: `ok standards <stack>`); no step runs, the
    Python floor included (Q-1837-2), so a broken floor in init still exits 0."""
    toml = 'project_lint_paths = ["web/**"]'
    if stack == "node":
        root = node_sample(tmp_path, mode="init", code="debugger;\n", toml=toml)
    else:
        root = py_sample(tmp_path, mode="init", toml=toml)
    code, out = gates(root, capsys)
    assert code == 0, out
    reason = f"not run standards {stack}: no product file in scope (setting: project_lint_paths)"
    assert reason in out
    assert f"standards {stack}" in last(out).split("not run:", 1)[1]
    assert f"ok standards {stack}" not in out and "floor" not in out


def test_unset_project_lint_paths_names_the_layers_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answer 3 (unset: the layers' paths)."""
    root = node_sample(tmp_path)
    (root / "frontend" / "greet.ts").unlink()
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "not run standards node: no product file in scope (key: architecture.layers)" in out


# Answer 4: the person is told.


def test_doctor_names_a_held_floor_and_a_pack_that_reads_no_file(tmp_path: Path) -> None:
    """REQ-079: brief #1837 answer 4 (each line once; no file, rule or value)."""
    root = node_sample(
        tmp_path / "a",
        rules=rules_off("no-debugger", "no-empty"),
        tsconfig='{"compilerOptions": {"strict": false}}',
    )
    run_gates.results(root)
    lines = doctor.held_floor_lines(root)
    assert lines == [
        "warn standards: the project's own node configuration leaves 2 of the pack's rules or"
        " compiler options off; turn them on, or keep one off with an ADR, then lower it with"
        " run_gates.py --baseline (setting: standards.config)",
        "warn standards: the project's own node configuration leaves 1 of the pack's rules or"
        " compiler options off; turn them on, or keep one off with an ADR, then lower it with"
        " run_gates.py --baseline (setting: standards.config)",
    ]
    idle = node_sample(tmp_path / "b", toml='project_lint_paths = ["web/**"]')
    assert doctor.held_floor_lines(idle) == [
        "warn standards: the node pack reads no file (setting: project_lint_paths)"
    ]
    for line in lines:
        for word in PLANTED:
            assert word not in line
    assert doctor.held_floor_lines(KIT_ROOT) == []


# Answer 5: the class stays closed.


def _planted(tmp_path: Path, stack: str) -> tuple[Path, dict]:
    if stack == "node":
        root = node_sample(
            tmp_path,
            code="\tdebugger;\n" + node.FAULT,
            rules=rules_off("no-debugger"),
            tsconfig='{"compilerOptions": {"strict": false}}',
        )
        return root, next(e for e in node.node_entries("web-app") if e["stack"] == "node")
    root = py_sample(tmp_path, code="import json\nx=1\n\n\ndef f(a):\n    return a\n")
    entries = py.check_playbooks.standard(py.PLAYBOOKS / "api-service.toml", py.KIT_ROOT)[1]
    return root, next(e for e in entries if e["stack"] == "python-pyproject")


@pytest.mark.parametrize("stack", ["node", "python"])
def test_every_pack_step_is_tallied_or_has_a_reason(stack: str, tmp_path: Path) -> None:
    """REQ-079: brief #1837 answer 5 (a new untallied step fails, naming it)."""
    assert set(run_gates.PACKS) == {"python_pack", "node_pack"}, "a new pack: add its sample"
    root, entry = _planted(tmp_path, stack)
    module = node_pack if stack == "node" else python_pack
    tally: dict[str, dict[str, int]] = {}
    steps = module.run(root, entry, tally)
    for step, lines in steps:
        assert step in tally or step in REASONS, f"pack step {step} is neither tallied nor listed"
        if step in tally:
            assert lines, f"the planted finding of {step} was not found"


@pytest.mark.parametrize("stack", ["node", "python"])
def test_an_adopted_first_run_with_a_finding_per_step_is_never_red(
    stack: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1837 answer 5 (each step held, ok with a count or not run, never FAIL)."""
    root, _ = _planted(tmp_path, stack)
    code, out = gates(root, capsys)
    assert code == 0, out
    assert "FAIL" not in out and "held" in out
    for word in PLANTED:
        assert word not in out


def test_the_kit_repository_runs_no_pack(capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079: brief #1837 answer 6 (no `mode`: the kit's own output is unchanged)."""
    assert not baseline.adopted(KIT_ROOT)
    assert not any("standards" in line for _, line in run_gates.results(KIT_ROOT))
