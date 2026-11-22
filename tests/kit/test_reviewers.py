"""Tests of scripts/agk/reviewers.py."""

from __future__ import annotations

import pytest
from reviewers import ReviewerError, parse, render_codeowners, validate

GOOD = """version: 1
classes:
  protected: {paths: [config/, docs/requirements.md], approvers: [maintainers]}
  docs:      {paths: [docs/, README.md], approvers: [maintainers]}
teams:
  maintainers: {github_team: "@some-team"}   # comment
"""
PROTECTED = "config/\ndocs/requirements.md\n"


def test_ac1_schema_accepts_good_file():
    """REQ-005 AC1"""
    data = parse(GOOD)
    assert data["classes"]["docs"]["paths"] == ["docs/", "README.md"]
    assert data["teams"]["maintainers"]["github_team"] == "@some-team"
    assert validate(data, PROTECTED) == []


@pytest.mark.parametrize(
    "old,new",
    [
        ("version: 1", "version: 2"),
        ("approvers: [maintainers]}\n  docs", "approvers: [ghost]}\n  docs"),
        ("approvers: [maintainers]}\n  docs", "approvers: [@someone]}\n  docs"),
        ("paths: [docs/, README.md]", "paths: []"),
        ('"@some-team"', '"some-team"'),
    ],
)
def test_ac1_ac3_schema_rejects_bad_file(old, new):
    """REQ-005 AC1 AC3: approvers are team names, never personal handles."""
    assert validate(parse(GOOD.replace(old, new)), PROTECTED) != []


def test_protected_paths_must_equal_protected_class():
    """REQ-005 AC1"""
    assert validate(parse(GOOD), "config/\n") != []


def test_unparseable_input_raises():
    """REQ-005 AC1"""
    with pytest.raises(ReviewerError):
        parse("classes: [oops\n")


def test_ac2_codeowners_rendered_broad_to_narrow():
    """REQ-005 AC2: later lines win in CODEOWNERS, so broad paths come first."""
    out = render_codeowners(parse(GOOD))
    lines = [ln for ln in out.splitlines() if ln and not ln.startswith("#")]
    assert "/docs/ @some-team" in lines
    assert "/docs/requirements.md @some-team" in lines
    assert lines.index("/docs/ @some-team") < lines.index("/docs/requirements.md @some-team")


def test_cli_check_and_codeowners(repo):
    """REQ-005 AC1 AC2"""
    repo.commit({"config/reviewers.yaml": GOOD, "config/protected-paths.txt": PROTECTED})
    assert repo.run("reviewers.py", "--check").returncode == 0
    proc = repo.run("reviewers.py", "--codeowners")
    assert proc.returncode == 0 and "@some-team" in proc.stdout
    repo.commit({"config/protected-paths.txt": "config/\n"})
    assert repo.run("reviewers.py", "--check").returncode == 1


def codeowners_repo(repo, text=None):
    from reviewers import parse, render_codeowners

    rendered = render_codeowners(parse(GOOD))
    repo.commit(
        {
            "config/reviewers.yaml": GOOD,
            "config/protected-paths.txt": PROTECTED,
            ".github/CODEOWNERS": rendered if text is None else text,
        }
    )


def test_ac2_committed_codeowners_matching_rendering_passes(repo):
    """REQ-005 AC2"""
    codeowners_repo(repo)
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 0


def test_ac2_codeowners_mismatch_fails_and_names_file_not_content(repo):
    """REQ-005 AC2"""
    codeowners_repo(repo, "/docs/ @someone-else\n")
    proc = repo.run("reviewers.py", "--check-codeowners")
    assert proc.returncode == 1
    assert "CODEOWNERS" in proc.stdout and "someone-else" not in proc.stdout


def test_ac2_missing_codeowners_fails(repo):
    """REQ-005 AC2"""
    codeowners_repo(repo)
    repo.commit({".github/CODEOWNERS": None})
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 1


DUP = """version: 1
classes:
  first:  {paths: [x/, y/z.md], approvers: [t1]}
  second: {paths: [x/, w/], approvers: [t2]}
teams:
  t1: {github_team: "@one"}
  t2: {github_team: "@two"}
"""


def test_ac2_codeowners_emits_each_path_once_last_class_wins():
    """REQ-005 AC2: a path in two classes is rendered once, with the later class's owners."""
    out = render_codeowners(parse(DUP))
    lines = [ln for ln in out.splitlines() if ln and not ln.startswith("#")]
    paths = [ln.split()[0] for ln in lines]
    assert len(paths) == len(set(paths))
    assert "/x/ @two" in lines and "/x/ @one" not in lines
    assert "/y/z.md @one" in lines and "/w/ @two" in lines


