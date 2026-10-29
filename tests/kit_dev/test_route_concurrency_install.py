"""Brief 309 answer 3: init.py and upgrade.py write the router's per-pull-request concurrency group.

The installed `agk-route.yml` is the kit's file with only its `workflow_run` list set from the
project (brief #285), so a project gets the new group and keeps its own `workflows:` names. The
project's workflow and check names here are invented."""

from __future__ import annotations

import sys

from conftest import KIT_ROOT

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import common  # noqa: E402
import init  # noqa: E402
import upgrade  # noqa: E402

ROUTER = KIT_ROOT / ".github" / "workflows" / "agk-route.yml"
GROUP = (
    "  group: agk-route-${{ github.event.pull_request.number || github.event.issue.number"
    " || github.event.workflow_run.head_sha || github.ref }}"
)
PROJECT = "name: lint-suite\non: [pull_request]\njobs:\n  lint-suite:\n    runs-on: ubuntu-latest\n"
REQUIRED = 'required_checks = ["proof", "governance", "lint-suite"]\n'


def project(tmp_path):
    root = tmp_path / "proj"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "lint.yml").write_text(PROJECT, encoding="utf-8")
    (root / "agk.toml").write_text(REQUIRED, encoding="utf-8")
    return root


def test_the_kit_router_has_the_per_pull_request_group():
    assert GROUP in ROUTER.read_text(encoding="utf-8").splitlines()


def test_init_writes_the_group_and_the_projects_workflows(tmp_path):
    root = project(tmp_path)
    kit = init.kit_bytes(ROUTER)
    text = init.router_bytes(root, kit, REQUIRED.encode()).decode("utf-8")
    assert GROUP in text.splitlines()
    assert "lint-suite" in common.router_names(text)


def test_upgrade_replaces_the_single_group_and_keeps_the_projects_names(tmp_path):
    root = project(tmp_path)
    kit_text = ROUTER.read_text(encoding="utf-8")
    released = kit_text.replace(GROUP, "  group: agk-route")
    assert released != kit_text
    names = [*common.router_names(kit_text), "lint-suite", "hand-added"]
    installed = common.with_router_names(released, names)
    path = root / ".github" / "workflows" / "agk-route.yml"
    path.write_text(installed, encoding="utf-8")
    base = common.router_names(kit_text)
    old = {upgrade.digest(common.with_router_names(released, base).encode("utf-8"))}
    item = upgrade.router_file(root, kit_text.encode("utf-8"), old, [], ["proof", "lint-suite"])
    assert item.action == "replace", item
    written = item.content.decode("utf-8")
    assert GROUP in written.splitlines() and "  group: agk-route\n" not in written
    assert common.router_names(written) == names
