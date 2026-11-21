"""Tests of SPEC-0072 build (h): the steward shows the standard and applies it on one yes, the
work-type path, and the personal floor's gates (rules 8, 10 and 11; brief #1601, ADR-0681;
REQ-079 AC6 to AC8).

Saved replies, a search stub, the recorded memory double of `test_steward_memory` and a forge stub
stand in for the person, the web, GitHub and the forge; no network, no model, invented data only
(example.com).
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - a fixed `git init` and commit in a temporary folder, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_playbooks  # noqa: E402
import personal  # noqa: E402
import steward  # noqa: E402
import steward_owner  # noqa: E402
from test_steward_memory import GitHub  # noqa: E402

AT = "2026-11-21T09:30Z"
CONFIRMED = "Setup: standard: confirmed because the person said"
PLAN = '{"malformed": []}'
TRACE = "ok plan (3 briefs)\n"
APPROVER = "approver-example-1"
REVIEWERS = f"spec_approvers: [{APPROVER}]\nverdict_authors: [conductor-example-1]\n"
RESEARCH = """# Research: a booking web app for small clinics

## Option: a web app on one server
- Source: https://example.com/booking-guide (accessed 2026-11-21)

## Option: a web app with a separate service
- Source: https://example.org/clinic-apps (accessed 2026-11-21)

## Criteria
| criterion | note |
|---|---|
| capability fit | fit |
| cost | fit |
| licence | fit |
| data handling and residency | fit |
| maturity | fit |
| integration effort | fit |
| lock-in | fit |