def test_ac2_codeowners_order_rule_is_unchanged_for_unique_paths():
    """REQ-005 AC2: broad first, narrow last (depth, then length)."""
    out = render_codeowners(parse(DUP))
    lines = [ln.split()[0] for ln in out.splitlines() if ln and not ln.startswith("#")]
    assert lines == sorted(lines, key=lambda p: (p.lstrip("/").rstrip("/").count("/"), len(p) - 1))


def test_ac2_committed_codeowners_of_this_repository_has_no_duplicate_paths():
    """REQ-005 AC2: the rendering of the repository's own config is duplicate-free."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    text = (root / "config" / "reviewers.yaml").read_text(encoding="utf-8")
    paths = [
        ln.split()[0]
        for ln in render_codeowners(parse(text)).splitlines()
        if ln and not ln.startswith("#")
    ]
    assert len(paths) == len(set(paths))


def test_ac2_codeowners_block_is_checked_alone(repo):
    """REQ-005 AC2: a marked block inside a project CODEOWNERS is compared, the rest is ignored."""
    from reviewers import parse, render_codeowners

    rendered = render_codeowners(parse(GOOD))
    block = "# >>> agk\n" + rendered + "# <<< agk\n"
    repo.commit(
        {
            "config/reviewers.yaml": GOOD,
            "config/protected-paths.txt": PROTECTED,
            ".github/CODEOWNERS": "* @project\n" + block,
        }
    )
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 0
    repo.commit({".github/CODEOWNERS": "* @other\n" + block})
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 0
    repo.commit({".github/CODEOWNERS": "* @project\n" + block.replace("@some-team", "@x")})
    proc = repo.run("reviewers.py", "--check-codeowners")
    assert proc.returncode == 1 and "x" not in proc.stdout.replace("CODEOWNERS", "")


def test_ac2_codeowners_with_broken_markers_fails(repo):
    """REQ-005 AC2"""
    repo.commit(
        {
            "config/reviewers.yaml": GOOD,
            "config/protected-paths.txt": PROTECTED,
            ".github/CODEOWNERS": "# >>> agk\nno end marker\n",
        }
    )
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 1


def write_repo(repo, mode=None, codeowners=None):
    files = {"config/reviewers.yaml": GOOD, "config/protected-paths.txt": PROTECTED}
    if mode:
        files["agk.toml"] = f'mode = "{mode}"\n'
    if codeowners is not None:
        files[".github/CODEOWNERS"] = codeowners
    repo.commit(files)


def rendered():
    from reviewers import parse, render_codeowners

    return render_codeowners(parse(GOOD))


def test_ac2_plain_codeowners_still_prints_and_writes_nothing(repo):
    """REQ-005 AC2 (finding b)."""
    write_repo(repo)
    proc = repo.run("reviewers.py", "--codeowners")
    assert proc.returncode == 0 and proc.stdout == rendered()
    assert not (repo.root / ".github" / "CODEOWNERS").exists()


def test_ac2_write_creates_the_whole_file_and_check_passes(repo):
    """REQ-005 AC2 (finding b): init and this repository write the whole file."""
    write_repo(repo)
    proc = repo.run("reviewers.py", "--codeowners", "--write")
    assert proc.returncode == 0 and "wrote .github/CODEOWNERS" in proc.stdout
    assert (repo.root / ".github" / "CODEOWNERS").read_text() == rendered()
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 0


def test_ac2_write_replaces_a_stale_file_and_is_idempotent(repo):
    """REQ-005 AC2 (finding b)."""
    write_repo(repo, codeowners="/docs/ @stale\n")
    assert repo.run("reviewers.py", "--codeowners", "--write").returncode == 0
    path = repo.root / ".github" / "CODEOWNERS"
    assert path.read_text() == rendered()
    before = path.stat().st_mtime_ns
    proc = repo.run("reviewers.py", "--codeowners", "--write")
    assert proc.returncode == 0 and "unchanged" in proc.stdout
    assert path.stat().st_mtime_ns == before


def test_ac2_write_in_adopt_mode_appends_the_block_after_project_lines(repo):
    """REQ-005 AC2 (finding b): adopt mode writes only the marked block."""
    write_repo(repo, mode="adopt", codeowners="* @project\n")
    proc = repo.run("reviewers.py", "--codeowners", "--write")
    assert proc.returncode == 0 and "agk block" in proc.stdout
    text = (repo.root / ".github" / "CODEOWNERS").read_text()
    assert text == "* @project\n# >>> agk\n" + rendered() + "# <<< agk\n"
    assert repo.run("reviewers.py", "--check-codeowners").returncode == 0


def test_ac2_write_in_adopt_mode_replaces_a_stale_block_and_keeps_the_rest(repo):
    """REQ-005 AC2 (finding b)."""
    stale = "* @project\n# >>> agk\n/docs/ @stale\n# <<< agk\n/pkg/ @project\n"
    write_repo(repo, mode="adopt", codeowners=stale)
    assert repo.run("reviewers.py", "--codeowners", "--write").returncode == 0
    text = (repo.root / ".github" / "CODEOWNERS").read_text()
    assert text == "* @project\n# >>> agk\n" + rendered() + "# <<< agk\n/pkg/ @project\n"
    again = repo.run("reviewers.py", "--codeowners", "--write")
    assert again.returncode == 0 and "unchanged" in again.stdout


def test_ac2_write_in_adopt_mode_creates_an_absent_file_whole(repo):
    """REQ-005 AC2 (finding b): the same as adopt, which creates an absent CODEOWNERS whole."""
    write_repo(repo, mode="adopt")
    assert repo.run("reviewers.py", "--codeowners", "--write").returncode == 0
    assert (repo.root / ".github" / "CODEOWNERS").read_text() == rendered()


def test_ac2_write_refuses_a_broken_block_and_leaves_the_file_alone(repo):
    """REQ-005 AC2 (finding b)."""
    broken = "* @project\n# >>> agk\nno end marker\n"
    write_repo(repo, mode="adopt", codeowners=broken)
    proc = repo.run("reviewers.py", "--codeowners", "--write")
    assert proc.returncode == 1 and "CODEOWNERS" in proc.stdout
    assert (repo.root / ".github" / "CODEOWNERS").read_text() == broken


def test_ac2_write_refuses_an_invalid_config_and_writes_nothing(repo):
    """REQ-005 AC2 (finding b)."""
    repo.commit(
        {
            "config/reviewers.yaml": GOOD.replace("version: 1", "version: 2"),
            "config/protected-paths.txt": PROTECTED,
        }
    )
    proc = repo.run("reviewers.py", "--codeowners", "--write")
    assert proc.returncode == 1
    assert not (repo.root / ".github" / "CODEOWNERS").exists()


def test_ac2_write_needs_codeowners_and_nothing_else(repo):
    """REQ-005 AC2 (finding b): --write alone, or with another mode, is a usage error."""
    write_repo(repo)
    for args in (["--write"], ["--check", "--write"], ["--check-codeowners", "--write"]):
        proc = repo.run("reviewers.py", *args)
        assert proc.returncode == 1 and "usage" in proc.stdout
    assert not (repo.root / ".github" / "CODEOWNERS").exists()


# --- brief #1691 (ADR-0661 build (b), ADR-0704; REQ-069): the `Who:` reading of approvals ------

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import reviewers  # noqa: E402

SHA = "c" * 40
APPS = ["claude"]
SAID = 'Owner said (2026-11-22T04:00Z): "Yes, go ahead."'
ASKED = 'Asked (2026-11-22T03:55Z): "Shall I approve the login page?" https://example.com/pull/7'
FOOTER = "\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_\n"
SHOWN_LINES = ["Shown:", "1. what changes: x", "2. what it risks: y", "3. what stays: z"]
SIGNED = "confirmed by boss in a session at 2026-11-22T04:00:00Z"


def posted(body: str, login: str = "boss", app: str | None = None) -> dict:
    item = {"user": {"login": login}, "body": body, "created_at": "2026-11-22T04:01:00Z"}
    if app:
        item["performed_via_github_app"] = {"slug": app}
    return item


def steward_post(first: list[str], who: str = "Who: ProductOwner", quotes=(SAID, ASKED)) -> str:
    return "\n".join([*first, *quotes, "", who]) + FOOTER


def solo_confirmation(who: str = "Who: ProductOwner", quotes=(SAID, ASKED)) -> str:
    lines = [f"Confirmed: {SHA}", f"Verdict: cleared {SHA}", "Approve: SPEC-0062", *quotes]
    return "\n".join([*lines, *SHOWN_LINES, SIGNED, "", who]) + FOOTER


def derived(body: str, app: str | None = None) -> list[str]:
    items = [posted(body, app=app)]
    return [x["body"] for x in reviewers.confirmed_comments(items, APPS, "boss")[1:]]


def test_req069_a_solo_steward_confirmation_counts_without_its_quotes():
    """REQ-069 AC7: amendment 194 item 5, the footer and `Who: ProductOwner` dropped, both quotes
    present; the verdict it stands for holds no quote line."""
    found = derived(solo_confirmation())
    assert found[1] == f"Approve: {SHA} SPEC-0062"
    assert found[0].startswith(f"Verdict: cleared {SHA}")
    assert "Owner said" not in found[0] and "Asked (" not in found[0]


@pytest.mark.parametrize(
    "body",
    [
        solo_confirmation("Who: AGK steward"),
        solo_confirmation("Who: AGK"),
        solo_confirmation(quotes=(SAID,)),
        solo_confirmation(quotes=(ASKED,)),
        solo_confirmation(quotes=()),
    ],
)
def test_req069_a_confirmation_marked_by_the_kit_or_missing_a_quote_counts_for_nothing(body):
    """REQ-069 AC7: any `Who: AGK…` approves nothing; `Who: ProductOwner` needs both quotes."""
    assert derived(body) == []


def test_req069_a_typed_confirmation_without_who_still_counts_and_an_app_post_never():
    """REQ-069 AC7: a comment with no `Who:` line counts as today; an app mark adds nothing."""
    typed = "\n".join([f"Confirmed: {SHA}", f"Verdict: cleared {SHA}", *SHOWN_LINES, SIGNED])
    assert derived(typed) == [f"Verdict: cleared {SHA}\n"]
    assert derived(solo_confirmation(), app="claude") == []


def test_req069_crlf_two_who_lines_and_unicode_read_the_same():
    """REQ-069 AC7: Windows line ends, the last of two `Who:` lines, non-ASCII words."""
    body = solo_confirmation().replace('"Yes, go ahead."', '"Ja, gerne."')
    assert derived(body.replace("\n", "\r\n"))[1] == f"Approve: {SHA} SPEC-0062"
    two = solo_confirmation("Who: AGK steward\nWho: ProductOwner")
    assert derived(two)[1] == f"Approve: {SHA} SPEC-0062"
    assert derived(solo_confirmation("Who: ProductOwner\nWho: AGK steward")) == []


@pytest.mark.parametrize(
    ("who", "quotes", "app", "counts"),
    [
        ("Who: ProductOwner", (SAID, ASKED), None, True),
        ("Who: AGK steward", (SAID, ASKED), None, False),
        ("Who: ProductOwner", (SAID,), None, False),
        ("Who: ProductOwner", (SAID, ASKED), "claude", False),
        (None, (), None, True),
    ],
)
def test_req069_each_approval_reader_reads_the_who_line(who, quotes, app, counts):
    """REQ-069 AC7: `approval_shas`, `person_approvals`, `design_approvals`, `plan_approvals` and
    `scope_approvals` drop the footer and the last `Who:` line, then read the first line."""

    def item(first: str) -> list[dict]:
        text = first if who is None else steward_post([first], who, quotes)
        return [posted(text, app=app)]

    for solo, expected in ((True, counts), (False, counts and who is None)):
        spec = item(f"Approve: {SHA} SPEC-0062")
        found = reviewers.approval_shas(spec, [], ["boss"], agent_apps=APPS, solo=solo)
        assert bool(found) is expected
        short = item("Approve: SPEC-0062")
        found = reviewers.person_approvals(short, [], ["boss"], agent_apps=APPS, solo=solo)
        assert bool(found) is expected
        design = item(f"Approve: design v1 {SHA}")
        assert bool(reviewers.design_approvals(design, ["boss"], APPS, solo=solo)) is expected
        plan = item(f"Approve: plan {SHA}")
        assert bool(reviewers.plan_approvals(plan, ["boss"], APPS, solo=solo)) is expected
        scope = item(f"Approve: scope SC-1 {SHA}")
        assert bool(reviewers.scope_approvals(scope, ["boss"], APPS, solo=solo)) is expected


def test_req069_an_empty_agent_apps_lets_a_marked_post_count():
    """REQ-069 AC7: `agent_apps` empty: the project chose that a marked post counts."""
    body = steward_post([f"Approve: {SHA} SPEC-0062"])
    items = [posted(body, app="claude")]
    assert reviewers.approval_shas(items, [], ["boss"], agent_apps=[], solo=True)


@pytest.mark.parametrize(
    ("toml", "counts"),
    [('review_mode = "solo"\n', True), ('review_mode = "team"\n', False), (None, False)],
)
def test_req069_a_steward_approval_counts_only_in_solo_mode_read_once(
    tmp_path, monkeypatch, toml, counts
):
    """REQ-069 AC7: SPEC-0062 rule 15 (fix list on 404e674): with no mode given, the readers
    read `review_mode` of the repository once; team mode, or a mode that cannot be read, counts
    no `Who: ProductOwner` approval, while a typed one with no `Who:` line counts as today."""
    if toml is not None:
        (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    root = tmp_path if toml is not None else tmp_path / "missing"
    monkeypatch.setattr(reviewers, "repo_root", lambda: root)
    reviewers.solo_here.cache_clear()
    try:
        steward = [posted(steward_post([f"Approve: {SHA} SPEC-0062"]))]
        assert bool(reviewers.approval_shas(steward, [], ["boss"], agent_apps=APPS)) is counts
        typed = [posted(f"Approve: {SHA} SPEC-0062")]
        assert reviewers.approval_shas(typed, [], ["boss"], agent_apps=APPS)
        assert bool(derived(solo_confirmation())) is True  # a person is named: solo was read
    finally:
        reviewers.solo_here.cache_clear()
