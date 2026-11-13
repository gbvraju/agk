"""Tests of the baseline and the scope changes (SPEC-0043 rules 20 to 22; REQ-050 AC6).

Rule 20: `docs/plan/baseline.json` is written once; `check_plan.py` fails a baseline of the wrong
shape and a change to, or the removal of, a baseline the merge base already holds. Rule 21: a
scope change is one block of `docs/plan/scope-changes.md` with `What:`, `Why:`, `Source:`,
`Effect:` and `Status: proposed`, and `plan_estimate.py --with SC-<n>` prints its effect before and
after. Rule 22: a brief under a baselined milestone that neither the baseline nor an approved scope
change names fails, and so does a removed baseline brief with none; with `--comments FILE` an
approval counts only as `Approve: scope SC-<n> <full head ID>` by an account of `spec_approvers`.
Invented files only (example.com), in `tmp_path`; no network.
"""

from __future__ import annotations

import json
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import check_plan
import plan_estimate
import pytest
import reviewers

HEAD = "0123456789abcdef0123456789abcdef01234567"
OWNER = "owner-example"
LINK = "https://github.com/example-org/example-repo/pull/7#issuecomment-1"
SOW = (
    "Source: Example statement of work\nKind: sow\nVersion: 1\nDate: 2026-10-01\n\n"
    "# Orders\n\n"
    "The portal at example.com lists orders.\n"  # line 8
)
SCOPE = "# Scope\n\n## In scope\n\n- Orders are listed `docs/sources/sow.md:8`\n"
REQS = (
    "# Proposed requirements\n\n### orders-list Orders are listed\n\n"
    "- Status: planned\n- Source: docs/sources/sow.md:8\n"
)
MILESTONES = (
    "# Milestones\n\n"
    "### M1 Orders\n\nExit: all 2 briefs merged.\nTarget: 2026-12-18\n\n"
    "### M2 Invoices\n\nExit: all 1 briefs merged.\nTarget: 2027-01-15\n"
)
REVIEWERS = f"verdict_authors: [conductor-example]\nspec_approvers: [{OWNER}]\n"


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def brief(root: Path, milestone: str, key: str, size: str = "M", hours: str = "4-8") -> None:
    write(
        root,
        f"docs/plan/briefs/{milestone}/{key}.md",
        f"Advances: orders-list\nTouches: app/{key}.py\nPriority: 1\nSize: {size}\n"
        f"Expected: {hours} hours\nMilestone: {milestone}\n",
    )


def baseline(**change) -> dict:
    doc = {
        "schema": 1,
        "head": HEAD,
        "date": "2026-11-12",
        "link": LINK,
        "milestones": [
            {
                "id": "M1",
                "briefs": ["m1-list", "m1-filter"],
                "target": "2026-12-18",
                "estimate": "M1 Orders: uncalibrated (history 0 of 10); declared 8-16 hours",
            },
            {
                "id": "M2",
                "briefs": ["m2-invoice"],
                "target": "2027-01-15",
                "estimate": "M2 Invoices: uncalibrated (history 0 of 10); declared 4-8 hours",
            },
        ],
    }
    return doc | change


def plan(root: Path, base: dict | None = None) -> Path:
    """The invented project with its plan, three briefs and, unless None, a baseline."""
    write(root, "docs/sources/sow.md", SOW)
    write(root, "docs/plan/scope.md", SCOPE)
    write(root, "docs/plan/requirements-proposed.md", REQS)
    write(root, "docs/plan/milestones.md", MILESTONES)
    write(root, "config/reviewers.yaml", REVIEWERS)
    brief(root, "M1", "m1-list")
    brief(root, "M1", "m1-filter", "S", "2-4")
    brief(root, "M2", "m2-invoice")
    if base is not None:
        write(root, "docs/plan/baseline.json", json.dumps(base, indent=2) + "\n")
    return root


