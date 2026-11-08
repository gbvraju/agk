"""Kit-only tests of the reflow run and the screenshots of a version (SPEC-0037 rule 8, brief #461).

`design.py screenshots --version v<n>` opens each page of the version at each breakpoint of the
standard, in light and dark, with a headless browser found on PATH: it writes one screenshot per
page, breakpoint and mode and `screenshots/reflow.json` (`ok` or `sideways`); without a browser it
says so, writes every entry as `not run` and succeeds. `design_render.pixel_share` reads two PNGs
with the standard library. A fake browser stands in for a real one: no network, no model.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env
from design_fixture import VERSION, fake_browser, frozen_version, png

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import design_render  # noqa: E402
import design_standard  # noqa: E402

SCRIPT = KIT_ROOT / "scripts" / "agk" / "design.py"
PAGES = ("home--default.html", "home--empty.html")
WHITE, BLACK = (255, 255, 255), (0, 0, 0)


def design(root, *args, path):
    env = clean_env()
    env["PATH"] = path
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=env,
    )


def empty_path(tmp_path):
    empty = tmp_path.parent / (tmp_path.name + "-empty")
    empty.mkdir()
    return str(empty)


def entries(folder):
    return json.loads((folder / "screenshots" / "reflow.json").read_text(encoding="utf-8"))


def test_ac6_without_a_browser_every_reflow_entry_reads_not_run(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 8 (no browser: says so, `not run` never passed, exit 0)."""
    folder = frozen_version(tmp_path)
    proc = design(tmp_path, "screenshots", "--version", VERSION, path=empty_path(tmp_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "design: no headless browser found; reflow not run\n"
    data = entries(folder)
    assert data["version"] == VERSION
    want = [
        (page, width, mode)
        for page in PAGES
        for width in design_standard.BREAKPOINTS
        for mode in ("light", "dark")
    ]
    assert [(e["page"], e["width"], e["mode"]) for e in data["entries"]] == want
    assert {e["reflow"] for e in data["entries"]} == {"not run"}
    assert sorted(p.name for p in (folder / "screenshots").iterdir()) == ["reflow.json"]


def test_ac6_a_browser_writes_every_screenshot_and_measures_a_sideways_page(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 8 (one picture per page, breakpoint and mode; sideways)."""
    folder = frozen_version(tmp_path)
    shot = png(tmp_path.parent / (tmp_path.name + "-shot.png"), [[WHITE]])
    log = fake_browser(tmp_path.parent / (tmp_path.name + "-bin"), shot)
    path = f"{log.parent}{os.pathsep}{os.environ['PATH']}"
    proc = design(tmp_path, "screenshots", "--version", VERSION, path=path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = entries(folder)["entries"]
    assert len(data) == len(PAGES) * len(design_standard.BREAKPOINTS) * 2
    for e in data:
        assert e["reflow"] == ("sideways" if e["width"] == 360 else "ok"), e
    names = sorted(p.name for p in (folder / "screenshots").iterdir() if p.suffix == ".png")
    want = sorted(
        f"{page[:-5]}-{width}-{mode}.png"
        for page in PAGES
        for width in design_standard.BREAKPOINTS
        for mode in ("light", "dark")
    )
    assert names == want
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls and all("--headless" in c and "MAP * ~NOTFOUND" in c for c in calls)
    assert all("index.html" not in c for c in calls)  # the flows page is not a screen
    assert "sideways" in proc.stdout and "360" in proc.stdout


@pytest.mark.parametrize("version", ["v0", "x1", "v2"])
def test_ac6_screenshots_of_a_version_that_does_not_exist_are_refused(tmp_path, version):
    """REQ-044 AC6: SPEC-0037 rule 8 (only a version folder, named by the rule, never a value)."""
    frozen_version(tmp_path)
    proc = design(tmp_path, "screenshots", "--version", version, path=empty_path(tmp_path))
    assert proc.returncode == 1
    assert proc.stdout.startswith("FAIL design: rule 8:") and version not in proc.stdout


def test_ac6_folder_and_version_together_are_a_usage_error(tmp_path):
    """REQ-044 AC6: the `--folder` of mockups is unchanged beside the new `--version`."""
    frozen_version(tmp_path)
    proc = design(
        tmp_path, "screenshots", "--version", VERSION, "--folder", "x", path=empty_path(tmp_path)
    )
    assert proc.returncode == 2 and "usage:" in proc.stderr


def test_ac6_pixel_share_counts_the_share_of_differing_pixels(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 11 (the pixel diff, decoded with the standard library)."""
    rows = [[WHITE, BLACK, (10, 20, 30)], [(1, 2, 3), WHITE, BLACK]]
    first = png(tmp_path / "a.png", rows)
    same = png(tmp_path / "b.png", rows, filters=[1, 2])  # other filters, same pixels
    changed = png(tmp_path / "c.png", [[WHITE, BLACK, (10, 20, 31)], [(1, 2, 3), BLACK, BLACK]])
    other_size = png(tmp_path / "d.png", [[WHITE, BLACK]])
    assert design_render.pixel_share(first, same) == 0.0
    assert design_render.pixel_share(first, changed) == pytest.approx(2 / 6)
    assert design_render.pixel_share(first, other_size) == 1.0


def test_ac6_a_file_that_is_not_a_png_is_refused_naming_the_rule(tmp_path):
    """REQ-044 AC6: a decode error names the rule, never the file's bytes."""
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not a picture")
    good = png(tmp_path / "good.png", [[WHITE]])
    with pytest.raises(Exception, match="rule 11: a screenshot is not a PNG"):
        design_render.pixel_share(bad, good)


def test_ac6_the_design_text_says_screenshots_are_written_only_by_the_command():
    """REQ-044 AC6: the skill and `design.py` say who writes `screenshots/`."""
    doc = SCRIPT.read_text(encoding="utf-8")
    skill = (KIT_ROOT / "skills" / "design" / "SKILL.md").read_text(encoding="utf-8")
    for text in (doc, skill):
        assert "written only by `design.py screenshots`, never by hand" in text
        assert "screenshots --version" in " ".join(text.split())
