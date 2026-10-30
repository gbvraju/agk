"""Adopt from a release (brief #263 build c, ADR-0160's residual; ADR-0200).

`init.py` refuses kit files that are not those of the release it stamps (item 8, ADR-0160), but
`adopt.py` stamped `kit_version` on whatever files the plugin held. Now adopt runs the same check
(`init.release_problem`: the release row of `kit_version` in `kit/hashes.json`, CRLF read as LF)
and refuses before any write, naming the path class and the remedy; `--unreleased` installs the
checkout as it is, with a notice, for the kit's own tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import KIT_ROOT, clean_env, manifest
from test_adopt import make_existing
from test_install_from_release import kit_copy

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import kit_hashes  # noqa: E402


def adopt(kit: Path, target: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(kit / "scripts" / "agk" / "adopt.py"), str(target), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def unreleased(kit: Path) -> Path:
    common = kit / "scripts" / "agk" / "common.py"
    common.write_text(common.read_text(encoding="utf-8") + "# unreleased\n", encoding="utf-8")
    return kit


def files_of(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def test_a_kit_at_its_release_adopts(tmp_path):
    """REQ-039: brief #263 build (c) (the files are those of the release row; adopt installs)."""
    proc = adopt(kit_copy(tmp_path / "kit"), make_existing(tmp_path / "p"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "installed " in proc.stdout and "notice: --unreleased" not in proc.stdout


def test_a_windows_cache_at_the_release_adopts_with_lf(tmp_path):
    """REQ-039: brief #263 build (c) with item 7 (a CRLF plugin cache at the right release)."""
    target = make_existing(tmp_path / "p")
    proc = adopt(kit_copy(tmp_path / "kit", crlf=True), target)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert b"\r\n" not in (target / "scripts" / "agk" / "common.py").read_bytes()


@pytest.mark.parametrize("dry", [[], ["--dry-run"]])
def test_a_kit_between_releases_is_refused_before_any_write(tmp_path, dry):
    """REQ-039: brief #263 build (c): the refusal names the release, the path class and the
    remedy (the plugin's ref), and the target is byte for byte as it was."""
    target = make_existing(tmp_path / "p")
    before = files_of(target)
    proc = adopt(unreleased(kit_copy(tmp_path / "kit")), target, *dry)
    version = manifest()["kit_version"]
    assert proc.returncode == 1, proc.stdout
    first = proc.stdout.splitlines()[0]
    assert first.startswith(f"refused: the plugin's kit files are not those of release {version}")
    assert "(path class kit/hashes.json)" in first and "nothing was written" in first
    assert "`ref` of the agk marketplace entry" in proc.stdout
    assert '"extraKnownMarketplaces"' in proc.stdout
    assert files_of(target) == before


def test_a_kit_whose_version_has_no_release_row_is_refused(tmp_path):
    """REQ-039: brief #263 build (c): no row for `kit_version` is not a release either."""
    kit = kit_copy(tmp_path / "kit")
    table = json.loads((kit / "kit" / "hashes.json").read_text(encoding="utf-8"))
    del table["releases"][manifest()["kit_version"]]
    (kit / "kit" / "hashes.json").write_text(kit_hashes.dump(table), encoding="utf-8")
    proc = adopt(kit, make_existing(tmp_path / "p"))
    assert proc.returncode == 1 and "are not those of release" in proc.stdout


def test_an_unreleased_adopt_template_is_refused_too(tmp_path):
    """REQ-039: brief #263 build (c): a template only adopt renders is part of the check."""
    kit = kit_copy(tmp_path / "kit")
    src = manifest()["adopt"]["templates"]["config/protected-paths.txt"]
    path = kit / src
    path.write_text(path.read_text(encoding="utf-8") + "extra/\n", encoding="utf-8")
    proc = adopt(kit, make_existing(tmp_path / "p"), "--dry-run")
    assert proc.returncode == 1 and "are not those of release" in proc.stdout


def test_unreleased_adopts_the_files_as_they_are_and_says_so(tmp_path):
    """REQ-039: brief #263 build (c): the kit's own tests adopt the checkout between releases."""
    target = make_existing(tmp_path / "p")
    proc = adopt(unreleased(kit_copy(tmp_path / "kit")), target, "--unreleased")
    assert proc.returncode == 0, proc.stdout
    assert "notice: --unreleased: the kit files are not those of release" in proc.stdout
    assert (
        (target / "scripts" / "agk" / "common.py")
        .read_text(encoding="utf-8")
        .endswith("# unreleased\n")
    )


def test_the_usage_names_the_new_option(tmp_path):
    """REQ-039: brief #263 build (c): an unknown option is still a usage error."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "adopt.py"), "--bogus"],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 2 and "--unreleased" in proc.stderr


def init(kit: Path, target: Path, *args: str) -> subprocess.CompletedProcess:
    target.mkdir(parents=True, exist_ok=True)
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(kit / "scripts" / "agk" / "init.py"), str(target), *args],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


@pytest.mark.parametrize("installer", ["adopt", "init"])
@pytest.mark.parametrize("source", sorted(set(manifest()["adopt"]["block_sources"].values())))
def test_an_unreleased_block_source_is_refused_by_both_installers(tmp_path, installer, source):
    """REQ-039: brief #263 build (c) (verdict on 7c7e85c, item 1): a file written as a marked
    block (`kit/templates/gitignore`, `kit/templates/gitattributes`) is compared with the release
    row's `blocks`, as `kit_hashes.snapshot_of` hashes it, by init and adopt alike."""
    kit = kit_copy(tmp_path / "kit")
    path = kit / source
    path.write_text(path.read_text(encoding="utf-8") + "unreleased-entry/\n", encoding="utf-8")
    if installer == "adopt":
        proc = adopt(kit, make_existing(tmp_path / "p"), "--dry-run")
    else:
        proc = init(kit, tmp_path / "t", "--dry-run")
    assert proc.returncode == 1, proc.stdout
    assert "are not those of release" in proc.stdout


@pytest.mark.parametrize("installer", ["adopt", "init"])
def test_a_block_source_at_the_release_with_crlf_still_installs(tmp_path, installer):
    """REQ-039: brief #263 build (c) with item 7: a CRLF block source of the release passes."""
    kit = kit_copy(tmp_path / "kit")
    for source in set(manifest()["adopt"]["block_sources"].values()):
        path = kit / source
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    if installer == "adopt":
        proc = adopt(kit, make_existing(tmp_path / "p"), "--dry-run")
    else:
        proc = init(kit, tmp_path / "t", "--dry-run")
    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize("data", [b"", b"a", b"a\n", b"a\n\n\n", b"\n"])
def test_init_hashes_a_block_as_kit_hashes_does(data):
    """REQ-039: brief #263 build (c): `init.block_text` equals `kit_hashes.normalized`, which init
    cannot import (it imports no module that runs a process)."""
    import init

    assert init.block_text(data) == kit_hashes.normalized(data)
