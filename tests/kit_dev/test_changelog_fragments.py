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
