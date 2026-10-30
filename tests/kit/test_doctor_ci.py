"""A project's CI is fast and cheap by default (brief #283; REQ-039).

Answer 3: the doctor warns, never fails, when a workflow that holds a check of `required_checks`
runs on draft pull requests (`ci-drafts`) or has no concurrency group (`ci-concurrency`); the
message names the setting and the path class, never a workflow or a check. Answer 2: the kit's own
workflows follow the five defaults where they apply and say why where they cannot. Answer 1: the
guide gives the five defaults with copyable snippets, and the stack ADR template carries the
practice. Workflow and check names here are invented; no network.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from test_doctor import checks_of, doctor, prepare

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import doctor as doctor_script  # noqa: E402

WORKFLOWS = ROOT / ".github" / "workflows"
GUIDE = ROOT / "docs" / "guides" / "project-ci.md"
STACK_TEMPLATE = ROOT / "kit" / "templates" / "stack-adr.md"
IDS = ("ci-drafts", "ci-concurrency")

SLOW = (
    "name: slow-suite\n"
    "on:\n"
    "  pull_request:\n"
    "    types: [opened, synchronize, reopened, ready_for_review]\n"
    "  push:\n"
    "    branches: [main]\n"
    "{concurrency}"
    "jobs:\n"
    "  zq-suite:\n"
    "{condition}"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - run: echo suite\n"
)
CONCURRENCY = (
    "concurrency:\n"
    "  group: slow-suite-${{ github.event.pull_request.number || github.sha }}\n"
    "  cancel-in-progress: ${{ github.event_name == 'pull_request' }}\n"
)
NOT_DRAFT = (
    "    if: ${{ github.event_name != 'pull_request' || !github.event.pull_request.draft }}\n"
)


def slow(concurrency: str = "", condition: str = "") -> str:
    return SLOW.format(concurrency=concurrency, condition=condition)


def ci_case(tmp_path: Path, files: dict[str, str], required=("proof", "governance", "zq-suite")):
    dirs = prepare("ok", tmp_path)
    root = dirs["root"]
    folder = root / ".github" / "workflows"
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    toml = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text(f"{toml}required_checks = {json.dumps(list(required))}\n")
    proc = doctor("--api-dir", str(dirs["api"]), "--json", str(root))
    return proc, checks_of(proc.stdout)


# --- answer 3: the doctor's warnings -------------------------------------------------------------


def test_a_required_check_that_runs_on_drafts_without_a_group_gets_two_warnings(tmp_path):
    """REQ-039: brief #283 answer 3 (warnings with the fix, never a failure)."""
    proc, report = ci_case(tmp_path, {"slow.yml": slow()})
    for check in IDS:
        entry = report[check]
        assert (entry["status"], entry["severity"]) == ("fail", "warn"), check
        assert "required_checks" in entry["message"] and ".github/workflows/" in entry["message"]
        for value in ("slow", "zq-suite", "slow-suite", "slow.yml"):
            assert value not in entry["message"] and value not in entry["fix"], value
        assert "project-ci.md" in entry["fix"]
    assert (
        "draft" in report["ci-drafts"]["fix"] and "ready_for_review" in report["ci-drafts"]["fix"]
    )
    assert "cancel-in-progress" in report["ci-concurrency"]["fix"]
    assert proc.returncode == 4


def test_a_workflow_that_skips_drafts_and_has_a_group_is_ok(tmp_path):
    """REQ-039: brief #283 answer 3."""
    _, report = ci_case(tmp_path, {"slow.yml": slow(CONCURRENCY, NOT_DRAFT)})
    assert [report[c]["status"] for c in IDS] == ["ok", "ok"]


def test_each_warning_is_its_own(tmp_path):
    """REQ-039: brief #283 answer 3 (the draft rule and the group rule are told apart)."""
    _, report = ci_case(tmp_path / "a", {"slow.yml": slow(CONCURRENCY)})
    assert [report[c]["status"] for c in IDS] == ["fail", "ok"]
    _, report = ci_case(tmp_path / "b", {"slow.yml": slow("", NOT_DRAFT)})
    assert [report[c]["status"] for c in IDS] == ["ok", "fail"]


def test_a_draft_named_only_in_a_comment_does_not_count(tmp_path):
    """REQ-039: brief #283 answer 3 (a comment is not a condition)."""
    text = slow(CONCURRENCY).replace(
        "jobs:\n", "# skip github.event.pull_request.draft later\njobs:\n"
    )
    _, report = ci_case(tmp_path, {"slow.yml": text})
    assert report["ci-drafts"]["status"] == "fail"


