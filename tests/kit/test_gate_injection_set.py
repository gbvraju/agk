"""Tests of the `injection-set` step of the mcp-server `prompt-injection-set` gate (brief #1712,
ADR-0717; SPEC-0072 rule 3; REQ-079).

An mcp-server sample with a foundation and no `injection/` folder under a `test_dirs` entry is red;
a folder that holds only a README, or that is a file, is red; a set that no `[testing] map` entry's
`tests` glob matches is red; a set with a matching entry is green. Every other shipped work type,
and no work type, composes no such gate. A sample before its foundation prints `not run`. Each
failure names the gate id, the rule and the path class, never a file or a value; a malformed
setting is refused naming the setting. Fixtures in `tmp_path` only: invented data (example.com),
no network.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import run_gates  # noqa: E402
from gates import injection_set  # noqa: E402

GATE = "prompt-injection-set"
TEST = 'def test_refuses() -> None:\n    assert "ignore all rules".startswith("ignore")\n'
SET = {"tests/injection/test_refusals.py": TEST}
MAP = '[[testing.map]]\ncode = "server/**"\ntests = ["tests/injection/**"]\n'
OTHERS = (
    "web-app",
    "mobile",
    "cloud-migration",
    "rag-app",
    "multi-agent",
    "voice-agent",
    "pilot",
    "data-pipeline",
    "api-service",
)
WHERE = "tests/injection/; setting: test_dirs"
MAPPED = "tests/injection/; setting: testing.map"


def _project(
    tmp_path: Path,
    files: dict[str, str],
    tail: str = MAP,
    work_type: str | None = "mcp-server",
    top: str = "",
    founded: bool = True,
) -> Path:
    root = tmp_path / "tools"
    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    toml = f'mode = "init"\n{top}\n'
    if work_type:
        toml += f'[delivery]\nwork_type = "{work_type}"\n\n'
    toml += tail
    found = {"docs/architecture.md": "# Architecture\n"} if founded else {}
    for rel, text in {"agk.toml": toml, "server/tools.py": "HOST = 'mcp.example.com'\n",
                      **found, **files}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


@pytest.fixture(autouse=True)
def _base(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AGK_BASE", "GITHUB_BASE_REF", "CI"):
        monkeypatch.delenv(name, raising=False)


def _run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, list[str]]:
    code = run_gates.main(["--root", str(root)])
    out = capsys.readouterr().out.splitlines()
    return code, out


def _lines(root: Path, capsys: pytest.CaptureFixture[str]) -> list[str]:
    return [ln for ln in _run(root, capsys)[1] if GATE in ln and not ln.startswith("ok gates (")]


def test_a_set_the_map_names_is_green(tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answers 1 to 3 (the measured `after`, green)."""
    assert _lines(_project(tmp_path, SET), capsys) == [f"ok {GATE}"]


