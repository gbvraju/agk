"""Install and upgrade on Windows (brief #263 build c, items 7 and 9; ADR-0160).

Item 7: the doctor compares the kit's files ignoring the difference between CRLF and LF, and the
installed `.gitattributes` pins `eol=lf` for every path the kit installs. Item 9: an invalid
`config/reviewers.yaml` names the key and the reason, never only "is invalid; run --check".
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from fnmatch import fnmatch
from pathlib import Path

import doctor

ROOT = Path(__file__).resolve().parents[2]
REVIEWERS = ROOT / "scripts" / "agk" / "reviewers.py"


def test_the_doctor_does_not_report_a_crlf_checkout_of_a_kit_file_as_differing(tmp_path):
    """Brief #263 item 7 (REQ-039): Git for Windows checks text out with CRLF."""
    kit, root = tmp_path / "kit", tmp_path / "root"
    for base, data in ((kit, b"a\nb\n"), (root, b"a\r\nb\r\n")):
        (base / "scripts" / "agk").mkdir(parents=True)
        (base / "scripts" / "agk" / "x.py").write_bytes(data)
    missing, differs = doctor.compare_tree(root, kit, ["scripts/agk/x.py"], {})
    assert (missing, differs) == ([], [])
    (root / "scripts" / "agk" / "x.py").write_bytes(b"a\r\nc\r\n")
    assert doctor.compare_tree(root, kit, ["scripts/agk/x.py"], {})[1] == ["scripts/agk/x.py"]


def eol_patterns() -> list[str]:
    text = (ROOT / "kit" / "templates" / "gitattributes").read_text(encoding="utf-8")
    return [
        line.split()[0]
        for line in text.splitlines()
        if line and not line.startswith("#") and "eol=lf" in line.split()[1:]
    ]


def matched(rel: str, pattern: str) -> bool:
    """A gitattributes pattern: `dir/**` matches everything below `dir/`; any other pattern is
    a path, or a file-name glob without a slash."""
    if pattern.endswith("/**"):
        return rel.startswith(pattern[:-2])
    return rel == pattern or ("/" not in pattern and fnmatch(rel.rsplit("/", 1)[-1], pattern))


def test_the_installed_gitattributes_pins_lf_for_every_path_the_kit_installs():
    """Brief #263 item 7 (REQ-039): `text eol=lf` for the kit's paths, so a Windows checkout of
    them stays LF; the project's own files are left to its own settings."""
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    installed = [
        p
        for p in [*manifest["verbatim"], *manifest.get("experimental", [])]
        if not p.startswith(("kit/", "tests/kit_dev/"))
        and p not in ("scripts/agk/init.py", "scripts/agk/adopt.py")
    ]
    patterns = eol_patterns()
    assert patterns, "no eol=lf line"
    for rel in installed:
        assert any(matched(rel, p) for p in patterns), rel
    assert "*" not in patterns  # the project's own files keep the project's settings


def reviewers(tmp_path: Path, text: str, *args: str) -> subprocess.CompletedProcess:
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "reviewers.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "config" / "protected-paths.txt").write_text("config/\n", encoding="utf-8")
    git = ["git", "init", "-q", str(tmp_path)]
    subprocess.run(git, check=True)  # nosec B603 - fixed argument list, no shell
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(REVIEWERS), *args], cwd=tmp_path, capture_output=True, text=True
    )


GOOD = (
    "version: 1\n"
    "classes:\n"
    "  protected: {paths: [config/], approvers: [maintainers]}\n"
    "teams:\n"
    '  maintainers: {github_team: "@someone"}\n'
)
UNDER_TEAMS = GOOD + "  spec_approvers: [someone]\n"


def test_a_top_level_key_indented_under_teams_is_named_with_the_reason(tmp_path):
    """Brief #263 item 9 (REQ-039): the pilot's `spec_approvers` indented under `teams:`."""
    for args in (["--codeowners"], ["--check-codeowners"], ["--check"]):
        out = reviewers(tmp_path, UNDER_TEAMS, *args)
        text = out.stdout + out.stderr
        assert out.returncode == 1, (args, text)
        assert "spec_approvers is indented under teams" in text, (args, text)
        assert "start of its line" in text, (args, text)
        assert "github_team must be" not in text, (args, text)


