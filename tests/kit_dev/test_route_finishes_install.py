"""Brief 302 (REQ-039, ADR-0178): init.py and upgrade.py write the router that wakes on a merge.

The installed `agk-route.yml` is the kit's file with only its `workflow_run` list set from the
project (brief #285), so a project gets `closed` in the `pull_request` types and the job's
merge-only condition, and keeps its own `workflows:` names. Names here are invented."""

from __future__ import annotations

import sys

from conftest import KIT_ROOT

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import common  # noqa: E402
import init  # noqa: E402
import upgrade  # noqa: E402

ROUTER = KIT_ROOT / ".github" / "workflows" / "agk-route.yml"
TYPES = "    types: [opened, synchronize, reopened, closed]"  # brief #369 dropped `edited`
RELEASED = "    types: [opened, synchronize, reopened, edited]"
MERGED = (
    "(github.event_name != 'pull_request' || github.event.action != 'closed' "
    "|| github.event.pull_request.merged == true)"
)
PROJECT = "name: lint-suite\non: [pull_request]\njobs:\n  lint-suite:\n    runs-on: ubuntu-latest\n"
REQUIRED = 'required_checks = ["proof", "governance", "lint-suite"]\n'


def project(tmp_path):
    root = tmp_path / "proj"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "lint.yml").write_text(PROJECT, encoding="utf-8")
    (root / "agk.toml").write_text(REQUIRED, encoding="utf-8")
    return root


def released_text(kit_text: str) -> str:
    """The kit's router as the release before this brief shipped it."""
    out = kit_text.replace(TYPES, RELEASED).replace(f"{MERGED} && ", "")
    assert out != kit_text and MERGED not in out
    return out


def test_the_kit_router_wakes_on_closed_and_runs_for_a_merge_only():
    text = ROUTER.read_text(encoding="utf-8")
    assert TYPES in text.splitlines() and MERGED in text


def test_init_writes_closed_and_the_projects_workflows(tmp_path):
    root = project(tmp_path)
    text = init.router_bytes(root, init.kit_bytes(ROUTER), REQUIRED.encode()).decode("utf-8")
    assert TYPES in text.splitlines() and MERGED in text
    assert "lint-suite" in common.router_names(text)


def test_upgrade_replaces_the_released_router_and_keeps_the_projects_names(tmp_path):
    root = project(tmp_path)
    kit_text = ROUTER.read_text(encoding="utf-8")
    released = released_text(kit_text)
    names = [*common.router_names(kit_text), "lint-suite", "hand-added"]
    path = root / ".github" / "workflows" / "agk-route.yml"
    path.write_text(common.with_router_names(released, names), encoding="utf-8")
    base = common.router_names(kit_text)
    old = {upgrade.digest(common.with_router_names(released, base).encode("utf-8"))}
    item = upgrade.router_file(root, kit_text.encode("utf-8"), old, [], ["proof", "lint-suite"])
    assert item.action == "replace", item
    written = item.content.decode("utf-8")
    assert TYPES in written.splitlines() and MERGED in written
    assert common.router_names(written) == names
