"""Kit tests: the `pins` step reads the Python dependency files a project really uses (brief #1838,
ADR-0768; SPEC-0072 rule 4; REQ-079).

With a Python runtime chosen, `gates/pins.py` reads, besides `[project] dependencies` and
`optional-dependencies`, the root `requirements.txt`, each file a `-r` line names and each file of
`[tool.setuptools.dynamic]`; a range, a bare name, a wildcard, a URL or `@` reference and an `-e`
line other than `-e .` fail as `not pinned exactly`, held to the file they are in, naming the rule
and the component class, never a name or a version. Invented package names under a temporary root
(example.com); no network.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from test_pins import HASH, check, gate_rows, node_project, python_project

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

from gates import pins  # noqa: E402

UNPINNED = "FAIL pins: SPEC-0072 rule 4: the stack's build file and lock are not pinned and in step: a direct dependency is not pinned exactly (component class: dependency)"  # noqa: E501
UNREADABLE = "the build file is missing or unreadable (component class: build file)"
WORDS = ("examplelib", "example-requests", "example-extra", "1.0", "1.2.3", "0.4.1", "9.9.9")
DYNAMIC = (
    '[project]\nname = "sample"\nversion = "0.0.0"\ndynamic = ["dependencies"]\n'
    '[tool.setuptools.dynamic]\ndependencies = {file = ["requirements.txt"]}\n'
)


def no_values(text: str) -> None:
    for word in WORDS:
        assert word not in text, word


def py(tmp: Path, req: str | None, lock: str | None = None, **files: str) -> Path:
    if lock is None:
        lock = f"examplelib==1.2.3 \\\n    {HASH}\nexample-extra==0.4.1 \\\n    {HASH}\n"
    root = python_project(tmp, lock=lock)
    if req is not None:
        (root / "requirements.txt").write_text(req, encoding="utf-8")
    for rel, text in files.items():
        path = root / rel.replace("__", "/").replace("_txt", ".txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def held(root: Path) -> list[tuple[str, str]]:
    return pins.check(root, {})


# Answer 1: requirements.txt is read; each kind of float fails, held to the file.


@pytest.mark.parametrize(
    "line",
    [
        "examplelib>=1.0",
        "examplelib~=1.2",
        "examplelib<2",
        "examplelib!=1.0",
        "example-requests",
        "examplelib==1.*",
        "examplelib @ https://example.com/examplelib-1.2.3.tar.gz",
        "https://example.com/examplelib-1.2.3.tar.gz",
        "-e git+https://example.com/examplelib.git#egg=examplelib",
    ],
)
def test_req079_a_floating_requirement_line_fails_held_to_its_file(
    tmp_path: Path, line: str
) -> None:
    root = py(tmp_path, f"{line}\n")
    result = check(root)
    assert result.returncode == 1, result.stdout
    assert result.stdout.splitlines() == [UNPINNED], result.stdout
    no_values(result.stdout + result.stderr)
    assert held(root) == [(UNPINNED.removeprefix("FAIL pins: "), "requirements.txt")]


def test_req079_the_briefs_measured_case_fails_once(tmp_path: Path) -> None:
    result = check(py(tmp_path, "examplelib>=1.0\nexample-requests\n"))
    assert result.returncode == 1 and result.stdout.splitlines() == [UNPINNED]
    assert pins.counts(py(tmp_path / "b", "examplelib>=1.0\nexample-requests\n"), {}) == {
        "requirements.txt": 2
    }


def test_req079_exact_pins_in_the_lock_pass_with_options_and_comments(tmp_path: Path) -> None:
    req = (
        "# the service's own list\n"
        "--index-url https://example.com/simple\n"
        "--extra-index-url https://example.com/extra\n-f https://example.com/wheels\n"
        "--trusted-host example.com\n--no-binary :all:\n--only-binary :none:\n--pre\n\n"
        "-e .\n"
        f"examplelib==1.2.3 \\\n    {HASH}  # pinned\n"
        'example-extra[fast]==0.4.1 ; python_version < "3.12"\n'
    )
    result = check(py(tmp_path, req))
    assert result.returncode == 0, result.stdout
    assert result.stdout == "ok pins\n"


def test_req079_a_crlf_requirements_file_is_read(tmp_path: Path) -> None:
    assert check(py(tmp_path, "examplelib==1.2.3\r\nexample-extra==0.4.1\r\n")).returncode == 0
    assert check(py(tmp_path / "b", "examplelib==1.2.3\r\nexample-extra\r\n")).returncode == 1


def test_req079_a_hash_pinned_requirements_file_passes_when_locked(tmp_path: Path) -> None:
    req = f"examplelib==1.2.3 \\\n    {HASH} \\\n    {HASH}\nexample-extra==0.4.1 {HASH}\n"
    assert check(py(tmp_path, req)).returncode == 0


@pytest.mark.parametrize(
    ("line", "says"),
    [
        ("example-requests==9.9.9", "a direct dependency is not in the lock"),
        ("examplelib==9.9.9", "a direct dependency differs from the lock"),
    ],
)
def test_req079_a_requirements_name_is_looked_up_in_the_lock(
    tmp_path: Path, line: str, says: str
) -> None:
    root = py(tmp_path, f"{line}\n")
    result = check(root)
    assert result.returncode == 1 and says in result.stdout
    no_values(result.stdout)
    assert [f for _, f in held(root)] == ["requirements.lock"]


def test_req079_no_requirements_file_is_today(tmp_path: Path) -> None:
    assert check(py(tmp_path, None)).stdout == "ok pins\n"


# Answer 1: what else is read, and what is not.


def test_req079_an_included_file_is_read_and_held_to_its_own_path(tmp_path: Path) -> None:
    root = py(
        tmp_path,
        "examplelib==1.2.3\n-r requirements/base.txt\n",
        requirements__base_txt="example-extra>=0.4\n",
    )
    result = check(root)
    assert result.returncode == 1 and result.stdout.splitlines() == [UNPINNED]
    assert [f for _, f in held(root)] == ["requirements/base.txt"]
    root2 = py(
        tmp_path / "b",
        "--requirement=requirements/base.txt\n",
        requirements__base_txt="example-extra\n",
    )
    assert [f for _, f in held(root2)] == ["requirements/base.txt"]


def test_req079_an_include_is_relative_to_the_including_file(tmp_path: Path) -> None:
    root = py(
        tmp_path,
        "-r requirements/base.txt\n",
        requirements__base_txt="-r common.txt\n",
        requirements__common_txt="example-extra\n",
    )
    assert [f for _, f in held(root)] == ["requirements/common.txt"]


def test_req079_a_constraints_file_is_not_read(tmp_path: Path) -> None:
    root = py(
        tmp_path, "-c constraints.txt\nexamplelib==1.2.3\n", constraints_txt="example-extra>=0\n"
    )
    assert check(root).returncode == 0


def test_req079_an_include_loop_reads_each_file_once(tmp_path: Path) -> None:
    root = py(
        tmp_path,
        "-r requirements.txt\n-r other.txt\nexamplelib>=1\n",
        other_txt="-r requirements.txt\n-r other.txt\n",
    )
    result = check(root)
    assert result.returncode == 1 and "Traceback" not in result.stderr
    assert pins.counts(root, {}) == {"requirements.txt": 1}


@pytest.mark.parametrize("include", ["../outside.txt", "/etc/example-absolute.txt", "missing.txt"])
def test_req079_an_include_outside_the_root_or_missing_is_refused_by_class(
    tmp_path: Path, include: str
) -> None:
    (tmp_path / "outside.txt").write_text("examplelib\n", encoding="utf-8")
    root = py(tmp_path / "p", f"-r {include}\n")
    result = check(root)
    assert result.returncode == 1, result.stdout
    assert UNREADABLE in result.stdout
    assert include not in result.stdout and "outside" not in result.stdout
    assert [f for _, f in held(root)] == ["requirements.txt"]


def test_req079_the_dynamic_table_names_the_file(tmp_path: Path) -> None:
    root = py(tmp_path, "examplelib>=1.0\n")
    (root / "pyproject.toml").write_text(DYNAMIC, encoding="utf-8")
    result = check(root)
    assert result.returncode == 1 and result.stdout.splitlines() == [UNPINNED]
    assert pins.counts(root, {}) == {"requirements.txt": 1}


def test_req079_the_dynamic_optional_files_are_read(tmp_path: Path) -> None:
    text = DYNAMIC.replace('"dependencies"]', '"dependencies", "optional-dependencies"]') + (
        '[tool.setuptools.dynamic.optional-dependencies]\ndev = {file = "dev.txt"}\n'
    )
    root = py(tmp_path, "examplelib==1.2.3\n", dev_txt="example-extra~=0.4\n")
    (root / "pyproject.toml").write_text(text, encoding="utf-8")
    assert pins.counts(root, {}) == {"dev.txt": 1}


def test_req079_a_dynamic_file_that_is_missing_is_refused_by_class(tmp_path: Path) -> None:
    root = py(tmp_path, None)
    (root / "pyproject.toml").write_text(
        DYNAMIC.replace("requirements.txt", "gone.txt"), encoding="utf-8"
    )
    result = check(root)
    assert result.returncode == 1 and UNREADABLE in result.stdout
    assert "gone" not in result.stdout
    assert [f for _, f in held(root)] == ["pyproject.toml"]


def test_req079_other_requirement_files_are_not_read(tmp_path: Path) -> None:
    root = py(
        tmp_path,
        "examplelib==1.2.3\n",
        **{"requirements-dev.txt": "example-extra\n", "requirements.in": "examplelib\n"},
        requirements__test_txt="example-extra\n",
    )
    assert check(root).returncode == 0


def test_req079_a_name_in_both_files_is_one_finding_held_to_requirements(tmp_path: Path) -> None:
    root = py(tmp_path, "examplelib>=1.0\n")
    assert pins.counts(root, {}) == {"requirements.txt": 1}


def test_req079_a_secret_shaped_value_is_never_printed(tmp_path: Path) -> None:
    fake = "ghp_" + "Z" * 36
    root = py(tmp_path, f"examplelib @ https://user:{fake}@example.com/x.tar.gz\n")
    result = check(root)
    assert result.returncode == 1 and fake not in result.stdout + result.stderr


# Answer 5: settings.


def test_req079_a_node_runtime_never_reads_requirements(tmp_path: Path) -> None:
    root = node_project(tmp_path)
    (root / "requirements.txt").write_text("examplelib>=1\n", encoding="utf-8")
    assert check(root).stdout == "ok pins\n"


def test_req079_a_capitalised_python_runtime_reads_requirements(tmp_path: Path) -> None:
    root = py(tmp_path, "example-extra\n")
    record = root / "docs" / "adr" / "0002-stack-options.md"
    text = record.read_text(encoding="utf-8").replace(
        "Parts: python 3.12.7", "Parts: Python 3.12.7"
    )
    record.write_text(text, encoding="utf-8")
    assert check(root).returncode == 1


def test_req079_no_work_type_is_still_not_run(tmp_path: Path) -> None:
    root = py(tmp_path, "examplelib>=1\n")
    (root / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    assert "not run: no stack chosen" in check(root).stdout


def test_req079_an_adopted_project_holds_requirements_on_its_first_run(tmp_path: Path) -> None:
    root = py(tmp_path, "examplelib>=1.0\n")
    text = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text('mode = "adopt"\n' + text, encoding="utf-8")
    rows = gate_rows(root)
    assert (True, "pins (baseline)") in rows, rows
    base = root / "config" / "agk-baseline" / "pins.txt"
    assert base.read_text(encoding="utf-8") == "requirements.txt 1\n"


def test_req079_an_older_pins_baseline_fails_the_new_findings(tmp_path: Path) -> None:
    root = py(tmp_path, "examplelib>=1.0\n")
    text = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text('mode = "adopt"\n' + text, encoding="utf-8")
    (root / "config" / "agk-baseline").mkdir(parents=True)
    (root / "config" / "agk-baseline" / "pins.txt").write_text(
        "pyproject.toml 0\n", encoding="utf-8"
    )
    rows = gate_rows(root)
    assert any(p is False and "SPEC-0072 rule 7" in line for p, line in rows), rows


# Answer 4: the class stays closed.


def test_req079_python_files_lists_each_form_a_project_uses(tmp_path: Path) -> None:
    root = py(tmp_path, "-r requirements/base.txt\n", requirements__base_txt="examplelib==1.2.3\n")
    assert [rel for rel, _ in pins.python_files(root)] == [
        "pyproject.toml",
        "requirements.txt",
        "requirements/base.txt",
    ]
    (root / "pyproject.toml").write_text(DYNAMIC, encoding="utf-8")
    assert [rel for rel, _ in pins.python_files(root)] == [
        "pyproject.toml",
        "requirements.txt",
        "requirements/base.txt",
    ]


@pytest.mark.parametrize("name", ["pins.py", "licences.py"])
def test_req079_no_gate_reads_a_python_dependency_file_by_its_own_literal(name: str) -> None:
    code = (KIT_ROOT / "scripts" / "agk" / "gates" / name).read_text(encoding="utf-8")
    body = code.split('"""', 2)[2]  # the module's text after its docstring
    literal = re.findall(r"[\"']requirements\.txt[\"']", body)
    assert len(literal) == (1 if name == "pins.py" else 0), literal