def test_a_job_level_group_counts(tmp_path):
    """REQ-039: brief #283 answer 3 (the group may sit on the job)."""
    text = slow("", NOT_DRAFT).replace(
        "    runs-on:",
        "    concurrency:\n      group: suite-${{ github.ref }}\n      cancel-in-progress: true\n"
        "    runs-on:",
    )
    _, report = ci_case(tmp_path, {"slow.yml": text})
    assert report["ci-concurrency"]["status"] == "ok"


def test_a_workflow_of_no_required_check_and_a_push_only_workflow_are_not_judged_on_drafts(
    tmp_path,
):
    """REQ-039: brief #283 answer 3 (only the jobs of required_checks; drafts need pull_request)."""
    _, report = ci_case(tmp_path / "a", {"slow.yml": slow()}, required=("proof", "governance"))
    assert [report[c]["status"] for c in IDS] == ["ok", "ok"]
    push_only = slow(CONCURRENCY).replace(
        "  pull_request:\n    types: [opened, synchronize, reopened, ready_for_review]\n", ""
    )
    _, report = ci_case(tmp_path / "b", {"slow.yml": push_only})
    assert report["ci-drafts"]["status"] == "ok"


def test_the_router_is_not_judged(tmp_path):
    """REQ-039: brief #283 answer 3 (the router holds no required check and labels drafts too)."""
    router = slow().replace("name: slow-suite", "name: agk-route")
    _, report = ci_case(tmp_path, {"agk-route.yml": router})
    assert [report[c]["status"] for c in IDS] == ["ok", "ok"]


def test_the_kits_own_governance_and_proof_pass_both_checks(tmp_path):
    """REQ-039: brief #283 answers 2 and 3 (the kit follows its own advice)."""
    files = {
        n: (WORKFLOWS / n).read_text(encoding="utf-8") for n in ("governance.yml", "proof.yml")
    }
    _, report = ci_case(tmp_path, files, required=("proof", "governance"))
    assert [report[c]["status"] for c in IDS] == ["ok", "ok"]


def test_an_unreadable_workflow_cannot_be_checked(tmp_path):
    """REQ-039: brief #283 answer 3 (a file that cannot be read is never ok)."""
    dirs = prepare("ok", tmp_path)
    root = dirs["root"]
    folder = root / ".github" / "workflows"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "slow.yml").write_bytes(b"name: slow\n\xff\xfe\n")
    toml = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text(f'{toml}required_checks = ["proof", "governance"]\n')
    report = checks_of(doctor("--api-dir", str(dirs["api"]), "--json", str(root)).stdout)
    assert [report[c]["status"] for c in IDS] == ["cannot-check", "cannot-check"]


def test_the_two_checks_are_warnings_after_the_router_check():
    """REQ-039: brief #283 answer 3 (two new ids, warnings, in the report order)."""
    ids = list(doctor_script.CHECKS)
    assert ids.index("ci-drafts") == ids.index("router-wake") + 1
    assert ids.index("ci-concurrency") == ids.index("ci-drafts") + 1
    assert all(doctor_script.CHECKS[c][0] == "warn" for c in IDS)


# --- answer 2: the kit's own workflows -----------------------------------------------------------


def step(text: str, name: str) -> str:
    body = text.split("    steps:\n", 1)[1]
    parts = re.split(r"(?m)^      - (?=name: |uses: )", body)[1:]
    return next(p for p in parts if p.startswith(f"name: {name}"))


def test_governance_skips_its_heavy_steps_on_a_draft_and_still_reports():
    """REQ-039: brief #283 answer 2 (the same skip as a status-only commit; the job stays)."""
    text = (WORKFLOWS / "governance.yml").read_text(encoding="utf-8")
    part = step(text, "Status-only final commit")
    assert "PR_DRAFT: ${{ github.event.pull_request.draft }}" in part
    draft = part.split('if [ "$PR_DRAFT" = true ]', 1)[1].split("fi\n", 1)[0]
    assert 'echo "skip=true" >> "$GITHUB_OUTPUT"' in draft and "GITHUB_STEP_SUMMARY" in draft
    assert "ready for review" in draft and "exit 0" in draft
    assert "ready_for_review" in text.split("\njobs:", 1)[0]


def test_proof_runs_when_a_draft_is_marked_ready_and_skips_a_draft():
    """REQ-039: brief #283 answer 2 (proof reports `skipped` on a draft, then runs in full)."""
    text = (WORKFLOWS / "proof.yml").read_text(encoding="utf-8")
    types = re.search(r"pull_request:\s*\n\s*types:\s*\[([^\]]*)\]", text)
    assert types and {t.strip() for t in types.group(1).split(",")} == {
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
    }
    part = step(text, "Status-only final commit")
    assert "PR_DRAFT: ${{ github.event.pull_request.draft }}" in part
    draft = part.split('if [ "$PR_DRAFT" = true ]', 1)[1].split("fi\n", 1)[0]
    assert 'echo "skip=true" >> "$GITHUB_OUTPUT"' in draft and "exit 0" in draft


