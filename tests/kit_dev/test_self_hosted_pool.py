"""Kit-only tests of the self-hosted runner guide's section on one shared pool for an organisation.

Brief #410, ADR-0224; REQ-039.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

GUIDE = KIT_ROOT / "docs" / "guides" / "self-hosted-runner.md"
TITLE = "One pool for an organisation"
RUNS_ON = "runs-on: ${{ vars.AGK_HEAVY_RUNNER || 'ubuntu-latest' }}"
FORK_GUARD = "github.event.pull_request.head.repo.full_name == github.repository"


def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


def section() -> str:
    found = re.search(rf"(?ms)^## {re.escape(TITLE)}\n(.*?)(?=^## |\Z)", guide())
    assert found, f"the guide has no section '{TITLE}'"
    return found.group(1)


def blocks(text: str) -> list[str]:
    return re.findall(r"(?ms)^```[a-z]*\n(.*?)^```", text)


def snippet() -> str:
    found = [b for b in blocks(section()) if RUNS_ON in b]
    assert len(found) == 1, "the section has no single job snippet with the runs-on line"
    return found[0]


def test_the_section_exists_once_and_comes_after_the_one_project_sections():
    """REQ-039: brief #410 answer 1 (a section of the existing guide)."""
    text = guide()
    assert text.count(f"\n## {TITLE}\n") == 1
    assert text.find(f"\n## {TITLE}\n") > text.find("\n## How a heavy job opts in\n") > 0


def test_the_runner_group_is_limited_to_named_private_repositories_never_public_ones():
    """REQ-039: brief #410 answer 1, first rule."""
    body = flat(section()).lower()
    for phrase in ("runner group", "selected repositories", "private", "never a public"):
        assert phrase in body, phrase


def test_the_pool_takes_ephemeral_runners_only_starting_with_one_machine():
    """REQ-039: brief #410 answer 1, second rule."""
    body = flat(section()).lower()
    for phrase in ("ephemeral", "one job", "one machine", "autoscal"):
        assert phrase in body, phrase


def test_shared_caches_name_their_kinds_and_hold_no_credential():
    """REQ-039: brief #410 answer 1, third rule."""
    body = flat(section()).lower()
    kinds = ("shared cache", "container layers", "package manager", "browsers", "no credential")
    for phrase in kinds:
        assert phrase in body, phrase


def test_no_deploy_or_production_secret_and_a_read_only_job_token():
    """REQ-039: brief #410 answer 1, fourth rule; the snippet asks for read permissions only."""
    body = flat(section()).lower()
    for phrase in ("deploy", "production", "read permissions only"):
        assert phrase in body, phrase
    lines = [line.strip() for line in snippet().splitlines()]
    assert "permissions:" in lines and "contents: read" in lines
    assert not [line for line in lines if line.endswith(": write")], lines


def test_governance_and_proof_stay_on_github_hosted_runners_as_the_trust_anchor():
    """REQ-039: brief #410 answer 1, fifth rule; no block of the section moves them."""
    body = flat(section())
    for phrase in ("governance", "proof", "GitHub-hosted", "trust anchor"):
        assert phrase in body, phrase
    for block in blocks(section()):
        if "governance" in block or "proof" in block:
            assert "AGK_HEAVY_RUNNER" not in block and "self-hosted" not in block, block


def test_the_snippet_reads_the_runner_from_a_variable_with_hosted_fallback_and_the_fork_guard():
    """REQ-039: brief #410 answer 2."""
    code = snippet()
    assert RUNS_ON in code
    guard = [line for line in code.splitlines() if line.strip().startswith("if:")]
    assert len(guard) == 1 and FORK_GUARD in guard[0], guard
    jobs = re.findall(r"(?m)^\s{2}([A-Za-z0-9_-]+):\s*$", code)
    assert jobs and not set(jobs) & {"governance", "proof"}, jobs


def test_the_section_says_how_to_measure_with_minutes_py_one_week_before_and_after():
    """REQ-039: brief #410 answer 3."""
    body = flat(section())
    assert "python3 scripts/agk/minutes.py" in body
    assert "not billed" in body
    for phrase in ("one week before", "one week after"):
        assert phrase in body.lower(), phrase


def test_the_kit_sets_up_nothing_and_each_setting_is_a_step_of_the_person():
    """REQ-039: brief #410 answer 4: runner, group and variable are the person's steps."""
    body = section()
    assert "The kit sets up no runner, no runner group and no variable" in flat(body)
    steps = re.findall(r"(?ms)^\d+\. (.*?)(?=^\d+\. |^\S|\Z)", body)
    joined = flat(" ".join(steps)).lower()
    for thing in ("runner group", "ephemeral", "agk_heavy_runner"):
        assert thing in joined, thing
    for step in steps:
        assert "(verify)" in step, step[:80]


def test_the_one_repository_rule_points_to_the_organisation_pool():
    """REQ-039: brief #410: rule 2 of the guide no longer forbids the pool of the new section."""
    rules = re.search(r"(?ms)^## The rules\n(.*?)(?=^## )", guide()).group(1)
    assert "](#one-pool-for-an-organisation)" in rules


def test_a_step_checks_that_the_repository_reaches_no_other_self_hosted_runner():
    """REQ-039: brief #410, the verdict on 4c868ed item 1: the label picks the pool only alone."""
    body = section()
    steps = re.findall(r"(?ms)^\d+\. (.*?)(?=^\d+\. |^\S|\Z)", body)
    found = [s for s in steps if "no other self-hosted runner" in flat(s).lower()]
    assert len(found) == 1, steps
    step = flat(found[0])
    for phrase in (
        "registered on the repository",
        "Default group",
        "Settings, Actions, Runners",
        "(verify)",
    ):
        assert phrase in step, phrase
    text = flat(body)
    assert "so the label picks the pool" not in text
    assert "only while the pool's group holds the repository's only self-hosted runners" in text
