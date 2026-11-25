"""Tests of the `committed-secrets` and `environment-settings` steps (SPEC-0072 rules 2 and 12
build (f); REQ-079 AC4; brief #1593, ADR-0673).

A tracked environment file, an unignored one, a planted fake key, an example settings file with a
value and a setting the code reads that the example file does not name are each red, naming the
gate id, the rule and the path class and never a value; `mode = "adopt"` holds the findings; the
kit's own tree is green. Fixtures in `tmp_path` only: invented data (example.com), an invented key
shape built at run time, no network.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import run_gates  # noqa: E402
from gates import environment_settings  # noqa: E402

GIT = [
    "git",
    "-c",
    "user.name=Ada",
    "-c",
    "user.email=ada@example.com",
    "-c",
    "commit.gpgsign=false",
]
# An invented key shape, built here so that no tracked file holds one (principle 9).
FAKE = "AKIA" + "QX7ZB3MPL2W6RTNJ"
APP = 'import os\n\nHOST = os.environ["SHOP_HOST"]\nLIMIT = os.getenv("SHOP_LIMIT", "10")\n'


def _project(tmp_path: Path, files: dict[str, str], mode: str = "init") -> Path:
    shutil.copytree(KIT_ROOT / "config" / "playbooks", tmp_path / "config" / "playbooks")
    files = {"agk.toml": f'mode = "{mode}"\n', ".gitignore": ".env\n", **files}
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # nosec B603 B607 - fixed
    subprocess.run([*GIT, "-C", str(tmp_path), "add", "-A", "-f"], check=True)  # nosec B603 - fixed
    subprocess.run([*GIT, "-C", str(tmp_path), "commit", "-q", "-m", "x"], check=True)  # nosec B603 - fixed
    return tmp_path


def _run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = run_gates.main(["--root", str(root)])
    return code, capsys.readouterr().out


CLEAN = {"app/main.py": APP, ".env.example": "# names only\nSHOP_HOST=\nSHOP_LIMIT=<a number>\n"}


def test_a_clean_sample_is_green(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079 AC4."""
    code, out = _run(_project(tmp_path, CLEAN), capsys)
    assert code == 0, out
    assert "ok secrets\n" in out and "ok environment-settings\n" in out


