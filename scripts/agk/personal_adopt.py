# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Personal adopt: the model's proposals become sidecar records only through citations that exist.

    python3 personal_adopt.py check FILE [--clone DIR] [--sidecar DIR]
    python3 personal_adopt.py render FILE [--clone DIR] [--sidecar DIR] [--today YYYY-MM-DD]

SPEC-0041 build (g), part 2, rules 13, 14 and 28 (ADR-0633). FILE is the JSON the skill
`/agk:personal-adopt` has the model write: `requirements`, `specs` and `adrs`, each record a
`title` and `claims`, each claim a `statement` and `citations` of the form `path:start-end@blob`.
`check` refuses each claim whose citation does not exist in the product clone (the path is
tracked, the blob is that path's blob at a commit, the range lies inside it), that quotes more code
lines than `[personal] quote_lines` or in which the data guard finds a value; one line per refused
claim names its position and the rule, never its text. `render` writes the records with a claim
left into the sidecar in one commit: requirements `planned` with a `Source:` line, specs `Draft`,
ADRs `Proposed` with `- Kind: recorded`; nothing is decided until `personal.py confirm`. Every git
call on the clone is read-only with `--no-optional-locks` (rule 4). Standard library only; no
network. Refusals name the setting or the rule, never a value.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess  # nosec B404 - fixed git argument lists only, no shell
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (  # noqa: E402
    REQ_HEADER,
    TITLE_TEXT,
    CheckError,
    next_free_ids,
    personal_table,
    utf8_output,
)
from guard import scan_text  # noqa: E402
from survey import _git, blob_sizes, find_sidecar, read_blobs, tracked  # noqa: E402

USAGE = (
    "usage: personal_adopt.py check|render FILE [--clone DIR] [--sidecar DIR] [--today YYYY-MM-DD]"
)
KINDS = {"requirements": "docs/requirements.md", "specs": "docs/specs/", "adrs": "docs/adr/"}
CITATION = re.compile(
    r"(?P<path>[^@\s]+):(?P<start>\d+)-(?P<end>\d+)@(?P<blob>[0-9a-f]{40}|[0-9a-f]{64})"
)
QUOTE_MIN = 8  # a cited line shorter than this, stripped, is not counted as an excerpt
PROJECT_FIRST_REQ = 101  # the sidecar's text keeps REQ-001 to REQ-099 for AGK (Q-1504-1)
SHAPE = "the proposals file is not of the shape of SPEC-0041 rule 13"
RULE13 = "SPEC-0041 rule 13"
FORMAT = f"{RULE13}: not a citation of the form path:start-end@blob"
UNTRACKED = f"{RULE13}: the path is not tracked"
NO_BLOB = f"{RULE13}: the blob is not that path's blob at a commit"
OUTSIDE = f"{RULE13}: the range lies outside the blob"
EXCERPT = "SPEC-0041 rule 28: a code excerpt beyond the setting personal.quote_lines"
GUARDED = "SPEC-0041 rule 28: the data guard finds a secret or personal value (path class {})"
DIRTY = "render needs a clean sidecar work tree (SPEC-0041 rule 14)"
OWNER = "reviewer group (a team from config/reviewers.yaml)"
CONTEXTS = (
    "- personal: the sidecar holds this spec, drafted from the product's code\n"
    "- kit, github, local, stacks: not applicable: drafted in personal mode from code (verify)\n"
)


def _nonempty_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _links_ok(record: dict, key: str, data: dict) -> bool:
    links = record.get(key, [])
    size = len(data.get(key, []))
    return isinstance(links, list) and all(
        isinstance(i, int) and not isinstance(i, bool) and 0 <= i < size for i in links
    )


def load(path: Path) -> dict:
    """The proposals of ADR-0633 decision 1, else refused whole."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise CheckError(SHAPE) from None
    if not isinstance(data, dict) or not data or not set(data) <= set(KINDS):
        raise CheckError(SHAPE)
    for kind, links in (
        ("requirements", ()),
        ("specs", ("requirements",)),
        ("adrs", ("specs", "requirements")),
    ):
        records = data.get(kind, [])
        if not isinstance(records, list):
            raise CheckError(SHAPE)
        for record in records:
            claims = record.get("claims") if isinstance(record, dict) else None
            if not _nonempty_text(record.get("title") if claims else None) or not isinstance(
                claims, list
            ):
                raise CheckError(SHAPE)
            for item in claims:
                if not isinstance(item, dict) or not _nonempty_text(item.get("statement")):
                    raise CheckError(SHAPE)
                cites = item.get("citations")
                if (
                    not isinstance(cites, list)
                    or not cites
                    or not all(isinstance(c, str) for c in cites)
                ):
                    raise CheckError(SHAPE)
                if not isinstance(item.get("verify", False), bool):
                    raise CheckError(SHAPE)
            if not all(_links_ok(record, key, data) for key in links):
                raise CheckError(SHAPE)
    return data


def one_line(text: str) -> str:
    return " ".join(text.split())


class Clone:
    """Read-only views of the clone: its index, the blobs of a path in history, a blob's lines."""

    def __init__(self, root: Path):
        self.root = root
        self.index = tracked(root)
        self.history: dict[str, set[str]] = {}
        self.texts: dict[str, list[str] | None] = {}

    def blobs_of(self, path: str) -> set[str]:
        if path not in self.history:
            done = _git(self.root, "log", "--all", "-m", "--no-renames", "--format=", "--raw",
                        "--no-abbrev", "-z", "--", path)  # fmt: skip
            found = set()
            for part in done.stdout.decode("utf-8", "surrogateescape").split("\0"):
                fields = part.split()
                if part.startswith(":") and len(fields) >= 4:
                    found.update(b for b in fields[2:4] if b.strip("0"))
            self.history[path] = found
        return self.history[path]

    def lines(self, blob: str) -> list[str] | None:
        if blob not in self.texts:
            self.texts[blob] = None
            if blob in blob_sizes(self.root, [blob]):
                for _, data in read_blobs(self.root, [blob]):
                    self.texts[blob] = data.decode("utf-8", "replace").splitlines()
        return self.texts[blob]


def citation_problem(clone: Clone, citation: str) -> tuple[str | None, list[str]]:
    """(why the citation does not exist or None, the cited lines)."""
    found = CITATION.fullmatch(citation)
    if found is None:
        return FORMAT, []
    path, blob = found["path"], found["blob"]
    if path not in clone.index:
        return UNTRACKED, []
    if blob not in clone.blobs_of(path):
        return NO_BLOB, []
    lines = clone.lines(blob)
    start, end = int(found["start"]), int(found["end"])
    if lines is None or not 1 <= start <= end <= len(lines):
        return OUTSIDE, []
    return None, lines[start - 1 : end]


def claim_problem(clone: Clone, item: dict, quote_lines: int, where: str) -> str | None:
    cited: set[str] = set()
    for citation in item["citations"]:
        why, lines = citation_problem(clone, citation)
        if why:
            return why
        cited.update(one_line(x) for x in lines if len(one_line(x)) >= QUOTE_MIN)
    statement = one_line(item["statement"])
    if sum(1 for line in cited if line in statement) > quote_lines:
        return EXCERPT
    if scan_text(item["statement"]):
        return GUARDED.format(where)
    return None


def review(clone: Clone, data: dict, quote_lines: int) -> tuple[dict, list[str], int, int]:
    """{(kind, index): the claims left}, the refusal lines, the refused and the claim counts."""
    kept, said, refused, total = {}, [], 0, 0
    for kind, where in KINDS.items():
        for i, record in enumerate(data.get(kind, [])):
            total += len(record["claims"])
            if scan_text(record["title"]):
                said.append(f"refused: {kind}[{i}].title: {GUARDED.format(where)}")
                refused += len(record["claims"])
                continue
            left = []
            for j, item in enumerate(record["claims"]):
                why = claim_problem(clone, item, quote_lines, where)
                if why:
                    said.append(f"refused: {kind}[{i}].claims[{j}]: {why}")
                    refused += 1
                else:
                    left.append(item)
            if left:
                kept[(kind, i)] = left
    return kept, said, refused, total


def _sidecar_git(sidecar: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed git argument list, no shell
        ["git", *args], cwd=sidecar, capture_output=True, text=True, encoding="utf-8", check=False
    )


def citations_of(claims: list[dict]) -> list[str]:
    return sorted({c for item in claims for c in item["citations"]})


def existing(sidecar: Path) -> dict[tuple[str, str, tuple[str, ...]], str]:
    """(kind, title, citations) -> id of each record in the sidecar, so none is rendered twice."""
    out = {}
    req = sidecar / KINDS["requirements"]
    text = req.read_text(encoding="utf-8") if req.is_file() else ""
    rid, title = None, None
    for line in text.splitlines():
        if (header := REQ_HEADER.match(line)) is not None:
            found = TITLE_TEXT.match(line)
            rid, title = header[1], found[1] if found else ""
        elif rid and line.startswith("- Source: observed in code at "):
            out[("requirements", title, tuple(sorted(set(_cites(line)))))] = rid
    for kind, prefix in (("specs", "SPEC"), ("adrs", "ADR")):
        for path in sorted((sidecar / KINDS[kind]).glob("[0-9][0-9][0-9][0-9]-*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            head = lines[0].split(": ", 1) if lines else []
            if len(head) == 2:
                key = (kind, head[1], tuple(sorted(set(_cites("\n".join(lines))))))
                out[key] = f"{prefix}-{path.name[:4]}"
    return out


def _cites(text: str) -> list[str]:
    return [m.group(0) for m in CITATION.finditer(text)]


def slug(title: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", title.lower()))[:60].strip("-") or "record"


def points(claims: list[dict]) -> list[str]:
    return [one_line(c["statement"]) + (" (verify)" if c.get("verify") else "") for c in claims]


def observed(claims: list[dict]) -> list[str]:
    return [
        f"{i}. {p} (observed in code at {', '.join(sorted(c['citations']))})"
        for i, (p, c) in enumerate(zip(points(claims), claims, strict=True), 1)
    ]


def named(ids: list[str]) -> str:
    return ", ".join(ids) if ids else "none named (verify)"


def requirement_text(rid: str, title: str, claims: list[dict]) -> str:
    acs = "; ".join(f"AC{i} {p}" for i, p in enumerate(points(claims), 1))
    return (
        f"\n### {rid} — {one_line(title)}\n\n- Acceptance: {acs}\n"
        f"- Source: observed in code at {', '.join(citations_of(claims))}\n- Status: planned\n"
    )


def spec_text(sid: str, title: str, claims: list[dict], reqs: list[str]) -> str:
    return (
        f"# {sid}: {one_line(title)}\n\n- Status: Draft\n- Owner: {OWNER}\n"
        f"- Requirements: {named(reqs)}\n\n"
        f"Drafted from the product's code by `/agk:personal-adopt`; nothing here is decided until "
        "the "
        f"person runs `personal.py confirm {sid}` at their own terminal.\n\n## Rules\n\n"
        + "\n".join(observed(claims)) + f"\n\n## Contexts\n\n{CONTEXTS}"
    )  # fmt: skip


def adr_text(
    aid: str, title: str, claims: list[dict], specs: list[str], reqs: list[str], today: str
) -> str:
    return (
        f"# {aid}: {one_line(title)}\n\n- Status: Proposed\n- Date: {today}\n"
        f"- Deciders: the person, at `personal.py confirm {aid}`\n- Related: {named(specs)}\n"
        f"- Requirements: {named(reqs)}\n- Kind: recorded\n\n## Context\n\n"
        "A decision already in the product's code, recorded by `/agk:personal-adopt` from the "
        "lines "
        "it cites.\n\n## Decision\n\n" + "\n".join(observed(claims)) + "\n\n## Consequences\n\n"
        "Not shown by the citations (verify).\n\n## Residual\n\nNone recorded.\n"
    )  # fmt: skip


def plan(sidecar: Path, data: dict, kept: dict, today: str) -> tuple[dict[str, str], list[str]]:
    """{path: new text or the text to append}, the new ids in order; nothing written."""
    free = next_free_ids(sidecar, "HEAD")
    number = {
        "requirements": max(int(free["req"][4:]), PROJECT_FIRST_REQ),
        "specs": int(free["spec"]),
        "adrs": int(free["adr"]),
    }
    have, ids, new, writes = existing(sidecar), {}, [], {}
    appended = ""
    for kind in KINDS:
        for i, record in enumerate(data.get(kind, [])):
            if (kind, i) not in kept:
                continue
            claims, title = kept[(kind, i)], one_line(record["title"])
            key = (kind, title, tuple(citations_of(claims)))
            if key in have:
                ids[(kind, i)] = have[key]
                continue
            n = number[kind]
            number[kind] += 1
            reqs = [
                ids[("requirements", x)]
                for x in record.get("requirements", [])
                if ("requirements", x) in ids
            ]
            if kind == "requirements":
                rid = ids[(kind, i)] = f"REQ-{n:03d}"
                appended += requirement_text(rid, title, claims)
            elif kind == "specs":
                rid = ids[(kind, i)] = f"SPEC-{n:04d}"
                writes[f"{KINDS[kind]}{n:04d}-{slug(title)}.md"] = spec_text(
                    rid, title, claims, reqs
                )
            else:
                rid = ids[(kind, i)] = f"ADR-{n:04d}"
                specs = [ids[("specs", x)] for x in record.get("specs", []) if ("specs", x) in ids]
                writes[f"{KINDS[kind]}{n:04d}-{slug(title)}.md"] = adr_text(
                    rid, title, claims, specs, reqs, today
                )
            have[key] = rid
            new.append(rid)
    if appended:
        writes[KINDS["requirements"]] = appended
    return writes, new


def place(sidecar: Path, writes: dict[str, str]) -> dict[str, str | None]:
    """Write each file; the text before (None for a new file), to restore on a failure."""
    before: dict[str, str | None] = {}
    for rel, text in writes.items():
        path = sidecar / rel
        if rel == KINDS["requirements"]:
            old = path.read_text(encoding="utf-8")
            before[rel] = old
            path.write_text(old + ("" if old.endswith("\n") else "\n") + text, encoding="utf-8")
        else:
            before[rel] = None
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    return before


def restore(sidecar: Path, before: dict[str, str | None]) -> None:
    for rel, old in before.items():
        if old is None:
            (sidecar / rel).unlink(missing_ok=True)
        else:
            (sidecar / rel).write_text(old, encoding="utf-8")


def render(sidecar: Path, data: dict, kept: dict, today: str) -> tuple[list[str], list[str]]:
    """Rule 14: the planned writes, the guard over each, then one commit; (new ids, lines)."""
    from forge import FilesForge  # noqa: PLC0415 - `render` only
    from personal import commit_options  # noqa: PLC0415 - `render` only

    files = FilesForge(sidecar)
    with files.locked():
        state = _sidecar_git(sidecar, "status", "--porcelain")
        if state.returncode != 0 or state.stdout.strip():
            raise CheckError(DIRTY)
        writes, new = plan(sidecar, data, kept, today)
        for rel, text in writes.items():
            if scan_text(text):
                where = next(w for w in KINDS.values() if rel.startswith(w))
                raise CheckError(f"{GUARDED.format(where)}; nothing written")
        if not new:
            return [], ["render: nothing new; every record is already in the sidecar"]
        before = place(sidecar, writes)
        _sidecar_git(sidecar, "add", "--", *writes)
        subject = f"personal: adopt {', '.join(new)}"
        done = _sidecar_git(
            sidecar, *commit_options(sidecar, files.person), "-m", subject, "--", *writes
        )
        if done.returncode != 0:
            _sidecar_git(sidecar, "reset", "-q", "--", *writes)
            restore(sidecar, before)
            raise CheckError("the sidecar commit failed; nothing written (SPEC-0041 rule 14)")
    script = shlex.quote(str(Path(__file__).resolve().parent / "personal.py"))
    lines = [
        f"rendered: {', '.join(new)}",
        "next, at your own terminal (never in an agent session):",
    ]
    lines += [
        f"  python3 {script} confirm {rid} --sidecar {shlex.quote(str(sidecar))}" for rid in new
    ]
    return new, lines


def parse(args: list[str]) -> dict | None:
    if len(args) < 2 or args[0] not in ("check", "render"):
        return None
    out: dict = {"command": args[0], "file": args[1], "clone": ".", "sidecar": None, "today": None}
    rest = args[2:]
    while rest:
        flag = rest.pop(0)
        if flag not in ("--clone", "--sidecar", "--today") or not rest:
            return None
        out[flag[2:]] = rest.pop(0)
    return out


def run(options: dict) -> tuple[int, list[str]]:
    today = options["today"] or datetime.now(UTC).strftime("%Y-%m-%d")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
        raise CheckError("not a date of the form YYYY-MM-DD (option: --today)")
    probe = _git(Path(options["clone"]), "rev-parse", "--show-toplevel")
    if probe.returncode != 0:
        raise CheckError("the clone cannot be read as a git repository (option: --clone)")
    clone = Clone(Path(probe.stdout.decode("utf-8", "surrogateescape").strip()))
    sidecar = Path(options["sidecar"]) if options["sidecar"] else find_sidecar(clone.root)
    table = personal_table(sidecar)
    if table is None:
        raise CheckError("not a sidecar (setting: personal)")
    data = load(Path(options["file"]))
    kept, said, refused, total = review(clone, data, table.get("quote_lines", 0))
    tally = f"{refused} of {total} claims refused"
    if options["command"] == "check":
        return (1 if refused else 0), [*said, f"check: {tally}"]
    if not kept:
        return 1, [*said, f"render: nothing rendered; {tally}"]
    _new, lines = render(sidecar, data, kept, today)
    return 0, [*said, *lines, f"render: {tally}"]


def main(argv: list[str] | None = None, out=print) -> int:
    utf8_output()
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        out(USAGE)
        return 2
    try:
        code, lines = run(options)
    except CheckError as exc:
        out(f"refused: {exc}")
        return 1
    for line in lines:
        out(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
