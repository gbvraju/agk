"""Install from a release (brief #263 build c, item 8; ADR-0160).

The plugin follows the default branch, so `/agk:init` between two releases installed unreleased
files and stamped the last release's version, and an upgrade then read them as unknown. Now init
compares the kit files it would install with the release row of `kit_version` in
`kit/hashes.json` (ignoring CRLF and LF, item 7) and refuses when any differs, naming the setting
that pins the plugin's ref. `--unreleased` installs them as they are, for the kit's own tests.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, manifest

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import kit_hashes  # noqa: E402


def kit_copy(dest: Path, crlf: bool = False) -> Path:
    """A copy of the kit whose table's row for `kit_version` lists exactly its own files."""
    shutil.copytree(
        KIT_ROOT / "scripts" / "agk",
        dest / "scripts" / "agk",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copytree(KIT_ROOT / "kit", dest / "kit")
    for rel in manifest()["verbatim"] + manifest().get("experimental", []):
        if not (dest / rel).exists():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(KIT_ROOT / rel, dest / rel)
    man = manifest()
    snap = kit_hashes.snapshot_of(
        man, lambda p: (dest / p).read_bytes() if (dest / p).is_file() else None
    )
    table = json.loads((dest / "kit" / "hashes.json").read_text(encoding="utf-8"))
    table["releases"][man["kit_version"]] = {
        "commits": [],
        **{name: {p: [d] for p, d in snap[name].items()} for name in snap},
    }
    (dest / "kit" / "hashes.json").write_text(kit_hashes.dump(table), encoding="utf-8")
    if crlf:
        for rel in man["verbatim"]:
            path = dest / rel
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    return dest


def init(kit: Path, target: Path, *args: str) -> subprocess.CompletedProcess:
    target.mkdir(parents=True, exist_ok=True)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(kit / "scripts" / "agk" / "init.py"), str(target), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def test_a_kit_at_its_release_installs(tmp_path):
    """Brief #263 item 8 (REQ-039): the files are those of the release row; init installs."""
    proc = init(kit_copy(tmp_path / "kit"), tmp_path / "target")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "installed " in proc.stdout


def test_a_windows_cache_at_the_release_installs(tmp_path):
    """Brief #263 items 7 and 8 (REQ-039): a CRLF plugin cache at the right release passes."""
    proc = init(kit_copy(tmp_path / "kit", crlf=True), tmp_path / "target")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    target = tmp_path / "target"
    assert b"\r\n" not in (target / "scripts" / "agk" / "common.py").read_bytes()


@pytest.mark.parametrize("dry", [[], ["--dry-run"]])
def test_a_kit_between_releases_is_refused_and_names_the_ref_setting(tmp_path, dry):
    """Brief #263 item 8 (REQ-039): one unreleased file; nothing is written; the refusal names the
    release and says where the plugin's ref is set, as the dry run prints it."""
    kit = kit_copy(tmp_path / "kit")
    common = kit / "scripts" / "agk" / "common.py"
    common.write_text(common.read_text(encoding="utf-8") + "# unreleased\n", encoding="utf-8")
    proc = init(kit, tmp_path / "target", *dry)
    version = manifest()["kit_version"]
    assert proc.returncode == 1, proc.stdout
    assert f"refused: the plugin's kit files are not those of release {version}" in proc.stdout
    assert "`ref` of the agk marketplace entry" in proc.stdout
    assert '"extraKnownMarketplaces"' in proc.stdout  # the entry, as the dry run prints it
    assert list((tmp_path / "target").iterdir()) == []


def test_a_kit_whose_version_has_no_release_row_is_refused(tmp_path):
    """Brief #263 item 8: no row for `kit_version` is not a release either."""
    kit = kit_copy(tmp_path / "kit")
    table = json.loads((kit / "kit" / "hashes.json").read_text(encoding="utf-8"))
    del table["releases"][manifest()["kit_version"]]
    (kit / "kit" / "hashes.json").write_text(kit_hashes.dump(table), encoding="utf-8")
    proc = init(kit, tmp_path / "target")
    assert proc.returncode == 1 and "are not those of release" in proc.stdout


def test_unreleased_installs_the_files_as_they_are_and_says_so(tmp_path):
    """Brief #263 item 8: the kit's own tests install the checkout between releases."""
    kit = kit_copy(tmp_path / "kit")
    common = kit / "scripts" / "agk" / "common.py"
    common.write_text(common.read_text(encoding="utf-8") + "# unreleased\n", encoding="utf-8")
    proc = init(kit, tmp_path / "target", "--unreleased")
    assert proc.returncode == 0, proc.stdout
    assert "notice: --unreleased: the kit files are not those of release" in proc.stdout
