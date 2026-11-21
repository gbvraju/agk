"""The bill of materials of a clean-layout project lists the product's own components only (brief
#1667, ADR-0694; SPEC-0054 rule 2, SPEC-0071 rule 2; REQ-078).

With `[kit] layout = "plugin"` the kit's CI tool pins and kit files belong to the plugin: the bill
reads neither, and a missing `config/ci-tools.txt` is no failure. The installed layout reads as
before. Git fixtures in tmp_path, invented package names (example.com); no network.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import sbom  # noqa: E402
from common import CheckError  # noqa: E402
from gates import bom  # noqa: E402

SHA = "a1" * 20
RECORD = (
    "# ADR-0003: Stack options\n\n- Status: Accepted\n\n"
    "1. **Options**:\n   - Option A — web. Parts: {part}, tiny-util 2.1.0 ISC (verify)."
    " Why: invented.\n3. **Chosen**: Option A\n"
)
NODE_LOCK = json.dumps(
    {
        "name": "shop",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "shop", "version": "0.1.0"},
            "node_modules/tiny-util": {"version": "2.1.0", "license": "ISC"},
        },
    }
)
CLEAN = (
    'version = "0.1.0"\nmode = "init"\nexecution = "{execution}"\nreview_mode = "{review}"\n'
    '\n[delivery]\nwork_type = "web-app"\n\n[kit]\nlayout = "plugin"\nplugin_version = "0.1.0"\n'
)
BASE = {
    "pyproject.toml": '[project]\nname = "shop"\nversion = "0.1.0"\ndependencies = []\n',
    ".gitignore": "out/\n",
}
STACKS = {
    "python": {
        "docs/adr/0003-stack-options.md": RECORD.format(part="python 3.12.7 PSF-2.0"),
        "requirements.lock": "tiny-util==2.1.0 \\\n    --hash=sha256:" + "ab" * 32 + "\n",
    },
    "node": {
        "docs/adr/0003-stack-options.md": RECORD.format(part="node 22.11.0 MIT"),
        "package.json": json.dumps({"name": "shop", "private": True}),
        "package-lock.json": NODE_LOCK,
    },
}
SETTINGS = [("local", "solo"), ("hosted", "team")]


def clean(repo, stack: str, execution: str = "local", review: str = "solo", **extra) -> None:
    shutil.copytree(KIT_ROOT / "config" / "playbooks", repo.root / "config" / "playbooks")
    agk = CLEAN.format(execution=execution, review=review)
    repo.commit({**BASE, **STACKS[stack], "agk.toml": agk, **extra})


def refs(root: Path) -> set[str]:
    doc = sbom.build(root, sbom.resolve(root, "HEAD"))
    return {c["bom-ref"] for c in doc["components"]}


@pytest.mark.parametrize("execution,review", SETTINGS)
@pytest.mark.parametrize("stack,kind", [("python", "python"), ("node", "node")])
def test_req078_a_clean_project_lists_only_its_own_lock(repo, stack, kind, execution, review):
    """REQ-078: no `config/ci-tools.txt` is no failure; the kit's pins and files are left out."""
    clean(repo, stack, execution, review)
    assert refs(repo.root) == {f"{kind}:tiny-util@2.1.0"}
    assert bom.applies(repo.root) and bom.check(repo.root, {}) == []


def test_req078_a_clean_project_leaves_out_the_kits_pins_and_files_even_when_present(repo):
    """REQ-078: a stray `config/ci-tools.txt` or `kit/manifest.json` is the plugin's, not listed."""
    stray = {
        "config/ci-tools.txt": "ruff==0.17.4\n",
        "kit/manifest.json": json.dumps({"verbatim": ["scripts/agk/one.py"]}),
        "scripts/agk/one.py": "one\n",
    }
    clean(repo, "python", **stray)
    assert refs(repo.root) == {"python:tiny-util@2.1.0"}


def test_req078_a_clean_project_lists_its_own_workflows(repo):
    """REQ-078 edge case: the product's own workflows stay in its bill."""
    workflow = f"jobs:\n  a:\n    steps:\n      - uses: actions/checkout@{SHA}   # v4.4.0\n"
    clean(repo, "node", **{".github/workflows/ci.yml": workflow})
    assert refs(repo.root) == {f"action:actions/checkout@{SHA}:v4.4.0", "node:tiny-util@2.1.0"}


def test_req078_a_clean_project_with_no_lock_lists_nothing_and_the_gate_does_not_run(repo):
    """REQ-078 edge case: no lock, no component, and the bom step is not run, as today."""
    clean(repo, "node")
    repo.commit({"package-lock.json": None})
    assert refs(repo.root) == set()
    assert not bom.applies(repo.root)


def test_req078_another_layout_is_refused_naming_the_setting(repo):
    """REQ-078: a `[kit] layout` that is neither value is refused naming `layout`, not the value."""
    clean(repo, "python")
    text = (repo.root / "agk.toml").read_text(encoding="utf-8")
    repo.commit({"agk.toml": text.replace('layout = "plugin"', 'layout = "sideways-x"')})
    with pytest.raises(CheckError) as found:
        refs(repo.root)
    assert "(setting: layout)" in str(found.value) and "sideways-x" not in str(found.value)


def test_req078_the_personal_table_reads_the_same(repo):
    """REQ-078: a `[personal]` table does not change what a clean project's bill reads."""
    clean(repo, "python")
    text = (repo.root / "agk.toml").read_text(encoding="utf-8")
    repo.commit({"agk.toml": text + '\n[personal]\nforge = "files"\n'})
    assert refs(repo.root) == {"python:tiny-util@2.1.0"}


def test_req078_the_installed_layout_reads_as_before(repo):
    """REQ-078 edge case: `layout = "installed"` gives the same components as no `[kit]` table,
    and the installed bill still needs `config/ci-tools.txt`."""
    files = {
        **BASE,
        "agk.toml": 'version = "0.1.0"\n',
        "config/ci-tools.txt": "ruff==0.17.4\n",
    }
    repo.commit(files)
    before = sbom.build(repo.root, sbom.resolve(repo.root, "HEAD"))["components"]
    assert {c["bom-ref"] for c in before} == {"ci-tool:ruff@0.17.4"}
    repo.commit({"agk.toml": 'version = "0.1.0"\n\n[kit]\nlayout = "installed"\n'})
    after = sbom.build(repo.root, sbom.resolve(repo.root, "HEAD"))["components"]
    assert json.dumps(after, sort_keys=True) == json.dumps(before, sort_keys=True)
    repo.commit({"config/ci-tools.txt": None})
    with pytest.raises(CheckError, match="config/ci-tools.txt cannot be read"):
        refs(repo.root)
