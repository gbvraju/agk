"""Every place that names the licence names the AGK Proprietary Licence (REQ-014, brief #1016,
ADR-0433; brief #1419, ADR-0596)."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib

from conftest import KIT_ROOT, make_repo, manifest, run_init

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import check_licence_notice as notice  # noqa: E402
import upgrade  # noqa: E402

NAMING_FILES = [
    "LICENSE",
    "LICENSE-AGK",
    "pyproject.toml",
    ".claude-plugin/plugin.json",
    "README.md",
    "docs/guides/reference.md",
]

LICENCE_LINES = [
    "AGK (Agentic Governance Kit) Proprietary Licence. Copyright (c) 2026 Balavardhi Raju Gangula. "
    "All rights reserved.",
    "1. Ownership. AGK, its source code, scripts, prompts, agents, hooks, workflows, playbooks, "
    "guides and documentation (the Software) are built and owned by Balavardhi Raju Gangula (the "
    "Owner).",
    "2. No licence without a written grant. No right to use, copy, modify, distribute or create "
    "derivative works of the Software is granted, except by a written grant signed by the Owner "
    "that names the repository and the term.",
    "3. One repository only. A grant covers only the repository it names. No user of any "
    "repository may copy or use the Software, in whole or in part, in any other repository, "
    "project, product or organisation without the Owner's prior written permission.",
    "4. End of use. When the grant's term ends or the project is delivered, whichever comes first, "
    "the grantee stops using the Software and removes it from the repository and from every "
    "machine it was installed on, and the history of the repository is cleaned of it as the Owner "
    "and the grantee agree.",
    "5. Confidentiality. The Software is confidential information of the Owner.",
    "6. No warranty. The Software is provided as is, without warranty of any kind, and the Owner "
    "is not liable for any damages arising from its use.",
]


def test_no_file_names_the_apache_licence() -> None:
    """REQ-014: none of the licence files names Apache-2.0 or the Apache License."""
    for rel in NAMING_FILES:
        text = (KIT_ROOT / rel).read_text(encoding="utf-8")
        assert "Apache-2.0" not in text, rel
        assert "Apache License" not in text, rel


def test_metadata_names_the_agk_proprietary_licence() -> None:
    """REQ-014: the package and plugin metadata name LicenseRef-AGK-Proprietary."""
    project = tomllib.loads((KIT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["license"] == "LicenseRef-AGK-Proprietary"
    plugin = json.loads((KIT_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["license"] == "LicenseRef-AGK-Proprietary"


def test_licence_is_the_agk_proprietary_licence_word_for_word() -> None:
    """REQ-014: LICENSE holds the brief's text exactly, one paragraph per line, and nothing else."""
    text = (KIT_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text == "\n\n".join(LICENCE_LINES) + "\n"
    for rel in ("README.md", "docs/guides/reference.md"):
        body = (KIT_ROOT / rel).read_text(encoding="utf-8")
        assert "Licence: proprietary, all rights reserved (see LICENSE)." in body, rel


def test_licence_agk_is_the_licence_then_the_annotation() -> None:
    """REQ-014: LICENSE-AGK starts with LICENSE verbatim and carries the REUSE.toml annotation."""
    licence = (KIT_ROOT / "LICENSE").read_text(encoding="utf-8")
    copy = (KIT_ROOT / "LICENSE-AGK").read_text(encoding="utf-8")
    assert copy.startswith(licence + "\n")
    reuse = tomllib.loads((KIT_ROOT / "REUSE.toml").read_text(encoding="utf-8"))
    for entry in reuse["annotations"]:
        for path in entry["path"]:
            assert path in copy, path
    assert "SPDX-License-Identifier: LicenseRef-AGK-Proprietary" in copy


def test_the_manifest_installs_licence_agk_and_never_license() -> None:
    """REQ-014: init and adopt write LICENSE-AGK; the project's LICENSE is never the kit's."""
    m = manifest()
    assert "LICENSE-AGK" in m["verbatim"]
    assert "LICENSE" not in m["verbatim"]
    assert "LICENSE" not in m["templates"]
    for mode in ("init", "adopt"):
        whole, blocks = upgrade.installed_set(m, mode)
        assert "LICENSE-AGK" in whole, mode
        assert "LICENSE" not in whole and "LICENSE" not in blocks, mode


def test_upgrade_creates_licence_agk_in_a_project_that_lacks_it(tmp_path) -> None:
    """REQ-014: `upgrade` brings LICENSE-AGK to an installed project as a new whole file."""
    new = (KIT_ROOT / "LICENSE-AGK").read_bytes()
    item = upgrade.whole_file(tmp_path, "LICENSE-AGK", new, set(), [])
    assert item.action == "create"
    assert item.content == new


def test_init_installs_licence_agk_and_leaves_the_projects_licence(tmp_path) -> None:
    """REQ-014: `init` writes LICENSE-AGK and never touches the project's own LICENSE."""
    target = make_repo(tmp_path / "target")
    (target / "LICENSE").write_text("the project's own licence\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "licence"], cwd=target, check=True)
    proc = run_init(target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (target / "LICENSE").read_text(encoding="utf-8") == "the project's own licence\n"
    assert (target / "LICENSE-AGK").read_bytes() == (KIT_ROOT / "LICENSE-AGK").read_bytes()


def test_the_kit_repository_passes_its_own_licence_check() -> None:
    """REQ-014: every kit file of this repository is headed or annotated."""
    proc = subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "check_licence_notice.py")],
        cwd=KIT_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout


def test_every_plugin_command_file_is_a_kit_file_with_the_header() -> None:
    """REQ-014 (Q-1419-2): each `skills/<name>/SKILL.md`, a command of the plugin, is one of the
    files the check reads, and carries the header after its front matter."""
    tracked = subprocess.run(
        ["git", "ls-files", "skills"], cwd=KIT_ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    commands = [rel for rel in tracked if rel.endswith("/SKILL.md")]
    assert commands
    files = set(notice.kit_files(KIT_ROOT, tracked))
    for rel in commands:
        assert rel in files, rel
        text = (KIT_ROOT / rel).read_text(encoding="utf-8")
        assert text.startswith("---\n"), rel
        assert notice.has_header(text, "html"), rel


def test_every_workflow_carries_the_header_or_its_proposal_does() -> None:
    """REQ-014 (Q-1419-1): each workflow carries the `#` header, or, until the owner applies it
    with /agk:workflow-apply, its proposal is the workflow with the header and nothing else."""
    proposals = KIT_ROOT / ".agk" / "workflow-proposals"
    for path in sorted((KIT_ROOT / ".github" / "workflows").glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if notice.has_header(text, "hash"):
            continue
        proposal = proposals / path.name
        assert proposal.is_file(), path.name
        assert proposal.read_text(encoding="utf-8") == notice.add_header(text, "hash"), path.name
