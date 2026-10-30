"""The router wakes when any required check finishes (brief #285, ADR-0165; SPEC-0032 rule 1).

`workflow_run` takes workflow names, not patterns, so the `workflows:` list of `workflow_run` in
`agk-route.yml` must name every workflow that holds a check of `required_checks`. The helpers that
read and write that list live in `common.py`; `upgrade.py`, `init.py` and `doctor.py` use them.
The doctor's `router-wake` warning names the setting, never a value. Workflow and check names
here are invented.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from test_doctor import checks_of, doctor, prepare

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import common as doc  # noqa: E402
import doctor as doctor_script  # noqa: E402

ROUTER = ".github/workflows/agk-route.yml"
# The shape of the kit's router (the installed file may carry a project's names, so it is not read).
KIT_ROUTER = (
    "name: agk-route\n"
    "on:\n"
    "  pull_request:\n"
    "    types: [opened, synchronize, reopened, closed]\n"
    "  workflow_run:\n"
    "    # the workflows of required_checks\n"
    "    workflows: [governance, proof]\n"
    "    types: [completed]\n"
    "  push:\n"
    "jobs:\n"
    "  agk-route:\n"
    "    runs-on: ubuntu-latest\n"
)
PROJECT_WORKFLOW = (
    "name: project\n"
    "on: [pull_request]\n"
    "jobs:\n"
    "  lint-suite:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - run: echo lint\n"
    "  e2e:\n"
    '    name: "browser e2e"   # the check run carries this name\n'
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - name: not a job name\n"
    "        run: echo e2e\n"
)
SLOW_WORKFLOW = (
    "# a workflow with no top-level name: GitHub names it by its path (verify)\n"
    "on:\n"
    "  pull_request:\n"
    "jobs:\n"
    "  slow-profile:\n"
    "    runs-on: ubuntu-latest\n"
)


def tree(tmp_path: Path, workflows: dict[str, str], router: str = KIT_ROUTER) -> Path:
    root = tmp_path / "proj"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ROUTER).write_text(router, encoding="utf-8")
    for name, text in workflows.items():
        (root / ".github" / "workflows" / name).write_text(text, encoding="utf-8")
    return root


# --- answer 1: the list, read and written ---


def test_the_list_is_read():
    """REQ-039: brief #285 answer 1."""
    assert doc.router_names(KIT_ROUTER) == ["governance", "proof"]


def test_names_are_written_in_one_flow_list_and_read_back():
    """REQ-039: brief #285 answer 1 (a name that YAML would misread is quoted)."""
    names = ["governance", "proof", "project", "a, b", "x: y", "#hash", ".github/workflows/z.yml"]
    text = doc.with_router_names(KIT_ROUTER, names)
    assert text is not None
    assert doc.router_names(text) == names
    assert '"a, b"' in text and '"x: y"' in text and '"#hash"' in text
    assert "[governance, proof, project," in text
    # only the one line changes
    old, new = KIT_ROUTER.splitlines(), text.splitlines()
    assert len(old) == len(new)
    assert [i for i, (a, b) in enumerate(zip(old, new, strict=True)) if a != b] == [
        old.index("    workflows: [governance, proof]")
    ]


def test_quoted_and_commented_lists_are_read():
    """REQ-039: brief #285 answer 1 (a project may write the list by hand)."""
    text = KIT_ROUTER.replace(
        "    workflows: [governance, proof]",
        "    workflows: [ governance, 'proof', \"browser e2e\" ]   # mine",
    )
    assert doc.router_names(text) == ["governance", "proof", "browser e2e"]


def test_a_file_without_the_list_is_not_read():
    """REQ-039: brief #285 answer 1 (no list under workflow_run: nothing to read or write)."""
    for text in (
        "name: x\non:\n  push:\n",
        KIT_ROUTER.replace("    workflows: [governance, proof]\n", ""),
        KIT_ROUTER.replace("    workflows: [governance, proof]", "    workflows:\n      - proof"),
        KIT_ROUTER.replace("[governance, proof]", "[governance, 'proof]"),
    ):
        assert doc.router_names(text) is None
        assert doc.with_router_names(text, ["proof"]) is None


def test_workflow_checks_reads_job_ids_and_job_names(tmp_path):
    """REQ-039: brief #285 answer 1 (a check run is named by the job's `name:`, else its id)."""
    root = tree(tmp_path, {"project.yml": PROJECT_WORKFLOW, "slow.yaml": SLOW_WORKFLOW})
    checks = doc.workflow_checks(root)
    assert checks["project"] == {"lint-suite", "browser e2e"}
    assert checks[".github/workflows/slow.yaml"] == {"slow-profile"}
    assert "agk-route" not in checks  # the router's own file is never a source


def test_the_wanted_list_keeps_the_present_names_and_adds_the_missing(tmp_path):
    """REQ-039: brief #285 answer 1 (kit names first, the rest sorted; project names kept)."""
    root = tree(tmp_path, {"project.yml": PROJECT_WORKFLOW, "slow.yaml": SLOW_WORKFLOW})
    required = ["proof", "governance", "lint-suite", "browser e2e", "slow-profile", "a-status"]
    present = ["governance", "proof", "hand-added"]
    assert doc.router_wanted(root, required, present) == [
        "governance",
        "proof",
        "hand-added",
        ".github/workflows/slow.yaml",
        "project",
    ]
    # a check no workflow holds (a commit status, say) adds nothing
    assert doc.router_wanted(root, ["a-status"], ["governance", "proof"]) == ["governance", "proof"]


