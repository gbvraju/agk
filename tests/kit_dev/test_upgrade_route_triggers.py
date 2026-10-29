"""Brief #285 (REQ-039, ADR-0165): upgrade and init write the router's `workflow_run` list.

The installed `agk-route.yml` wakes on `workflow_run` of the workflows named in its `workflows:`
list; `upgrade.py` and `init.py` write that list from `required_checks` and the project's
workflows, and keep names a project added by hand. The rest of the file is compared as before.
The fixture kit is the one of test_upgrade.py with a router added; workflow names are invented.
"""

from __future__ import annotations

import json
import sys

import pytest
from conftest import KIT_ROOT
from test_upgrade import NEW, OLD, TEMPLATES_NEW, TEMPLATES_OLD, init_target, manifest_of, put, run

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import doctor  # noqa: E402
import init  # noqa: E402
import kit_hashes  # noqa: E402
import upgrade  # noqa: E402

ROUTER = ".github/workflows/agk-route.yml"
ROUTE_OLD = (
    "name: agk-route\non:\n  workflow_run:\n    workflows: [governance, proof]\n"
    "    types: [completed]\njobs:\n  agk-route:\n    runs-on: ubuntu-latest\n"
)
ROUTE_NEW = ROUTE_OLD.replace(
    "    workflows:", "    # the workflows of required_checks (brief #285)\n    workflows:"
)
PROJECT = (
    "name: project\non: [pull_request]\njobs:\n  lint-suite:\n    runs-on: ubuntu-latest\n"
    "  e2e:\n    name: browser-e2e\n    runs-on: ubuntu-latest\n"
)
REQUIRED = 'required_checks = ["proof", "governance", "lint-suite"]\n'


def listed(text: str, names: list[str]) -> str:
    out = doctor.with_router_names(text, names)
    assert out is not None
    return out


@pytest.fixture
def kit(tmp_path, monkeypatch):
    """The fixture kit (1.0.0 and 2.0.0) with the router in both releases."""
    root = tmp_path / "kit_root"
    table: dict = {"table": 1, "releases": {}}
    for version, files, templates in (
        ("1.0.0", {**OLD, ROUTER: ROUTE_OLD}, TEMPLATES_OLD),
        ("2.0.0", {**NEW, ROUTER: ROUTE_NEW}, TEMPLATES_NEW),
    ):
        manifest = manifest_of(version, files, templates)
        store = {k: v.encode() for k, v in {**files, **templates}.items()}
        snap = kit_hashes.snapshot_of(manifest, store.get)
        table["releases"][version] = {
            "commits": [],
            **{name: {p: [d] for p, d in snap[name].items()} for name in snap},
        }
        if version == "2.0.0":
            for rel, data in store.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(data)
            (root / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "kit" / "hashes.json").write_text(kit_hashes.dump(table), encoding="utf-8")
    monkeypatch.setattr(upgrade, "KIT_ROOT", root)
    return root


def target_with(tmp_path, router: str = ROUTE_OLD, required: str = REQUIRED, **over: str):
    target = init_target(tmp_path, **{ROUTER: router, ".github/workflows/project.yml": PROJECT})
    toml = (target / "agk.toml").read_text(encoding="utf-8")
    put(target, {"agk.toml": toml + required, **over})
    return target


def line_for(out: list[str], rel: str) -> str:
    return next(ln for ln in out if ln.split(" (")[0].split(" ", 1)[-1] == rel)


def test_upgrade_adds_the_workflow_of_a_required_check(tmp_path, kit, capsys):
    """REQ-039: brief #285 answer 1, the case of the pilot (a check that finishes last)."""
    target = target_with(tmp_path)
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / ROUTER).read_text() == listed(ROUTE_NEW, ["governance", "proof", "project"])
    assert line_for(out, ROUTER) == f"replace {ROUTER} (router workflows added: 1)"