@pytest.mark.parametrize("name", sorted(p.name for p in WORKFLOWS.glob("*.yml")))
def test_every_kit_workflow_says_how_it_meets_the_five_defaults(name):
    """REQ-039: brief #283 answer 2 (where a default cannot apply, a comment says why)."""
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    head = text.split("\njobs:", 1)[0]
    lines = [ln for ln in head.splitlines() if ln.startswith("#")]
    block = "\n".join(lines)
    assert "Fast CI (brief #283)" in block, name
    for word in ("draft", "concurrency", "cache", "documentation", "retention"):
        assert word in block.lower(), (name, word)


def test_the_kits_uploads_keep_a_short_retention_or_say_why():
    """REQ-039: brief #283 answers 1 and 2 (short artifact retention)."""
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        for days in re.findall(r"retention-days: (\d+)", text):
            assert int(days) <= 7 or "retention" in text.split("\njobs:", 1)[0], path.name


# --- answer 1: the guide and the stack ADR template ----------------------------------------------


def test_the_guide_gives_the_five_defaults_with_snippets():
    """REQ-039: brief #283 answer 1."""
    text = GUIDE.read_text(encoding="utf-8")
    assert text.startswith("# ")
    for needle in (
        "github.event.pull_request.draft",
        "ready_for_review",
        "cancel-in-progress: true",
        "type=gha",
        "retention-days:",
        "paths-ignore",
        "ci-drafts",
        "ci-concurrency",
        "[proof]",
    ):
        assert needle in text, needle
    assert text.count("```yaml") >= 5


def test_the_guide_never_leaves_a_required_check_waiting_on_a_documentation_change():
    """REQ-039: brief #283 answer 1 (skip heavy steps, but the job reports success)."""
    text = GUIDE.read_text(encoding="utf-8")
    docs = text.split("## 4.", 1)[1].split("\n## ", 1)[0]
    assert "paths-ignore" in docs and "never" in docs.lower()
    assert "outputs.docs_only" in docs and "git diff --name-only" in docs