def test_an_invalid_file_names_each_problem_not_only_run_check(tmp_path):
    """Brief #263 item 9 (REQ-039): the generator's refusal names the key and the reason."""
    out = reviewers(tmp_path, GOOD.replace("version: 1", "version: 2"), "--codeowners")
    text = out.stdout + out.stderr
    assert out.returncode == 1 and "config/reviewers.yaml is invalid: version must be 1" in text
    assert "@someone" not in text


def test_a_valid_file_still_renders(tmp_path):
    """Brief #263 item 9: no change for a valid file."""
    out = reviewers(tmp_path, GOOD, "--codeowners")
    assert out.returncode == 0 and "@someone" in out.stdout


# --- item 10: every kit script reads and writes text as UTF-8 ------------------------------------

PROCESS = {"run", "check_output", "Popen", "call", "check_call"}


def unpinned(path: Path) -> list[str]:
    """Text I/O in PATH that leaves the encoding to the platform: a `read_text`, `write_text` or
    text `open` without `encoding`, a subprocess call with `text=True` and no `encoding`, or a
    read of `sys.stdin` (whose encoding is the console's, not UTF-8)."""
    import ast

    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute | ast.Name):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        keys = {k.arg for k in node.keywords}
        if name in ("read_text", "write_text"):
            bad = "encoding" not in keys and len(node.args) < (1 if name == "read_text" else 2)
        elif name == "open":
            mode = node.args[1].value if len(node.args) > 1 else "r"
            bad = "encoding" not in keys and "b" not in str(mode)
        elif name in PROCESS:
            bad = bool({"text", "universal_newlines"} & keys) and "encoding" not in keys
        else:
            value = node.func.value if isinstance(node.func, ast.Attribute) else None
            bad = isinstance(value, ast.Attribute) and value.attr == "stdin"
        if bad:
            found.append(f"{path.name}:{node.lineno} {name}")
    return found


def test_every_kit_script_reads_and_writes_text_as_utf8():
    """Brief #263 item 10 (REQ-039): whatever the platform default (cp1252 on Windows)."""
    scripts = sorted((ROOT / "scripts" / "agk").glob("*.py"))
    hooks = sorted((ROOT / ".claude" / "hooks").glob("*.py"))
    assert len(scripts) > 30 and hooks
    assert [hit for path in [*scripts, *hooks] for hit in unpinned(path)] == []


PROBE = """
import sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
import common
root = Path(sys.argv[2])
committed = common.show(root, "HEAD", "docs/requirements.md")
working = (root / "docs" / "requirements.md").read_text(encoding="utf-8")
print("same" if committed is not None and working.startswith(committed) else "differs")
"""


def test_git_show_reads_the_committed_copy_as_utf8_under_a_non_utf8_locale(tmp_path):
    """Brief #263 item 10 (REQ-039): the pilot's `intake.py check` read `git show` in the
    platform's encoding and the working copy as UTF-8, so a line with an em dash differed and a
    pure append read as a changed line. Here the locale is ASCII, with UTF-8 mode off."""
    import os

    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "requirements.md").write_text("REQ-001 — a line\n", encoding="utf-8")
    for args in (
        ["init", "-q"],
        ["-c", "user.email=t@example.invalid", "-c", "user.name=t", "add", "-A"],
        ["-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "x"],
    ):
        git = ["git", *args]
        subprocess.run(git, cwd=repo, check=True)  # nosec B603 - fixed argument list, no shell
    with (repo / "docs" / "requirements.md").open("a", encoding="utf-8") as fh:
        fh.write("REQ-002 — appended\n")
    env = {**os.environ, "LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
    env.pop("PYTHONIOENCODING", None)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-c", PROBE, str(ROOT / "scripts" / "agk"), str(repo)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert proc.stdout.strip() == "same", proc.stdout + proc.stderr