def change(
    n: int = 1,
    briefs: str | None = "+M1/m1-export M 4-8 hours",
    approved: bool = False,
    drop: str = "",
    status: str = "proposed",
) -> str:
    lines = {
        "What": f"What: add the export of orders to M1 (SC-{n})",
        "Why": "Why: the person asked for it",
        "Source": "Source: person 2026-11-12",
        "Effect": "Effect: M1 hours before declared 8-16, after declared 12-24",
        "Status": f"Status: {status}",
    }
    block = [f"Scope change: SC-{n}"]
    block += [line for key, line in lines.items() if key != drop]
    if briefs is not None:
        block.insert(4, f"Briefs: {briefs}")
    if approved:
        block.append(f"Approved: 2026-11-13 {LINK}")
    return "\n".join(block) + "\n"


def changes(root: Path, *blocks: str) -> None:
    write(root, "docs/plan/scope-changes.md", "# Scope changes\n\n" + "\n".join(blocks))


def comment(body: str, login: str = OWNER, app: str | None = None) -> dict:
    via = {"slug": app} if app else None
    return {"body": body, "user": {"login": login}, "performed_via_github_app": via}


def check(root: Path, capsys, *args: str) -> tuple[int, list[str]]:
    code = check_plan.main(["--root", str(root), *args])
    return code, capsys.readouterr().out.splitlines()


def failures(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("FAIL ")]


@pytest.fixture(autouse=True)
def no_network(monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("the plan check opens no socket")

    monkeypatch.setattr(socket, "socket", refuse)


# --- rule 20: the baseline ----------------------------------------------------------------------


def test_a_well_formed_baseline_with_its_briefs_passes(tmp_path, capsys):
    """REQ-050 AC6: the baseline and the brief files agree, so nothing fails."""
    code, lines = check(plan(tmp_path, baseline()), capsys)
    assert failures(lines) == []
    assert code == 0
    assert lines[-1].startswith("ok plan: ")


def test_no_baseline_checks_no_scope(tmp_path, capsys):
    """REQ-050 AC6: before the confirmation any brief may be added; nothing is controlled."""
    root = plan(tmp_path)
    brief(root, "M1", "m1-export")
    code, lines = check(root, capsys)
    assert failures(lines) == [] and code == 0


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"schema": 2}, "schema"),
        ({"head": "abc1234"}, "head"),
        ({"date": "2026-02-30"}, "date"),
        ({"link": "http://example.com/x"}, "link"),
        ({"milestones": {}}, "milestones"),
    ],
)
def test_a_baseline_of_the_wrong_shape_fails_naming_the_field(tmp_path, capsys, change, field):
    """REQ-050 AC6: rule 20's fields; the failure names the field and never its value."""
    code, lines = check(plan(tmp_path, baseline(**change)), capsys)
    found = failures(lines)
    assert code == 1
    assert found == [f"FAIL plan: rule 20: docs/plan/baseline.json: {field} is not as rule 20 says"]
    value = json.dumps(change[field]).strip('"')
    assert all(value not in line for line in found if value not in ("2", "{}"))


def test_a_baseline_milestone_of_the_wrong_shape_fails(tmp_path, capsys):
    """REQ-050 AC6: each milestone holds its id, brief keys, target and estimate."""
    base = baseline()
    base["milestones"][1] = {"id": "M2", "briefs": "m2-invoice", "target": None, "estimate": "x"}
    code, lines = check(plan(tmp_path, base), capsys)
    assert code == 1
    assert failures(lines) == [
        "FAIL plan: rule 20: docs/plan/baseline.json: milestones[2] is not as rule 20 says"
    ]


def test_a_baseline_that_is_not_json_fails(tmp_path, capsys):
    root = plan(tmp_path)
    write(root, "docs/plan/baseline.json", "{not json")
    code, lines = check(root, capsys)
    assert code == 1
    assert failures(lines) == ["FAIL plan: rule 20: docs/plan/baseline.json: not a JSON object"]


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=Example", "-c", "user.email=dev@example.com", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def committed(root: Path) -> Path:
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the confirmed plan")
    return root


