"""Brief #269 (REQ-039, ADR-0164): the doctor compares only the kit's block of `.gitignore`.

Lines outside the block belong to the project: never a difference, reported once as
"project lines kept: n". The ignore lines are invented.
"""

from __future__ import annotations

import json
from pathlib import Path

from test_doctor import checks_of, doctor, prepare

BLOCK = "# >>> agk\n*.pyc\n# <<< agk\n"


def init_target(tmp_path: Path, gitignore: str, extendable: bool = True) -> dict[str, Path]:
    dirs = prepare("ok", tmp_path)
    kit, root = dirs["kit"], dirs["root"]
    manifest: dict = {
        "kit_version": "9.9.9",
        "verbatim": [".gitignore", "a.txt"],
        "templates": {},
        "rendered": [],
        "adopt": {
            "skip": [],
            "blocks": {".gitignore": "hash"},
            "block_sources": {".gitignore": "kit/templates/gitignore"},
            "templates": {},
        },
    }
    if extendable:
        manifest["extendable"] = {".gitignore": "hash"}
    (kit / "kit" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kit / "kit" / "templates").mkdir(parents=True, exist_ok=True)
    (kit / "kit" / "templates" / "gitignore").write_text("*.pyc\n", encoding="utf-8")
    (kit / ".gitignore").write_text(BLOCK, encoding="utf-8")
    (kit / "a.txt").write_text("a\n", encoding="utf-8")
    (root / ".gitignore").write_text(gitignore, encoding="utf-8")
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "agk.toml").write_text('mode = "init"\nversion = "9.9.9"\n', encoding="utf-8")
    return dirs


def report_of(dirs: dict[str, Path]) -> dict[str, dict]:
    proc = doctor(
        "--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json", str(dirs["root"])
    )
    return checks_of(proc.stdout)


def test_init_project_lines_outside_the_block_are_not_a_difference(tmp_path):
    """REQ-039: brief #269 answer 2."""
    report = report_of(init_target(tmp_path, "# mine\n" + BLOCK + "private-src/\n"))
    assert report["vendored-differs"]["status"] == "ok"
    assert report["vendored-differs"]["message"].endswith(" (.gitignore: project lines kept: 2)")
    assert report["vendored-missing"]["status"] == "ok"


def test_init_the_kit_file_alone_reports_no_project_lines(tmp_path):
    """REQ-039: brief #269 answer 2 (nothing to report when there is no project line)."""
    report = report_of(init_target(tmp_path, BLOCK))
    assert report["vendored-differs"]["status"] == "ok"
    assert "project lines" not in report["vendored-differs"].get("message", "")


def test_init_edited_block_missing_and_broken_markers_differ(tmp_path):
    """REQ-039: brief #269 answers 2 and 3 (a file without markers waits for the upgrade)."""
    for i, text in enumerate(
        [
            "# >>> agk\n*.pyc\nprivate-src/\n# <<< agk\n",
            "*.pyc\nprivate-src/\n",
            "*.pyc\n",
            "# >>> agk\n*.pyc\n",
            BLOCK * 2,
        ]
    ):
        report = report_of(init_target(tmp_path / str(i), text))
        assert report["vendored-differs"]["status"] == "fail", text
        assert ".gitignore" in report["vendored-differs"]["message"], text


def test_init_without_the_extendable_key_compares_the_whole_file(tmp_path):
    """REQ-039: brief #269 answer 4 (only a file the manifest names is extendable)."""
    report = report_of(init_target(tmp_path, BLOCK + "private-src/\n", extendable=False))
    assert report["vendored-differs"]["status"] == "fail"
    report = report_of(init_target(tmp_path / "same", BLOCK, extendable=False))
    assert report["vendored-differs"]["status"] == "ok"
