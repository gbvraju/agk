"""Kit-only tests of the changelog fragments of flow mode (SPEC-0031 rules 1 to 8; REQ-038).

In flow mode a build adds one file under `changelog.d/` instead of a line in `CHANGELOG.md`; the
release pull request gathers the files (`changelog_fragments.py gather`) and `check_release.py`
accepts their deletion. Fixtures use git in `tmp_path`. No network, no model.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, git
from test_changelog_flow import flow_kit
from test_kit_hashes import kit_hashes

GATHER = KIT_ROOT / "scripts" / "agk" / "changelog_fragments.py"
RELEASE = KIT_ROOT / "scripts" / "agk" / "check_release.py"
FRAG = "changelog.d/"
ADR = next((KIT_ROOT / "docs" / "adr").glob("0108-*.md"), None)
GUIDE = KIT_ROOT / "docs" / "guides" / "reference.md"
TEMPLATE = KIT_ROOT / "kit" / "templates" / "changelog.md"


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fragment(root: Path, slug: str = "first-build", text: str = "- the a.txt change\n") -> None:
    put(root, f"{FRAG}{slug}.md", text)


def problems(root: Path) -> list[str]:
    return kit_hashes.problems(root, "HEAD")


def gitout(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def commit_as(root: Path, subject: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", subject)


# --- the build pull request (rules 1, 2, 5 and 6) -------------------------------------------------


def test_ac1_a_flow_build_with_one_fragment_and_no_other_shared_file_passes(tmp_path):
    """REQ-038 AC1: rules 1, 2 and 6 (the changelog and the table are not edited)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed in flow\n", encoding="utf-8")
    fragment(root)
    assert problems(root) == []


def test_ac1_the_current_row_of_the_table_is_not_compared_between_releases(tmp_path):
    """REQ-038 AC7: rule 6 (the release regenerates the current row, a build leaves the file)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a by the first build\n", encoding="utf-8")
    fragment(root)
    commit_as(root, "first build (#7)")
    (root / "a.txt").write_text("a by the second build\n", encoding="utf-8")
    fragment(root, "second-build", "- the second change\n")
    assert problems(root) == []


def test_ac2_a_build_that_edits_the_changelog_fails_naming_the_rule_and_the_class(tmp_path):
    """REQ-038 AC2: rule 2 (no edit of `CHANGELOG.md`, with or without a fragment)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed\n", encoding="utf-8")
    fragment(root)
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    (root / "CHANGELOG.md").write_text(text.replace("## Unreleased\n", "## Unreleased\n\n- #7 x\n"))
    found = problems(root)
    assert any("CHANGELOG.md" in f and FRAG in f and "flow mode" in f for f in found), found


def test_ac2_an_edit_of_the_changelog_fails_even_when_no_installed_file_changed(tmp_path):
    """REQ-038 AC2: rule 2 (every flow build leaves the changelog to the release)."""
    root = flow_kit(tmp_path)
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- #7 x\n", encoding="utf-8")
    assert any("CHANGELOG.md" in f for f in problems(root))


def test_ac3_a_triggering_build_without_a_fragment_fails_naming_the_class(tmp_path):
    """REQ-038 AC3: rule 2 (the trigger is the one of SPEC-0028 rule 2)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed silently\n", encoding="utf-8")
    found = problems(root)
    assert any(FRAG in f and "a.txt" in f for f in found), found


def test_ac3_two_fragments_fail(tmp_path):
    """REQ-038 AC3: rule 2 (exactly one fragment)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed\n", encoding="utf-8")
    fragment(root)
    fragment(root, "another", "- another\n")
    assert any("exactly one" in f and FRAG in f for f in problems(root))


def test_ac3_a_fragment_that_is_not_one_line_without_a_number_fails(tmp_path):
    """REQ-038 AC3: rules 1 and 2 (`- <one-line change>`, no pull request number)."""
    for i, bad in enumerate(
        ("- #7 numbered\n", "- two\n- lines\n", "no dash\n", "- \n", "", "- x")
    ):
        (tmp_path / f"c{i}").mkdir()
        root = flow_kit(tmp_path / f"c{i}")
        (root / "a.txt").write_text("a changed\n", encoding="utf-8")
        fragment(root, text=bad)
        found = problems(root)
        assert any(FRAG in f and "one line" in f for f in found), (bad, found)