## Recommendation
A web app on one server (proposal).
"""


def project(
    tmp_path: Path,
    mode: str = "solo",
    work_type: str | None = "web-app",
    personal_mode: bool = True,
) -> Path:
    root = tmp_path / "product"
    shutil.copytree(ROOT / "config" / "playbooks", root / "config" / "playbooks")
    lines = [f'review_mode = "{mode}"']
    if personal_mode:
        lines += ["", "[personal]", 'level = "light"', 'forge = "files"']
    if work_type:
        lines += ["", "[delivery]", f'work_type = "{work_type}"']
    (root / "agk.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "config" / "reviewers.yaml").write_text(REVIEWERS, encoding="utf-8")
    (root / "docs" / "plan").mkdir(parents=True)
    (root / "docs" / "plan" / "scope-lock.md").write_text("# Scope lock\n", encoding="utf-8")
    return root


def said(tmp_path: Path, words: str) -> Path:
    path = tmp_path / "said.txt"
    path.write_text(words, encoding="utf-8")
    return path


def memory(root: Path) -> list[str]:
    return [e["body"] for e in steward.personal_entries(root)]


def test_req079_ac6_a_business_user_sees_one_plain_screen_with_no_kit_term(tmp_path):
    """REQ-079 AC6: rule 8, solo mode prints one plain screen, no stack, layer or rule asked."""
    root = project(tmp_path, "solo")
    code, lines = steward_owner.standard_screen(root, None)
    text = "\n".join(lines)
    assert code == 0
    assert steward_owner.KIT_TERMS.search(text) is None, text
    assert "?" not in text.replace(steward_owner.YES_ASK, "")  # only the one yes is asked
    assert lines[-1] == steward_owner.YES_ASK
    assert len([x for x in lines if x.startswith("- ")]) <= 5  # the steward's voice
    assert all(len(x) <= 100 for x in lines)


def test_req079_ac6_a_team_sees_the_full_list(tmp_path):
    """REQ-079 AC6: rule 8, team mode lists the layers and directions, each pack and every gate."""
    root = project(tmp_path, "team")
    code, lines = steward_owner.standard_screen(root, None)
    text = "\n".join(lines)
    gates, _, _ = check_playbooks.composed(root / "config/playbooks/web-app.toml", root)
    assert code == 0
    assert "Layer frontend: frontend/**" in text and "Allowed: frontend -> contracts" in text
    assert "Pack python-pyproject: lint python-lint" in text and "ruff 0.17.4" in text
    for gate in gates:
        assert f"Gate {gate['id']}: {gate['kind']}" in text
    assert "Gate secrets: check (step committed-secrets)" in text


def test_req079_ac6_nothing_is_applied_before_an_explicit_yes(tmp_path):
    """REQ-079 AC6: a reply that is not an explicit yes records nothing and the plan waits."""
    root = project(tmp_path)
    for words in ("yes, but drop the type checks", "maybe later", "what does this mean?", ""):
        code, lines = steward_owner.confirm(root, said(tmp_path, words), AT, None, GitHub())
        assert code == 1 and lines == [steward_owner.NOT_CONFIRMED]
    assert memory(root) == []
    failed = steward_owner.not_ready(root, PLAN, TRACE)
    assert steward_owner.UNCONFIRMED in failed


def test_req079_ac6_one_yes_records_one_setup_entry_and_applies_all(tmp_path):
    """REQ-079 AC6: one yes is one Setup entry with the quoted words and time; the plan may go."""
    root = project(tmp_path)
    code, lines = steward_owner.confirm(root, said(tmp_path, "Yes"), AT, None, GitHub())
    assert code == 0, lines
    assert memory(root) == [f'{CONFIRMED} "Yes" at {AT}']
    assert steward_owner.confirmed(root)
    assert steward_owner.UNCONFIRMED not in steward_owner.not_ready(root, PLAN, TRACE)


def test_req079_ac6_hosted_memory_holds_the_entry(tmp_path):
    """REQ-079 AC6: outside personal mode the entry goes to the memory issue, read back from it."""
    root = project(tmp_path, personal_mode=False)
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # the cache lives in .git
    gh = GitHub()
    code, _ = steward_owner.confirm(root, said(tmp_path, "yes"), AT, None, gh)
    assert code == 0
    bodies = [c["body"] for issue in gh.issues.values() for c in issue["c"]]
    assert any(b.startswith(f'{CONFIRMED} "yes" at {AT}') for b in bodies)
    assert steward_owner.confirmed(root)


def test_req079_ac6_team_mode_counts_only_a_spec_approvers_yes(tmp_path, monkeypatch):
    """REQ-079 AC6 (Q-S0072-13): in team mode only a spec approver confirms; a conductor-started
    steward confirms nothing."""
    root = project(tmp_path, "team")
    reply = said(tmp_path, "yes")
    code, lines = steward_owner.confirm(root, reply, AT, "member-example-2", GitHub())
    assert code == 2 and "spec_approvers" in lines[0] and "member-example-2" not in lines[0]
    assert steward_owner.confirm(root, reply, AT, None, GitHub())[0] == 2
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    assert steward_owner.confirm(root, reply, AT, APPROVER, GitHub())[0] == 2
    monkeypatch.delenv("AGK_STEWARD_START")
    assert steward_owner.confirm(root, reply, AT, APPROVER, GitHub())[0] == 0
    assert memory(root) == [f'{CONFIRMED} "yes" at {AT} (by {APPROVER})']


def test_req079_ac7_no_work_type_asks_the_work_type_question_and_holds_nothing_else(tmp_path):
    """REQ-079 AC7: with no work type the screen is the work-type path's question; nothing is
    applied and the kit's own case (no work type) is not held by the confirmation."""
    root = project(tmp_path, work_type=None)
    code, lines = steward_owner.standard_screen(root, None)
    assert code == 1 and lines == [steward_owner.NO_WORK_TYPE]
    assert steward_owner.KIT_TERMS.search(steward_owner.NO_WORK_TYPE) is None
    assert steward_owner.UNCONFIRMED not in steward_owner.not_ready(root, PLAN, TRACE)


def test_req079_ac6_no_search_without_a_yes_and_only_the_generic_description(tmp_path):
    """REQ-079 AC6: no yes, no search; on a yes only the generic description reaches the stub,
    and a planted customer name or example.com address never does."""
    root = project(tmp_path, work_type=None)
    sent: list[str] = []
    generic = "a booking web app for small clinics"
    code, lines = steward_owner.research(
        root, said(tmp_path, "no"), AT, generic, GitHub(), sent.append
    )
    assert code == 0 and sent == [] and lines[-1] == steward_owner.NO_SEARCH
    for planted in (
        "a booking web app for Northwind Clinics",
        "a booking app for clinic@example.com",
        "a booking app like https://example.com",
        "a booking app for 3 clinics",
    ):
        code, lines = steward_owner.research(
            root, said(tmp_path, "yes"), AT, planted, GitHub(), sent.append
        )
        assert code == 2 and sent == [], planted
        assert "example.com" not in lines[0] and "Northwind" not in lines[0]
    code, _ = steward_owner.research(
        root, said(tmp_path, "yes"), AT, generic, GitHub(), sent.append
    )
    assert code == 0 and sent == [generic]
    assert memory(root) == [
        f'Setup: web-research: no because the person said "no" at {AT}',
        f'Setup: web-research: yes because the person said "yes" at {AT}',
    ]


