"""The headless browser of the design commands: reflow, screenshots and the pixel diff (SPEC-0037
rules 8 and 11, brief #461).

Kit-only (never installed); `design.py screenshots --version` and `design_compare.py` use it.
`find_browser()` is `design.py`'s. `measure(browser, page, width, mode)` opens PAGE from the files,
offline, in an `iframe` WIDTH px wide of a wrapper page written to a temporary folder outside the
version (the version gains no script), and returns True when the page's document is wider than
its viewport (a sideways scroll). `shoot(browser, page, width, mode, target)` writes one PNG.
`pixel_share(first, second)` decodes two PNGs with the standard library (`zlib`) and returns the
share of pixels that differ (1.0 when the sizes differ). `reflow(root, version)` is the
`screenshots --version` command: at each breakpoint of the standard, in light and dark, it writes
`docs/design/prototype/<version>/screenshots/<screen>--<state>-<width>-<mode>.png` and
`screenshots/reflow.json` (`{"version": ..., "entries": [{"page", "width", "mode", "reflow"}]}`,
`reflow` being `ok`, `sideways` or `not run`); without a browser every entry reads `not run`.
`screenshots/` is written only by `design.py screenshots`, never by hand. The browser runs with
`--host-resolver-rules=MAP * ~NOTFOUND`, so no request leaves the machine. Messages name the
rule, never a value.
"""

from __future__ import annotations

import html
import json
import re
import struct
import subprocess  # nosec B404 - a fixed argument list, no shell
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design
import design_signoff
from common import CheckError
from design_standard import BREAKPOINTS

HEIGHT = 800
MODES = ("light", "dark")
# Measured on Chromium (2026-11-08): with these flags a file page is opened, its iframe read and no
# host resolved.
OFFLINE = ("--headless", "--disable-gpu", "--host-resolver-rules=MAP * ~NOTFOUND")
MARK = re.compile(r'id="agk-reflow">(ok|sideways)<')
PAGE = re.compile(r"^[a-z0-9][a-z0-9-]*--[a-z0-9][a-z0-9-]*\.html$")
REFLOW = "reflow.json"
NO_BROWSER = "design: no headless browser found; reflow not run"
WRAPPER = (
    '<!doctype html><html><body style="margin:0"><iframe style="width:{width}px;height:{height}px;'
    'border:0" src="{src}" onload="var d=this.contentDocument.documentElement;'
    "document.getElementById('agk-reflow').textContent=d.scrollWidth>d.clientWidth?'sideways':'ok'"
    '"></iframe><pre id="agk-reflow">pending</pre></body></html>\n'
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}  # grey, RGB, grey and alpha, RGBA
NOT_PNG = "rule 11: a screenshot is not a PNG the comparison reads"


def find_browser() -> str | None:
    return design.find_browser()


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - a fixed argument list, no shell
        command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
    )


def measure(browser: str, page: Path, width: int, mode: str) -> bool:
    """True when PAGE scrolls sideways at WIDTH px in MODE; refused when it cannot be measured."""
    with tempfile.TemporaryDirectory(prefix="agk-reflow-") as scratch:
        wrapper = Path(scratch) / "wrapper.html"
        src = html.escape(page.resolve().as_uri(), quote=True)
        wrapper.write_text(WRAPPER.format(width=width, height=HEIGHT, src=src), encoding="utf-8")
        command = [
            browser,
            *OFFLINE,
            "--dump-dom",
            "--allow-file-access-from-files",
            f"--window-size={width},{HEIGHT}",
            design.SCHEME[mode],
            wrapper.as_uri(),
        ]
        proc = _run(command)
    found = MARK.search(proc.stdout or "")
    if proc.returncode != 0 or found is None:
        raise CheckError("rule 8: the headless browser did not measure a page")
    return found.group(1) == "sideways"


