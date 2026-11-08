"""Kit-only tests of the comparison of a build with its signed-off version (SPEC-0037 rule 11,
brief #461).

`design_compare.py --version v<n> --screens "<screen>/<state>, ..."` renders each named screen and
state with the project's `render` command of `[design]`, compares it with the frozen page in
structure, tokens and (with a browser) pixels, prints one line per screen and state, and exits 0
on drift: it fails nothing. An invented frozen version and a fake `render` command under
`tmp_path` stand in for a project; no network, no model.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env
from design_fixture import FROZEN, VERSION, fake_browser, frozen_version, png

SCRIPT = KIT_ROOT / "scripts" / "agk" / "design_compare.py"
RENDER = """import os, pathlib, shutil
root = pathlib.Path(__file__).parent
name = os.environ["AGK_DESIGN_SCREEN"] + "--" + os.environ["AGK_DESIGN_STATE"] + ".html"
shutil.copy(root / "built" / name, pathlib.Path(os.environ["AGK_DESIGN_OUT"]) / name)
"""
# The built page as a project renders it: the prototype's own state bar, demo bar, flows link and
# runtime are not part of it, and its structure and tokens are those of the frozen page.
BUILT = """<!doctype html>
<html lang="en"><head><title>Home</title>
<style>.lead {{ color: var({token}); }}</style></head>
<body>
<header><p>Example Org</p></header>
<main>
<h1>{heading}</h1>
<h2>Recent orders</h2>
<form><label for="q">Search orders</label><input id="q" type="search"><button>Find</button></form>
<a href="/orders">All orders</a>
</main>
</body></html>
"""


def project(tmp_path, render=True, tolerance=None, heading="Home", token="--color-text"):
    frozen_version(tmp_path)
    (tmp_path / "render.py").write_text(RENDER, encoding="utf-8")
    built = tmp_path / "built"
    built.mkdir()
    for state in ("default", "empty"):
        page = BUILT.format(heading=heading, token=token)
        (built / f"home--{state}.html").write_text(page, encoding="utf-8")
    lines = ["[design]"]
    if render:
        lines.append(f'render = "{sys.executable} {tmp_path / "render.py"}"')
    if tolerance is not None:
        lines.append(f"pixel_tolerance = {tolerance}")
    (tmp_path / "agk.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def compare(root, *args, path=None):
    env = clean_env()
    if path is None:
        empty = root.parent / (root.name + "-empty")
        empty.mkdir(exist_ok=True)
        path = f"{empty}{os.pathsep}{os.path.dirname(sys.executable)}"
    env["PATH"] = path
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_ac6_an_equal_page_reads_match_and_pixels_not_run_without_a_browser(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 11 (match; the prototype's own bars are not compared)."""
    project(tmp_path)
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "home/default match; pixels: not run\n"