def test_an_edited_baseline_fails_against_the_merge_base(tmp_path, capsys):
    """REQ-050 AC6: a second write of an existing baseline fails, like an edited build-state row."""
    root = committed(plan(tmp_path, baseline()))
    base = baseline()
    base["milestones"][0]["target"] = "2027-02-01"
    write(root, "docs/plan/baseline.json", json.dumps(base, indent=2) + "\n")
    code, lines = check(root, capsys, "--base", "main")
    assert code == 1
    assert failures(lines) == [
        "FAIL plan: rule 20: docs/plan/baseline.json: changed or removed after it was written"
    ]


def test_a_removed_baseline_fails_against_the_merge_base(tmp_path, capsys):
    root = committed(plan(tmp_path, baseline()))
    (root / "docs/plan/baseline.json").unlink()
    code, lines = check(root, capsys, "--base", "main")
    assert code == 1
    assert failures(lines) == [
        "FAIL plan: rule 20: docs/plan/baseline.json: changed or removed after it was written"
    ]


def test_the_first_write_and_an_unchanged_baseline_pass(tmp_path, capsys):
    """REQ-050 AC6: a baseline absent at the merge base may be written; an unchanged one passes."""
    root = committed(plan(tmp_path))
    write(root, "docs/plan/baseline.json", json.dumps(baseline(), indent=2) + "\n")
    code, lines = check(root, capsys, "--base", "main")
    assert failures(lines) == [] and code == 0
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the baseline")
    code, lines = check(root, capsys, "--base", "main")
    assert failures(lines) == [] and code == 0