def shoot(browser: str, page: Path, width: int, mode: str, target: Path) -> None:
    """Write one screenshot of PAGE at WIDTH px in MODE to TARGET."""
    command = [
        browser,
        *OFFLINE,
        f"--screenshot={target}",
        f"--window-size={width},{HEIGHT}",
        design.SCHEME[mode],
        page.resolve().as_uri(),
    ]
    proc = _run(command)
    if proc.returncode != 0 or not target.is_file():
        raise CheckError("rule 8: the headless browser did not make a screenshot")


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png(path: Path) -> tuple[int, int, int, bytes]:
    """(width, height, bytes per pixel, the unfiltered pixel bytes) of an 8-bit PNG."""
    try:
        data = path.read_bytes()
    except OSError:
        raise CheckError(NOT_PNG) from None
    if not data.startswith(PNG_SIGNATURE):
        raise CheckError(NOT_PNG)
    pos, header, idat = 8, None, bytearray()
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind, body = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
    if header is None or header[2] != 8 or header[3] not in CHANNELS or header[6] != 0:
        raise CheckError(NOT_PNG)
    width, height, bpp = header[0], header[1], CHANNELS[header[3]]
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        raise CheckError(NOT_PNG) from None
    stride = width * bpp
    if len(raw) < height * (stride + 1):
        raise CheckError(NOT_PNG)
    out = bytearray(height * stride)
    previous = bytearray(stride)
    for y in range(height):
        kind = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        if kind == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif kind == 2:
            line = bytearray((x + p) & 255 for x, p in zip(line, previous, strict=True))
        elif kind == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 255
        elif kind == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                up_left = previous[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, previous[i], up_left)) & 255
        elif kind != 0:
            raise CheckError(NOT_PNG)
        out[y * stride : (y + 1) * stride] = line
        previous = line
    return width, height, bpp, bytes(out)


def pixel_share(first: Path, second: Path) -> float:
    """The share of pixels that differ between two PNGs; 1.0 when their sizes differ."""
    w1, h1, b1, p1 = decode_png(first)
    w2, h2, b2, p2 = decode_png(second)
    if (w1, h1) != (w2, h2):
        return 1.0
    total = w1 * h1
    if total == 0:
        return 0.0
    if b1 == b2 and p1 == p2:
        return 0.0
    differ = sum(p1[i * b1 : (i + 1) * b1] != p2[i * b2 : (i + 1) * b2] for i in range(total))
    return differ / total


def pages(folder: Path) -> list[str]:
    """The `<screen>--<state>.html` pages of a version folder, sorted (not `index.html`)."""
    return sorted(p.name for p in folder.glob("*.html") if PAGE.match(p.name))


def version_folder(root: Path, version: str) -> Path:
    folder = root / design_signoff.PROTOTYPE / version
    if not design_signoff.VERSION.match(version) or not folder.is_dir():
        raise CheckError("rule 8: the version is not a prototype version folder")
    return folder


def reflow(root: Path, version: str) -> int:
    """`design.py screenshots --version`: the screenshots and `reflow.json` of a version."""
    folder = version_folder(root, version)
    out = folder / design_signoff.SCREENSHOTS
    browser = find_browser()
    entries, sideways = [], []
    if browser is not None:
        out.mkdir(exist_ok=True)
    for name in pages(folder):
        for width in BREAKPOINTS:
            for mode in MODES:
                result = "not run"
                if browser is not None:
                    shoot(
                        browser, folder / name, width, mode, out / f"{name[:-5]}-{width}-{mode}.png"
                    )
                    result = "sideways" if measure(browser, folder / name, width, mode) else "ok"
                    if result == "sideways":
                        sideways.append(f"{name[:-5]} {width} {mode}")
                entries.append({"page": name, "width": width, "mode": mode, "reflow": result})
    out.mkdir(exist_ok=True)
    text = json.dumps({"version": version, "entries": entries}, indent=2) + "\n"
    (out / REFLOW).write_text(text, encoding="utf-8")
    if browser is None:
        print(NO_BROWSER)
        return 0
    shots = len(entries)
    print(
        f"wrote {shots} screenshots and {REFLOW} in {design_signoff.PROTOTYPE}/{version}/screenshots/"
    )
    for line in sideways:
        print(f"sideways: {line}")
    return 0
