"""Kit-only tests of the local-mode guide and the lines that point to it.

Brief #322, ADR-0182; REQ-039.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

GUIDE = KIT_ROOT / "docs" / "guides" / "local-mode.md"
SECTIONS = (
    "When to use it",
    "Enter local mode",
    "What a builder runs before asking for review",
    "What the conductor checks instead of CI",
    "What is lost",
    "Leave local mode",
)
# Names of hosts, clouds, runners, scanners and model makers that a guide of the kit could
# slip into; GitHub is the one host the kit is built for (answer 4 of the brief).
VENDORS = (
    "gitlab",
    "bitbucket",
    "azure",
    "aws",
    "amazon",
    "google",
    "gcp",
    "circleci",
    "jenkins",
    "travis",
    "buildkite",
    "docker",
    "gitleaks",
    "anthropic",
    "claude",
    "openai",
    "slack",
    "jira",
    "microsoft",
    "apple",
)


def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def section(title: str) -> str:
    found = re.search(rf"(?ms)^## {re.escape(title)}\n(.*?)(?=^## |\Z)", guide())
    assert found, f"the guide has no section '{title}'"
    return found.group(1)


def flat(rel: str) -> str:
    return " ".join((KIT_ROOT / rel).read_text(encoding="utf-8").split())


def test_the_guide_has_each_section_of_answer_1_in_order():
    text = guide()
    at = [text.find(f"\n## {title}\n") for title in SECTIONS]
    assert all(i >= 0 for i in at) and at == sorted(at), at


def test_when_to_use_it_names_the_three_causes():
    body = section("When to use it").lower()
    for phrase in ("minutes", "billing", "outage"):
        assert phrase in body, phrase


def test_entering_disables_each_installed_workflow_with_one_command_and_opens_the_record_issue():
    body = section("Enter local mode")
    workflows = sorted(
        path.rsplit("/", 1)[1] for path in _installed() if path.startswith(".github/workflows/")
    )
    assert workflows, "the manifest installs no workflow"
    for name in workflows:
        assert f"gh workflow disable {name}" in body, name
    assert "agk-tag.yml" not in body, "a kit-only workflow is not installed in a project"
    assert "repos/{owner}/{repo}/issues" in body and "Local merge:" in body


def test_the_builder_runs_governance_and_its_own_proof_under_the_lock_and_pastes_the_result():
    body = section("What a builder runs before asking for review")
    for phrase in (
        "agk-heavy.lock",
        "mkdir",
        "rmdir",
        "make governance",
        "python3 scripts/agk/proof.py",
        "python3 scripts/agk/check_pr_body.py",
        "Local evidence:",
        "pull request body",
    ):
        assert phrase in body, phrase


def test_the_conductor_reruns_governance_on_the_head_and_reads_checks_not_reported():
    body = section("What the conductor checks instead of CI")
    for phrase in (
        "make -C <scratch> governance",
        'env -i PATH="$PATH" HOME=<scratch>',
        "checks not reported",
        "python3 scripts/agk/session.py review-queue",
        "Local evidence:",
    ):
        assert phrase in body, phrase


def test_what_is_lost_is_stated_plainly():
    body = section("What is lost").lower()
    phrases = ("router", "label", "proof", "server-side", "the person's call", "local evidence")
    for phrase in phrases:
        assert phrase in body, phrase


def test_leaving_reenables_each_workflow_runs_one_pull_request_green_and_closes_the_record():
    body = section("Leave local mode")
    for name in ("agk-route.yml", "governance.yml", "proof.yml"):
        assert f"gh workflow enable {name}" in body, name
    assert "green" in body and "close" in body.lower()


def test_every_gh_workflow_command_is_spelled_as_the_cli_spells_it():
    text = guide()
    commands = re.findall(r"gh workflow ([a-z-]+)", text)
    assert commands and set(commands) <= {"disable", "enable", "list"}, sorted(set(commands))
    assert "gh workflows" not in text and "gh workflow-" not in text


def test_every_kit_script_and_make_target_the_guide_calls_exists():
    text = guide()
    scripts = set(re.findall(r"scripts/agk/([a-z_]+\.py)", text))
    assert scripts, "the guide calls no kit script"
    for name in sorted(scripts):
        assert (KIT_ROOT / "scripts" / "agk" / name).is_file(), name
    makefile = (KIT_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in set(re.findall(r"make (?:-C <scratch> )?([a-z-]+)", text)):
        assert re.search(rf"(?m)^{re.escape(target)}:", makefile), target
    session = (KIT_ROOT / "scripts" / "agk" / "session.py").read_text(encoding="utf-8")
    for sub in set(re.findall(r"scripts/agk/session\.py ([a-z-]+)", text)):
        assert f'"{sub}"' in session, sub


def test_the_guide_names_no_vendor_beyond_github():
    words = set(re.findall(r"[a-z0-9]+", guide().lower()))
    assert not words & set(VENDORS), sorted(words & set(VENDORS))


def test_the_session_rules_and_the_conductor_point_to_the_guide_and_name_the_local_evidence():
    rules = flat("config/session-rules.md")
    text = (KIT_ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")
    rule = re.search(r"(?m)^\d+\. .*docs/guides/local-mode\.md", text)
    assert rule, "no session rule points to the guide"
    assert "Local evidence:" in rules
    conductor = flat(".claude/agents/conductor.md")
    assert "docs/guides/local-mode.md" in conductor and "Local evidence:" in conductor


def test_the_reference_lists_the_guide_and_getting_started_links_it():
    assert "local-mode.md" in flat("docs/guides/reference.md")
    start = (KIT_ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    wrong = start.split("## When something goes wrong", 1)[1]
    assert "](local-mode.md)" in wrong


def _installed() -> list[str]:
    from conftest import manifest

    data = manifest()
    paths: list[str] = []
    for value in data.values():
        if isinstance(value, list):
            paths.extend(v for v in value if isinstance(v, str))
    return paths


def test_fix_1_the_ci_first_exception_is_bounded_in_the_rule_and_the_role():
    """Verdict on 712354d, item 1."""
    for rel in ("config/session-rules.md", ".claude/agents/conductor.md"):
        text = flat(rel)
        for phrase in (
            "while the one local-mode record issue is open",
            "required checks that never reported on that head",
            "A red check still blocks a clearing verdict",
        ):
            assert phrase in text, (rel, phrase)


def test_fix_2_entering_removes_a_frozen_ci_running_label_and_the_conductor_reads_all():
    """Verdict on 712354d, item 2."""
    enter = " ".join(section("Enter local mode").split())
    assert "gh pr edit <n> --remove-label agk:ci-running" in enter
    conductor = section("What the conductor checks instead of CI")
    assert "python3 scripts/agk/session.py review-queue --all" in conductor


def test_fix_3_a_billing_refusal_is_a_sign_and_a_new_head_is_pushed_once_disabled():
    """Verdict on 712354d, item 3."""
    body = " ".join(section("When to use it").split())
    for phrase in ("recent account payments have failed", "spending limit", "push a new head"):
        assert phrase in body, phrase


def test_fix_4_the_lock_block_runs_as_one_script():
    """Verdict on 712354d, item 4."""
    body = section("What a builder runs before asking for review")
    assert "bash -c '" in body and "one script" in body
    script = body.split("bash -c '", 1)[1].split("\n    '\n", 1)[0]
    for phrase in ("mkdir", "trap", "rmdir", "make governance", "proof.py"):
        assert phrase in script, phrase
