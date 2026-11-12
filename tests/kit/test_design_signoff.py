"""Tests of the frozen signed-off version (SPEC-0037 rules 9 and 12; REQ-044 AC5, brief #459).

`design_signoff.frozen_problems(root)` compares each `design` row of `docs/design/signoffs.md` with
`version_digest` of its folder and fails `rule 9: docs/design/prototype/<version>: a signed-off
version changed`, naming the version and never a digest; `screenshots/` stays outside.
`check_design.py` calls it, and a theme whose evidence line names a prototype version reads
approved only with a `design` row of a matching digest (rule 12). No check writes a file.

An imported version `i<n>` (amendment 161 item 4, brief #1062, ADR-0449) is signed off with
`Approve: design i<n> <full head ID>` by an account of `spec_approvers` on the head it names,
inside a
solo `Confirmed:` comment too; its `design` row carries `i<n>` and the digest of the whole folder
`docs/design/imported/i<n>/` by rule 9's formula, and a change, an addition or a removal anywhere in
that folder fails `rule 9: docs/design/imported/i<n>: a signed-off version changed`.
Invented data only, in `tmp_path`; files only, no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import check_design  # noqa: E402
import design_signoff as ds  # noqa: E402
import pytest  # noqa: E402
import reviewers  # noqa: E402

V1 = "docs/design/prototype/v1"
HEAD = "0123456789abcdef0123456789abcdef01234567"
LINK = "https://example.com/acme/books/pull/12#issuecomment-345"
CHANGED = "rule 9: docs/design/prototype/v1: a signed-off version changed"
THEME = "# Theme\n\n## Brand\n\n## Evidence\n\nEvidence: docs/design/prototype/v1/\n"


def signed(root: Path, digest: str | None = None) -> Path:
    """An invented version v1 and its `design` row with the digest of the folder as it is."""
    folder = root / V1
    (folder / "screenshots").mkdir(parents=True)
    (folder / "index.html").write_text("<!doctype html><title>Books</title>\n", encoding="utf-8")
    (folder / "books--default.html").write_text("<h1>Books</h1>\n", encoding="utf-8")
    (folder / "screenshots" / "reflow.json").write_text("{}\n", encoding="utf-8")
    value = digest or ds.version_digest(root, "v1")
    (root / ds.SIGNOFFS).write_text(
        "# Design sign-offs\n\n| kind | version | digest | head | date | comment |\n"
        f"|---|---|---|---|---|---|\n| design | v1 | {value} | {HEAD} | 2026-11-10 | {LINK} |\n",
        encoding="utf-8",
    )
    return folder


def listing(root: Path) -> dict[str, tuple[int, int]]:
    return {
        p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
    }


def test_ac5_a_frozen_version_passes(tmp_path):
    """REQ-044 AC5: a version whose folder still has the signed-off digest has no problem."""
    signed(tmp_path)
    assert ds.frozen_problems(tmp_path) == []


def test_ac5_a_changed_file_fails_naming_the_version_never_the_digest(tmp_path):
    """REQ-044 AC5: a change in place fails naming rule 9 and the version."""
    folder = signed(tmp_path)
    before = ds.version_digest(tmp_path, "v1")
    (folder / "books--default.html").write_text("<h1>Books, changed</h1>\n", encoding="utf-8")
    after = ds.version_digest(tmp_path, "v1")
    problems = ds.frozen_problems(tmp_path)
    assert problems == [CHANGED]
    assert before not in problems[0] and after not in problems[0]


def test_ac5_an_added_file_fails(tmp_path):
    """REQ-044 AC5: an addition counts as a change."""
    folder = signed(tmp_path)
    (folder / "books--empty.html").write_text("<h1>No books</h1>\n", encoding="utf-8")
    assert ds.frozen_problems(tmp_path) == [CHANGED]


def test_ac5_a_removed_file_fails(tmp_path):
    """REQ-044 AC5: a removal counts as a change."""
    folder = signed(tmp_path)
    (folder / "books--default.html").unlink()
    assert ds.frozen_problems(tmp_path) == [CHANGED]


def test_ac5_a_removed_folder_fails(tmp_path):
    """REQ-044 AC5: a signed-off folder that is gone has changed too."""
    folder = signed(tmp_path)
    for path in sorted(folder.rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    folder.rmdir()
    assert ds.frozen_problems(tmp_path) == [CHANGED]


def test_ac5_a_change_under_screenshots_passes(tmp_path):
    """REQ-044 AC5: `screenshots/` stays outside what the person signs off."""
    folder = signed(tmp_path)
    (folder / "screenshots" / "reflow.json").write_text('{"v1": []}\n', encoding="utf-8")
    (folder / "screenshots" / "home--default-360-light.png").write_bytes(b"\x89PNG one")
    assert ds.frozen_problems(tmp_path) == []


def test_ac5_no_record_and_inventory_rows_have_no_problem(tmp_path):
    """REQ-044 AC5: only `design` rows freeze a folder; no record freezes nothing."""
    assert ds.frozen_problems(tmp_path) == []
    (tmp_path / "docs" / "design").mkdir(parents=True)
    (tmp_path / ds.SIGNOFFS).write_text(
        "| kind | version | digest | head | date | comment |\n|---|---|---|---|---|---|\n"
        f"| inventory | - | {'c' * 64} | {HEAD} | 2026-11-10 | {LINK} |\n",
        encoding="utf-8",
    )
    assert ds.frozen_problems(tmp_path) == []


def test_ac5_check_design_fails_a_changed_signed_off_version(tmp_path):
    """REQ-044 AC5: `check_design.py` calls `frozen_problems` and prints its line."""
    folder = signed(tmp_path)
    (folder / "index.html").write_text("<!doctype html><title>Other</title>\n", encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_design.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        env={**os.environ},
        check=False,
    )
    assert proc.returncode == 1
    assert f"FAIL design: {CHANGED}" in proc.stdout


def test_ac5_the_evidence_line_reads_approved_with_a_matching_row(tmp_path):
    """REQ-044 AC5 (rule 12): a prototype version with a row of its digest reads approved."""
    signed(tmp_path)
    assert check_design.theme_problems(tmp_path, THEME)[3] is True


def test_ac5_the_evidence_line_reads_not_approved_yet_without_a_matching_row(tmp_path):
    """REQ-044 AC5 (rule 12): no row, or a row of another digest, reads not approved yet."""
    signed(tmp_path, digest="d" * 64)
    assert check_design.theme_problems(tmp_path, THEME)[3] is False
    (tmp_path / ds.SIGNOFFS).unlink()
    assert check_design.theme_problems(tmp_path, THEME)[3] is False


def test_ac5_no_check_writes_a_file(tmp_path):
    """REQ-044 AC5: sizes and times of every path are unchanged after every check."""
    folder = signed(tmp_path)
    (tmp_path / check_design.THEME).write_text(THEME, encoding="utf-8")
    (folder / "books--default.html").write_text("<h1>Changed</h1>\n", encoding="utf-8")
    before = listing(tmp_path)
    ds.frozen_problems(tmp_path)
    ds.rows(tmp_path)
    check_design.theme_problems(tmp_path, THEME)
    subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_design.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert listing(tmp_path) == before


# Amendment 161 item 4: the sign-off of an imported version (brief #1062, ADR-0449).

I1 = "docs/design/imported/i1"
I_CHANGED = "rule 9: docs/design/imported/i1: a signed-off version changed"
OWNER = "example-owner"
OTHER = "example-other"
AT = "2026-11-12T03:00:00Z"
TABLE = (
    "# Design sign-offs\n\n| kind | version | digest | head | date | comment |\n"
    "|---|---|---|---|---|---|\n"
)


def imported(root: Path) -> Path:
    """An invented imported version i1: copied files, manifest, map and external list."""
    folder = root / I1
    (folder / "files" / "img").mkdir(parents=True)
    (folder / "files" / "index.html").write_text(
        "<!doctype html><title>Books</title><script>go()</script>\n", encoding="utf-8"
    )
    (folder / "files" / "img" / "logo.svg").write_text("<svg></svg>\n", encoding="utf-8")
    (folder / "manifest.json").write_text(
        '{"files": [], "digest": "", "pages": []}\n', encoding="utf-8"
    )
    (folder / "map.md").write_text("index.html -> books/default\n", encoding="utf-8")
    (folder / "external.txt").write_text(
        "files/index.html https://example.com/a.css\n", encoding="utf-8"
    )
    return folder


def sign_imported(root: Path, digest: str | None = None) -> Path:
    folder = imported(root)
    value = digest or ds.imported_digest(root, "i1")
    (root / ds.SIGNOFFS).write_text(
        TABLE + f"| design | i1 | {value} | {HEAD} | 2026-11-12 | {LINK} |\n", encoding="utf-8"
    )
    return folder


def test_ac5_the_imported_digest_is_rule_9s_formula_over_the_whole_folder(tmp_path):
    """REQ-044 AC5: `files/`, `manifest.json`, `map.md` and `external.txt` all count, by rule 9."""
    folder = imported(tmp_path)
    paths = sorted(p for p in folder.rglob("*") if p.is_file())
    assert len(paths) == 5
    assert ds.imported_digest(tmp_path, "i1") == ds.digest(tmp_path, paths)
    assert ds.version_digest(tmp_path, "i1") == ds.imported_digest(tmp_path, "i1")


def test_ac5_the_imported_digest_refuses_a_kit_version_and_a_missing_folder(tmp_path):
    """REQ-044 AC5: `imported_digest` reads only `i<n>` and an existing folder, naming the rule."""
    for version in ("v1", "i0", "x1", "i1"):
        with pytest.raises(ds.CheckError, match="^rule 9: "):
            ds.imported_digest(tmp_path, version)


def test_ac5_the_version_accepts_i_n_beside_v_n():
    """REQ-044 AC5: `VERSION` and `APPROVE_DESIGN` accept `i<n>` beside `v<n>`, nothing else."""
    for good in ("v1", "v12", "i1", "i30"):
        assert ds.VERSION.match(good)
    for bad in ("i0", "v0", "x1", "i", "I1", "i1a"):
        assert not ds.VERSION.match(bad)
    head = "1" * 40
    assert reviewers.APPROVE_DESIGN.fullmatch(f"Approve: design i1 {head}")[1] == "i1"
    assert reviewers.APPROVE_DESIGN.fullmatch(f"Approve: design v2 {head}")[1] == "v2"
    assert not reviewers.APPROVE_DESIGN.fullmatch(f"Approve: design i0 {head}")


def test_ac5_a_design_row_reads_i_n_and_refuses_another_version(tmp_path):
    """REQ-044 AC5: the record reads an `i<n>` row; another version fails naming the column."""
    sign_imported(tmp_path)
    assert [r["version"] for r in ds.rows(tmp_path)] == ["i1"]
    bad = TABLE + f"| design | x1 | {'a' * 64} | {HEAD} | 2026-11-12 | {LINK} |\n"
    with pytest.raises(
        ds.CheckError, match="row 1: the version of a design row is not v<n> or i<n>$"
    ):
        ds.parse_rows(bad)


def test_ac5_a_signed_off_imported_version_passes_while_unchanged(tmp_path):
    """REQ-044 AC5: the folder with its signed-off digest has no problem and reads signed off."""
    sign_imported(tmp_path)
    assert ds.frozen_problems(tmp_path) == []
    assert ds.signed_off(tmp_path, "i1") is True


@pytest.mark.parametrize("change", ["map", "page", "add", "remove", "external", "manifest", "gone"])
def test_ac5_a_changed_signed_off_imported_folder_fails_naming_the_version(tmp_path, change):
    """REQ-044 AC5: a change, an addition or a removal anywhere fails, never naming a digest."""
    folder = sign_imported(tmp_path)
    before = ds.imported_digest(tmp_path, "i1")
    if change == "map":
        (folder / "map.md").write_text("index.html -> books/empty\n", encoding="utf-8")
    elif change == "page":
        (folder / "files" / "index.html").write_text("<title>Other</title>\n", encoding="utf-8")
    elif change == "add":
        (folder / "files" / "more.html").write_text("<h1>More</h1>\n", encoding="utf-8")
    elif change == "remove":
        (folder / "files" / "img" / "logo.svg").unlink()
    elif change == "external":
        (folder / "external.txt").write_text("", encoding="utf-8")
    elif change == "manifest":
        (folder / "manifest.json").write_text("{}\n", encoding="utf-8")
    else:
        for path in sorted(folder.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        folder.rmdir()
    problems = ds.frozen_problems(tmp_path)
    assert problems == [I_CHANGED]
    assert before not in problems[0]
    assert ds.signed_off(tmp_path, "i1") is False


def test_ac5_a_kit_and_an_imported_version_are_frozen_apart(tmp_path):
    """REQ-044 AC5: `v1` and `i1` rows each name their own folder; a change to one names only it."""
    signed(tmp_path)
    folder = imported(tmp_path)
    rows = (tmp_path / ds.SIGNOFFS).read_text(encoding="utf-8")
    row = f"| design | i1 | {ds.imported_digest(tmp_path, 'i1')} | {HEAD} | 2026-11-12 | {LINK} |\n"
    (tmp_path / ds.SIGNOFFS).write_text(rows + row, encoding="utf-8")
    assert ds.frozen_problems(tmp_path) == []
    (folder / "map.md").write_text("index.html -> out: replaced\n", encoding="utf-8")
    assert ds.frozen_problems(tmp_path) == [I_CHANGED]


def test_ac5_check_design_fails_a_changed_signed_off_imported_version(tmp_path):
    """REQ-044 AC5: `check_design.py` prints the line naming the rule and the version."""
    folder = sign_imported(tmp_path)
    (folder / "map.md").write_text("index.html -> books/empty\n", encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts/agk/check_design.py"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert f"FAIL design: {I_CHANGED}" in proc.stdout


def _comment(body: str, login: str = OWNER, app: str | None = None) -> dict:
    item = {"body": body, "created_at": AT, "user": {"login": login}}
    if app:
        item["performed_via_github_app"] = {"slug": app}
    return item


def test_ac5_approve_design_i_n_by_a_listed_account_counts():
    """REQ-044 AC5: a listed account's `Approve: design i1 <head>` gives (design, i1, head);
    another account, an app, a short head or a line that is not first gives nothing."""
    head = "1" * 40
    items = [
        _comment(f"Approve: design i1 {head}"),
        _comment(f"Approve: design i2 {head}", login=OTHER),
        _comment(f"Approve: design i3 {head}", app="claude"),
        _comment(f"Approve: design i4 {head[:7]}"),
        _comment(f"note\nApprove: design i5 {head}"),
    ]
    assert reviewers.design_approvals(items, [OWNER], ["claude"]) == {("design", "i1", head)}


def _confirmed(head: str, line: str) -> dict:
    body = "\n".join(
        [
            f"Confirmed: {head}",
            f"Verdict: cleared {head}",
            line,
            "Shown:",
            "the imported version i1",
            "every page mapped",
            "signed off",
            f"confirmed by {OWNER} in a session at {AT}",
        ]
    )
    return _comment(body)


def test_ac5_a_solo_confirmed_comment_counts_for_i_n_as_for_v_n():
    """REQ-044 AC5: inside the person's `Confirmed:` the `i<n>` line counts on that head only."""
    head = "2" * 40
    for version in ("v1", "i1"):
        items = reviewers.confirmed_comments(
            [_confirmed(head, f"Approve: design {version} {head}")], ["claude"], OWNER, heads={head}
        )
        assert reviewers.design_approvals(items, [OWNER], ["claude"]) == {("design", version, head)}
    other = reviewers.confirmed_comments(
        [_confirmed("3" * 40, f"Approve: design i1 {head}")], ["claude"], OWNER
    )
    assert reviewers.design_approvals(other, [OWNER], ["claude"]) == set()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=Example", "-c", "user.email=a@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _clearance(tmp_path: Path, *comments: dict, head_of_line: str | None = None):
    """A repository whose `main` holds the imported version i1; the branch adds its `design` row in
    a commit of its own, and `check_final_clearance.py` reads COMMENTS (built from the head)."""
    import json

    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "config").mkdir()
    (root / "config" / "reviewers.yaml").write_text(
        f"version: 1\nverdict_authors: [example-conductor]\nspec_approvers: [{OWNER}]\n",
        encoding="utf-8",
    )
    (root / "agk.toml").write_text('agent_apps = ["claude"]\n', encoding="utf-8")
    imported(root)
    (root / ds.SIGNOFFS).write_text(TABLE, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--no-gpg-sign", "-m", "imported i1")
    head = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-q", "-b", "feature")
    row = f"| design | i1 | {ds.imported_digest(root, 'i1')} | {head} | 2026-11-12 | {LINK} |\n"
    (root / ds.SIGNOFFS).write_text(TABLE + row, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--no-gpg-sign", "-m", "sign-off row")
    named = head_of_line or head
    items = [dict(c, body=c["body"].replace("<head>", named)) for c in comments]
    path = tmp_path / "comments.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "CI")}
    env["AGK_BASE"] = "main"
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [
            sys.executable,
            str(KIT_ROOT / "scripts/agk/check_final_clearance.py"),
            "--comments",
            str(path),
            "--head",
            "HEAD",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


NO_LINE = "rule 9: a design sign-off row has no Approve line by an account in spec_approvers"


def test_ac5_check_final_clearance_counts_an_i_n_row_with_its_line(tmp_path):
    """REQ-044 AC5: the `i1` row counts with a listed account's line on the head it names."""
    proc = _clearance(tmp_path, _comment("Approve: design i1 <head>"))
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("case", ["other account", "other head", "app", "kit version", "none"])
def test_ac5_check_final_clearance_refuses_an_i_n_row_without_its_line(tmp_path, case):
    """REQ-044 AC5: another account, another head, an app, a `v1` line or no line does not count."""
    comments = {
        "other account": [_comment("Approve: design i1 <head>", login=OTHER)],
        "other head": [_comment("Approve: design i1 <head>")],
        "app": [_comment("Approve: design i1 <head>", app="claude")],
        "kit version": [_comment("Approve: design v1 <head>")],
        "none": [_comment("Looks good.")],
    }[case]
    proc = _clearance(tmp_path, *comments, head_of_line="4" * 40 if case == "other head" else None)
    assert proc.returncode == 1 and NO_LINE in proc.stdout