def test_the_reference_points_to_the_guide():
    """REQ-039: brief #283 answer 1."""
    ref = (ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    assert "project-ci.md" in ref and "ci-drafts" in ref and "ci-concurrency" in ref


def test_the_stack_adr_template_carries_the_fast_ci_practice():
    """REQ-039: brief #283 answer 1 (a stack that names CI keeps the practice)."""
    text = STACK_TEMPLATE.read_text(encoding="utf-8")
    practices = text[text.index("2. **Practices**") : text.index("3. **Chosen**")]
    line = next(ln for ln in practices.splitlines() if ln.strip().startswith("- fast CI:"))
    assert ": check (step: " in line and "ci-drafts" in line and "ci-concurrency" in line


# --- the fix list of 8579af0 ---------------------------------------------------------------------


def test_a_workflow_that_skips_drafts_without_ready_for_review_is_warned_as_its_own_case(tmp_path):
    """REQ-039: brief #283 answer 3 (a draft's green check would stay when it is marked ready)."""
    text = slow(CONCURRENCY, NOT_DRAFT).replace(
        "    types: [opened, synchronize, reopened, ready_for_review]\n",
        "    types: [opened, synchronize, reopened]\n",
    )
    _, report = ci_case(tmp_path / "a", {"slow.yml": text})
    entry = report["ci-drafts"]
    assert entry["status"] == "fail"
    assert entry["message"].endswith("(1 skips drafts but has no ready_for_review)")
    assert "slow" not in entry["message"]
    assert "ready_for_review" in entry["fix"]
    bare = text.replace(
        "  pull_request:\n    types: [opened, synchronize, reopened]\n", "  pull_request:\n"
    )
    _, report = ci_case(tmp_path / "b", {"slow.yml": bare})
    assert "skips drafts but has no ready_for_review" in report["ci-drafts"]["message"]


def test_a_workflow_that_runs_on_drafts_is_named_as_that_case(tmp_path):
    """REQ-039: brief #283 answer 3 (the two draft cases are told apart in the message)."""
    _, report = ci_case(tmp_path, {"slow.yml": slow(CONCURRENCY)})
    counts = report["ci-drafts"]["message"].rsplit("(", 1)[1]
    assert counts == "1 runs on drafts)"


def test_the_guide_names_no_build_action_setting_and_says_why_ready_for_review_matters():
    """REQ-039: brief #283 answers 1 and 4 (Q-283-3: no vendor-prefixed name)."""
    text = GUIDE.read_text(encoding="utf-8")
    assert "DOCKER" not in text.upper()
    five = text.split("## 5.", 1)[1].split("\n## ", 1)[0]
    assert "build record" in five and "build summary" in five and "(verify)" in five
    one = text.split("## 1.", 1)[1].split("\n## ", 1)[0]
    assert "merge" in one and "ready_for_review" in one and "no new commit" in one


# --- brief #370: the minutes line in the doctor -----------------------------------------------


def minutes_case(tmp_path: Path, billing=None, refused: tuple[str, ...] = ()):
    dirs = prepare("ok", tmp_path)
    api = dirs["api"]
    if billing is not None:
        (api / "billing.json").write_text(json.dumps(billing), encoding="utf-8")
    for name in refused:
        (api / f"{name}.json").unlink(missing_ok=True)
        (api / f"{name}.status").write_text("403\n", encoding="utf-8")
    proc = doctor("--api-dir", str(api), "--json", str(dirs["root"]))
    return proc, checks_of(proc.stdout)["actions-minutes"]


def test_the_minutes_line_is_ok_under_half(tmp_path):
    """REQ-020: brief #370 answer 2 (one check that prints the line)."""
    proc, entry = minutes_case(tmp_path, {"total_minutes_used": 999, "included_minutes": 2000})
    assert (entry["status"], entry["severity"]) == ("ok", "warn")
    assert "actions minutes: 999 of 2000 used (49%), level ok" in entry["message"]
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize(
    ("used", "level"), [(1000, "50%"), (1600, "80%"), (1900, "95%"), (2500, "95%")]
)
def test_the_minutes_line_warns_from_half_and_never_fails(tmp_path, used, level):
    """REQ-020: brief #370 answers 2 and 4 (a warning from the 50% level on, never a failure)."""
    proc, entry = minutes_case(tmp_path, {"total_minutes_used": used, "included_minutes": 2000})
    assert (entry["status"], entry["severity"]) == ("fail", "warn")
    assert f"level {level}" in entry["message"]
    assert "local-mode.md" in entry["fix"]
    assert proc.returncode == 4  # a warning, not an error


def test_the_minutes_line_is_unknown_without_billing_and_run_history(tmp_path):
    """REQ-020: brief #370 answer 2 (`unknown` when the token cannot read billing and no estimate
    exists: cannot-check, never ok and never a failure)."""
    proc, entry = minutes_case(tmp_path, refused=("billing", "runs"))
    assert (entry["status"], entry["reason"]) == ("cannot-check", "minutes-unknown")
    assert proc.returncode == 4
    text = doctor_text(tmp_path / "t", refused=("billing", "runs"))
    assert "?? actions-minutes warn cannot check (minutes-unknown)" in text
    assert "python3 scripts/agk/minutes.py" in text


def test_the_minutes_line_with_an_estimate_only_is_not_unknown(tmp_path):
    """REQ-020: brief #370 answer 2 (billing refused, the run history read: the estimate)."""
    api_dir = tmp_path / "e"
    dirs = prepare("ok", api_dir)
    month = ROOT / "tests" / "kit" / "fixtures" / "minutes" / "month"
    for file in month.glob("*.json"):
        if file.name not in ("repo.json", "billing.json"):
            (dirs["api"] / file.name).write_text(file.read_text(encoding="utf-8"))
    (dirs["api"] / "billing.json").unlink(missing_ok=True)
    (dirs["api"] / "billing.status").write_text("403\n", encoding="utf-8")
    proc = doctor("--api-dir", str(dirs["api"]), "--json", str(dirs["root"]))
    entry = checks_of(proc.stdout)["actions-minutes"]
    assert entry["status"] == "ok"
    assert "used this month (estimate from run history)" in entry["message"]
    assert "level unknown" in entry["message"]


def doctor_text(tmp_path: Path, refused: tuple[str, ...]) -> str:
    dirs = prepare("ok", tmp_path)
    for name in refused:
        (dirs["api"] / f"{name}.json").unlink(missing_ok=True)
        (dirs["api"] / f"{name}.status").write_text("403\n", encoding="utf-8")
    return doctor("--api-dir", str(dirs["api"]), str(dirs["root"])).stdout


def test_launch_prints_the_line_before_it_asks_and_recommends_local_mode_at_95():
    """REQ-020: brief #370 answer 3."""
    text = (ROOT / "skills" / "launch" / "SKILL.md").read_text(encoding="utf-8")
    line_at = text.index("python3 scripts/agk/minutes.py --line")
    assert line_at < text.index("**Confirm.**")
    assert "95%" in text and "docs/guides/local-mode.md" in text


def test_the_guide_names_the_doctor_check_and_the_levels():
    """REQ-020: brief #370 answers 1 and 2."""
    text = GUIDE.read_text(encoding="utf-8")
    for needle in ("actions-minutes", "--line", "50%", "95%", "runs out about", "not this month"):
        assert needle in text, needle