def test_req079_ac6_the_drafted_playbook_keeps_every_default_gate_with_a_proposed_adr(tmp_path):
    """REQ-079 AC6: the draft composes on default.toml, keeps each gate at its kind, carries a
    Proposed ADR naming its sources, and never writes the work type."""
    root = project(tmp_path, work_type=None)
    (root / "docs" / "research").mkdir(parents=True)
    (root / "docs" / "research" / "clinic-booking.md").write_text(RESEARCH, encoding="utf-8")
    (root / "docs" / "adr").mkdir()
    (root / "docs" / "adr" / "0001-adopt-agk.md").write_text("# ADR-0001: Adopt\n", "utf-8")
    before = (root / "agk.toml").read_text(encoding="utf-8")
    code, lines = steward_owner.draft(root, "clinic-booking")
    assert code == 0, lines
    path = root / "config" / "playbooks" / "clinic-booking.toml"
    base, _, _ = check_playbooks.composed(root / "config/playbooks/default.toml", root)
    gates, _, problems = check_playbooks.composed(path, root)
    assert problems == [] and check_playbooks.findings(root, [path]) == []
    kinds = {g["id"]: g["kind"] for g in gates}
    assert all(kinds.get(g["id"]) == g["kind"] for g in base)
    adr = (root / "docs" / "adr" / "0002-the-project-s-work-type-clinic-booking.md").read_text()
    assert "- Status: Proposed" in adr and "https://example.com/booking-guide" in adr
    assert (root / "agk.toml").read_text(encoding="utf-8") == before
    assert steward_owner.draft(root, "clinic-booking")[0] == 2  # never overwritten
    assert steward_owner.draft(root, "web-app")[0] == 2  # a shipped playbook
    code, lines = steward_owner.standard_screen(root, "clinic-booking")
    assert code == 0 and lines[-1] == steward_owner.YES_ASK


def test_req079_ac8_the_personal_floor_runs_the_gates_with_no_forge_call(tmp_path, monkeypatch):
    """REQ-079 AC8: rule 11, `floor` runs the gate runner after its secret scan, at every level,
    and a red gate fails the floor; no forge call is made."""
    clone = tmp_path / "clone"
    clone.mkdir()
    git = ["git", "-C", str(clone), "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    (clone / "app.py").write_text("print('hello')\n", encoding="utf-8")
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-qm", "one"], check=True)
    sidecar = tmp_path / "sidecar"
    sidecar.mkdir()
    (sidecar / "agk.toml").write_text(
        '[personal]\nlevel = "review"\nforge = "files"\ntest_command = "python3 -m pytest -q"\n',
        encoding="utf-8",
    )
    order: list[str] = []
    monkeypatch.setattr(personal, "scan_step", lambda c, b: (order.append("scan"), (True, "s"))[1])
    monkeypatch.setattr(
        personal, "forge_call", lambda *a: pytest.fail("a forge call"), raising=False
    )
    seen: list[Path] = []

    def green(root):
        order.append("gates")
        seen.append(root)
        return [(True, "secrets")]

    monkeypatch.setattr(personal.run_gates, "results", green)
    monkeypatch.setattr(personal, "regression_step", lambda *a: (True, "floor: no-regression ok"))
    assert personal.GATES_NOT_RUN in personal.floor(clone, sidecar, "HEAD", False)[1]
    assert order == ["scan"]
    order.clear()
    _, text = personal.floor(clone, sidecar, "HEAD", True)
    assert order == ["scan", "gates"] and "floor: gates ok (1 check gates)" in text
    assert (seen[0] / "app.py").is_file() and seen[0] != clone
    monkeypatch.setattr(
        personal.run_gates, "results", lambda root: [(False, "secrets: x (path class: src)")]
    )
    passed, text = personal.floor(clone, sidecar, "HEAD", True)
    assert not passed and "floor: gates FAIL: secrets: x (path class: src)" in text
    assert not (sidecar / "forge").exists()
