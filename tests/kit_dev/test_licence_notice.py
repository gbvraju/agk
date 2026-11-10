"""The licence is named as proprietary, all rights reserved, in every place that names it (REQ-014, brief #1016, ADR-0433)."""

from __future__ import annotations

import json
import tomllib

from conftest import KIT_ROOT

NAMING_FILES = [
    "LICENSE",
    "pyproject.toml",
    ".claude-plugin/plugin.json",
    "README.md",
    "docs/guides/reference.md",
]


def test_no_file_names_the_apache_licence() -> None:
    """REQ-014: none of the five files that name the licence names Apache-2.0 or the Apache License."""
    for rel in NAMING_FILES:
        text = (KIT_ROOT / rel).read_text(encoding="utf-8")
        assert "Apache-2.0" not in text, rel
        assert "Apache License" not in text, rel


def test_metadata_names_the_proprietary_licence() -> None:
    """REQ-014: the package and plugin metadata name LicenseRef-Proprietary."""
    project = tomllib.loads((KIT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["license"] == "LicenseRef-Proprietary"
    plugin = json.loads((KIT_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["license"] == "LicenseRef-Proprietary"


def test_licence_is_the_all_rights_reserved_notice() -> None:
    """REQ-014: LICENSE holds the all-rights-reserved notice and nothing else."""
    text = (KIT_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("Copyright (c) 2026 Balavardhi Raju Gangula. All rights reserved.\n\n")
    assert "No licence is granted to use, copy, modify or distribute them" in text
    for rel in ("README.md", "docs/guides/reference.md"):
        body = (KIT_ROOT / rel).read_text(encoding="utf-8")
        assert "Licence: proprietary, all rights reserved (see LICENSE)." in body, rel
