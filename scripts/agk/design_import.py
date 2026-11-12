"""The imported version (SPEC-0037 rule 15 as amendment 161 items 1 to 3 propose; brief #1061).
Installed: `kit/manifest.json` lists it in `verbatim`; `design.py import` writes with it and
`check_design.py` checks with it.

`import_folder(root, source)` copies every file of SOURCE byte for byte into
`docs/design/imported/i<n>/files/`, `i<n>` the next free number, never over an existing version,
keeping each relative path, and writes beside it `manifest.json` (one entry per file with its
`path`, `size` and `sha256`, sorted by path; `digest`, the SHA-256 of the sorted
`<path> <SHA-256 of the file>` lines, the formula of rule 9; and `pages`) and `external.txt` (every
reference to `http:`, `https:` or `//` that a page or a stylesheet makes, one `<file> <url>` per
line). It refuses, naming the rule and the file and copying nothing, a symbolic link, a source
folder inside `docs/design/` and a folder with no file. Of the files, an HTML file is a page; an
image (PNG, JPEG, SVG, WebP) that no page references by a relative `href`, `src`, `srcset`,
`poster`, `data` or CSS `url()` is a picture page; each page of a PDF is a picture page
`<file>#page=<n>`; every other file is an asset.

`imported_problems(root)` checks each `docs/design/imported/i<n>/`: a file of `files/` the manifest
does not list, a listed file that is missing, a size or SHA-256 that does not match, a `digest`,
a `pages` list or an `external.txt` that does not follow from the files, and the rows of `map.md`
(`<file> -> <screen>/<state>` or `<file> -> out: <reason>`) against the manifest and
`docs/design/inventory.md`; then, with an imported version and an inventory, every `yes` state
that neither a row of an imported version nor a page `<screen>--<state>.html` of a kit version
covers. Rules 5 to 7 do not apply to an imported version. Every file is read as bytes or text: no
page is opened or run, no network, no model, and the check writes nothing. Messages name the rule
and the file, or the screen and state, never a value.

`python3 design_import.py source --version i<n> --slug <slug> [--root DIR]` (SPEC-0043 rule 2a as
amendment 163 item 2 proposes, with the owner's ruling on Q-1073-2; brief #1077, ADR-0458) writes
once, as a new file only, `docs/sources/<slug>-prototype-i<n>.md`: rule 1's header
(`Source: imported prototype i<n>`, `Kind: design`, `Version: i<n> <digest>`, `Date:` from the
clock in UTC) and one blank line, then for each row of the version's `map.md` that is not `out:`,
in the map's order, one `## <screen>/<state>` heading and under it the page's visible text: every
text outside `script`, `style` and `template` elements, in document order, with the names and
placeholders of fields and the value of an input button, one per line, white space collapsed,
empty ones left out; `picture: <file>` for a picture page. A text line that Markdown would read as
a heading or a fence gets a leading backslash. It refuses with exit 1, naming the rule and the
version and writing nothing, a version that is not there and one for which `imported_problems`
names a problem of that version or of the coverage; an existing target file, naming the file; and
a missing or malformed `--slug` or `--version` with exit 2. `source_text(root, version)` returns
the text and writes nothing. Pages are parsed as text by the standard library: nothing is run,
opened or fetched.
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import shutil
import sys
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import design_inventory
from common import CheckError

IMPORTED = "docs/design/imported"
DESIGN = "docs/design"
PROTOTYPE = "docs/design/prototype"
VERSION = re.compile(r"^i[1-9]\d*$")
KIT_VERSION = re.compile(r"^v[1-9]\d*$")
FILES = "files"
MANIFEST = "manifest.json"
MAP = "map.md"
EXTERNAL = "external.txt"
PAGES = (".html", ".htm")
IMAGES = (".png", ".jpg", ".jpeg", ".svg", ".webp")
PDF = ".pdf"
STYLESHEETS = (".css",)
REFERENCE = re.compile(
    r"""(?is)\b(?:href|src|srcset|poster|data)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))"""
    r"""|url\(\s*(?:"([^"]*)"|'([^']*)'|([^)'"]*))\s*\)"""
)
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
EXTERNAL_URL = re.compile(
    r"""(?i)\bhttps?:[^\s"'()<>]+"""
    r"""|(?:=\s*["']?|url\(\s*["']?|@import\s+["']?)\s*(//[^\s"'()<>]+)"""
)
PDF_PAGE = re.compile(rb"/Type\s*/Page(?![A-Za-z])")
PDF_COUNT = re.compile(
    rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)|/Count\s+(\d+)[^>]*?/Type\s*/Pages\b", re.S
)
PERCENT = re.compile(rb"%([0-9A-Fa-f]{2})")
ROW = re.compile(r"^\s*(?:[-*]\s+)?`?(?P<file>[^`]+?)`?\s+->\s*(?P<target>.*?)\s*$")
OUT = re.compile(r"^out:(.*)$")
TARGET = re.compile(r"^([a-z0-9][a-z0-9-]*)/([a-z0-9][a-z0-9-]*)$")


