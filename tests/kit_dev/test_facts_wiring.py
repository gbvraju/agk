"""Kit-only tests of the facts engine wiring: schema, validator, manifest (SPEC-0009)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

from conftest import KIT_ROOT, assert_lean, clean_env, kit_fixture_files, manifest
from jsonschema_lite import KEYWORDS, errors

SCHEMA = KIT_ROOT / "kit" / "facts-schema.json"
FIXTURES = KIT_ROOT / "tests" / "kit" / "fixtures" / "facts"
INSTALLED = {"scripts/agk/facts.py", "tests/kit/test_facts.py"}


def schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def keywords_used(node) -> set[str]:
    """Every schema keyword in the file, outside the property names of `properties`."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            if key == "properties":
                for sub in value.values():
                    found |= keywords_used(sub)
            elif key in ("items", "additionalProperties") or key == "oneOf":
                for sub in value if isinstance(value, list) else [value]:
                    found |= keywords_used(sub)
    return found


def test_ac2_the_files_are_in_the_manifest_and_the_schema_is_kit_only():
    """REQ-018 AC2: rules 19 and 21."""
    m = manifest()
    assert_lean(INSTALLED)
    fixtures = kit_fixture_files("tests/kit/fixtures/facts")
    assert len(fixtures) > 100 and not fixtures & set(m["verbatim"])
    assert "kit/facts-schema.json" not in m["verbatim"] and SCHEMA.is_file()
    assert "tests/kit_dev/test_facts_wiring.py" not in m["verbatim"]


def test_ac2_the_schema_is_hand_written_not_generated():
    """REQ-018 AC2: rule 19. No script writes it and no test regenerates it."""
    for path in (KIT_ROOT / "scripts" / "agk").glob("*.py"):
        assert "facts-schema" not in path.read_text(encoding="utf-8"), path.name
    for path in (KIT_ROOT / "tests").rglob("test_*.py"):
        if path.name != "test_facts_wiring.py":
            assert "facts-schema" not in path.read_text(encoding="utf-8"), path.name


def test_ac2_the_schema_uses_only_the_keywords_the_validator_implements():
    """REQ-018 AC2: rule 19 (type, required, properties, additionalProperties, items, enum, ...)."""
    used = keywords_used(schema()) - {"$schema", "title", "description"}
    assert used <= KEYWORDS
    assert KEYWORDS == {
        "type",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "pattern",
        "oneOf",
    }


def test_ac2_the_validator_fails_on_a_keyword_it_does_not_implement():
    """REQ-018 AC2: rule 19."""
    try:
        errors(1, {"type": "integer", "minimum": 0})
    except ValueError as exc:
        assert "minimum" in str(exc)
    else:
        raise AssertionError("an unimplemented keyword passed")


def test_ac2_the_schema_const_equals_the_documents_schema_number():
    """REQ-018 AC2: rule 19."""
    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import facts

    assert schema()["properties"]["schema"] == {"const": facts.SCHEMA}


def test_ac2_every_golden_validates_and_a_broken_document_does_not():
    """REQ-018 AC2: rule 19."""
    goldens = sorted(FIXTURES.glob("*/facts.json"))
    assert len(goldens) >= 11
    for path in goldens:
        assert errors(json.loads(path.read_text(encoding="utf-8")), schema()) == [], (
            path.parent.name
        )
    doc = json.loads((FIXTURES / "ok" / "facts.json").read_text(encoding="utf-8"))
    assert errors({k: v for k, v in doc.items() if k != "drift"}, schema())
    assert errors({**doc, "extra": 1}, schema())
    assert errors({**doc, "schema": 2}, schema())
    assert errors({**doc, "dirty": "maybe"}, schema())
    assert errors({**doc, "pull_requests": [{"number": 1}]}, schema())


def run_here(tmp_path, *args: str) -> subprocess.CompletedProcess:
    env = clean_env()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    link = bin_dir / "git"
    if not link.exists():
        link.symlink_to(shutil.which("git"))
    env["PATH"] = str(bin_dir)
    return subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "facts.py"), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=KIT_ROOT,
    )


def test_ac2_the_document_for_this_repository_at_head_validates(tmp_path):
    """REQ-018 AC2: rule 23 (offline: no `gh` on PATH, so the GitHub sections are unknown)."""
    proc = run_here(tmp_path, "--repo", "example-org/example-repo", ".")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert errors(doc, schema()) == []
    assert doc["pull_requests"] == "unknown" and doc["issues"] == "unknown"
    assert doc["schema"] == 1 and len(doc["requirements"]) >= 20


def test_ac1_the_go_style_golden_stands_in_for_the_pilot_and_validates():
    """REQ-016 AC1: rule 23 (a Go module with `*_test.go` and `.` as the test directory)."""
    doc = json.loads((FIXTURES / "go-style" / "facts.json").read_text(encoding="utf-8"))
    assert doc["config"]["test_patterns"] == ["*_test.go"] and doc["config"]["test_dirs"] == ["."]
    assert [m["file"] for m in doc["markers"]] == ["pkg/bar_test.go", "pkg/foo_test.go"]
    assert errors(doc, schema()) == []


def test_ac2_the_installed_script_runs_without_the_kit_checkout(installed):
    """REQ-018 AC2: rule 1. The installed copy runs on its own repository."""
    assert (installed / "scripts" / "agk" / "facts.py").is_file()
    env = clean_env()
    env["PATH"] = os.path.dirname(shutil.which("git"))
    proc = subprocess.run(
        [sys.executable, "scripts/agk/facts.py", "--today", "2026-10-14", "--repo", "o/r"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["today"] == "2026-10-14" and doc["repo"] == "o/r" and doc["config"] != "unknown"
    assert {r["id"] for r in doc["requirements"]} >= set()
    assert doc["pull_requests"] == "unknown" or isinstance(doc["pull_requests"], list)


def test_ac2_kit_version_is_at_least_0_12_0():
    """REQ-018 AC2: rule 21 (an installed script is new: the minor version is bumped)."""
    version = tuple(int(part) for part in manifest()["kit_version"].split("."))
    assert version >= (0, 12, 0)