def test_upgrade_keeps_names_a_project_added_by_hand(tmp_path, kit, capsys):
    """REQ-039: brief #285 answer 1 (the list is extendable: the workaround survives)."""
    target = target_with(tmp_path, router=listed(ROUTE_OLD, ["governance", "proof", "nightly"]))
    code, out = run(capsys, target)
    assert code == 0, out
    assert doctor.router_names((target / ROUTER).read_text()) == [
        "governance",
        "proof",
        "nightly",
        "project",
    ]


def test_upgrade_with_only_the_kits_checks_writes_the_kits_file(tmp_path, kit, capsys):
    """REQ-039: brief #285 answer 1 (the default required_checks change nothing)."""
    target = target_with(tmp_path, required="")
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / ROUTER).read_text() == ROUTE_NEW
    assert line_for(out, ROUTER) == f"replace {ROUTER}"


def test_an_edit_outside_the_list_is_still_a_conflict(tmp_path, kit, capsys):
    """REQ-039: brief #285 answer 1 (only the list is the project's)."""
    edited = ROUTE_OLD.replace("types: [completed]", "types: [requested]")
    target = target_with(tmp_path, router=edited)
    code, out = run(capsys, target)
    assert code == 1, out
    assert line_for(out, ROUTER).startswith(f"conflict {ROUTER} (path class ")
    assert (target / ROUTER).read_text() == edited


def test_a_second_upgrade_is_nothing_to_do(tmp_path, kit, capsys):
    """REQ-039: brief #285 answer 1 (idempotence, SPEC-0008 rule 21)."""
    target = target_with(tmp_path)
    assert run(capsys, target)[0] == 0
    code, out = run(capsys, target)
    assert code == 0, out
    assert out[-1] == "nothing to do"
    assert line_for(out, ROUTER) == f"unchanged {ROUTER} (router workflows added: 1)"


def test_a_new_required_check_at_the_same_version_is_written(tmp_path, kit, capsys):
    """REQ-039: brief #285 answer 1 (the next upgrade run keeps the list in step)."""
    target = target_with(tmp_path)
    assert run(capsys, target)[0] == 0
    toml = (target / "agk.toml").read_text().replace('"lint-suite"]', '"lint-suite", "slow"]')
    extra = "name: slow-suite\non: [pull_request]\njobs:\n  slow:\n    runs-on: ubuntu-latest\n"
    put(target, {"agk.toml": toml, ".github/workflows/slow.yml": extra})
    code, out = run(capsys, target)
    assert code == 0, out
    assert doctor.router_names((target / ROUTER).read_text()) == [
        "governance",
        "proof",
        "project",
        "slow-suite",
    ]


def test_an_unreadable_required_checks_adds_nothing_and_says_so(tmp_path, kit, capsys):
    """REQ-039: brief #285 answer 1 (the setting is named, never its value)."""
    target = target_with(tmp_path, required='required_checks = "proof"\n')
    code, out = run(capsys, target)
    assert code == 0, out
    assert (target / ROUTER).read_text() == ROUTE_NEW
    assert "router-workflows required_checks in agk.toml is not a list of names; none added" in out


def test_init_writes_the_list_from_the_targets_workflows(tmp_path, monkeypatch):
    """REQ-039: brief #285 answer 1 (init: the template's required_checks and the workflows)."""
    target = tmp_path / "fresh"
    target.mkdir()
    holder = "name: holder\non: [push]\njobs:\n  proof:\n    runs-on: ubuntu-latest\n"
    put(target, {".github/workflows/holder.yml": holder})
    items, _, _ = init.build_items(target, "2020-01-02")
    router = dict(items)[ROUTER].decode("utf-8")
    kit_text = (KIT_ROOT / ROUTER).read_text(encoding="utf-8")
    assert router == listed(kit_text, ["governance", "proof", "holder"])


def test_init_into_an_empty_target_installs_the_kits_router(tmp_path):
    """REQ-039: brief #285 answer 1 (no project workflow: the kit's file, byte for byte)."""
    target = tmp_path / "empty"
    target.mkdir()
    items, _, _ = init.build_items(target, "2020-01-02")
    assert dict(items)[ROUTER] == (KIT_ROOT / ROUTER).read_bytes()
