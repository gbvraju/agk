"""The pipeline document of the router (SPEC-0036 rules 2 to 5 and 7; REQ-043).

`route.py` writes `pipeline.json` after every routing run from saved GitHub responses (a `gh`
stub): what waits for a person, in plain words, with no sha and no verdict text. No network."""

# ruff: noqa: F811 - the fixtures of test_route are imported by name
from __future__ import annotations

import base64
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_route import HEAD, REPO, WORKFLOW, Stub, proj, run_router, said, stub  # noqa: E402,F401

EVENT = {"ref": "refs/heads/main", "repository": {"full_name": REPO, "default_branch": "main"}}
SIX = ["review", "fix", "ci-red", "conflict", "approve", "ready"]
ASK = "Approval: SPEC-0036 docs/specs/0036-the-spec.md Draft -> Approved, waiting for a person"


def listed(n: int, label: str, body: str = "") -> dict:
    return {
        "number": n,
        "html_url": f"https://github.com/{REPO}/pull/{n}",
        "body": body,
        "head": {"sha": HEAD},
        "state": "open",
        "labels": [{"name": label}],
    }


def route(proj, stub, tmp_path, items, *, comments=None, spec="# SPEC-0036: A plain title\n"):
    stub.fixtures[f"repos/{REPO}/pulls"] = items
    for item in items:
        stub.pull(item["number"], labels=[x["name"] for x in item["labels"]])
        stub.serve(f"issues/{item['number']}/comments", (comments or {}).get(item["number"], []))
    if spec is not None:
        stub.serve(
            "contents/docs/specs/0036-the-spec.md",
            {"encoding": "base64", "content": base64.b64encode(spec.encode()).decode()},
        )
    out = tmp_path / "out.json"
    proc = run_router(proj, stub, tmp_path, "push", EVENT, AGK_PIPELINE_FILE=str(out))
    return proc, out


def test_ready_items_carry_the_summary_line_or_unknown(proj, stub, tmp_path):
    items = [
        listed(7, "agk:ready", "Advances: REQ-1\nSummary: A person can see the queue.\n"),
        listed(8, "agk:ready", "no summary line here"),
    ]
    proc, out = route(proj, stub, tmp_path, items)
    doc = json.loads(out.read_text())
    assert doc["schema"] == 1 and doc["as_of"].endswith("Z")
    assert doc["ready"] == [
        {"number": 7, "summary": "A person can see the queue.", "url": items[0]["html_url"]},
        {"number": 8, "summary": "unknown", "url": items[1]["html_url"]},
    ]
    assert proc.returncode == 0


def test_counts_are_exactly_the_six_labels(proj, stub, tmp_path):
    items = [listed(7, "agk:ready"), listed(8, "agk:fix"), listed(9, "agk:fix")]
    _, out = route(proj, stub, tmp_path, items)
    counts = json.loads(out.read_text())["counts"]
    assert list(counts) == SIX
    assert counts["fix"] == 2 and counts["ready"] == 1 and counts["review"] == 0


def test_approve_has_one_item_per_approval_line(proj, stub, tmp_path):
    other = "Approval: SPEC-0037 docs/specs/0037-b.md Draft -> Approved, waiting for a person"
    verdict = f"Verdict: cleared {HEAD[:7]}\n{ASK}\n{other}\n"
    comments = {7: [said(1, "boss", verdict)]}
    _, out = route(proj, stub, tmp_path, [listed(7, "agk:approve")], comments=comments)
    doc = json.loads(out.read_text())
    assert doc["counts"]["approve"] == 1
    assert [(a["number"], a["spec"]) for a in doc["approve"]] == [
        (7, "SPEC-0036"),
        (7, "SPEC-0037"),
    ]
    assert doc["approve"][0]["spec_title"] == "A plain title"
    assert doc["approve"][1]["spec_title"] == "unknown"


def test_no_sha_and_no_verdict_text(proj, stub, tmp_path):
    comments = {7: [said(1, "boss", f"Verdict: cleared {HEAD[:7]}\nSECRETWORDS\n{ASK}\n")]}
    _, out = route(proj, stub, tmp_path, [listed(7, "agk:approve")], comments=comments)
    text = out.read_text()
    assert HEAD[:7] not in text and "SECRETWORDS" not in text and "Verdict" not in text


def test_an_unreadable_list_gives_unknown_counts_never_zero(proj, stub, tmp_path):
    stub.fixtures[f"repos/{REPO}/pulls"] = "FAIL"
    out = tmp_path / "out.json"
    proc = run_router(proj, stub, tmp_path, "push", EVENT, AGK_PIPELINE_FILE=str(out))
    doc = json.loads(out.read_text())
    assert set(doc["counts"].values()) == {"unknown"} and list(doc["counts"]) == SIX
    assert proc.returncode == 0