def test_ac6_a_changed_heading_reads_drift_structure_and_exits_0(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 11 (drift is named, never failed)."""
    project(tmp_path, heading="Welcome")
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.returncode == 0
    assert proc.stdout == "home/default drift: structure; pixels: not run\n"


def test_ac6_a_changed_token_reads_drift_tokens(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 11 (the standard's custom properties the page uses)."""
    project(tmp_path, token="--color-muted")
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.returncode == 0
    assert proc.stdout == "home/default drift: tokens; pixels: not run\n"


def test_ac6_several_kinds_are_named_comma_separated(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 11 (several kinds may be named)."""
    project(tmp_path, heading="Welcome", token="--color-muted")
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.stdout == "home/default drift: structure, tokens; pixels: not run\n"


@pytest.mark.parametrize("screens", ["*", "home/*", "home/default, home/empty"])
def test_ac6_a_star_expands_to_the_pages_of_the_version(tmp_path, screens):
    """REQ-044 AC6: `*` is every page of the version, `<screen>/*` every state of the screen."""
    project(tmp_path)
    proc = compare(tmp_path, "--version", VERSION, "--screens", screens)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [
        "home/default match; pixels: not run",
        "home/empty match; pixels: not run",
    ]


def test_ac6_with_a_browser_the_pixels_are_compared_against_the_tolerance(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 11 (`pixel_share` at each breakpoint and mode)."""
    project(tmp_path, tolerance=0.3)
    white, black = (255, 255, 255), (0, 0, 0)
    frozen = png(tmp_path.parent / (tmp_path.name + "-f.png"), [[white, white, white, white]])
    near = png(tmp_path.parent / (tmp_path.name + "-n.png"), [[white, white, white, black]])
    far = png(tmp_path.parent / (tmp_path.name + "-x.png"), [[white, black, black, black]])
    for built, want in ((frozen, "match"), (near, "match"), (far, "drift: pixels")):
        log = fake_browser(tmp_path.parent / (tmp_path.name + f"-bin-{built.stem}"), frozen, built)
        path = f"{log.parent}{os.pathsep}{os.path.dirname(sys.executable)}"
        proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default", path=path)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert proc.stdout == f"home/default {want}\n"
        calls = log.read_text(encoding="utf-8").splitlines()
        # frozen and built, light and dark, five breakpoints; drift stops at the first that differs
        assert len(calls) == (2 if want.startswith("drift") else 2 * 2 * 5)


def test_ac6_an_unset_render_is_refused_naming_the_setting(tmp_path):
    """REQ-044 AC6: exit 1 naming the setting, never a value."""
    project(tmp_path, render=False)
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.returncode == 1
    assert "render" in proc.stdout and "[design]" in proc.stdout


def test_ac6_a_version_without_a_design_row_is_refused(tmp_path):
    """REQ-044 AC6: exit 1 naming the rule and the file, never a value."""
    project(tmp_path)
    (tmp_path / "docs" / "design" / "signoffs.md").unlink()
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.returncode == 1
    assert "rule 11:" in proc.stdout and "signoffs.md" in proc.stdout
    assert VERSION not in proc.stdout


@pytest.mark.parametrize(
    "args",
    [
        ("--version", VERSION),
        ("--screens", "home/default"),
        ("--version", "x1", "--screens", "home/default"),
        ("--version", VERSION, "--screens", "Home Default"),
        ("--version", VERSION, "--screens", "home/default", "--other", "x"),
    ],
)
def test_ac6_a_usage_error_exits_1(tmp_path, args):
    """REQ-044 AC6: exit 1 on a usage error."""
    project(tmp_path)
    proc = compare(tmp_path, *args)
    assert proc.returncode == 1
    assert "usage:" in proc.stdout + proc.stderr


def test_ac6_a_screen_the_version_does_not_have_is_refused(tmp_path):
    """REQ-044 AC6: a named screen or state must be a page of the version."""
    project(tmp_path)
    proc = compare(tmp_path, "--version", VERSION, "--screens", "orders/default")
    assert proc.returncode == 1
    assert "orders" not in proc.stdout and "rule" in proc.stdout


def test_ac6_a_bad_tolerance_is_refused_naming_the_setting(tmp_path):
    """REQ-044 AC6: `pixel_tolerance` is a share from 0 to 1."""
    project(tmp_path, tolerance=2)
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.returncode == 1 and "pixel_tolerance" in proc.stdout and "2" not in proc.stdout


def test_ac6_a_render_that_writes_no_page_is_refused_naming_the_setting(tmp_path):
    """REQ-044 AC6 (Q-461-2): nothing to compare is not a match; it names the setting."""
    project(tmp_path)
    (tmp_path / "built" / "home--default.html").unlink()
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.returncode == 1 and "render" in proc.stdout
    assert "match" not in proc.stdout


def test_ac6_the_frozen_page_is_unchanged_by_a_comparison(tmp_path):
    """REQ-044 AC6: the comparison writes nothing into the version."""
    project(tmp_path)
    folder = tmp_path / "docs" / "design" / "prototype" / VERSION
    before = sorted(p.name for p in folder.iterdir())
    compare(tmp_path, "--version", VERSION, "--screens", "*")
    assert sorted(p.name for p in folder.iterdir()) == before
    assert (folder / "home--default.html").read_text(encoding="utf-8") == FROZEN.format(
        state="default"
    )
