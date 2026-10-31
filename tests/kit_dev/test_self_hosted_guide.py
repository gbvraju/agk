"""Kit-only tests of the self-hosted runner guide and the lines that point to it.

Brief #372, ADR-0217; REQ-039.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

GUIDE = KIT_ROOT / "docs" / "guides" / "self-hosted-runner.md"
SECTIONS = (
    "When it fits",
    "The rules",
    "Set up an ephemeral runner",
    "How a heavy job opts in",
    "When the runner is down",
)
# The kit's workflows and jobs: each stays on a GitHub-hosted runner (answer 1, the trust anchor).
KIT_WORKFLOWS = (
    "agk-route.yml",
    "governance.yml",
    "proof.yml",
    "drift-audit.yml",
    "metrics.yml",
    "product-report.yml",
    "agk-tag.yml",
)
KIT_JOBS = ("governance", "proof", "agk-route", "drift-audit", "metrics", "product-report")
# Names of hosts, clouds, runners, scanners and model makers that a guide of the kit could slip
# into; GitHub is the one host the kit is built for (answer 3 of the brief).
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
    "kubernetes",
    "podman",
    "gitleaks",
    "anthropic",
    "claude",
    "openai",
    "slack",
    "jira",
    "microsoft",
    "apple",
    "hetzner",
    "digitalocean",
)


def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


def section(title: str) -> str:
    found = re.search(rf"(?ms)^## {re.escape(title)}\n(.*?)(?=^## |\Z)", guide())
    assert found, f"the guide has no section '{title}'"
    return found.group(1)


def blocks(text: str) -> list[str]:
    """The fenced code blocks of a text."""
    return re.findall(r"(?ms)^```[a-z]*\n(.*?)^```", text)


def test_the_guide_has_each_section_of_answer_1_in_order():
    text = guide()
    at = [text.find(f"\n## {title}\n") for title in SECTIONS]
    assert all(i >= 0 for i in at) and at == sorted(at), at


def test_when_it_fits_names_a_private_repository_heavy_jobs_and_short_minutes():
    body = flat(section("When it fits")).lower()
    for phrase in ("private repository", "heavy jobs", "minutes"):
        assert phrase in body, phrase
    assert "public repository" in body


def test_the_rules_state_ephemeral_no_public_or_fork_and_no_secrets_beyond_the_job():
    body = flat(section("The rules")).lower()
    for phrase in (
        "ephemeral",
        "one job",
        "removed",
        "never on a public repository",
        "fork",
        "no secret beyond the job's own",
        "deploy",
        "production",
    ):
        assert phrase in body, phrase


def test_setting_up_marks_each_step_that_depends_on_the_machine_or_plan_verify():
    body = section("Set up an ephemeral runner")
    steps = re.findall(r"(?ms)^\d+\. (.*?)(?=^\d+\. |^\S|\Z)", body)
    assert len(steps) >= 3, steps
    for step in steps:
        assert "(verify)" in step, step[:80]
    assert "--ephemeral" in body


def test_a_heavy_job_opts_in_with_runs_on_labels_and_governance_and_proof_stay_hosted():
    body = flat(section("How a heavy job opts in"))
    assert "runs-on:" in body and "self-hosted" in body
    for phrase in ("governance", "proof", "GitHub-hosted", "trust anchor"):
        assert phrase in body, phrase


def test_the_guide_never_puts_a_kit_workflow_or_job_on_a_self_hosted_runner():
    for block in blocks(guide()):
        if "self-hosted" not in block:
            continue
        lowered = block.lower()
        for name in KIT_WORKFLOWS:
            assert name not in lowered, name
        jobs = re.findall(r"(?m)^\s{2}([A-Za-z0-9_-]+):\s*$", block)
        for job in jobs:
            assert job not in KIT_JOBS, job
    hosted = [b for b in blocks(guide()) if any(name in b for name in ("governance", "proof"))]
    for block in hosted:
        assert "self-hosted" not in block, block


def test_when_the_runner_is_down_says_the_job_waits_and_how_to_fall_back():
    body = flat(section("When the runner is down"))
    for phrase in ("waits", "ubuntu-latest", "local-mode.md"):
        assert phrase in body, phrase


def test_the_guide_names_no_vendor_beyond_github():
    words = set(re.findall(r"[a-z0-9]+", guide().lower()))
    assert not words & set(VENDORS), sorted(words & set(VENDORS))


def test_the_reference_lists_the_guide_and_project_ci_links_it_from_its_minutes_section():
    assert "](self-hosted-runner.md)" in (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(
        encoding="utf-8"
    )
    text = (KIT_ROOT / "docs" / "guides" / "project-ci.md").read_text(encoding="utf-8")
    minutes = text.split("## How many minutes are left", 1)[1]
    assert "](self-hosted-runner.md)" in minutes
