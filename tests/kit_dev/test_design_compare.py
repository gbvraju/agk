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
import shutil
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


def test_ac6_the_version_copy_of_the_kit_standard_adds_no_tokens(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 11 (tokens used are the page's own; `standard.css` is the
    kit's standard unchanged, as `design.py prototype` writes it, and is not counted)."""
    project(tmp_path)
    folder = tmp_path / "docs" / "design" / "prototype" / VERSION
    kit_standard = KIT_ROOT / "kit" / "templates" / "design-standard.css"
    (folder / "standard.css").write_text(kit_standard.read_text(encoding="utf-8"), "utf-8")
    proc = compare(tmp_path, "--version", VERSION, "--screens", "home/default")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "home/default match; pixels: not run\n"


def test_ac6_a_page_own_linked_stylesheet_is_still_counted(tmp_path):
    """REQ-044 AC6: SPEC-0037 rule 11 (a stylesheet of the page's own, beside it, is counted)."""
    project(tmp_path)
    folder = tmp_path / "docs" / "design" / "prototype" / VERSION
    (folder / "screens.css").write_text(".x { color: var(--color-muted); }\n", "utf-8")
    page = folder / "home--default.html"
    text = page.read_text(encoding="utf-8")
    own = 'href="standard.css">\n<link rel="stylesheet" href="screens.css">'
    page.write_text(text.replace('href="standard.css">', own), "utf-8")
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


# --- brief #1063: the comparison with an imported version i<n> (amendment 161 item 5) -----------

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
import design_compare  # noqa: E402

# The customer's page, as imported: its own markup, inline script, external stylesheet and
# colours, none of the kit's structure or tokens; only its visible text in order is compared.
IMPORTED_PAGE = """<!doctype html>
<html><head><title>Not compared</title>
<link rel="stylesheet" href="https://example.com/brand.css">
<style>h1 {{ color: #ff00aa; }}</style>
<script>document.title = "x";</script></head>
<body><div class="hero"><p>Example Org</p></div>
<section><h1>{heading}</h1><h3>Recent orders</h3>
<span>Search orders</span><input><button>Find</button>
<template><p>Never shown</p></template><p hidden>Hidden note</p>
<a href="orders.html">All orders</a></section></body></html>
"""
IMPORTED_MAP = """# Map of i1

- home.html -> home/default
- shot.png -> home/empty
- brief.pdf#page=2 -> home/error
- intro.html -> out: a splash page the product drops
"""
IMPORTED_SIGNOFF = "| design | i1 | " + "c" * 64 + " | " + "d" * 40 + " | 2026-11-12 | x |\n"


def imported(tmp_path, heading="Home", signed=True):
    """An invented project with the built pages of `project` and an imported version i1."""
    project(tmp_path, tolerance=0.3)
    (tmp_path / "built" / "home--error.html").write_text(
        BUILT.format(heading="Home", token="--color-text"), encoding="utf-8"
    )
    folder = tmp_path / "docs" / "design" / "imported" / "i1"
    files = folder / "files"
    files.mkdir(parents=True)
    (files / "home.html").write_text(IMPORTED_PAGE.format(heading=heading), encoding="utf-8")
    (files / "intro.html").write_text("<!doctype html><p>Welcome</p>\n", encoding="utf-8")
    png(files / "shot.png", [[(255, 255, 255)] * 2])
    (files / "brief.pdf").write_bytes(b"%PDF-1.4\n% invented\n")
    (folder / "map.md").write_text(IMPORTED_MAP, encoding="utf-8")
    signoffs = tmp_path / "docs" / "design" / "signoffs.md"
    if signed:
        signoffs.write_text(signoffs.read_text(encoding="utf-8") + IMPORTED_SIGNOFF, "utf-8")
    return files


def test_ac6_an_imported_page_with_the_same_visible_text_reads_match_pixels_not_run(tmp_path):
    """REQ-044 AC6: amendment 161 item 5 (text in order; structure and tokens do not apply)."""
    imported(tmp_path)
    proc = compare(tmp_path, "--version", "i1", "--screens", "home/default")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "home/default match; pixels: not run\n"


def test_ac6_an_imported_page_with_other_text_reads_drift_text_and_exits_0(tmp_path):
    """REQ-044 AC6: amendment 161 item 5 (`drift: text`, exit 0 on drift)."""
    imported(tmp_path, heading="Welcome back")
    proc = compare(tmp_path, "--version", "i1", "--screens", "home/default")
    assert proc.returncode == 0
    assert proc.stdout == "home/default drift: text; pixels: not run\n"


def test_ac6_a_picture_page_without_a_browser_reads_pixels_not_run_never_match(tmp_path):
    """REQ-044 AC6: amendment 161 items 5 and 7 (a picture page is compared by pixels only, so
    without a browser nothing is compared and the line never reads `match`)."""
    imported(tmp_path)
    proc = compare(tmp_path, "--version", "i1", "--screens", "home/empty, home/error")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == ["home/empty pixels: not run", "home/error pixels: not run"]
    assert "match" not in proc.stdout and "passed" not in proc.stdout


def test_ac6_a_star_of_an_imported_version_is_every_mapped_state(tmp_path):
    """REQ-044 AC6: a bare `*` is every screen and state the map covers, an `out:` row none."""
    imported(tmp_path)
    proc = compare(tmp_path, "--version", "i1", "--screens", "*")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [line.split(" ")[0] for line in proc.stdout.splitlines()] == [
        "home/default",
        "home/empty",
        "home/error",
    ]


def test_ac6_an_unmapped_state_or_an_unsigned_imported_version_is_refused(tmp_path):
    """REQ-044 AC6: exit 1 naming the rule, never a value."""
    imported(tmp_path)
    proc = compare(tmp_path, "--version", "i1", "--screens", "orders/default")
    assert proc.returncode == 1 and "rule 11:" in proc.stdout and "orders" not in proc.stdout
    unsigned = tmp_path / "other"
    unsigned.mkdir()
    imported(unsigned, signed=False)
    proc = compare(unsigned, "--version", "i1", "--screens", "home/default")
    assert proc.returncode == 1 and "signoffs.md" in proc.stdout and "i1" not in proc.stdout


def imported_browser(directory, imported_png, built_png):
    """A `chromium` that logs its arguments and writes IMPORTED_PNG for a page it opens through
    the comparison's server, BUILT_PNG for a file page."""
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / "calls"
    cp = shutil.which("cp")
    script = directory / "chromium"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{log}"\n'
        'last=""; for a in "$@"; do last="$a"; done\n'
        'for a in "$@"; do case "$a" in --screenshot=*)\n'
        f'  case "$last" in http://{design_compare.HOST}/*) {cp} "{imported_png}" '
        '"${a#--screenshot=}";;\n'
        f'  *) {cp} "{built_png}" "${{a#--screenshot=}}";; esac;; esac; done\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    return log


def test_ac6_with_a_browser_an_imported_page_is_shot_once_at_1440_light_through_the_server(
    tmp_path,
):
    """REQ-044 AC6: amendment 161 item 5 (pixels within `pixel_tolerance` at 1440 px in light
    mode; the imported page is opened only through the server that serves its version's files,
    with every request sent through it)."""
    imported(tmp_path)
    white, black = (255, 255, 255), (0, 0, 0)
    same = png(tmp_path.parent / (tmp_path.name + "-s.png"), [[white] * 4])
    far = png(tmp_path.parent / (tmp_path.name + "-f.png"), [[white, black, black, black]])
    for built, want in ((same, "match"), (far, "drift: pixels")):
        log = imported_browser(tmp_path.parent / (tmp_path.name + f"-b-{built.stem}"), same, built)
        path = f"{log.parent}{os.pathsep}{os.path.dirname(sys.executable)}"
        proc = compare(tmp_path, "--version", "i1", "--screens", "home/default", path=path)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert proc.stdout == f"home/default {want}\n"
        calls = log.read_text(encoding="utf-8").splitlines()
        assert len(calls) == 2
        built_call, imported_call = calls
        assert "--window-size=1440," in built_call and "--window-size=1440," in imported_call
        assert "dark" not in built_call + imported_call
        assert imported_call.endswith(f"http://{design_compare.HOST}/home.html")
        assert "--proxy-server=http://127.0.0.1:" in imported_call
        assert "--proxy-bypass-list=<-loopback>" in imported_call


def test_ac6_a_picture_page_with_a_browser_is_compared_at_the_width_of_the_image(tmp_path):
    """REQ-044 AC6: amendment 161 item 5 (a picture page: pixels only, at its width)."""
    imported(tmp_path)
    white = (255, 255, 255)
    same = png(tmp_path.parent / (tmp_path.name + "-s.png"), [[white] * 2])
    log = imported_browser(tmp_path.parent / (tmp_path.name + "-b"), same, same)
    path = f"{log.parent}{os.pathsep}{os.path.dirname(sys.executable)}"
    proc = compare(tmp_path, "--version", "i1", "--screens", "home/empty", path=path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "home/empty match\n"
    calls = log.read_text(encoding="utf-8").splitlines()
    assert all("--window-size=2,1" in call for call in calls), calls
    assert calls[1].endswith(f"http://{design_compare.HOST}/shot.png")


def test_ac6_a_pdf_page_without_a_pdf_renderer_reads_pixels_not_run(tmp_path):
    """REQ-044 AC6: amendment 161 item 5 (a PDF page is rendered at 1440 px wide, so without a
    renderer its pixels are not run even with a browser)."""
    imported(tmp_path)
    white = (255, 255, 255)
    same = png(tmp_path.parent / (tmp_path.name + "-s.png"), [[white] * 2])
    log = imported_browser(tmp_path.parent / (tmp_path.name + "-b"), same, same)
    path = f"{log.parent}{os.pathsep}{os.path.dirname(sys.executable)}"
    proc = compare(tmp_path, "--version", "i1", "--screens", "home/error", path=path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout == "home/error pixels: not run\n"


def request(port, method, target):
    import http.client

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, target)
    response = conn.getresponse()
    body = response.read()
    conn.close()
    return response.status, body


def test_ac6_the_server_refuses_every_request_outside_the_version_files(tmp_path):
    """REQ-044 AC6: amendment 161 item 5 (every request outside `docs/design/imported/i<n>/files/`
    is refused while the imported page renders, so an external reference renders without it).
    The server listens on the loopback only; no request leaves the machine."""
    files = imported(tmp_path)
    (files.parent / "secret.txt").write_text("outside the files\n", encoding="utf-8")
    host = design_compare.HOST
    with design_compare.FilesServer(files) as port:
        status, body = request(port, "GET", f"http://{host}/home.html")
        assert status == 200 and b"Recent orders" in body
        refused = [
            ("GET", "http://example.com/brand.css"),
            ("GET", f"http://{host}/../secret.txt"),
            ("GET", f"http://{host}/%2e%2e/secret.txt"),
            ("GET", f"http://{host}/missing.css"),
            ("GET", "/home.html"),
            ("POST", f"http://{host}/home.html"),
            ("CONNECT", "example.com:443"),
        ]
        for method, target in refused:
            status, body = request(port, method, target)
            assert status == 403, (method, target)
            assert b"outside the files" not in body


@pytest.mark.parametrize(
    ("target", "served"),
    [
        ("http://agk-imported.invalid/home.html", "home.html"),
        ("http://agk-imported.invalid/a%20b/c.css?v=1", "a b/c.css"),
        ("http://agk-imported.invalid/", None),
        ("http://agk-imported.invalid/../x", None),
        ("http://agk-imported.invalid//etc/hostname", None),
        ("https://agk-imported.invalid/home.html", None),
        ("http://example.com/home.html", None),
        ("file:///etc/hostname", None),
    ],
)
def test_ac6_a_request_is_served_only_inside_the_files(tmp_path, target, served):
    """REQ-044 AC6: the server's choice, as a function of the files and the request."""
    files = tmp_path / "files"
    (files / "a b").mkdir(parents=True)
    (files / "home.html").write_text("x", encoding="utf-8")
    (files / "a b" / "c.css").write_text("x", encoding="utf-8")
    found = design_compare.served(files, target)
    assert found == (None if served is None else (files / served).resolve())


def test_ac6_the_visible_text_of_a_page_is_read_in_order():
    """REQ-044 AC6: the text a reader sees, without the head, scripts, styles, templates and
    hidden elements."""
    page = IMPORTED_PAGE.format(heading="Home")
    assert design_compare.visible_text(page) == (
        "Example Org Home Recent orders Search orders Find All orders"
    )