# --- answer 2: the doctor's warning ---


def router_case(tmp_path: Path, required: list[str], names: list[str] | None) -> dict[str, dict]:
    dirs = prepare("ok", tmp_path)
    root = dirs["root"]
    (root / ".github" / "workflows" / "project.yml").write_text(PROJECT_WORKFLOW, encoding="utf-8")
    if names is not None:
        text = doc.with_router_names(KIT_ROUTER, names)
        (root / ROUTER).write_text(text or "", encoding="utf-8")
    toml = (root / "agk.toml").read_text(encoding="utf-8")
    (root / "agk.toml").write_text(f"{toml}required_checks = {json.dumps(required)}\n")
    proc = doctor("--api-dir", str(dirs["api"]), "--json", str(root))
    return checks_of(proc.stdout)


def test_doctor_warns_when_a_required_checks_workflow_is_not_listed(tmp_path):
    """REQ-039: brief #285 answer 2 (a warning, with the fix; the message names no value)."""
    report = router_case(tmp_path, ["proof", "governance", "lint-suite"], ["governance", "proof"])
    check = report["router-wake"]
    assert (check["status"], check["severity"]) == ("fail", "warn")
    for value in ("lint-suite", "project", "1"):
        assert value not in check["message"].split()
    assert "required_checks" in check["message"]
    assert "upgrade" in check["fix"] and "workflow_run" in check["fix"]


def test_doctor_is_ok_when_every_workflow_is_listed(tmp_path):
    """REQ-039: brief #285 answer 2."""
    report = router_case(
        tmp_path, ["proof", "governance", "lint-suite"], ["governance", "proof", "project"]
    )
    assert report["router-wake"]["status"] == "ok"


def test_doctor_is_ok_without_a_router_and_for_a_check_no_workflow_holds(tmp_path):
    """REQ-039: brief #285 answer 2 (no router: nothing to wake; a status context: not known)."""
    assert (
        router_case(tmp_path / "a", ["proof", "lint-suite"], None)["router-wake"]["status"] == "ok"
    )
    report = router_case(tmp_path / "b", ["proof", "a-status"], ["governance", "proof"])
    assert report["router-wake"]["status"] == "ok"


def test_doctor_fails_when_the_router_list_cannot_be_read(tmp_path):
    """REQ-039: brief #285 answer 2 (an unreadable list wakes nothing that is listed)."""
    dirs = prepare("ok", tmp_path)
    root = dirs["root"]
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (root / ROUTER).write_text("name: agk-route\non:\n  push:\n", encoding="utf-8")
    proc = doctor("--api-dir", str(dirs["api"]), "--json", str(root))
    assert checks_of(proc.stdout)["router-wake"]["status"] == "fail"


def test_vendored_differs_ignores_the_names_a_project_added(tmp_path):
    """REQ-039: brief #285 answer 1 (the list is the extendable part; the rest is compared)."""
    dirs = prepare("ok", tmp_path)
    kit, root = dirs["kit"], dirs["root"]
    manifest = json.loads((kit / "kit" / "manifest.json").read_text(encoding="utf-8"))
    manifest["verbatim"] = sorted({*manifest["verbatim"], ROUTER})
    (kit / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kit / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (kit / ROUTER).write_text(KIT_ROUTER, encoding="utf-8")
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    extended = doc.with_router_names(KIT_ROUTER, ["governance", "proof", "project"])
    (root / ROUTER).write_text(extended or "", encoding="utf-8")
    args = ("--api-dir", str(dirs["api"]), "--kit-root", str(kit), "--json", str(root))
    assert checks_of(doctor(*args).stdout)["vendored-differs"]["status"] == "ok"
    (root / ROUTER).write_text((extended or "").replace("types: [completed]", "types: [requested]"))
    report = checks_of(doctor(*args).stdout)
    assert report["vendored-differs"]["status"] == "fail"
    assert ROUTER in report["vendored-differs"]["message"]


@pytest.mark.parametrize("name", ["router-wake"])
def test_the_new_check_is_after_the_kit_checks(name):
    """REQ-039: brief #285 answer 2 (one new id, a warning, in the report order)."""
    ids = list(doctor_script.CHECKS)
    assert ids.index(name) == ids.index("vendored-differs") + 1
    assert doctor_script.CHECKS[name][0] == "warn"


# --- brief #369: an edit is labelled through the `governance edited` wake ---


def test_the_router_still_labels_a_pull_request_after_an_edit():
    """REQ-039: brief #369 answer 2 (`edited` leaves the router's own triggers; the finished
    `governance edited` run, a run of the workflow named `governance`, wakes it instead)."""
    from test_ci_saving import holds, jobs_started, pr_event, router_condition, triggers, workflow

    router = workflow("agk-route.yml")
    assert "edited" not in triggers(router)["pull_request"]["types"]
    assert "edited" in triggers(workflow("governance.yml"))["pull_request"]["types"]
    assert "governance" in doc.router_names(router)
    for draft in (True, False):
        count = jobs_started(pr_event("edited", draft))
        assert (count["agk-route.yml"], count["agk-route wake"]) == (0, 1), draft
    for conclusion in ("success", "failure", "cancelled"):
        run = {"name": "governance", "conclusion": conclusion}
        wake = {
            "event_name": "workflow_run",
            "ref_name": "main",
            "event": {"workflow_run": run, "repository": {"default_branch": "main"}},
        }
        assert holds(router_condition(), wake), conclusion
