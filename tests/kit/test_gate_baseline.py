"""Tests of the baseline and ratchet of adopted and upgraded projects (SPEC-0072 rule 7; REQ-079
AC5; brief #1600, ADR-0680).

On a sample adopted tree (`mode = "adopt"`, an api-service with a disallowed layer import) the
first run writes `config/agk-baseline/layers.txt` and passes, and no other file changes; after
that a finding in a file not listed fails, a count that rises fails, and a fixed finding passes
and prints that a count fell, which `run_gates.py --baseline` writes lowered and never raises. In
`mode = "init"` nothing is written and the finding fails as before. A pull request that raises a
baseline line, adds one or adds a file without an ADR that names it is refused by
`check_protected_changes.py`, while one that only lowers needs no ADR. Paths are forward
slashes, sorted bytewise; no output names a file or a value. Fixtures in `tmp_path` only:
invented data (example.com), no network.
"""

from __future__ import annotations

import hashlib
import shutil
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import run_gates  # noqa: E402
from gates import baseline  # noqa: E402

PLAYBOOKS = KIT_ROOT / "config" / "playbooks"
BAD = "from api import routes\n"  # data may not import api (the api-service playbook)
SAMPLE = {
    "contracts/__init__.py": "",
    "contracts/orders.py": "SHAPE = {'site': 'https://example.com'}\n",
    "api/__init__.py": "",
    "api/routes.py": "from domain import rules\n",
    "domain/__init__.py": "",
    "domain/rules.py": "import data.store\n",
    "data/__init__.py": "",
    "data/store.py": BAD,
    "data/old_cache.py": BAD + "import api.routes\n",
}
FILE = "config/agk-baseline/layers.txt"


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the baseline opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _project(tmp_path: Path, mode: str = "adopt") -> Path:
    shutil.copytree(PLAYBOOKS, tmp_path / "config" / "playbooks")
    text = f'mode = "{mode}"\n\n[delivery]\nwork_type = "api-service"\n'
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    for rel, body in SAMPLE.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(body, encoding="utf-8")
    return tmp_path


def _gates(root: Path, capsys, *extra: str) -> tuple[int, str]:
    code = run_gates.main([*extra, "--root", str(root)])
    return code, capsys.readouterr().out


def _tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def test_the_text_is_forward_slashes_sorted_bytewise() -> None:
    """REQ-079 AC5: two machines write the same file."""
    text = baseline.text({"b/x.py": 1, "a\\Z.py": 2, "a/a.py": 3, "c.py": 0})
    assert text == "a/Z.py 2\na/a.py 3\nb/x.py 1\n"
    assert baseline.parse(text) == {"a/Z.py": 2, "a/a.py": 3, "b/x.py": 1}
    assert baseline.name("standards python-pyproject lint") == "standards-python-pyproject-lint"


def test_the_first_run_of_an_adopted_tree_writes_the_baseline_and_passes(
    tmp_path: Path, capsys
) -> None:
    """REQ-079 AC5: green on the first run; no tracked file but the baseline changes."""
    root = _project(tmp_path)
    before = _tree(root)
    code, out = _gates(root, capsys)
    assert code == 0, out
    assert "baseline layers: written (path class: config/agk-baseline/)" in out
    assert (root / FILE).read_text(encoding="utf-8") == "data/old_cache.py 2\ndata/store.py 1\n"
    after = _tree(root)
    assert {k: v for k, v in after.items() if k != FILE} == before
    code, out = _gates(root, capsys)
    assert code == 0 and "ok layers (baseline)" in out, out


def test_a_new_finding_fails_and_names_no_file(tmp_path: Path, capsys) -> None:
    """REQ-079 AC5: a finding in a file the baseline does not list."""
    root = _project(tmp_path)
    _gates(root, capsys)
    (root / "data/new_repo.py").write_text(BAD, encoding="utf-8")
    code, out = _gates(root, capsys)
    assert code == 1
    assert "FAIL gates: layers: SPEC-0072 rule 7: " in out
    assert "(path class: config/agk-baseline/)" in out
    for value in ("new_repo", "store.py", "old_cache"):
        assert value not in out


