"""The sign-off digest and the reading of the sign-off record (SPEC-0037 rules 3 and 9). Installed:
`kit/manifest.json` lists it in `verbatim`.

`digest(root, paths)` is the SHA-256 (lower-case hex) of the sorted lines
`<path> <SHA-256 of the file>`, each ended by a newline, where `<path>` is the file's path from the
project root with `/`. `version_digest(root, version)` applies it to every file of
`docs/design/prototype/<version>/` except its `screenshots/` folder, which only
`design.py screenshots` writes and which stays outside what the person signs off;
`inventory_digest(root)` applies it to `docs/design/inventory.md`. `rows(root)` reads the one table
of `docs/design/signoffs.md` (columns kind, version, digest, head, date and comment) and returns its
`inventory` and `design` rows in file order, refusing a row of another shape naming the rule and
the row number, never a value. Whether a row counts (the person's `Approve:` line on the head it
names) is `check_final_clearance.py`'s question, not this module's; `parse_rows(text)` reads the
same table from a text (the file at a commit). `frozen_problems(root)` fails each `design` row whose
folder no longer has the row's digest (rule 9: a signed-off version changed, naming the version and
never a digest), and `signed_off(root, version)` is rule 12's evidence reading (brief #459). Files
only: no network, no model, nothing written.
"""

from __future__ import annotations

import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError

INVENTORY = "docs/design/inventory.md"
PROTOTYPE = "docs/design/prototype"
SIGNOFFS = "docs/design/signoffs.md"
SCREENSHOTS = "screenshots"
COLUMNS = ("kind", "version", "digest", "head", "date", "comment")
VERSION = re.compile(r"^v[1-9]\d*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK = re.compile(r"^https://\S+$")


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(root: Path, paths: list[str] | list[Path]) -> str:
    """The SHA-256 of the sorted `<path> <SHA-256 of the file>` lines of PATHS (from ROOT)."""
    lines = []
    for rel in paths:
        path = Path(rel) if Path(rel).is_absolute() else root / rel
        name = path.relative_to(root).as_posix()
        lines.append(f"{name} {_file_hash(path)}")
    text = "".join(f"{line}\n" for line in sorted(lines))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def version_digest(root: Path, version: str) -> str:
    """The digest of every file of a prototype version folder except `screenshots/`."""
    if not VERSION.match(version):
        raise CheckError("rule 9: the version is not v<n>")
    folder = root / PROTOTYPE / version
    if not folder.is_dir():
        raise CheckError("rule 9: the version folder does not exist")
    files = [
        p
        for p in folder.rglob("*")
        if p.is_file() and p.relative_to(folder).parts[0] != SCREENSHOTS
    ]
    return digest(root, files)


def inventory_digest(root: Path) -> str:
    """The digest of `docs/design/inventory.md`, which an `inventory` row records."""
    if not (root / INVENTORY).is_file():
        raise CheckError(f"rule 3: {INVENTORY} does not exist")
    return digest(root, [INVENTORY])


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def _real_date(text: str) -> bool:
    if not DATE.match(text):
        return False
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _row_problem(row: dict[str, str]) -> str | None:
    """What is wrong with one row, by its column and never its value; None when it is sound."""
    kind = row["kind"]
    if kind not in ("inventory", "design"):
        return "the kind is not inventory or design"
    if kind == "inventory" and row["version"] != "-":
        return "the version of an inventory row is not -"
    if kind == "design" and not VERSION.match(row["version"]):
        return "the version of a design row is not v<n>"
    if not SHA256.match(row["digest"]):
        return "the digest is not a SHA-256 in lower-case hex"
    if not COMMIT.match(row["head"]):
        return "the head is not a full commit ID"
    if not _real_date(row["date"]):
        return "the date is not a real YYYY-MM-DD"
    if not LINK.match(row["comment"]):
        return "the comment is not the https link of the person's comment"
    return None


def rows(root: Path) -> list[dict]:
    """The rows of `docs/design/signoffs.md` in file order; none when the file does not exist."""
    path = root / SIGNOFFS
    if not path.is_file():
        return []
    return parse_rows(path.read_text(encoding="utf-8"))


def parse_rows(text: str) -> list[dict]:
    """The rows of the sign-off table in TEXT, in file order, refusing a row of another shape."""
    lines = text.splitlines()
    header = next(
        (i for i, ln in enumerate(lines) if ln.startswith("|") and tuple(_cells(ln)) == COLUMNS),
        None,
    )
    if header is None or header + 1 >= len(lines):
        raise CheckError(f"rule 9: {SIGNOFFS}: the file has no sign-off table")
    separator = _cells(lines[header + 1])
    if len(separator) != len(COLUMNS) or not all(re.match(r"^:?-+:?$", c) for c in separator):
        raise CheckError(f"rule 9: {SIGNOFFS}: the file has no sign-off table")
    found: list[dict] = []
    for line in lines[header + 2 :]:
        if not line.strip().startswith("|"):
            continue  # every table line after the header is a row, wherever it stands
        number = len(found) + 1
        cells = _cells(line)
        if len(cells) != len(COLUMNS):
            raise CheckError(f"rule 9: {SIGNOFFS}: row {number}: the row has not six cells")
        row = dict(zip(COLUMNS, cells, strict=True))
        problem = _row_problem(row)
        if problem:
            raise CheckError(f"rule 9: {SIGNOFFS}: row {number}: {problem}")
        found.append({"row": number, **row})
    return found


def frozen_problems(root: Path) -> list[str]:
    """Rule 9: each `design` row's folder must still have the row's digest (screenshots aside)."""
    out: list[str] = []
    for row in rows(root):
        if row["kind"] != "design":
            continue
        try:
            same = version_digest(root, row["version"]) == row["digest"]
        except CheckError:
            same = False  # a signed-off folder that is gone has changed too
        problem = f"rule 9: {PROTOTYPE}/{row['version']}: a signed-off version changed"
        if not same and problem not in out:
            out.append(problem)
    return out


def signed_off(root: Path, version: str) -> bool:
    """Rule 12: a `design` row of VERSION records the digest its folder has now."""
    try:
        now = version_digest(root, version)
        return any(
            r["kind"] == "design" and r["version"] == version and r["digest"] == now
            for r in rows(root)
        )
    except CheckError:
        return False
