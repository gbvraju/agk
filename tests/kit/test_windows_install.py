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
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # nosec B603 B607
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