def test_in_ci_a_base_that_does_not_resolve_fails_naming_the_base(tmp_path, capsys, monkeypatch):
    """REQ-050 AC6: in CI an unread base is a failure, never a pass (principle 11)."""
    root = plan(tmp_path, baseline())
    git(root, "init", "-q", "-b", "trunk")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the confirmed plan")
    for name in ("AGK_BASE", "GITHUB_BASE_REF"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CI", "true")
    code, lines = check(root, capsys)
    assert code == 1
    assert lines == ["FAIL plan: no base ref resolves in CI"]


def test_outside_ci_with_no_base_the_change_is_not_read(tmp_path, capsys, monkeypatch):
    root = plan(tmp_path, baseline())
    git(root, "init", "-q", "-b", "trunk")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the confirmed plan")
    for name in ("AGK_BASE", "GITHUB_BASE_REF", "CI"):
        monkeypatch.delenv(name, raising=False)
    code, lines = check(root, capsys)
    assert failures(lines) == [] and code == 0


# --- rule 21: a scope change is a record --------------------------------------------------------


@pytest.mark.parametrize("field", ["What", "Why", "Source", "Effect", "Status"])
def test_a_scope_change_without_a_field_fails(tmp_path, capsys, field):
    """REQ-050 AC6: each of the five lines of rule 21 is needed."""
    root = plan(tmp_path, baseline())
    changes(root, change(drop=field))
    code, lines = check(root, capsys)
    assert code == 1
    assert f"FAIL plan: rule 21: docs/plan/scope-changes.md: SC-1: no {field}: line" in failures(
        lines
    )


def test_a_scope_change_of_another_shape_fails(tmp_path, capsys):
    """REQ-050 AC6: a status other than proposed, a bad Briefs entry, a reused number, a Source
    that names no location and an Approved line without a date and a link each fail."""
    root = plan(tmp_path, baseline())
    bad = change(2, briefs="M1/m1-export").replace("Source: person 2026-11-12", "Source: a call")
    changes(
        root,
        change(1, status="approved"),
        bad,
        change(2, briefs=None),
        "Scope change: SC-3\nWhat: x\nWhy: y\nSource: person 2026-11-12\nEffect: z\n"
        "Status: proposed\nApproved: soon\n",
    )
    code, lines = check(root, capsys)
    assert code == 1
    found = failures(lines)
    prefix = "FAIL plan: rule 21: docs/plan/scope-changes.md: "
    assert f"{prefix}SC-1: Status: is not proposed" in found
    assert (
        f"{prefix}SC-2: a Briefs: entry is not +M<n>/<key> <size> <low>-<high> hours or -M<n>/<key>"
        in found
    )
    assert f"{prefix}SC-2: Source: is neither a location nor person <date>" in found
    assert f"{prefix}SC-2: the number is used twice" in found
    assert (
        "FAIL plan: rule 22: docs/plan/scope-changes.md: SC-3: Approved: is not <date> <https link>"
        in found
    )
    assert all("a call" not in line and "soon" not in line for line in found)


def test_a_scope_change_with_a_location_source_passes(tmp_path, capsys):
    root = plan(tmp_path, baseline())
    changes(root, change().replace("person 2026-11-12", "`docs/sources/sow.md:8`"))
    code, lines = check(root, capsys)
    assert failures(lines) == [] and code == 0


# --- rule 22: approved before the briefs are added ----------------------------------------------


def test_a_brief_added_with_no_record_fails_naming_the_key(tmp_path, capsys):
    """REQ-050 AC6: a brief under a baselined milestone needs an approved scope change."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    code, lines = check(root, capsys)
    assert code == 1
    assert failures(lines) == [
        "FAIL plan: rule 22: docs/plan/briefs: m1-export: under baselined milestone M1, in "
        "neither the baseline nor an approved scope change"
    ]


def test_a_brief_added_with_a_proposed_record_fails(tmp_path, capsys):
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change())
    code, lines = check(root, capsys)
    assert code == 1
    assert any("rule 22: docs/plan/briefs: m1-export:" in line for line in failures(lines))


def test_a_brief_added_with_an_approved_record_passes(tmp_path, capsys):
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    code, lines = check(root, capsys)
    assert failures(lines) == [] and code == 0


def test_an_approval_by_an_unlisted_account_fails(tmp_path, capsys):
    """REQ-050 AC6: with the saved comments, only a listed approver's line approves."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    saved = tmp_path / "comments.json"
    saved.write_text(json.dumps([comment(f"Approve: scope SC-1 {HEAD}", "someone-else")]))
    code, lines = check(root, capsys, "--comments", str(saved))
    assert code == 1
    assert failures(lines) == [
        "FAIL plan: rule 22: docs/plan/briefs: m1-export: under baselined milestone M1, in "
        "neither the baseline nor an approved scope change"
    ]
    saved.write_text(json.dumps([comment(f"Approve: scope SC-1 {HEAD}")]))
    code, lines = check(root, capsys, "--comments", str(saved))
    assert failures(lines) == [] and code == 0


def test_an_approval_through_an_agent_app_or_for_a_short_head_does_not_count(tmp_path, capsys):
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    saved = tmp_path / "comments.json"
    saved.write_text(
        json.dumps(
            [
                comment(f"Approve: scope SC-1 {HEAD}", app="claude"),
                comment("Approve: scope SC-1 0123abc"),
            ]
        )
    )
    code, lines = check(root, capsys, "--comments", str(saved))
    assert code == 1


# --- rule 22 with the saved comments: the approver is checked (brief #1166, ADR-0496) -----------

M1_EXPORT = (
    "FAIL plan: rule 22: docs/plan/briefs: m1-export: under baselined milestone M1, in "
    "neither the baseline nor an approved scope change"
)


def saved_comments(tmp_path: Path, *items: dict) -> Path:
    saved = tmp_path / "saved" / "comments.json"
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_text(json.dumps(list(items)), encoding="utf-8")
    return saved


@pytest.mark.parametrize(
    "items",
    [
        [],
        [comment("Looks good to me, approved")],
        [comment(f"Approve: scope SC-2 {HEAD}")],
        [comment(f"Approve: plan {HEAD}")],
    ],
)
def test_with_the_saved_comments_an_approved_line_alone_does_not_approve(tmp_path, capsys, items):
    """REQ-050 AC6 (a): the `Approved:` line written into the file without a listed approver's
    `Approve: scope SC-<n> <full head ID>` on the pull request approves nothing; the brief it adds
    fails rule 22."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    code, lines = check(root, capsys, "--comments", str(saved_comments(tmp_path, *items)))
    assert code == 1
    assert failures(lines) == [M1_EXPORT]


def test_with_the_approvers_line_in_the_saved_comments_it_passes(tmp_path, capsys):
    """REQ-050 AC6 (b): the listed approver's line on the pull request and the `Approved:` line."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    saved = saved_comments(tmp_path, comment("a note"), comment(f"Approve: scope SC-1 {HEAD}"))
    code, lines = check(root, capsys, "--comments", str(saved))
    assert failures(lines) == [] and code == 0


def test_the_approvers_line_without_the_approved_line_does_not_approve(tmp_path, capsys):
    """REQ-050 AC6: both are needed; the comment alone leaves the record proposed."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change())
    saved = saved_comments(tmp_path, comment(f"Approve: scope SC-1 {HEAD}"))
    code, lines = check(root, capsys, "--comments", str(saved))
    assert code == 1 and failures(lines) == [M1_EXPORT]


@pytest.mark.parametrize(
    "content",
    [None, "", "{not json", '{"body": "Approve: scope SC-1"}', b"\xff\xfe\x00"],
    ids=["missing", "empty", "malformed", "not-a-list", "not-utf8"],
)
def test_a_comments_file_that_cannot_be_read_fails_naming_the_option(tmp_path, capsys, content):
    """REQ-050 AC6 (c): an unread comments file is a failure naming `--comments`, never a pass
    and never a fallback to the `Approved:` line alone (principle 11)."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    saved = tmp_path / "saved" / "comments.json"
    saved.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        saved.write_bytes(content)
    elif content is not None:
        saved.write_text(content, encoding="utf-8")
    code = check_plan.main(["--root", str(root), "--comments", str(saved)])
    out = capsys.readouterr()
    assert code == 2
    assert "--comments" in out.err
    assert str(saved) not in out.err and "PASS" not in out.out


def test_a_record_approved_on_an_earlier_pull_request_keeps_its_approval(tmp_path, capsys):
    """REQ-050 AC6: a scope change whose block the merge base already holds, `Approved:` line and
    all, was approved on the pull request that merged it; a later pull request's comments do not
    name it, and it still approves (brief #1166, Decisions taken)."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    committed(root)
    git(root, "checkout", "-q", "-b", "later")
    write(root, "app/other.py", "print('example')\n")
    saved = saved_comments(tmp_path)
    code, lines = check(root, capsys, "--comments", str(saved), "--base", "main")
    assert failures(lines) == [] and code == 0


def test_a_record_changed_since_the_merge_base_needs_the_approvers_line_again(tmp_path, capsys):
    """REQ-050 AC6: a block that differs from the merge base's, or is new, carries no approval
    from it: a widened `Briefs:` line needs a fresh `Approve: scope` on this pull request."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    committed(root)
    git(root, "checkout", "-q", "-b", "later")
    brief(root, "M1", "m1-import")
    changes(root, change(briefs="+M1/m1-export M 4-8 hours; +M1/m1-import S 2-4 hours", approved=True))
    saved = saved_comments(tmp_path)
    code, lines = check(root, capsys, "--comments", str(saved), "--base", "main")
    assert code == 1
    assert M1_EXPORT in failures(lines)
    saved = saved_comments(tmp_path, comment(f"Approve: scope SC-1 {HEAD}"))
    code, lines = check(root, capsys, "--comments", str(saved), "--base", "main")
    assert failures(lines) == [] and code == 0


def test_without_the_saved_comments_the_approved_line_counts_as_today(tmp_path, capsys):
    """REQ-050 AC6, the local context: a local run has no comments; the `Approved:` line alone
    counts there (ADR-0496 decision 3)."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export")
    changes(root, change(approved=True))
    code, lines = check(root, capsys)
    assert failures(lines) == [] and code == 0


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "governance.yml"


def _plan_step(text: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "- name: check_plan")
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("- name:")),
        len(lines),
    )
    return "\n".join(lines[start:end])


def test_the_governance_step_passes_the_saved_comments_on_a_pull_request():
    """REQ-050 AC6: the governance job's `check_plan` step reads the pull request's saved comments
    on a pull request event, and runs as before (no comments) on a push (brief #1166 answer 1)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    step = _plan_step(text)
    saved = text.index('> "$RUNNER_TEMP/comments.json"')
    assert saved < text.index("- name: check_plan")
    assert 'if [ "$EVENT" = pull_request ]; then' in step
    assert "EVENT: ${{ github.event_name }}" in step
    assert 'python scripts/agk/check_plan.py --comments "$RUNNER_TEMP/comments.json"' in step
    plain = [line.strip() for line in step.splitlines()]
    assert "python scripts/agk/check_plan.py" in plain


def test_a_removed_baseline_brief_needs_an_approved_record(tmp_path, capsys):
    """REQ-050 AC6: a baseline brief whose file is gone fails until a scope change removes it."""
    root = plan(tmp_path, baseline())
    (root / "docs/plan/briefs/M2/m2-invoice.md").unlink()
    brief(root, "M1", "m1-extra")  # M2 keeps no brief, so rule 10 fails too; only rule 22 is read
    changes(root, change(1, briefs="+M1/m1-extra M 4-8 hours", approved=True))
    code, lines = check(root, capsys)
    assert code == 1
    assert (
        "FAIL plan: rule 22: docs/plan/baseline.json: m2-invoice: removed from M2 with no "
        "approved scope change" in failures(lines)
    )
    changes(
        root,
        change(1, briefs="+M1/m1-extra M 4-8 hours", approved=True),
        change(2, briefs="-M2/m2-invoice", approved=True),
    )
    code, lines = check(root, capsys)
    assert all("rule 22" not in line for line in failures(lines))


def test_a_brief_under_a_milestone_outside_the_baseline_is_not_controlled(tmp_path, capsys):
    """A milestone the baseline does not hold is not baselined (rule 22 names baselined ones)."""
    base = baseline()
    base["milestones"] = base["milestones"][:1]
    root = plan(tmp_path, base)
    brief(root, "M2", "m2-credit")
    code, lines = check(root, capsys)
    assert failures(lines) == [] and code == 0


# --- reviewers: the approval line ---------------------------------------------------------------


def test_scope_approvals_reads_only_listed_full_head_lines():
    """REQ-050 AC6: `Approve: scope SC-<n> <full head ID>` by a listed account, never an app."""
    items = [
        comment(f"Approve: scope SC-1 {HEAD}"),
        comment(f"Approve: scope SC-2 {HEAD}", "someone-else"),
        comment(f"Approve: scope SC-3 {HEAD}", app="claude"),
        comment("Approve: scope SC-4 0123abc"),
        comment(f"Approve: scope SC-05 {HEAD}"),
        comment(f"note\nApprove: scope SC-6 {HEAD}"),
    ]
    assert reviewers.scope_approvals(items, [OWNER], ["claude"]) == {("SC-1", HEAD)}


def test_a_solo_confirmation_carries_the_scope_line():
    """REQ-050 AC6: in solo mode the line counts inside the person's whole `Confirmed:` comment."""
    body = "\n".join(
        [
            f"Confirmed: {HEAD}",
            f"Verdict: cleared {HEAD}",
            f"Approve: scope SC-1 {HEAD}",
            "Shown:",
            "one",
            "two",
            "three",
            f"confirmed by {OWNER} in a session at 2026-11-13T09:00:00Z",
        ]
    )
    items = reviewers.confirmed_comments([comment(body)], (), OWNER)
    assert reviewers.scope_approvals(items, [OWNER]) == {("SC-1", HEAD)}


# --- rule 21: the effect, before and after ------------------------------------------------------


def facts(tmp_path: Path) -> Path:
    path = tmp_path / "facts.json"
    doc = {"schema": 1, "today": "2026-11-04", "pull_requests": [], "flow": {"briefs": []}}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def estimate(tmp_path: Path, monkeypatch, capsys, *args: str) -> tuple[int, str, str]:
    monkeypatch.chdir(tmp_path)
    code = plan_estimate.main(["--facts", str(facts(tmp_path)), *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def test_with_prints_the_effect_before_and_after(tmp_path, monkeypatch, capsys):
    """REQ-050 AC6: `--with SC-1` prints the plan before the change and after it, each estimate
    with its inputs line, then the limits line once."""
    root = plan(tmp_path, baseline())
    changes(root, change(1, briefs="+M1/m1-export L 10-20 hours; -M2/m2-invoice"))
    code, out, err = estimate(tmp_path, monkeypatch, capsys, "--with", "SC-1")
    assert (code, err) == (0, "")
    lines = out.splitlines()
    assert lines[0] == "effect of SC-1: before"
    after = lines.index("effect of SC-1: after")
    before, later = lines[1:after], lines[after + 1 :]
    assert any(
        x.startswith("M1 Orders: uncalibrated") and "declared 6-12 hours" in x for x in before
    )
    assert any(
        x.startswith("M2 Invoices: uncalibrated") and "declared 4-8 hours" in x for x in before
    )
    assert any(
        x.startswith("M1 Orders: uncalibrated") and "declared 16-32 hours" in x for x in later
    )
    assert any(x.startswith("M2 Invoices: hours done") for x in later)
    assert sum(1 for x in lines if x.startswith("inputs: ")) == 4
    assert lines[-1] == plan_estimate.LIMITS and lines.count(plan_estimate.LIMITS) == 1


def test_with_reads_an_added_brief_file_once(tmp_path, monkeypatch, capsys):
    """After approval the brief file exists: before leaves it out, after counts it once."""
    root = plan(tmp_path, baseline())
    brief(root, "M1", "m1-export", "L", "10-20")
    changes(root, change(1, briefs="+M1/m1-export L 10-20 hours", approved=True))
    code, out, _ = estimate(tmp_path, monkeypatch, capsys, "--with", "SC-1")
    lines = out.splitlines()
    after = lines.index("effect of SC-1: after")
    assert any("declared 6-12 hours" in x for x in lines[1:after] if x.startswith("M1 "))
    assert any("declared 16-32 hours" in x for x in lines[after:] if x.startswith("M1 "))


def test_with_an_unknown_scope_change_exits_2_naming_the_option(tmp_path, monkeypatch, capsys):
    root = plan(tmp_path, baseline())
    changes(root, change(1))
    code, out, err = estimate(tmp_path, monkeypatch, capsys, "--with", "SC-9")
    assert (code, out) == (2, "")
    assert err == "plan_estimate: the scope change is not in scope-changes.md (option: --with)\n"
    code, out, err = estimate(tmp_path, monkeypatch, capsys, "--with", "nine")
    assert code == 2 and "(option: --with)" in err


def test_without_with_the_output_is_unchanged(tmp_path, monkeypatch, capsys):
    """The plain estimate prints no effect lines."""
    root = plan(tmp_path, baseline())
    changes(root, change(1))
    code, out, _ = estimate(tmp_path, monkeypatch, capsys)
    assert code == 0 and "effect of" not in out
