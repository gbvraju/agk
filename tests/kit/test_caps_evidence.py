"""Tests of the `Caps-evidence:` line of scripts/agk/check_protected_changes.py (brief #924).

SPEC-0049 rule 13 (build (e), first part): a change set that changes the `[caps]` table of
`agk.toml` against the merge base needs exactly one body line
`Caps-evidence: scorecard #<issue>:<YYYY-MM-DD> usage <S>/<M>/<L>`, each size being
`<tokens P50>,<tokens P85>,<hours P50>,<hours P85>`. The line is in addition to the ADR that a
change of `agk.toml` needs, never in its place. Invented data only; git fixtures; no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ADR = (
    "# ADR-0009: Set the caps\n\n- Status: Proposed\n- Date: 2026-01-01\n- Deciders: maintainers\n"
    "- Related: none\n- Requirements: REQ-056\n\nProtected classes: `agk.toml`\n"
)
BASE_TOML = '[project]\nname = "example"\n\n[caps]\nS = { tokens = 300000, hours = 2 }\n'
OTHER_TOML = '[project]\nname = "example-two"\n\n[caps]\nS = { tokens = 300000, hours = 2 }\n'
NEW_CAPS_TOML = '[project]\nname = "example"\n\n[caps]\nS = { tokens = 700000, hours = 5 }\n'
NO_CAPS_TOML = '[project]\nname = "example"\n'
GOOD = "Caps-evidence: scorecard #812:2026-11-08 usage 1,2,0.5,1.5/3,4,2,3/5,6,4,7"
# A value that must never appear in a refusal (principle 8): the new token cap.
SECRET_FREE_VALUE = "700000"


def make_base(repo, toml: str | None = BASE_TOML):
    files = {"config/protected-paths.txt": "# c\nagk.toml\n", "src/app.py": "x = 1\n"}
    if toml is not None:
        files["agk.toml"] = toml
    repo.commit(files, "base")
    repo.branch()
    return repo


def check(repo, tmp_path: Path, *lines: str):
    path = tmp_path / "pr-body.md"
    path.write_text("Advances: REQ-056\n" + "".join(f"{ln}\n" for ln in lines), encoding="utf-8")
    return repo.run("check_protected_changes.py", "--base", "main", "--body", str(path))


def change(repo, toml: str | None):
    repo.commit({"agk.toml": toml, "docs/adr/0009-set-the-caps.md": ADR})


def test_req056_caps_change_with_a_good_line_passes(repo, tmp_path):
    """REQ-056 AC6: an ADR naming agk.toml and one well-formed line pass."""
    make_base(repo)
    change(repo, NEW_CAPS_TOML)
    proc = check(repo, tmp_path, GOOD)
    assert proc.returncode == 0, proc.stdout


def test_req056_caps_change_without_the_line_fails_naming_the_rule(repo, tmp_path):
    """REQ-056 AC6: no line fails naming the rule and the setting, never the value."""
    make_base(repo)
    change(repo, NEW_CAPS_TOML)
    proc = check(repo, tmp_path)
    assert proc.returncode == 1
    assert "SPEC-0049 rule 13" in proc.stdout
    assert "setting: caps" in proc.stdout
    assert SECRET_FREE_VALUE not in proc.stdout


def test_req056_caps_change_without_a_body_fails(repo):
    """REQ-056 AC6: without a body there is no line, so the change fails."""
    make_base(repo)
    change(repo, NEW_CAPS_TOML)
    proc = repo.run("check_protected_changes.py", "--base", "main")
    assert proc.returncode == 1
    assert "SPEC-0049 rule 13" in proc.stdout


def test_req056_two_lines_fail(repo, tmp_path):
    """REQ-056 AC6: exactly one line."""
    make_base(repo)
    change(repo, NEW_CAPS_TOML)
    proc = check(repo, tmp_path, GOOD, GOOD)
    assert proc.returncode == 1
    assert "exactly one" in proc.stdout
    assert "SPEC-0049 rule 13" in proc.stdout


@pytest.mark.parametrize(
    "line",
    [
        "Caps-evidence: scorecard 2026-11-08 usage 1,2,0.5,1.5/3,4,2,3/5,6,4,7",
        "Caps-evidence: scorecard #812:2026-13-08 usage 1,2,0.5,1.5/3,4,2,3/5,6,4,7",
        "Caps-evidence: scorecard #812:2026-11-08 usage 1,2,0.5,1.5/3,4,2,3",
        "Caps-evidence: scorecard #812:2026-11-08 usage 1,2,0.5/3,4,2,3/5,6,4,7",
        "Caps-evidence: scorecard #812:2026-11-08 usage 1,2,x,1.5/3,4,2,3/5,6,4,7",
        "Caps-evidence: scorecard #812:2026-11-08 usage 1.5,2,0.5,1.5/3,4,2,3/5,6,4,7",
        "Caps-evidence: scorecard #812:2026-11-08 usage 2,1,0.5,1.5/3,4,2,3/5,6,4,7",
        "Caps-evidence: scorecard #812:2026-11-08 usage unknown",
        "Caps-evidence: by feel",
    ],
)
def test_req056_malformed_line_fails_naming_the_rule_not_the_value(repo, tmp_path, line):
    """REQ-056 AC6: a line without the shape fails the same way, never echoing the line."""
    make_base(repo)
    change(repo, NEW_CAPS_TOML)
    proc = check(repo, tmp_path, line)
    assert proc.returncode == 1
    assert "SPEC-0049 rule 13" in proc.stdout
    assert "setting: caps" in proc.stdout
    assert line not in proc.stdout
    assert SECRET_FREE_VALUE not in proc.stdout


def test_req056_other_table_change_needs_no_line(repo, tmp_path):
    """REQ-056 AC6: a change elsewhere in agk.toml is judged as today."""
    make_base(repo)
    change(repo, OTHER_TOML)
    proc = check(repo, tmp_path)
    assert proc.returncode == 0, proc.stdout


def test_req056_reformatted_but_equal_caps_need_no_line(repo, tmp_path):
    """REQ-056 AC6: the table is compared by value, so a comment or spacing is no change."""
    make_base(repo)
    change(repo, BASE_TOML.replace("S = {", "# tuned later\nS  = {"))
    proc = check(repo, tmp_path)
    assert proc.returncode == 0, proc.stdout


def test_req056_new_caps_table_counts_as_a_change(repo, tmp_path):
    """REQ-056 AC6: adding the table needs the line."""
    make_base(repo, NO_CAPS_TOML)
    change(repo, NEW_CAPS_TOML)
    assert check(repo, tmp_path).returncode == 1
    assert check(repo, tmp_path, GOOD).returncode == 0


def test_req056_removed_caps_table_counts_as_a_change(repo, tmp_path):
    """REQ-056 AC6: removing the table needs the line."""
    make_base(repo)
    change(repo, NO_CAPS_TOML)
    proc = check(repo, tmp_path)
    assert proc.returncode == 1
    assert "SPEC-0049 rule 13" in proc.stdout


def test_req056_new_agk_toml_with_caps_counts_as_a_change(repo, tmp_path):
    """REQ-056 AC6: an agk.toml added with a [caps] table needs the line."""
    make_base(repo, None)
    change(repo, NEW_CAPS_TOML)
    assert check(repo, tmp_path).returncode == 1


def test_req056_line_never_replaces_the_adr(repo, tmp_path):
    """REQ-056 AC6: a good line without an ADR still fails on the protected class."""
    make_base(repo)
    repo.commit({"agk.toml": NEW_CAPS_TOML})
    proc = check(repo, tmp_path, GOOD)
    assert proc.returncode == 1
    assert "'agk.toml'" in proc.stdout


def test_req056_no_caps_change_ignores_a_stray_line(repo, tmp_path):
    """REQ-056 AC6: a change set that leaves [caps] alone is judged as today."""
    make_base(repo)
    repo.commit({"src/app.py": "x = 2\n"})
    proc = check(repo, tmp_path, "Caps-evidence: by feel")
    assert proc.returncode == 0, proc.stdout


def test_req056_indented_line_is_not_read(repo, tmp_path):
    """REQ-056 AC6: the line must start a body line, as `Covered-by:` must, so indented is none."""
    make_base(repo)
    change(repo, NEW_CAPS_TOML)
    proc = check(repo, tmp_path, "  " + GOOD)
    assert proc.returncode == 1
    assert "SPEC-0049 rule 13" in proc.stdout