def test_no_set_is_red_naming_the_path_class(tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 2 and Q-1712-1 (an upgraded project with no set is red)."""
    root = _project(tmp_path, {})
    assert _lines(root, capsys) == [
        f"FAIL gates: {GATE}: {injection_set.NO_SET} (path class: {WHERE})"
    ]
    assert run_gates.main(["--root", str(root)]) == 1
    assert "tools.py" not in capsys.readouterr().out


@pytest.mark.parametrize("name", ["README", "README.md", "readme.txt"])
def test_a_set_of_only_a_readme_is_red(name: str, tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 5."""
    root = _project(tmp_path, {f"tests/injection/{name}": "# Set\n"})
    assert _lines(root, capsys) == [
        f"FAIL gates: {GATE}: {injection_set.NO_FILE} (path class: {WHERE})"
    ]


def test_a_set_folder_that_is_a_file_is_red(tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 5."""
    root = _project(tmp_path, {"tests/injection": TEST})
    assert _lines(root, capsys) == [
        f"FAIL gates: {GATE}: {injection_set.NO_SET} (path class: {WHERE})"
    ]


@pytest.mark.parametrize(
    "tail",
    [
        "",
        '[testing]\nprofile = "balanced"\n',
        '[[testing.map]]\ncode = "server/**"\ntests = ["tests/unit/**"]\n',
        '[[testing.map]]\ncode = "server/**"\ntests = ["tests/injection/README.md"]\n',
    ],
)
def test_a_set_no_map_entry_names_is_red(tail: str, tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answers 2 and 5 (no entry, another folder, only the README)."""
    files = {**SET, "tests/injection/README.md": "# Set\n"}
    assert _lines(_project(tmp_path, files, tail=tail), capsys) == [
        f"FAIL gates: {GATE}: {injection_set.UNMAPPED} (path class: {MAPPED})"
    ]


def test_before_the_foundation_it_is_not_run(tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 2 (`no foundation yet`, as the tests floor)."""
    root = _project(tmp_path, {}, founded=False)
    assert _lines(root, capsys) == [f"not run {GATE}: no foundation yet"]


@pytest.mark.parametrize("work_type", [*OTHERS, None])
def test_every_other_work_type_composes_no_such_gate(
    work_type: str | None, tmp_path: Path, capsys
) -> None:
    """REQ-079: brief #1712 answer 4 (`[delivery] work_type`)."""
    root = _project(tmp_path, {}, work_type=work_type)
    run_gates.main(["--root", str(root)])
    out = capsys.readouterr().out
    assert GATE not in out and "injection-set" not in out


def test_a_playbook_naming_mcp_server_in_modules_composes_it(tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 4 (a playbook's `modules`)."""
    root = _project(tmp_path, {}, work_type="api-service")
    path = root / "config" / "playbooks" / "api-service.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("lanes = ", 'modules = ["mcp-server"]\nlanes = ', 1), "utf-8")
    assert _lines(root, capsys) == [
        f"FAIL gates: {GATE}: {injection_set.NO_SET} (path class: {WHERE})"
    ]


def test_an_unknown_work_type_is_refused_naming_it(tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 4."""
    code, _ = _run(_project(tmp_path, SET, work_type="zz-invented"), capsys)
    assert code == 1


def test_a_set_under_any_test_dirs_entry_passes(tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 4 (`test_dirs`)."""
    tail = '[[testing.map]]\ncode = "server/**"\ntests = ["checks/injection/*.py"]\n'
    root = _project(
        tmp_path, {"checks/injection/test_a.py": TEST}, tail=tail, top='test_dirs = ["tests", "checks"]'
    )
    assert _lines(root, capsys) == [f"ok {GATE}"]


@pytest.mark.parametrize("value", ['"tests"', "[1]", '[""]', '["../up"]', '["a\\\\b"]'])
def test_a_malformed_test_dirs_is_refused_naming_it(value: str, tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 4 (the step validates `test_dirs` itself)."""
    root = _project(tmp_path, SET, top=f"test_dirs = {value}")
    with pytest.raises(injection_set.CheckError, match=r"\(setting: test_dirs\)$"):
        injection_set.check(root, {})
    if value.startswith('"'):  # a list of non-strings stops an earlier step first (found-bug)
        assert run_gates.main(["--root", str(root)]) == 1
        assert "(setting: test_dirs)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("tail", "setting"),
    [
        ('[[testing.map]]\ncode = "server/**"\n', "testing.map[1].tests"),
        ('[[testing.map]]\ncode = "server/**"\ntests = ["tests\\\\injection\\\\*"]\n',
         "testing.map[1].tests"),
        ('[testing]\nmap_source = "guessed"\n\n' + MAP, "testing.map_source"),
    ],
)
def test_a_malformed_testing_setting_is_refused_naming_it(
    tail: str, setting: str, tmp_path: Path, capsys
) -> None:
    """REQ-079: brief #1712 answer 4 (`[testing] map` and `map_source`; a backslash glob is
    refused, never matched)."""
    code, _ = _run(_project(tmp_path, SET, tail=tail), capsys)
    assert code == 1
    with pytest.raises(injection_set.CheckError, match=rf"\(setting: {re.escape(setting)}\)$"):
        injection_set.check(_project(tmp_path / "again", SET, tail=tail), {})


@pytest.mark.parametrize("source", ["curated", "generated"])
def test_either_map_source_reads_the_committed_entries(
    source: str, tmp_path: Path, capsys
) -> None:
    """REQ-079: brief #1712 answer 4 and Q-1712-2 (a generated map file does not count)."""
    tail = f'[testing]\nmap_source = "{source}"\n\n'
    assert _lines(_project(tmp_path, SET, tail=tail + MAP), capsys) == [f"ok {GATE}"]
    root = _project(tmp_path / "bare", SET, tail=tail)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "testing-map.toml").write_text(MAP, encoding="utf-8")
    assert _lines(root, capsys) == [
        f"FAIL gates: {GATE}: {injection_set.UNMAPPED} (path class: {MAPPED})"
    ]


def _settings() -> list[str]:
    from common import GOVERNANCE_LEVELS

    rows = [f'governance = {{ level = "{level}" }}' for level in GOVERNANCE_LEVELS]
    rows += [f'execution = "{x}"' for x in ("hosted", "local", "hybrid", "pool")]
    rows += [f'review_mode = "{x}"' for x in ("solo", "team")]
    rows += [f'pr_mode = "{x}"' for x in ("strict", "flow")]
    rows += ['mode = "adopt"']
    return rows


@pytest.mark.parametrize("setting", _settings())
def test_each_setting_runs_the_step_the_same_way(setting: str, tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 4 (`governance`, `execution`, `review_mode`, `pr_mode`, `mode`:
    every value runs the step, red without a set and green with one; no baseline file)."""
    top = setting
    root = _project(tmp_path / "red", {}, top=top)
    if setting.startswith("mode"):
        text = (root / "agk.toml").read_text(encoding="utf-8").replace('mode = "init"\n', "", 1)
        (root / "agk.toml").write_text(text, encoding="utf-8")
    assert _lines(root, capsys) == [
        f"FAIL gates: {GATE}: {injection_set.NO_SET} (path class: {WHERE})"
    ]
    assert not (root / "config" / "agk-baseline" / f"{GATE}.txt").exists()
    assert not hasattr(injection_set, "counts")
    green = _project(tmp_path / "green", SET, top=top)
    if setting.startswith("mode"):
        text = (green / "agk.toml").read_text(encoding="utf-8").replace('mode = "init"\n', "", 1)
        (green / "agk.toml").write_text(text, encoding="utf-8")
    assert _lines(green, capsys) == [f"ok {GATE}"]


@pytest.mark.parametrize("layout", ["installed", "plugin"])
def test_either_kit_layout_gives_the_same_result(layout: str, tmp_path: Path, capsys) -> None:
    """REQ-079: brief #1712 answer 4 (`[kit] layout`)."""
    root = _project(tmp_path, SET, tail=f'{MAP}\n[kit]\nlayout = "{layout}"\n')
    assert _lines(root, capsys) == [f"ok {GATE}"]


def test_the_kits_own_output_is_unchanged(capsys) -> None:
    """REQ-079: brief #1712 answer 5 (the default playbook composes no such gate)."""
    run_gates.main(["--root", str(KIT_ROOT)])
    assert GATE not in capsys.readouterr().out