# --- the files ------------------------------------------------------------------------------------


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _files(folder: Path) -> dict[str, bytes]:
    """{relative path: bytes} of every regular file under FOLDER, symbolic links left out."""
    found: dict[str, bytes] = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not path.is_symlink():
            found[path.relative_to(folder).as_posix()] = path.read_bytes()
    return found


def _text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _pdf_pages(data: bytes) -> int:
    """The pages of a PDF read as bytes: its `/Type /Page` objects, else the `/Count` of its
    `/Pages` tree, else one; never opened by a reader (Q-1061-2)."""
    pages = len(PDF_PAGE.findall(data))
    if pages:
        return pages
    counts = [int(a or b) for a, b in PDF_COUNT.findall(data)]
    return max(counts) if counts and max(counts) > 0 else 1


def _unquote(text: str) -> str:
    """A link's `%xx` escapes decoded as UTF-8 (no URL library: the module reads files only)."""
    raw = PERCENT.sub(lambda m: bytes([int(m.group(1), 16)]), text.encode("utf-8"))
    return raw.decode("utf-8", errors="replace")


def _references(page: str, text: str, names: set[str]) -> set[str]:
    """The files of NAMES that PAGE references by a relative link, `src` or CSS `url()`."""
    found: set[str] = set()
    base = posixpath.dirname(page)
    for match in REFERENCE.finditer(text):
        value = next((g for g in match.groups() if g is not None), "")
        for part in value.split(","):  # a srcset lists `<url> <width>` entries
            words = part.strip().split()
            if not words:
                continue
            target = _unquote(re.split(r"[?#]", words[0], maxsplit=1)[0])
            if not target or SCHEME.match(target) or target.startswith("//"):
                continue
            joined = target.lstrip("/") if target.startswith("/") else posixpath.join(base, target)
            name = posixpath.normpath(joined)
            if name in names:
                found.add(name)
    return found


def pages(files: dict[str, bytes]) -> list[str]:
    """The pages and picture pages of FILES, sorted (amendment 161 item 1)."""
    names = set(files)
    html = [n for n in names if n.lower().endswith(PAGES)]
    referenced: set[str] = set()
    for name in html:
        referenced |= _references(name, _text(files[name]), names)
    out = list(html)
    for name in names:
        lower = name.lower()
        if lower.endswith(IMAGES) and name not in referenced:
            out.append(name)
        elif lower.endswith(PDF):
            out += [f"{name}#page={n}" for n in range(1, _pdf_pages(files[name]) + 1)]
    return sorted(out)


def external(files: dict[str, bytes]) -> str:
    """`external.txt`: one `<file> <url>` line per external reference of a page or a stylesheet."""
    lines: set[str] = set()
    for name, data in files.items():
        if not name.lower().endswith((*PAGES, *STYLESHEETS)):
            continue
        for match in EXTERNAL_URL.finditer(_text(data)):
            lines.add(f"{name} {match.group(1) or match.group(0)}")
    return "".join(f"{line}\n" for line in sorted(lines))


def digest(files: dict[str, bytes]) -> str:
    """Rule 9's formula: the SHA-256 of the sorted `<path> <SHA-256 of the file>` lines."""
    lines = sorted(f"{name} {_sha(data)}\n" for name, data in files.items())
    return _sha("".join(lines).encode("utf-8"))


def manifest(folder: Path) -> dict:
    """The manifest of the files under FOLDER, as the import writes it."""
    files = _files(folder)
    return {
        "files": [
            {"path": name, "size": len(data), "sha256": _sha(data)}
            for name, data in sorted(files.items())
        ],
        "digest": digest(files),
        "pages": pages(files),
    }


# --- the import -----------------------------------------------------------------------------------