def test_ac3_a_slug_outside_the_pattern_fails(tmp_path):
    """REQ-038 AC3: rule 1 (`<slug>` is `[a-z0-9-]+`)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed\n", encoding="utf-8")
    fragment(root, "Bad_Slug")
    assert any(FRAG in f for f in problems(root))


def test_ac3_a_build_that_changes_no_installed_file_may_add_a_fragment_or_none(tmp_path):
    """REQ-038 AC3: rule 2 (a fragment is required exactly when the trigger is met)."""
    root = flow_kit(tmp_path)
    (root / "notes.md").write_text("not installed\n", encoding="utf-8")
    assert problems(root) == []
    fragment(root)
    assert problems(root) == []


def test_ac3_a_build_that_removes_a_fragment_fails(tmp_path):
    """REQ-038 AC3: rule 2 (only the release deletes fragments)."""
    root = flow_kit(tmp_path)
    fragment(root)
    commit_as(root, "first build (#7)")
    (root / FRAG / "first-build.md").unlink()
    assert any(FRAG in f for f in problems(root))


def test_ac6_in_strict_mode_no_fragment_is_required_and_the_changelog_may_be_edited(tmp_path):
    """REQ-038 AC6: rule 5 (strict mode is as before)."""
    root = flow_kit(tmp_path, mode="strict")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- #7 x\n", encoding="utf-8")
    assert problems(root) == []
    (root / "a.txt").write_text("a changed in strict\n", encoding="utf-8")
    found = problems(root)
    assert any("kit_version bump" in f for f in found) and not any(FRAG in f for f in found)


def test_ac7_a_build_that_edits_the_table_fails_in_flow_mode(tmp_path):
    """REQ-038 AC7: rule 6 (the measurement says the release can regenerate it)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed\n", encoding="utf-8")
    fragment(root)
    # a build between two releases changes no row of the table (the row of the current version
    # stays the release's), so the edit is made by hand: any difference from the base fails
    table = root / "kit" / "hashes.json"
    table.write_text(table.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    found = problems(root)
    assert any("kit/hashes.json" in f and "flow mode" in f for f in found), found


def test_ac7_the_table_of_a_release_is_regenerated_and_compared_in_full(tmp_path):
    """REQ-038 AC7: rule 6 (a raised version is a release; its table is the regenerated one)."""
    root = flow_kit(tmp_path)
    (root / "a.txt").write_text("a changed by a build\n", encoding="utf-8")
    fragment(root)
    commit_as(root, "a build (#7)")
    (root / "kit" / "manifest.json").write_text(
        (root / "kit" / "manifest.json").read_text(encoding="utf-8").replace("1.0.0", "1.1.0")
    )
    (root / "agk.toml").write_text('version = "1.1.0"\npr_mode = "flow"\n', encoding="utf-8")
    assert any("kit/hashes.json" in f or "row" in f for f in problems(root))
    (root / "kit" / "hashes.json").write_text(
        kit_hashes.dump(kit_hashes.build_table(root, "HEAD")), encoding="utf-8"
    )
    assert problems(root) == []


# --- the release script and its check (rules 3 and 4) ---------------------------------------------

OLD = (
    "# Changelog\n\n## Unreleased\n\n- #3 an old line\n\n## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
)


def run(script: Path, root: Path, *args: str, base: str | None = None):
    env = {**clean_env(), **({"AGK_BASE": base} if base else {})}
    return subprocess.run(
        [sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, env=env
    )


def release_repo(tmp_path: Path, numbers: tuple[int, ...] = (15, 9, 12)) -> Path:
    """A flow-mode kit at 1.0.0 whose merged builds each added one fragment (squash subjects)."""
    root = tmp_path / "rel"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")
    git(root, "config", "commit.gpgsign", "false")
    put(root, "agk.toml", 'version = "1.0.0"\npr_mode = "flow"\n')
    put(root, "kit/manifest.json", json.dumps({"kit_version": "1.0.0"}))
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": "1.0.0"}))
    put(root, "kit/hashes.json", "{}\n")
    put(root, "CHANGELOG.md", OLD)
    put(root, "README.md", "readme\n")
    put(root, "scripts/agk/check_release.py", "# this check exists on the base\n")
    commit_as(root, "base")
    for n in numbers:
        put(root, f"{FRAG}build-{n}.md", f"- the change of {n}\n")
        commit_as(root, f"feat: a build (#{n})")
    return root


def bump(root: Path, version: str = "1.1.0") -> None:
    put(root, "agk.toml", f'version = "{version}"\npr_mode = "flow"\n')
    put(root, "kit/manifest.json", json.dumps({"kit_version": version}))
    put(root, ".claude-plugin/plugin.json", json.dumps({"name": "agk", "version": version}))
    put(root, "kit/hashes.json", '{"new": 1}\n')


def gather(root: Path, version: str = "1.1.0"):
    return run(GATHER, root, "gather", "--version", version, "--date", "2026-10-25")


def test_ac4_the_script_moves_the_lines_in_pull_request_order_and_deletes_the_fragments(tmp_path):
    """REQ-038 AC4: rule 3 (old Unreleased lines first, then `- #<n> <change>` by number)."""
    root = release_repo(tmp_path)
    proc = gather(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text == (
        "# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-10-25)\n\n- #3 an old line\n"
        "- #9 the change of 9\n- #12 the change of 12\n- #15 the change of 15\n\n"
        "## 1.0.0 (2026-01-01)\n\n- #1 the start\n"
    )
    assert not list((root / "changelog.d").glob("*.md"))


def test_ac4_the_script_writes_no_other_file(tmp_path):
    """REQ-038 AC4: rule 3 (the changelog and the deleted fragments only)."""
    root = release_repo(tmp_path)
    gather(root)
    status = gitout(root, "status", "--porcelain").splitlines()
    assert sorted(line[3:] for line in status) == sorted(
        ["CHANGELOG.md", *[f"changelog.d/build-{n}.md" for n in (9, 12, 15)]]
    )


def test_ac4_a_fragment_whose_number_cannot_be_read_stops_the_script_and_writes_nothing(tmp_path):
    """REQ-038 AC4: rule 3 (the subject of the adding commit carries no `(#<n>)`)."""
    root = release_repo(tmp_path)
    put(root, "changelog.d/odd.md", "- an odd one\n")
    commit_as(root, "a commit without a number")
    before = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    proc = gather(root)
    assert proc.returncode == 1 and "changelog.d/" in proc.stdout + proc.stderr
    assert (root / "CHANGELOG.md").read_text(encoding="utf-8") == before
    assert (root / "changelog.d" / "odd.md").exists()


def test_ac4_with_no_fragment_the_script_moves_the_old_lines_only(tmp_path):
    """REQ-038 AC4: rule 3 (the release of SPEC-0028 rule 4 is unchanged)."""
    root = release_repo(tmp_path, numbers=())
    assert gather(root).returncode == 0
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 1.1.0 (2026-10-25)\n\n- #3 an old line\n" in text


def release_ok(tmp_path: Path) -> Path:
    root = release_repo(tmp_path)
    git(root, "switch", "-q", "-c", "release")
    assert gather(root).returncode == 0
    bump(root)
    return root


def check(root: Path):
    base = gitout(root, "rev-parse", "main").strip()
    return run(RELEASE, root, base=base)


def test_ac5_a_release_that_gathers_and_deletes_the_fragments_passes(tmp_path):
    """REQ-038 AC5: rule 4 (the deletions are release files)."""
    proc = check(release_ok(tmp_path))
    assert (proc.returncode, proc.stdout) == (0, "ok release\n"), proc.stdout


def test_ac5_a_fragment_left_behind_fails(tmp_path):
    """REQ-038 AC5: rule 4 (nothing is left under `changelog.d/`)."""
    root = release_ok(tmp_path)
    put(root, "changelog.d/build-9.md", "- the change of 9\n")
    proc = check(root)
    assert proc.returncode == 1 and "rule 4" in proc.stdout and FRAG in proc.stdout, proc.stdout


def test_ac5_a_line_not_moved_unchanged_or_dropped_fails(tmp_path):
    """REQ-038 AC5: rule 4 (with its number, in order)."""
    root = release_ok(tmp_path)
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    put(root, "CHANGELOG.md", text.replace("the change of 12", "the change of twelve"))
    assert check(root).returncode == 1
    put(root, "CHANGELOG.md", text.replace("- #12 the change of 12\n", ""))
    assert check(root).returncode == 1
    swapped = text.replace(
        "- #9 the change of 9\n- #12 the change of 12\n",
        "- #12 the change of 12\n- #9 the change of 9\n",
    )
    put(root, "CHANGELOG.md", swapped)
    assert check(root).returncode == 1


def test_ac5_a_fragment_added_or_edited_by_the_release_fails(tmp_path):
    """REQ-038 AC5: rule 4 (the release only deletes fragments)."""
    root = release_ok(tmp_path)
    put(root, "changelog.d/new-one.md", "- added by a release\n")
    proc = check(root)
    assert proc.returncode == 1 and FRAG in proc.stdout, proc.stdout


def test_ac5_a_fragment_without_a_readable_number_fails_the_release_check(tmp_path):
    """REQ-038 AC5: rule 4 (the number comes from the commit that added the fragment)."""
    root = release_repo(tmp_path, numbers=())
    put(root, "changelog.d/odd.md", "- an odd one\n")
    commit_as(root, "a commit without a number")
    git(root, "switch", "-q", "-c", "release")
    (root / "changelog.d" / "odd.md").unlink()
    moved = OLD.replace("## Unreleased\n", "## Unreleased\n\n## 1.1.0 (2026-10-25)\n")
    put(root, "CHANGELOG.md", moved)
    bump(root)
    proc = check(root)
    assert proc.returncode == 1 and "rule 4" in proc.stdout and FRAG in proc.stdout, proc.stdout


def test_ac5_the_messages_name_the_rule_and_the_class_and_never_a_value(tmp_path):
    """REQ-038 AC5 and CLAUDE.md rule 6 (no version, no fragment text in a refusal)."""
    root = release_ok(tmp_path)
    put(root, "changelog.d/build-9.md", "- the change of 9\n")
    proc = check(root)
    assert "1.1.0" not in proc.stdout and "the change of 9" not in proc.stdout


def test_ac4_the_script_reads_git_and_files_only(tmp_path):
    """REQ-038 AC4: rule 3 (no network, no model; kit-only)."""
    import ast

    tree = ast.parse(GATHER.read_text(encoding="utf-8"))
    names = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    names |= {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert not names & {"socket", "urllib", "http", "requests", "ssl"}
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/changelog_fragments.py" not in manifest["verbatim"]


# --- the texts and the ADR (rules 6 and 7) --------------------------------------------------------


def test_ac7_the_adr_records_the_measurement_of_the_table():
    """REQ-038 AC7: rule 6 (measured before the build: the release can regenerate the table)."""
    assert ADR is not None, "ADR-0108 is missing"
    text = ADR.read_text(encoding="utf-8")
    assert "## Measurement" in text
    section = text.split("## Measurement", 1)[1].split("\n## ", 1)[0]
    assert "kit/hashes.json" in section and "kit_hashes.py --write" in section
    assert "digest" in section and "commits" in section


def test_ac1_the_guide_and_the_template_describe_the_fragment():
    """REQ-038 AC1 and AC4: rules 1 and 3 (the guide section and the template of the shape)."""
    section = GUIDE.read_text(encoding="utf-8").split("## Developing the kit", 1)[1]
    guide = " ".join(section.split("\n## ", 1)[0].split())
    assert "`changelog.d/" in guide and "`- <one-line change>`" in guide
    assert "does not edit `CHANGELOG.md`" in guide and "does not edit `kit/hashes.json`" in guide
    assert "changelog_fragments.py gather" in guide
    template = " ".join(TEMPLATE.read_text(encoding="utf-8").split())
    assert "changelog.d/" in template and "`- <one-line change>`" in template


def test_ac1_this_repositorys_own_fragments_follow_rule_1():
    """REQ-038 AC1: rule 1 (the fragments of this repository are one line without a number)."""
    for path in sorted((KIT_ROOT / "changelog.d").glob("*.md")):
        assert re.fullmatch(r"[a-z0-9-]+\.md", path.name), path.name
        assert re.fullmatch(r"- (?!#\d+\b)\S[^\n]*\n", path.read_text(encoding="utf-8")), path.name


def test_ac4_a_merge_commit_repository_reads_the_number_from_the_merge_subject(tmp_path):
    """REQ-038 AC4: rule 3 (first-parent history; `Merge pull request #<n>` is read too)."""
    root = release_repo(tmp_path, numbers=())
    for n in (21, 20):
        git(root, "switch", "-q", "-c", f"branch-{n}")
        put(root, f"{FRAG}build-{n}.md", f"- the change of {n}\n")
        commit_as(root, "a branch commit without a number")
        git(root, "switch", "-q", "main")
        git(
            root, "merge", "-q", "--no-ff", f"branch-{n}", "-m", f"Merge pull request #{n} from o/b"
        )
    assert gather(root).returncode == 0
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "- #3 an old line\n- #20 the change of 20\n- #21 the change of 21\n" in text


def test_ac5_the_release_check_reads_a_merge_commit_number_and_stops_when_neither_form(tmp_path):
    """REQ-038 AC5: rule 4 (both forms accepted, a branch commit alone is not a number)."""
    root = release_repo(tmp_path, numbers=())
    git(root, "switch", "-q", "-c", "branch-30")
    put(root, f"{FRAG}build-30.md", "- the change of 30\n")
    commit_as(root, "a branch commit without a number")
    git(root, "switch", "-q", "main")
    git(root, "merge", "-q", "--no-ff", "branch-30", "-m", "Merge pull request #30 from o/b")
    git(root, "switch", "-q", "-c", "release")
    assert gather(root).returncode == 0
    bump(root)
    assert check(root).stdout == "ok release\n"
    git(root, "switch", "-q", "main")
    git(root, "switch", "-q", "-c", "branch-31")
    put(root, f"{FRAG}build-31.md", "- the change of 31\n")
    commit_as(root, "a branch commit without a number")
    git(root, "switch", "-q", "main")
    git(root, "merge", "-q", "--no-ff", "branch-31", "-m", "merged without a number")
    proc = gather(root)
    assert proc.returncode == 1 and FRAG in proc.stdout


# --- the release flips the decisions their Final comments accepted (brief #1706, ADR-0710) -------
# `changelog_fragments.py accept --comments FILE` sets to Accepted the one Status line of each ADR
# that `check_adrs.pending` lists (verified Final records only), byte for byte otherwise, so no
# session edits a Status line by hand (REQ-035). Fixtures: invented records and comments.

ACCEPT_ADRS = {
    "0009": "docs/adr/0009-an-invented-decision.md",
    "0010": "docs/adr/0010-another-invented-decision.md",
    "0011": "docs/adr/0011-a-third-invented-decision.md",
    "0012": "docs/adr/0012-an-unverified-decision.md",
    "0013": "docs/adr/0013-an-accepted-decision.md",
}
ACCEPT_RECORDS = {
    "0009": (7, 42),
    "0010": (8, 77),
    "0011": (9, 88),
    "0012": (10, 99),
    "0013": (11, 55),
}
VERIFIED = ("0009", "0010", "0011")
ACCEPT_CLASSES = "config/\nscripts/agk/\nkit/\nagk.toml\n.claude-plugin/\ndocs/adr/\n"
ACCEPT_TOML = 'version = "{v}"\npr_mode = "flow"\n'
ACCEPT_CHANGES = "# Changelog\n\n## Unreleased\n\n- #5 an invented change\n"


def decision(number: str, status: str, end: str = "\n") -> str:
    text = (
        f"# ADR-{number}: An invented decision\n\n- Status: {status}\n- Date: 2026-01-01\n"
        "- Deciders: maintainers\n- Related: none\n- Requirements: REQ-035\n\n"
        "## Context\n\nc\n\n## Decision\n\nd\n\n## Consequences\n\nq\n\n## Residual\n\nr\n"
    )
    return text.replace("\n", end)


def final_of(number: str) -> dict:
    """The Final comment of a record, as `gh api repos/{repo}/issues/comments/<id>` answers."""
    pr, cid = ACCEPT_RECORDS[number]
    return {
        "id": cid,
        "issue_url": f"https://api.example.com/repos/example-owner/example-repo/issues/{pr}",
        "user": {"login": "reviewer"},
        "body": f"Verdict: fix list a1b2c3d\n\nreviewed.\n\nFinal: {ACCEPT_ADRS[number]} "
        "Proposed -> Accepted\n",
    }


def accept_world(tmp_path: Path, toml: str = ACCEPT_TOML, crlf: bool = False) -> tuple[Path, str]:
    """A kit at 1.0.0 whose main records five Finals (0009 to 0013): three verified, one whose
    comment is by an unlisted account (0012), one whose file already says Accepted (0013); and a
    release branch that raises the version. Returns the root and the comments file."""
    from common import MERGED_BY  # the merger's squash message line (test_kit_hashes adds the path)

    root = tmp_path / "acc"
    root.mkdir()
    for args in (
        ("init", "-q", "-b", "main"),
        ("config", "user.email", "t@example.invalid"),
        ("config", "user.name", "t"),
        ("config", "commit.gpgsign", "false"),
    ):
        git(root, *args)
    put(root, "config/protected-paths.txt", "# c\n" + ACCEPT_CLASSES)
    put(root, "config/reviewers.yaml", "version: 1\nverdict_authors: [reviewer]\n")
    put(root, "CHANGELOG.md", ACCEPT_CHANGES)
    put(root, "kit/hashes.json", "{}\n")
    put(root, "scripts/agk/check_release.py", "# the check exists on the base\n")
    for name, text in versions_of("1.0.0", toml).items():
        put(root, name, text)
    for number, path in ACCEPT_ADRS.items():
        status = "Accepted" if number == "0013" else "Proposed"
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(decision(number, status, "\r\n" if crlf else "\n").encode())
    commit_as(root, "base")
    for number, (pr, cid) in sorted(ACCEPT_RECORDS.items()):
        put(root, "README.md", f"{number}\n")
        commit_as(root, f"Example (#{pr})\n\nADR-{number} Accepted (Final {cid})\n{MERGED_BY}\n")
    git(root, "switch", "-q", "-c", "release")
    for name, text in versions_of("1.1.0", toml).items():
        put(root, name, text)
    put(root, "kit/hashes.json", '{"new": 1}\n')
    put(
        root,
        "CHANGELOG.md",
        "# Changelog\n\n## Unreleased\n\n## 1.1.0 (2026-11-22)\n\n- #5 an invented change\n",
    )
    comments = [final_of(n) for n in VERIFIED + ("0013",)]
    unlisted = final_of("0012")
    unlisted["user"] = {"login": "someone-else"}
    saved = tmp_path / "record-comments.json"
    saved.write_text(json.dumps([*comments, unlisted]), encoding="utf-8")
    return root, str(saved)


def versions_of(version: str, toml: str = ACCEPT_TOML) -> dict[str, str]:
    return {
        "agk.toml": toml.format(v=version),
        "kit/manifest.json": json.dumps({"kit_version": version}),
        ".claude-plugin/plugin.json": json.dumps({"name": "agk", "version": version}),
    }


def accept(root: Path, *args: str):
    return run(GATHER, root, "accept", *args)


def changed(root: Path) -> list[str]:
    return sorted(line[3:] for line in gitout(root, "status", "--porcelain").splitlines())


def test_1706_accept_flips_exactly_the_verified_pending_decisions(tmp_path):
    """REQ-035: brief #1706 answer 1 and Measured (3 verified, 1 unverified, 1 already Accepted)."""
    root, saved = accept_world(tmp_path)
    before = {n: (root / p).read_bytes() for n, p in ACCEPT_ADRS.items()}
    proc = accept(root, "--comments", saved)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    flipped = [ACCEPT_ADRS[n] for n in VERIFIED]
    assert proc.stdout.splitlines() == [*(f"accepted: {p}" for p in flipped), "accept: 3 decisions"]
    for number, path in ACCEPT_ADRS.items():
        after = (root / path).read_bytes()
        if number in VERIFIED:
            assert after == before[number].replace(b"- Status: Proposed", b"- Status: Accepted")
        else:
            assert after == before[number], number


def test_1706_accept_changes_nothing_but_the_flipped_files(tmp_path):
    """REQ-035: brief #1706 answer 1 (only the listed files are written)."""
    root, saved = accept_world(tmp_path)
    git(root, "add", "-A")
    commit_as(root, "release: 1.1.0")
    accept(root, "--comments", saved)
    assert changed(root) == sorted(ACCEPT_ADRS[n] for n in VERIFIED)


def test_1706_after_accept_pending_is_empty_and_the_release_check_passes(tmp_path):
    """REQ-035: brief #1706 answers 2 and 5 (check_release.py, unchanged, checks the result)."""
    root, saved = accept_world(tmp_path)
    assert accept(root, "--comments", saved).returncode == 0
    commit_as(root, "release: 1.1.0")
    adrs = KIT_ROOT / "scripts" / "agk" / "check_adrs.py"
    left = run(adrs, root, "--pending", "--comments", saved, base="main")
    assert (left.returncode, left.stdout) == (0, "")
    proc = run(RELEASE, root, "--comments", saved, base="main")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_1706_without_the_release_flips_the_release_check_fails(tmp_path):
    """REQ-035: brief #1706 answer 2 (the check still refuses a release that left a flip out)."""
    root, saved = accept_world(tmp_path)
    commit_as(root, "release: 1.1.0")
    proc = run(RELEASE, root, "--comments", saved, base="main")
    assert proc.returncode == 1 and "rule 5" in proc.stdout


def test_1706_a_second_run_flips_nothing(tmp_path):
    """REQ-035: brief #1706 answer 5 (run twice)."""
    root, saved = accept_world(tmp_path)
    accept(root, "--comments", saved)
    snapshot = {p: (root / p).read_bytes() for p in ACCEPT_ADRS.values()}
    proc = accept(root, "--comments", saved)
    assert (proc.returncode, proc.stdout) == (0, "accept: none pending\n")
    assert snapshot == {p: (root / p).read_bytes() for p in ACCEPT_ADRS.values()}


def test_1706_nothing_pending_prints_none_and_writes_nothing(tmp_path):
    """REQ-035: brief #1706 answer 5 (no verified record: nothing pending)."""
    root, _ = accept_world(tmp_path)
    empty = tmp_path / "none.json"
    empty.write_text("[]", encoding="utf-8")
    proc = accept(root, "--comments", str(empty))
    assert (proc.returncode, proc.stdout) == (0, "accept: none pending\n")
    assert all(not line.startswith("docs/adr/") for line in changed(root))


def test_1706_a_crlf_decision_keeps_its_line_ends(tmp_path):
    """REQ-035: brief #1706 answer 5 (CRLF kept, byte for byte otherwise)."""
    root, saved = accept_world(tmp_path, crlf=True)
    path = root / ACCEPT_ADRS["0009"]
    assert accept(root, "--comments", saved).returncode == 0
    assert path.read_bytes() == decision("0009", "Accepted", "\r\n").encode()


def test_1706_without_comments_while_a_record_exists_it_refuses_and_writes_nothing(tmp_path):
    """REQ-035: brief #1706 answer 1 (fails closed as `--pending` does, naming the option)."""
    root, _ = accept_world(tmp_path)
    before = changed(root)
    proc = accept(root)
    assert proc.returncode == 1
    assert "--comments" in proc.stdout and "rule 3a" in proc.stdout
    assert changed(root) == before


def test_1706_an_unreadable_decision_refuses_before_the_first_write(tmp_path):
    """REQ-035: brief #1706 answer 1 (every file is checked before the first write)."""
    root, saved = accept_world(tmp_path)
    last = root / ACCEPT_ADRS["0011"]
    last.write_bytes(b"\xff" + last.read_bytes())
    proc = accept(root, "--comments", saved)
    assert proc.returncode != 0
    for number in ("0009", "0010"):
        assert b"- Status: Proposed" in (root / ACCEPT_ADRS[number]).read_bytes(), number


def test_1706_a_wrong_argument_prints_the_usage_naming_accept(tmp_path):
    """REQ-035: brief #1706 answer 1 (the usage names both commands)."""
    root, _ = accept_world(tmp_path)
    proc = accept(root, "--comment", "x")
    assert proc.returncode == 2 and "accept --comments FILE" in proc.stderr


@pytest.mark.parametrize(
    "toml",
    [
        'version = "{v}"\npr_mode = "flow"\n',
        'version = "{v}"\npr_mode = "strict"\n',
        'version = "{v}"\npr_mode = "flow"\nexecution = "hosted"\n',
        'version = "{v}"\npr_mode = "flow"\nexecution = "local"\n',
        'version = "{v}"\npr_mode = "flow"\nreview_mode = "solo"\n',
        'version = "{v}"\npr_mode = "flow"\nreview_mode = "team"\n',
    ],
    ids=["flow", "strict", "hosted", "local", "solo", "team"],
)
def test_1706_every_setting_flips_the_same_set(tmp_path, toml):
    """REQ-035: brief #1706 answer 4 (pr_mode, execution and review_mode change nothing)."""
    root, saved = accept_world(tmp_path, toml)
    proc = accept(root, "--comments", saved)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines()[-1] == "accept: 3 decisions"


def test_1706_the_release_script_is_never_installed():
    """REQ-035: brief #1706 answer 4 (personal mode and a project using AGK: not installed)."""
    text = (KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8")
    assert "changelog_fragments.py" not in text


# --- the release accepts a hand-merged decision on the owner's yes (brief #1738, ADR-0724) -------
# `accept --pulls FILE` also flips an ADR of a squash commit the merger did not make,
# when its latest verdict's Final verifies and the payload says that head merged as that commit.

HAND_ADR = "docs/adr/0014-a-hand-merged-decision.md"
HAND_HEAD = "e" * 40


def hand_merged(tmp_path: Path) -> tuple[Path, str, str]:
    """accept_world, then main gains a hand merge `(#12)` adding ADR-0014, merged into the
    release branch. Returns the root, the comments file (with #12's Final) and the commit."""
    root, saved = accept_world(tmp_path)
    git(root, "add", "-A")
    commit_as(root, "release: 1.1.0")
    git(root, "switch", "-q", "main")
    (root / HAND_ADR).write_bytes(decision("0014", "Proposed").encode())
    commit_as(root, "Add a hand-merged decision (#12)")
    sha = gitout(root, "rev-parse", "HEAD").strip()
    git(root, "switch", "-q", "release")
    git(root, "merge", "-q", "--no-ff", "-m", "Merge main", "main")
    comments = json.loads(Path(saved).read_text(encoding="utf-8"))
    comments.append(
        {
            "id": 120,
            "issue_url": "https://api.example.com/repos/example-owner/example-repo/issues/12",
            "user": {"login": "reviewer"},
            "created_at": "2026-11-21T10:00:00Z",
            "body": f"Verdict: fix list {HAND_HEAD}\n\nok.\n\n"
            f"Final: {HAND_ADR} Proposed -> Accepted\n",
        }
    )
    Path(saved).write_text(json.dumps(comments), encoding="utf-8")
    return root, saved, sha


def pulls_file(tmp_path: Path, sha: str, head: str = HAND_HEAD) -> str:
    path = tmp_path / "pulls.json"
    payload = {"number": 12, "merged": True, "merge_commit_sha": sha, "head": {"sha": head}}
    path.write_text(json.dumps([payload]), encoding="utf-8")
    return str(path)


def test_1738_accept_with_pulls_also_flips_the_hand_merged_decision(tmp_path):
    """REQ-035: brief #1738 answer 2 and edge case 5(a)."""
    root, saved, sha = hand_merged(tmp_path)
    proc = accept(root, "--comments", saved, "--pulls", pulls_file(tmp_path, sha), "--base", "main")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"accepted: {HAND_ADR}" in proc.stdout.splitlines()
    assert proc.stdout.splitlines()[-1] == "accept: 4 decisions"
    assert (root / HAND_ADR).read_bytes() == decision("0014", "Accepted").encode()


def test_1738_accept_without_pulls_leaves_the_hand_merged_decision(tmp_path):
    """REQ-035: brief #1738 answer 2 (without --pulls nothing changes)."""
    root, saved, _ = hand_merged(tmp_path)
    proc = accept(root, "--comments", saved, "--base", "main")
    assert proc.returncode == 0 and f"accepted: {HAND_ADR}" not in proc.stdout
    assert (root / HAND_ADR).read_bytes() == decision("0014", "Proposed").encode()


def test_1738_accept_never_flips_a_verdict_on_an_older_head(tmp_path):
    """REQ-035: brief #1738 edge cases 5(c) and 5(h)."""
    root, saved, sha = hand_merged(tmp_path)
    for pulls in (pulls_file(tmp_path, sha, head="f" * 40), pulls_file(tmp_path, "c" * 40)):
        proc = accept(root, "--comments", saved, "--pulls", pulls, "--base", "main")
        assert f"accepted: {HAND_ADR}" not in proc.stdout
        assert (root / HAND_ADR).read_bytes() == decision("0014", "Proposed").encode()
        git(root, "checkout", "-q", "--", ".")


def test_1738_a_bad_pulls_file_is_refused_naming_the_option_and_writes_nothing(tmp_path):
    """REQ-035: brief #1738 answer 2 (refused naming the option, never a value)."""
    root, saved, _ = hand_merged(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text('{"title": "invented-value"}', encoding="utf-8")
    proc = accept(root, "--comments", saved, "--pulls", str(bad), "--base", "main")
    assert proc.returncode != 0
    assert "--pulls" in proc.stdout + proc.stderr and "invented-value" not in proc.stdout
    assert changed(root) == []


# --- the release pull request's own check accepts a hand-merged flip (Q-1738-2) ------------------
# The release body names each accepted hand merge in one line `Hand-merged: #<n> Final <id>`;
# `check_release.py --body FILE --pulls FILE` lets the release flip its ADR only when the Final
# verifies, the payload names a hand-merge squash and the head the verdict names. Fixtures only.

ADRS_SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_adrs.py"
HAND_LINE = "Hand-merged: #12 Final 120"


def accepted_release(tmp_path: Path, line: str = HAND_LINE) -> tuple[Path, str, str, str, str]:
    """hand_merged, accepted with --pulls and committed; returns the root, the comments, the
    pulls file, the body file and the hand merge's commit."""
    root, saved, sha = hand_merged(tmp_path)
    pulls = pulls_file(tmp_path, sha)
    assert accept(root, "--comments", saved, "--pulls", pulls, "--base", "main").returncode == 0
    commit_as(root, "release: accept")
    body = tmp_path / "body.md"
    body.write_text(f"Summary: a release\n{line}\n", encoding="utf-8")
    return root, saved, pulls, str(body), sha


def release_check(root: Path, *args: str):
    return run(RELEASE, root, *args, base="main")


def test_1738_q2_the_release_check_passes_a_verified_hand_merged_flip(tmp_path):
    """REQ-035: Q-1738-2 (3): every fact holds, so the flip is part of the release."""
    root, saved, pulls, body, _ = accepted_release(tmp_path)
    proc = release_check(root, "--comments", saved, "--body", body, "--pulls", pulls)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_1738_q2_a_hand_merged_line_without_pulls_fails_closed_naming_the_option(tmp_path):
    """REQ-035: Q-1738-2 (4)."""
    root, saved, _, body, _ = accepted_release(tmp_path)
    proc = release_check(root, "--comments", saved, "--body", body)
    assert proc.returncode == 1 and "option --pulls" in proc.stdout, proc.stdout


def test_1738_q2_without_the_body_the_flip_is_refused_as_today(tmp_path):
    """REQ-035: Q-1738-2 (4): no line read, so the flip is a change outside the release files."""
    root, saved, pulls, _, _ = accepted_release(tmp_path)
    proc = release_check(root, "--comments", saved, "--pulls", pulls)
    assert proc.returncode == 1 and "rule 5" in proc.stdout and HAND_ADR in proc.stdout


def test_1738_q2_a_head_mismatch_or_a_missing_payload_fails_closed(tmp_path):
    """REQ-035: Q-1738-2 (4) and (6): a head mismatch, another merge commit, a missing payload."""
    root, saved, _, body, sha = accepted_release(tmp_path)
    for name, payload in (
        ("head", {"merge_commit_sha": sha, "head": {"sha": "f" * 40}}),
        ("commit", {"merge_commit_sha": "c" * 40, "head": {"sha": HAND_HEAD}}),
        ("merged", {"merge_commit_sha": sha, "head": {"sha": HAND_HEAD}, "merged": False}),
        ("missing", {"number": 13, "merge_commit_sha": sha, "head": {"sha": HAND_HEAD}}),
    ):
        path = tmp_path / f"pulls-{name}.json"
        path.write_text(json.dumps([{"number": 12, "merged": True, **payload}]), encoding="utf-8")
        proc = release_check(root, "--comments", saved, "--body", body, "--pulls", str(path))
        assert proc.returncode == 1, name
        assert "--pulls" in proc.stdout and sha not in proc.stdout, (name, proc.stdout)


def test_1738_q2_a_forged_hand_merged_line_fails_closed(tmp_path):
    """REQ-035: Q-1738-2 (6): a line naming another pull request's Final, or a merged squash."""
    for at, line in enumerate(("Hand-merged: #12 Final 42", "Hand-merged: #7 Final 42")):
        (tmp_path / str(at)).mkdir()
        root, saved, pulls, body, _ = accepted_release(tmp_path / str(at), line)
        proc = release_check(root, "--comments", saved, "--body", body, "--pulls", pulls)
        assert proc.returncode == 1, line
        assert "--pulls" in proc.stdout, proc.stdout


def test_1738_q2_a_body_with_no_hand_merged_line_checks_as_before(tmp_path):
    """REQ-035: Q-1738-2 (6): unchanged; the brief #1706 release still passes with the options."""
    root, saved = accept_world(tmp_path)
    assert accept(root, "--comments", saved).returncode == 0
    commit_as(root, "release: 1.1.0")
    body = tmp_path / "plain.md"
    body.write_text("Summary: a release\n", encoding="utf-8")
    empty = tmp_path / "empty-pulls.json"
    empty.write_text("", encoding="utf-8")
    for args in ((), ("--body", str(body)), ("--body", str(body), "--pulls", str(empty))):
        proc = release_check(root, "--comments", saved, *args)
        assert proc.returncode == 0, (args, proc.stdout + proc.stderr)


def test_1738_q2_record_ids_and_hand_merged_read_the_lines_offline(tmp_path):
    """REQ-035: Q-1738-2 (2): `--record-ids --body` adds the Final id, `--hand-merged` the number."""
    root, _, _, body, _ = accepted_release(tmp_path)
    ids = run(ADRS_SCRIPT, root, "--record-ids", "--body", body, base="main")
    assert "120" in ids.stdout.split(), ids.stdout
    numbers = run(ADRS_SCRIPT, root, "--hand-merged", "--body", body)
    assert (numbers.returncode, numbers.stdout) == (0, "12\n")
    none = run(ADRS_SCRIPT, root, "--hand-merged")
    assert none.returncode == 1 and "option --body" in none.stdout


def test_1738_q2_the_release_exemption_of_protected_changes_reads_the_lines(tmp_path):
    """REQ-035: Q-1738-2 (3): `valid_release`, which check_protected_changes asks, takes both."""
    import check_adrs
    import check_release
    from common import merge_base

    root, saved, pulls, body, _ = accepted_release(tmp_path)
    comments = check_adrs.read_comments(saved)
    mb = merge_base(root, "main")
    text = Path(body).read_text(encoding="utf-8")
    assert check_release.valid_release(root, mb, comments, text, pulls)
    assert not check_release.valid_release(root, mb, comments, text)