def test_a_count_that_rises_fails(tmp_path: Path, capsys) -> None:
    """REQ-079 AC5."""
    root = _project(tmp_path)
    _gates(root, capsys)
    (root / "data/store.py").write_text(BAD + "import api\n", encoding="utf-8")
    code, out = _gates(root, capsys)
    assert code == 1 and "SPEC-0072 rule 7" in out


def test_a_fixed_finding_prints_the_lower_count_and_never_raises(tmp_path: Path, capsys) -> None:
    """REQ-079 AC5: the next build commits the lowered baseline."""
    root = _project(tmp_path)
    _gates(root, capsys)
    (root / "data/old_cache.py").write_text(BAD, encoding="utf-8")
    code, out = _gates(root, capsys)
    assert code == 0, out
    assert "baseline layers: a count fell in 1 file (path class: config/agk-baseline/)" in out
    assert (root / FILE).read_text(encoding="utf-8").startswith("data/old_cache.py 2\n")
    code, out = _gates(root, capsys, "--baseline")
    assert code == 0, out
    assert (root / FILE).read_text(encoding="utf-8") == "data/old_cache.py 1\ndata/store.py 1\n"
    (root / "data/store.py").write_text(BAD * 3, encoding="utf-8")
    (root / "data/other.py").write_text(BAD, encoding="utf-8")
    _gates(root, capsys, "--baseline")
    assert (root / FILE).read_text(encoding="utf-8") == "data/old_cache.py 1\ndata/store.py 1\n"


def test_init_mode_writes_nothing_and_fails_as_before(tmp_path: Path, capsys) -> None:
    """REQ-079 AC5: in `mode = "init"` the baseline is empty from the first commit."""
    root = _project(tmp_path, mode="init")
    code, out = _gates(root, capsys)
    assert code == 1 and "SPEC-0072 rule 5" in out
    assert not (root / "config/agk-baseline").exists()


# check_protected_changes.py: the `repo` fixture of conftest.py (a project with `config/`
# protected, as every project template has).
NAMED = "config/agk-baseline/layers.txt"
ADR = f"# ADR-0002: x\n\n- Status: Proposed\n\nIt raises `{NAMED}` in `config/`.\n"


@pytest.fixture
def adopted(repo):
    repo.commit(
        {
            "config/protected-paths.txt": "config/\nscripts/agk/\n",
            NAMED: "data/old_cache.py 2\ndata/store.py 1\n",
            "src/app.py": "x = 1\n",
        },
        "base",
    )
    repo.branch()
    return repo


def _protected(repo):
    return repo.run("check_protected_changes.py", "--base", "main")


def test_a_lowered_baseline_needs_no_adr(adopted) -> None:
    """REQ-079 AC5."""
    adopted.commit({NAMED: "data/old_cache.py 1\n"})
    proc = _protected(adopted)
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize(
    "text",
    [
        "data/old_cache.py 3\ndata/store.py 1\n",  # a line rises
        "data/new.py 1\ndata/old_cache.py 2\ndata/store.py 1\n",  # a new line
    ],
)
def test_a_raised_or_new_line_without_an_adr_is_refused(adopted, text: str) -> None:
    """REQ-079 AC5: the refusal names the rule and the path class, never a file or a count."""
    adopted.commit({NAMED: text})
    proc = _protected(adopted)
    assert proc.returncode == 1
    assert "SPEC-0072 rule 7" in proc.stdout and "config/agk-baseline/" in proc.stdout
    assert "new.py" not in proc.stdout and "old_cache" not in proc.stdout


def test_a_new_baseline_file_or_a_deleted_one_needs_an_adr(adopted) -> None:
    """REQ-079 AC5: a later pull request's new file is new lines."""
    adopted.commit({"config/agk-baseline/standards-python-pyproject-lint.txt": "a.py 1\n"})
    assert _protected(adopted).returncode == 1
    adopted.commit({"config/agk-baseline/standards-python-pyproject-lint.txt": None, NAMED: None})
    assert _protected(adopted).returncode == 1


def test_an_adr_that_names_the_file_lets_it_rise(adopted) -> None:
    """REQ-079 AC5."""
    adopted.commit({NAMED: "data/old_cache.py 3\ndata/store.py 1\n", "docs/adr/0002-x.md": ADR})
    proc = _protected(adopted)
    assert proc.returncode == 0, proc.stdout