def versions(root: Path) -> list[str]:
    """The imported versions `i<n>` of `docs/design/imported/` that hold a file, in number order."""
    folder = root / IMPORTED
    if not folder.is_dir():
        return []
    found = [
        p.name
        for p in folder.iterdir()
        if p.is_dir() and VERSION.match(p.name) and any(p.iterdir())
    ]
    return sorted(found, key=lambda name: int(name[1:]))


def _next_version(root: Path) -> str:
    folder = root / IMPORTED
    taken = (
        [int(p.name[1:]) for p in folder.iterdir() if VERSION.match(p.name)]
        if folder.is_dir()
        else []
    )
    return f"i{max(taken, default=0) + 1}"


def _source_files(source: Path) -> list[str]:
    """The relative paths of SOURCE's files; a symbolic link or a special file refuses."""
    if source.is_symlink():
        raise CheckError("rule 15: the source folder is a symbolic link; nothing is imported")
    found: list[str] = []
    for top, dirs, names in os.walk(source, followlinks=False):
        for name in sorted(dirs + names):
            path = Path(top) / name
            rel = path.relative_to(source).as_posix()
            if "\n" in rel or "\r" in rel:
                raise CheckError("rule 15: a file name holds a line break; nothing is imported")
            if path.is_symlink():
                raise CheckError(f"rule 15: {rel}: a symbolic link is not imported; nothing is")
            if name in names:
                if not path.is_file():
                    raise CheckError(f"rule 15: {rel}: not a regular file; nothing is imported")
                found.append(rel)
    return sorted(found)


def import_folder(root: Path, source: Path) -> str:
    """Copy SOURCE into the next imported version and write its records; return the version."""
    if not source.is_dir():
        raise CheckError("rule 15: the source is not a folder; nothing is imported")
    design = (root / DESIGN).resolve()
    real = source.resolve()
    if real == design or design in real.parents:
        raise CheckError(f"rule 15: the source folder is inside {DESIGN}/; nothing is imported")
    names = _source_files(source)
    if not names:
        raise CheckError("rule 15: the source folder holds no file; nothing is imported")
    version = _next_version(root)
    target = root / IMPORTED / version
    target.mkdir(parents=True, exist_ok=False)  # never over an existing version
    for name in names:
        dest = target / FILES / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dest)  # the bytes only, nothing converted
    files = _files(target / FILES)
    record = manifest(target / FILES)
    (target / MANIFEST).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    (target / EXTERNAL).write_text(external(files), encoding="utf-8")
    print(
        f"wrote {IMPORTED}/{version}/ ({len(names)} files, {len(record['pages'])} pages);"
        f" next: write {IMPORTED}/{version}/{MAP}"
    )
    return version


# --- the check ------------------------------------------------------------------------------------


def inventory_states(root: Path) -> dict[tuple[str, str], str] | None:
    """{(screen, state): `yes` or `n/a`} of `docs/design/inventory.md`, or None without one."""
    path = root / design_inventory.INVENTORY
    if not path.is_file():
        return None
    parts = design_inventory._parts(path.read_text(encoding="utf-8"))
    found: dict[tuple[str, str], str] = {}
    for screen, lines in parts.get("Screens", []):
        for line in lines:
            match = design_inventory.FIELD.match(line)
            if match and match.group(1).strip().startswith("State "):
                state = match.group(1).strip()[len("State ") :].strip()
                value = match.group(2).strip()
                found[(screen, state)] = "yes" if value == "yes" else "n/a"
    return found


def _record_problems(folder: Path, rel: str) -> tuple[list[str], list[str] | None]:
    """(problems, the manifest's pages or None) of the files against the records."""
    out: list[str] = []
    files = _files(folder / FILES)
    try:
        record = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
        entries = {e["path"]: e for e in record["files"]}
        listed_pages = [str(p) for p in record["pages"]]
        recorded_digest = record["digest"]
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError):
        return [f"rule 15: {rel}/{MANIFEST}: the manifest cannot be read"], None
    for name in sorted(set(files) - set(entries)):
        out.append(f"rule 15: {rel}/{FILES}/{name}: the file is not in the manifest")
    for name in sorted(entries):
        if name not in files:
            out.append(f"rule 15: {rel}/{FILES}/{name}: a listed file is missing")
        elif entries[name].get("size") != len(files[name]) or entries[name].get("sha256") != _sha(
            files[name]
        ):
            out.append(
                f"rule 15: {rel}/{FILES}/{name}: the size or SHA-256 does not match the manifest"
            )
    if recorded_digest != digest(files):
        out.append(f"rule 15: {rel}/{MANIFEST}: the digest does not follow from the files")
    if listed_pages != pages(files):
        out.append(f"rule 15: {rel}/{MANIFEST}: the pages list does not follow from the files")
    path = folder / EXTERNAL
    try:
        listed = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        listed = None
    if listed != external(files):
        out.append(f"rule 15: {rel}/{EXTERNAL}: the list does not follow from the files")
    return out, listed_pages