def test_a_failed_write_fails_no_routing_and_labels_are_set(proj, stub, tmp_path):
    stub.pull(7, labels=["agk:fix"])
    stub.fixtures[f"repos/{REPO}/pulls"] = [listed(7, "agk:fix")]
    target = tmp_path / "no-such-dir" / "pipeline.json"
    proc = run_router(proj, stub, tmp_path, "push", EVENT, AGK_PIPELINE_FILE=str(target))
    assert proc.returncode == 0 and not target.exists()
    assert any(c[0] == "POST" and c[1].endswith("/issues/7/labels") for c in stub.writes())


def test_dry_run_writes_no_document(proj, stub, tmp_path):
    stub.pull(7)
    out = tmp_path / "out.json"
    run_router(
        proj, stub, tmp_path, "push", EVENT, "--pr", "7", "--dry-run", AGK_PIPELINE_FILE=str(out)
    )
    assert not out.exists()


def test_the_workflow_uploads_the_document_and_the_router_posts_nothing_new():
    text = WORKFLOW.read_text()
    assert "actions/upload-artifact@" in text and "name: agk-pipeline" in text
    assert "retention-days: 7" in text and "pipeline.json" in text
    assert re.search(r"actions/upload-artifact@[0-9a-f]{40}", text)
    assert "continue-on-error: true" in text
    assert "contents: read" in text and "contents: write" not in text


def test_the_approval_line_with_the_approve_instruction_gives_an_item(proj, stub, tmp_path):
    line = f'{ASK}: post "Approve: SPEC-0036"'
    comments = {7: [said(1, "boss", f"Verdict: cleared {HEAD[:7]}\n{line}\n")]}
    _, out = route(proj, stub, tmp_path, [listed(7, "agk:approve")], comments=comments)
    (item,) = json.loads(out.read_text())["approve"]
    assert (item["spec"], item["spec_title"]) == ("SPEC-0036", "A plain title")


# --- brief #1272: a local run writes an ignored file (REQ-039, ADR-0538) ------------------------

LOCAL = ".agk-pipeline.json"
KIT = Path(__file__).resolve().parents[2]


def test_a_local_run_writes_the_ignored_file_in_the_repository_root(proj, stub, tmp_path):
    """REQ-039: brief #1272 answers 1 and 3 (a) (no `AGK_PIPELINE_FILE`: `.agk-pipeline.json` in
    the repository root, and no `pipeline.json`)."""
    stub.fixtures[f"repos/{REPO}/pulls"] = [listed(7, "agk:ready", "Summary: One.\n")]
    stub.pull(7, labels=["agk:ready"])
    stub.serve("issues/7/comments", [])
    proc = run_router(proj, stub, tmp_path, "push", EVENT, AGK_PIPELINE_FILE="")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads((proj / LOCAL).read_text(encoding="utf-8"))
    assert doc["schema"] == 1 and [r["number"] for r in doc["ready"]] == [7]
    assert not (proj / "pipeline.json").exists()


def test_a_set_path_is_unchanged_for_ci(proj, stub, tmp_path):
    """REQ-039: brief #1272 answer 3 (b) (`AGK_PIPELINE_FILE` set, as the workflow sets it)."""
    _, out = route(proj, stub, tmp_path, [listed(7, "agk:fix")])
    assert json.loads(out.read_text(encoding="utf-8"))["counts"]["fix"] == 1
    assert not (proj / LOCAL).exists() and not (proj / "pipeline.json").exists()


def _install(tmp_path: Path, script: str) -> Path:
    target = tmp_path / script.removesuffix(".py")
    target.mkdir()
    who = ["-c", "user.name=Example", "-c", "user.email=dev@example.com"]
    (target / "README.md").write_text("An example project, example.com.\n", encoding="utf-8")
    for step in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "one"]):
        subprocess.run(  # nosec B603 B607 - fixed git argument list, no shell
            ["git", *who, *step], cwd=target, check=True
        )
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    done = subprocess.run(  # nosec B603 - fixed argument list from sys.executable, no shell
        [sys.executable, str(KIT / "scripts" / "agk" / script), str(target), "--unreleased"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return target


@pytest.mark.parametrize("script", ["init.py", "adopt.py"])
def test_the_installed_ignore_block_ignores_the_local_document(tmp_path, script):
    """REQ-039: brief #1272 answers 2 and 3 (c) (`git check-ignore` matches in an install)."""
    target = _install(tmp_path, script)
    (target / LOCAL).write_text('{"schema": 1}\n', encoding="utf-8")
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "check-ignore", "-q", LOCAL], cwd=target, check=False
    )
    assert done.returncode == 0