@pytest.mark.parametrize(
    ("files", "gate", "cls"),
    [
        ({".env.local": "SHOP_HOST=shop.example.com\n"}, "secrets", "secret files (tracked)"),
        ({"config/key.py": f'TOKEN = "{FAKE}"\n'}, "secrets", "tracked files (a secret shape)"),
        (
            {".env.example": "SHOP_HOST=shop.example.com\nSHOP_LIMIT=\n"},
            "secrets",
            "example settings file (a value)",
        ),
        (
            {".env.example": "SHOP_HOST=\n"},
            "environment-settings",
            "settings read in code (not in the example file)",
        ),
        (
            {"app/jobs.py": 'import os\nHOST = os.environ.get("SHOP_HOST", "shop.example.com")\n'},
            "environment-settings",
            "settings read in code (a required one with a default)",
        ),
    ],
)
def test_each_finding_is_red_naming_the_gate_and_class_never_a_value(
    files: dict[str, str],
    gate: str,
    cls: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-079 AC4: principle 8."""
    code, out = _run(_project(tmp_path, {**CLEAN, **files}), capsys)
    assert code == 1
    assert f"FAIL gates: {gate}: SPEC-0072 rule 2: " in out and f"(path class: {cls})" in out, out
    for value in (FAKE, "shop.example.com", "SHOP_HOST", "SHOP_LIMIT", ".env.local"):
        assert value not in out


def test_an_unignored_environment_file_is_red(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: on disk, untracked, and not ignored by `.gitignore`."""
    root = _project(tmp_path, CLEAN)
    (root / ".gitignore").write_text("", encoding="utf-8")
    (root / ".ENV").write_text("SHOP_HOST=shop.example.com\n", encoding="utf-8")
    code, out = _run(root, capsys)
    assert code == 1 and "(path class: environment files (not ignored))" in out
    (root / ".gitignore").write_text(".env\n.ENV\n", encoding="utf-8")
    assert _run(root, capsys)[0] == 0


def test_no_example_file_fails_only_when_the_code_reads_a_setting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: Q-1593-1."""
    assert _run(_project(tmp_path / "a", {"app/main.py": "print(1)\n"}), capsys)[0] == 0
    code, out = _run(_project(tmp_path / "b", {"app/main.py": APP}), capsys)
    assert code == 1 and "settings read in code (not in the example file)" in out


def test_kit_folders_and_tests_are_not_the_project_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: the kit's installed folders and the test folders read their own settings."""
    read = 'import os\nX = os.environ["AGK_EXAMPLE"]\n'
    files = {"scripts/agk/x.py": read, ".claude/hooks/x.py": read, "tests/test_x.py": read}
    assert _run(_project(tmp_path, files), capsys)[0] == 0


BAD_DIRS = "test_dirs is a list of folder paths inside the repository (setting: test_dirs)"


BAD_VALUES = ["[1]", '["tests", 2]', '"tests"', '[""]', '["../up"]', '["a/*"]']


@pytest.mark.parametrize("value", BAD_VALUES)
@pytest.mark.parametrize("work_type", [None, "mcp-server", "api-service"])
def test_a_malformed_test_dirs_is_refused_naming_it(
    value: str, work_type: str | None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: brief #1725 (ADR-0728): one refusal naming `test_dirs`, never a traceback."""
    toml = f'mode = "init"\ntest_dirs = {value}\n'
    if work_type:
        toml += f'[delivery]\nwork_type = "{work_type}"\n'
    files = {"agk.toml": toml, "app/main.py": "print(1)\n", "docs/architecture.md": "# A\n"}
    root = _project(tmp_path, files)
    with pytest.raises(environment_settings.CheckError, match=r"\(setting: test_dirs\)$"):
        environment_settings.check(root, {})
    code, out = _run(root, capsys)
    assert code == 1 and out.splitlines() == [f"FAIL gates: {BAD_DIRS}"], out


@pytest.mark.parametrize("value", ["[]", '["tests", "./checks/", "e2e/web"]'])
def test_a_list_of_folders_is_read_as_before(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: brief #1725: an empty list and a list of folders are taken as they were."""
    files = {"agk.toml": f'mode = "init"\ntest_dirs = {value}\n', "app/main.py": "print(1)\n"}
    assert _run(_project(tmp_path, files), capsys)[0] == 0


def test_a_back_slash_test_folder_reads_as_the_same_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC7: brief #1748: `.\\tests\\` is the folder `tests`, as the tests floor reads it."""
    read = 'import os\nX = os.environ["AGK_EXAMPLE"]\n'
    toml = "mode = \"init\"\ntest_dirs = ['.\\tests\\']\n"
    root = _project(tmp_path, {"agk.toml": toml, "tests/test_x.py": read})
    assert environment_settings.test_folders(root) == ["tests"]
    assert _run(root, capsys)[0] == 0


HELD = "secrets (baseline): 1 held (path class: tracked files (a secret shape))"
BASE = "config/agk-baseline/committed-secrets.txt"  # `secrets.txt` is a secret file name


def test_adopt_mode_holds_the_findings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """REQ-079: brief #1777 answers 1 and 2: held in the baseline, counted, never `ok secrets`."""
    files = {"config/key.py": f'TOKEN = "{FAKE}"\n', "app/main.py": APP}
    root = _project(tmp_path, files, mode="adopt")
    code, out = _run(root, capsys)
    assert code == 0, out
    assert HELD + "\n" in out and "ok secrets" not in out, out
    assert (root / BASE).read_text(encoding="utf-8") == "config/key.py 1\n"
    assert FAKE not in out and "config/key.py" not in out
    subprocess.run([*GIT, "-C", str(root), "add", "-A"], check=True)  # nosec B603 - fixed
    code, out = _run(root, capsys)  # named and counted on every run
    assert code == 0 and HELD + "\n" in out, out


@pytest.mark.parametrize("rel", ["config/other.py", "config/key.py"])
def test_adopt_mode_fails_a_new_secret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], rel: str
) -> None:
    """REQ-079: brief #1777 answer 7: a key added after adoption, or a second key in a held file,
    fails as rule 7, never naming the file or the value."""
    files = {"config/key.py": f'TOKEN = "{FAKE}"\n', "app/main.py": APP}
    root = _project(tmp_path, files, mode="adopt")
    assert _run(root, capsys)[0] == 0
    path = root / rel
    path.write_text(path.read_text(encoding="utf-8") if path.is_file() else "", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f'OTHER = "{FAKE[:-1]}Q"\n')
    subprocess.run([*GIT, "-C", str(root), "add", "-A"], check=True)  # nosec B603 - fixed
    code, out = _run(root, capsys)
    assert code == 1, out
    assert "FAIL gates: secrets: SPEC-0072 rule 7" in out, out
    assert FAKE[:8] not in out and rel not in out


def test_an_unset_mode_fails_and_writes_no_baseline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1777 answer 5: `mode` unset fails as today; no baseline is written."""
    files = {"agk.toml": "", "config/key.py": f'TOKEN = "{FAKE}"\n', "app/main.py": APP}
    root = _project(tmp_path, files)
    code, out = _run(root, capsys)
    assert code == 1, out
    assert "FAIL gates: secrets: SPEC-0072 rule 2" in out and "(baseline)" not in out, out
    assert not (root / "config" / "agk-baseline").exists()


def test_doctor_warns_while_the_baseline_holds_a_secret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079: brief #1777 answer 3: one warning naming the path class and the runbook."""
    import doctor  # noqa: PLC0415 - the one test of the doctor's line

    files = {"config/key.py": f'TOKEN = "{FAKE}"\n', "app/main.py": APP}
    root = _project(tmp_path, files, mode="adopt")
    assert doctor.held_secret_lines(root) == []
    assert _run(root, capsys)[0] == 0
    lines = doctor.held_secret_lines(root)
    assert len(lines) == 1, lines
    assert lines[0].startswith("warn secrets: ") and "docs/runbooks/leaked-secret.md" in lines[0]
    assert "(path class: config/agk-baseline/)" in lines[0] and "config/key.py" not in lines[0]
    (root / BASE).write_text("", encoding="utf-8")
    assert doctor.held_secret_lines(root) == []


def test_the_kits_own_tree_is_green() -> None:
    """REQ-079 AC4: the kit's own repository runs `default.toml`'s two checks."""
    for step in ("committed-secrets", "environment-settings"):
        module = run_gates.step_module(step)
        assert module is not None and module.check(KIT_ROOT, {}) == [], step


# Brief #1928 (ADR-0796): an exact dependency version after a package name in a dependency file.
LOCK = (
    '{\n  "packages": {\n    "node_modules/@typescript-eslint/visitor-keys": {\n'
    '      "version": "{V}"\n    }\n  },\n  "dependencies": {\n'
    '    "@typescript-eslint/visitor-keys": "{V}",\n    "left-pad": "^3.4.3"\n  }\n}\n'
)
PIN = '    "@typescript-eslint/visitor-keys": "{V}",\n'
# Versions built here, so that no tracked file holds a version after a key-like name.
V, W = ".".join(("8", "74", "0")), ".".join("123")
SHAPE = "tracked files (a secret shape)"


def _secrets(tmp_path: Path, files: dict[str, str]) -> list[tuple[str, str, int]]:
    from gates import committed_secrets  # noqa: PLC0415

    files = {k: v.replace("{V}", V).replace("{W}", W) for k, v in files.items()}
    return [f for f in committed_secrets.findings(_project(tmp_path, files)) if f[0] == SHAPE]


@pytest.mark.parametrize(
    ("rel", "text", "want"),
    [
        ("package-lock.json", LOCK, []),
        ("sub/Package-Lock.JSON", LOCK.replace("\n", "\r\n"), []),
        ("package.json", '{"dependencies": {"api-keys": "{W}", "x-keys": "{V}-rc.1"}}\n', []),
        ("yarn.lock", '"@scope/visitor-keys@^1.0.0":\n  "@scope/visitor-keys": "{W}"\n', []),
        ("config/app.json", PIN, [(SHAPE, "config/app.json", 1)]),
        ("package-lock.json.bak", PIN, [(SHAPE, "package-lock.json.bak", 1)]),
        ("package.json", '{"token": "{W}"}\n', [(SHAPE, "package.json", 1)]),
        ("package.json", '{"API_KEY": "{W}"}\n', [(SHAPE, "package.json", 1)]),
        ("composer.lock", 'api_key = "{W}"\n', [(SHAPE, "composer.lock", 1)]),
        (
            "package-lock.json",
            '    "@scope/visitor-keys": "' + "9f3c2a7b1e" * 4 + '",\n',
            [(SHAPE, "package-lock.json", 1)],
        ),
    ],
)
def test_an_exact_pin_in_a_dependency_file_is_no_secret(
    tmp_path: Path, rel: str, text: str, want: list[tuple[str, str, int]]
) -> None:
    """REQ-079 AC4: brief #1928 answers 1 and 5: only a version after a package name in a
    dependency file is not counted; the same line elsewhere and every other shape count."""
    assert _secrets(tmp_path, {rel: text, "app/main.py": APP}) == want


def test_a_custom_pattern_in_a_dependency_file_still_counts(tmp_path: Path) -> None:
    """REQ-079 AC4: brief #1928 answer 4: a `[guard] patterns` match counts, version-shaped."""
    toml = 'mode = "init"\n[guard]\npatterns = [{ name = "shop", regex = "8\\\\.74\\\\.0" }]\n'
    files = {"agk.toml": toml, "yarn.lock": PIN, "app/main.py": APP}
    assert _secrets(tmp_path, files) == [(SHAPE, "yarn.lock", 1)]


def test_a_baseline_of_false_findings_reads_lower_and_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """REQ-079 AC4: brief #1928 answer 4: a held count of 1 reads 0; a new real finding fails."""
    files = {"package-lock.json": LOCK.replace("{V}", V), "app/main.py": APP, BASE: "package-lock.json 1\n"}
    root = _project(tmp_path, files, mode="adopt")
    code, out = _run(root, capsys)
    assert code == 0 and "baseline secrets: a count fell in 1" in out, out
    (root / "config" / "key.py").write_text(f'TOKEN = "{FAKE}"\n', encoding="utf-8")
    subprocess.run([*GIT, "-C", str(root), "add", "-A"], check=True)  # nosec B603 - fixed
    code, out = _run(root, capsys)
    assert code == 1 and "FAIL gates: secrets: SPEC-0072 rule 7" in out, out


def test_every_file_the_pins_gate_reads_is_a_dependency_file() -> None:
    """REQ-079 AC4: brief #1928 answer 7: the class stays closed."""
    from gates import committed_secrets, pins  # noqa: PLC0415

    for _, build_file, lock_file, _ in pins.STACKS.values():
        for name in (build_file, lock_file, pins.REQUIREMENTS):
            assert name.casefold() in committed_secrets.DEPENDENCY_FILES, name