def _rows(folder: Path) -> list[tuple[str, str]]:
    path = folder / MAP
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = ROW.match(line)
        if match:
            rows.append((match.group("file").strip(), match.group("target")))
    return rows


def _map_problems(
    folder: Path,
    rel: str,
    listed: list[str],
    states: dict[tuple[str, str], str] | None,
    covered: set[tuple[str, str]],
) -> list[str]:
    where = f"rule 15: {rel}/{MAP}"
    out: list[str] = []
    rows = _rows(folder)
    seen: set[str] = set()
    targets: set[tuple[str, str]] = set()
    if states is None and any(not OUT.match(t) for _, t in rows):
        out.append(f"{where}: there is no inventory to check the map against")
    for name, target in rows:
        if name not in listed:
            out.append(f"{where}: {name}: the row names no page of the manifest")
        if name in seen:
            out.append(f"{where}: {name}: the file has more than one row")
        seen.add(name)
        reason = OUT.match(target)
        if reason:
            if not reason.group(1).strip():
                out.append(f"{where}: {name}: the out: row has no reason")
            continue
        match = TARGET.match(target)
        if not match:
            out.append(f"{where}: {name}: the row is neither <screen>/<state> nor out: <reason>")
            continue
        key = (match.group(1), match.group(2))
        label = f"{key[0]}/{key[1]}"
        if states is None:
            continue
        if key not in states:
            out.append(f"{where}: {label}: the row names a screen or state not in the inventory")
            continue
        if states[key] != "yes":
            out.append(f"{where}: {label}: the state is marked n/a: in the inventory")
            continue
        if key in targets:
            out.append(f"{where}: {label}: two rows name the same screen and state")
        targets.add(key)
        covered.add(key)
    for name in listed:
        if name not in seen:
            out.append(f"{where}: {name}: the page has no row")
    return out


def kit_covered(root: Path) -> set[tuple[str, str]]:
    """{(screen, state)} of the pages `<screen>--<state>.html` of every kit version `v<n>`."""
    found: set[tuple[str, str]] = set()
    folder = root / PROTOTYPE
    if not folder.is_dir():
        return found
    for version in folder.iterdir():
        if version.is_dir() and KIT_VERSION.match(version.name):
            for page in version.glob("*--*.html"):
                screen, _, state = page.stem.partition("--")
                found.add((screen, state))
    return found


def imported_problems(root: Path) -> list[str]:
    """The rule 15 problems of every imported version and of the coverage; [] when they pass."""
    found = versions(root)
    if not found:
        return []
    states = inventory_states(root)
    covered: set[tuple[str, str]] = set()
    out: list[str] = []
    for version in found:
        rel = f"{IMPORTED}/{version}"
        problems, listed = _record_problems(root / rel, rel)
        out += problems
        if listed is not None:
            out += _map_problems(root / rel, rel, listed, states, covered)
    if states is not None:
        covered |= kit_covered(root)
        for (screen, state), value in sorted(states.items()):
            if value == "yes" and (screen, state) not in covered:
                out.append(
                    f"rule 15: {design_inventory.INVENTORY}: {screen}/{state}:"
                    " no version covers the state"
                )
    return out


# --- the prototype source (SPEC-0043 rule 2a) -----------------------------------------------------

SOURCES = "docs/sources"
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SKIPPED = frozenset({"script", "style", "template"})
# Phrasing elements whose text runs on with the text around it; every other tag ends a line.
INLINE = frozenset(
    "abbr b bdi bdo cite code data dfn em i kbd mark q s samp small span strong sub sup time u"
    " var wbr".split()
)
FIELDS = frozenset({"input", "select", "textarea"})
INPUT_BUTTONS = frozenset({"submit", "button", "reset"})
MARKDOWN_LEAD = re.compile(r"^(#|```|~~~)")
SOURCE_USAGE = "usage: design_import.py source --version i<n> --slug <slug> [--root DIR]"


