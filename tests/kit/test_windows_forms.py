# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The forms a Windows machine writes are read one way by every reader (REQ-079; brief #1839,
ADR-0769).

A Git for Windows checkout (`core.autocrlf = true`) holds CRLF files that CI's checkout holds as
LF: the format step of each pack gives an LF file and its CRLF twin the same result. A `test_dirs`
entry written `tests\\`, `.\\tests`, `.\\tests\\`, `./tests` or `tests/` is the folder `tests` for
every reader that reads it through `common.load_config`, and a scan of `scripts/agk/` fails any
new reader that reads `test_dirs` from the raw settings, naming the file. Fixtures in `tmp_path`
only: invented data (example.com), no network.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
AGK = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))
import common  # noqa: E402
import doctor  # noqa: E402
import impact  # noqa: E402
import test_node_pack  # noqa: E402
import test_python_pack  # noqa: E402
from gates import bom, environment_settings, node_pack, python_pack, tests_floor  # noqa: E402

FORMS = ["tests", "tests/", "./tests", "tests\\", ".\\tests", ".\\tests\\"]
RAW = {"config_source", "loads", "load"}  # the raw settings: `agk.toml` read past load_config


@pytest.fixture(autouse=True)
def _no_bill(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bom, "applies", lambda _root: False)


def twin(text: str) -> str:
    return text.replace("\n", "\r\n")


@pytest.mark.parametrize("pack", ["node", "python"])
def test_each_pack_gives_an_lf_file_and_its_crlf_twin_the_same_result(
    pack: str, tmp_path: Path
) -> None:
    """REQ-079: brief #1839 answer 4 (the format step of each pack judges content)."""
    results = []
    for name in ("lf", "crlf"):
        root = tmp_path / name
        root.mkdir()
        if pack == "node":
            code = test_node_pack.CLEAN
            test_node_pack.sample(root, code if name == "lf" else twin(code))
            found = [("frontend/greet.ts", "frontend/**")]
            results.append(node_pack.format_check(root, found, {}))
        else:
            code = test_python_pack.CLEAN
            test_python_pack.sample(root, code if name == "lf" else twin(code))
            found = [("api/app.py", "api/**")]
            results.append(python_pack.format_check(root, found, {}))
    assert results == [[], []]


def write(root: Path, form: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "agk.toml").write_text(f"test_dirs = ['{form}']\n", encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_orders.py").write_text("# REQ-001 example.com\n", encoding="utf-8")
    (root / "tests" / "orders.spec.ts").write_text("// example.com\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("form", FORMS)
def test_every_reader_of_test_dirs_reads_one_folder(form: str, tmp_path: Path) -> None:
    """REQ-079: brief #1839 answers 2 and 4 (load_config, impact, markers, floors, doctor)."""
    root = write(tmp_path, form)
    dirs = common.load_config(root)["test_dirs"]
    assert dirs == ["tests"]
    assert common.test_dirs(root) == ["tests"] and common.test_dirs(root, [form]) == ["tests"]
    assert impact.in_test_dirs("tests/test_orders.py", dirs)
    assert not impact.in_test_dirs("app/core/orders.py", dirs)
    markers = common.find_ac_markers(root, dirs, ["test_*.py"], [])
    assert markers, form
    assert tests_floor.folders(root) == environment_settings.test_folders(root) == ["tests"]
    assert doctor.outside_test_dirs_lines(root) == []


def _is_raw(node: ast.AST, raw: set[str]) -> bool:
    """A call that reads the raw settings, or a name bound to one."""
    if isinstance(node, ast.Call):
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        return name in RAW
    return isinstance(node, ast.Name) and node.id in raw


def _key(node: ast.AST, raw: set[str]) -> object:
    """The constant key a raw read takes (`raw[...]` or `raw.get(...)`), or None."""
    if isinstance(node, ast.Subscript) and _is_raw(node.value, raw):
        return getattr(node.slice, "value", None)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
        if node.func.attr == "get" and _is_raw(node.func.value, raw):
            return getattr(node.args[0], "value", None)
    return None


def readers_past_load_config(folder: Path) -> list[str]:
    """The files under `folder` that read `test_dirs` from the raw settings (`config_source(...)`
    or a TOML read), not from `common.load_config`."""
    out = []
    for path in sorted(folder.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        raw: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and _is_raw(node.value, raw):
                raw.update(t.id for t in node.targets if isinstance(t, ast.Name))
        if any(_key(node, raw) == "test_dirs" for node in ast.walk(tree)):
            out.append(path.relative_to(folder).as_posix())
    return out


def test_no_reader_of_test_dirs_reads_past_load_config() -> None:
    """REQ-079: brief #1839 answer 4 (the class stays closed)."""
    assert readers_past_load_config(AGK) == []


@pytest.mark.parametrize(
    "body",
    [
        'source = config_source(root)\ndirs = source["test_dirs"]\n',
        'dirs = config_source(root).get("test_dirs", [])\n',
        'dirs = tomllib.loads(text)["test_dirs"]\n',
    ],
)
def test_the_scan_names_a_new_raw_reader(body: str, tmp_path: Path) -> None:
    """REQ-079: brief #1839 answer 4 (a planted reader fails naming the file, never the line)."""
    (tmp_path / "gates").mkdir()
    (tmp_path / "gates" / "planted.py").write_text(body, encoding="utf-8")
    (tmp_path / "fine.py").write_text('dirs = load_config(root)["test_dirs"]\n', encoding="utf-8")
    assert readers_past_load_config(tmp_path) == ["gates/planted.py"]
