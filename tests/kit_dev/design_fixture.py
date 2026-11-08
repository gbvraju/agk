"""Shared helpers of the design render and compare tests (SPEC-0037 rules 8 and 11): an invented
frozen version, a PNG writer and a fake headless browser. Files only; invented data only."""

from __future__ import annotations

import shutil
import struct
import zlib
from pathlib import Path

VERSION = "v1"
FROZEN = """<!doctype html>
<html lang="en">
<head><title>Home, {state}</title>
<link rel="stylesheet" href="standard.css">
<style>.lead {{ color: var(--color-text); }}</style>
</head>
<body>
<div class="page stack">
<nav class="cluster" aria-label="States of home" id="states">
<a href="home--default.html">default</a></nav>
<header><p>Example Org</p></header>
<main id="main" class="stack">
<h1>Home</h1>
<h2>Recent orders</h2>
<form><label for="q">Search orders</label><input id="q" type="search"><button>Find</button></form>
<a href="orders--default.html">All orders</a>
</main>
<nav class="cluster" aria-label="Demo: orders" data-demo="Start here.">
<a href="x">Next step</a></nav>
<p><a href="index.html">All flows</a></p>
</div>
<script src="agk-prototype.js"></script>
</body>
</html>
"""
STANDARD = ":root {\n  --color-text: #111111;\n  --color-muted: #555555;\n}\n"
SIGNOFFS = (
    "# Sign-offs\n\n| kind | version | digest | head | date | comment |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| design | v1 | " + "a" * 64 + " | " + "b" * 40 + " | 2026-11-01 | "
    "https://example.com/comment/1 |\n"
)


def frozen_version(root: Path, states=("default", "empty"), signed: bool = True) -> Path:
    """An invented version folder `docs/design/prototype/v1/` with one page per state of `home`."""
    folder = root / "docs" / "design" / "prototype" / VERSION
    folder.mkdir(parents=True)
    (folder / "index.html").write_text("<!doctype html><title>Flows</title>\n", encoding="utf-8")
    (folder / "standard.css").write_text(STANDARD, encoding="utf-8")
    for state in states:
        (folder / f"home--{state}.html").write_text(FROZEN.format(state=state), encoding="utf-8")
    if signed:
        (root / "docs" / "design" / "signoffs.md").write_text(SIGNOFFS, encoding="utf-8")
    return folder


def png(path: Path, rows: list[list[tuple[int, int, int]]], filters=None) -> Path:
    """Write an 8-bit RGB PNG of ROWS, each row with its filter type (0 none, 1 sub, 2 up)."""
    width = len(rows[0])
    raw = b""
    previous = bytes(width * 3)
    for i, row in enumerate(rows):
        line = bytes(c for pixel in row for c in pixel)
        kind = (filters or [0] * len(rows))[i]
        if kind == 1:
            out = bytes((line[j] - (line[j - 3] if j >= 3 else 0)) % 256 for j in range(len(line)))
        elif kind == 2:
            out = bytes((line[j] - previous[j]) % 256 for j in range(len(line)))
        else:
            out = line
        raw += bytes([kind]) + out
        previous = line

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, len(rows), 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
    data += chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    path.write_bytes(data)
    return path


def fake_browser(directory: Path, frozen_png: Path, built_png: Path | None = None) -> Path:
    """A `chromium` on PATH that logs its arguments. `--dump-dom` prints the reflow mark,
    `sideways` at a 360 px window and `ok` otherwise; `--screenshot=T` copies FROZEN_PNG to T,
    or BUILT_PNG when the page opened is not under a `prototype/` folder."""
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / "calls"
    built = built_png or frozen_png
    cp = shutil.which("cp")  # by its full path: the tests may run with a PATH without it
    script = directory / "chromium"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{log}"\n'
        'last=""; for a in "$@"; do last="$a"; done\n'
        'case "$*" in *--dump-dom*)\n'
        '  case "$*" in *--window-size=360,*) echo \'<pre id="agk-reflow">sideways</pre>\';;\n'
        "  *) echo '<pre id=\"agk-reflow\">ok</pre>';; esac; exit 0;; esac\n"
        'for a in "$@"; do case "$a" in --screenshot=*)\n'
        f'  case "$last" in */prototype/*) {cp} "{frozen_png}" "${{a#--screenshot=}}";;\n'
        f'  *) {cp} "{built}" "${{a#--screenshot=}}";; esac;; esac; done\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    return log