class _VisibleText(HTMLParser):
    """The visible text of a page (the Q-1073-2 ruling): every text outside `script`, `style` and
    `template`, in document order, with the names and placeholders of fields."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._run: list[str] = []
        self._skip: list[str] = []

    def _flush(self) -> None:
        text = " ".join("".join(self._run).split())
        self._run = []
        if text:
            self.lines.append(text)

    def _add(self, value: str | None) -> None:
        text = " ".join((value or "").split())
        if text:
            self.lines.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip:
            if tag == "template":
                self._skip.append(tag)
            return
        if tag in SKIPPED:
            self._flush()
            self._skip.append(tag)
            return
        if tag in INLINE:
            return
        self._flush()
        if tag in FIELDS:
            values = dict(attrs)
            kind = (values.get("type") or "").lower()
            if tag == "input" and kind == "hidden":
                return
            if tag == "input" and kind in INPUT_BUTTONS:
                self._add(values.get("value"))
                return
            self._add(values.get("name"))
            self._add(values.get("placeholder"))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._skip:
            if tag == self._skip[-1]:
                self._skip.pop()
            return
        if tag not in INLINE:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._run.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def visible_text(html: str) -> list[str]:
    """The visible text lines of a page read as text; nothing is run, opened or fetched."""
    parser = _VisibleText()
    parser.feed(html)
    parser.close()
    return ["\\" + line if MARKDOWN_LEAD.match(line) else line for line in parser.lines]


def _version_problems(root: Path, version: str) -> list[str]:
    """The `imported_problems` that name VERSION's folder or the coverage (no other version)."""
    own = f"{IMPORTED}/{version}/"
    other = re.compile(rf"{re.escape(IMPORTED)}/i\d+/")
    return [p for p in imported_problems(root) if own in p or not other.search(p)]


def source_text(root: Path, version: str, today: str | None = None) -> str:
    """The prototype source of VERSION (rule 2a); refuses a missing or failing version."""
    folder = root / IMPORTED / version
    if not VERSION.match(version) or version not in versions(root):
        raise CheckError(f"rule 2a: {version}: no such imported version; nothing is written")
    problems = _version_problems(root, version)
    if problems:
        for problem in problems:
            print(f"FAIL design: {problem}")
        raise CheckError(f"rule 2a: {version}: the import or map check fails; nothing is written")
    record = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    date = today or datetime.now(UTC).date().isoformat()
    out = [
        f"Source: imported prototype {version}",
        "Kind: design",
        f"Version: {version} {record['digest']}",
        f"Date: {date}",
        "",
    ]
    for name, target in _rows(folder):
        if OUT.match(target):
            continue
        out += [f"## {target}", ""]
        if name.lower().endswith(PAGES):
            data = (folder / FILES / name).read_bytes()
            out += visible_text(_text(data))
        else:
            out.append(f"picture: {name}")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def write_source(root: Path, version: str, slug: str) -> Path:
    """Write the prototype source once as `docs/sources/<slug>-prototype-<version>.md`."""
    rel = f"{SOURCES}/{slug}-prototype-{version}.md"
    path = root / rel
    if path.exists():
        raise CheckError(f"rule 2a: {rel}: the file exists; nothing is written")
    text = source_text(root, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:  # never over an existing file
        handle.write(text)
    print(f"wrote {rel} ({text.count(chr(10) + '## ')} headings)")
    return path


def _options(args: list[str]) -> dict[str, str] | None:
    opts: dict[str, str] = {}
    while args:
        flag = args.pop(0)
        if flag not in ("--version", "--slug", "--root") or flag in opts or not args:
            return None
        opts[flag] = args.pop(0)
    return opts


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] != ["source"]:
        print(SOURCE_USAGE, file=sys.stderr)
        return 2
    opts = _options(args[1:])
    if opts is None:
        print(SOURCE_USAGE, file=sys.stderr)
        return 2
    if not SLUG.match(opts.get("--slug", "")):
        print(
            "design_import: --slug is required, a lower-case slug [a-z0-9][a-z0-9-]*",
            file=sys.stderr,
        )
        return 2
    if not VERSION.match(opts.get("--version", "")):
        print("design_import: --version is required, an imported version i<n>", file=sys.stderr)
        return 2
    from common import repo_root, run

    root = Path(opts["--root"]) if "--root" in opts else repo_root()

    def write() -> int:
        write_source(root, opts["--version"], opts["--slug"])
        return 0

    return run("design", write)


if __name__ == "__main__":
    sys.exit(main())
