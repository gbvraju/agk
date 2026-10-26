# ruff: noqa: F811 - the fixtures and helpers of test_approve_short are imported by name
"""The CI check of spec approvals ignores an approval an agent posted (brief 242; REQ-039).

`check_specs.py --comments` reads the same rule as the router: a comment whose
`performed_via_github_app.slug` is in `agent_apps` (default `["claude"]`) never approves a spec."""

from __future__ import annotations

from test_approve_short import AFTER, BEFORE, drafted, head, ok, run, run_of, short  # noqa: F401


def via(comment: dict, slug: str = "claude") -> dict:
    return {**comment, "performed_via_github_app": {"slug": slug, "id": 1236702}}


def flipped(drafted):
    repo, reviewed = drafted
    from test_approve_short import SPEC, spec

    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    return repo, [run_of(reviewed, BEFORE), run_of(head(repo), AFTER)]


def test_an_approval_posted_through_the_agent_app_does_not_approve_the_spec(drafted):
    repo, runs = flipped(drafted)
    proc = run(repo, [via(short())], runs)
    assert proc.returncode == 1 and "rule 5: no Approve line" in proc.stdout


def test_the_same_approval_without_the_marker_or_through_another_app_does_pass(drafted):
    repo, runs = flipped(drafted)
    assert ok(run(repo, [short()], runs))
    assert ok(run(repo, [via(short(), "some-other-app")], runs))


def test_a_project_that_empties_agent_apps_counts_every_approval_again(drafted):
    repo, runs = flipped(drafted)
    repo.write("agk.toml", "agent_apps = []\n")
    assert ok(run(repo, [via(short())], runs))


def test_an_invalid_setting_is_refused_naming_the_setting(drafted):
    repo, runs = flipped(drafted)
    repo.write("agk.toml", 'agent_apps = "claude"\n')
    proc = run(repo, [short()], runs)
    assert proc.returncode != 0 and "agent_apps" in proc.stdout + proc.stderr


def test_a_review_counts_only_when_agent_apps_is_empty(drafted):
    """Q-242-1 (b): a review shows no app, so while an app is listed it approves nothing."""
    from test_approve_short import review

    repo, reviewed = drafted
    from test_approve_short import SPEC, spec

    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    approving = [review("APPROVED", reviewed)]
    assert run(repo, [], reviews=approving).returncode == 1
    repo.write("agk.toml", "agent_apps = []\n")
    assert ok(run(repo, [], reviews=approving))
