# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Requirements file: unique ids, valid Status, a test marker for every `done` requirement and, per
the `ac_coverage` setting (`warn` or `block`), for every criterion `ACn` of it (SPEC-0010). A
`retired` requirement has no marker left: the check names the requirement and the files
(brief 244).

In a sidecar only (SPEC-0041 rule 8, brief #1502), `--comments FILE [--base REF]` also fails a
requirement with a `- Source: observed in code` line that moves to `done` from the merge base
without the `Confirm: <C> REQ-nnn` line of the person's terminal confirmation at a `<C>` of the
head's history where its entry equals the current one apart from its status line. Team and solo
mode take no such reading."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    ALLOWED_STATUS,
    REQ_HEADER,
    CheckError,
    ac_coverage_mode,
    ac_markers_for,
    ac_shortfalls,
    agent_apps,
    base_arg,
    base_context,
    markers_for,
    parse_requirements,
    personal_table,
    repo_root,
    run,
    show,
    utf8_output,
)

NAME = "requirements"
PATH = "docs/requirements.md"
OBSERVED = re.compile(r"^- Source: observed in code\b")


def dirs_arg(argv: list[str]) -> list[str]:
    dirs: list[str] = []
    for i, arg in enumerate(argv):
        if arg == "--tests-dir":
            if i + 1 >= len(argv):
                raise CheckError("--tests-dir needs a value")
            dirs.append(argv[i + 1])
    return dirs


def entries(text: str) -> dict[str, str]:
    """REQ id -> its entry: the header line up to the next heading, line endings kept."""
    found: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines(keepends=True):
        header = REQ_HEADER.match(line)
        if header:
            current = header.group(1)
            found.setdefault(current, "")
        elif line.startswith("#"):
            current = None
        if current is not None:
            found[current] += line
    return found


def terminal_failures(root: Path, argv: list[str], reqs: list[dict]) -> list[str]:
    """SPEC-0041 rule 8: an observed requirement that moves to `done` needs its confirmation."""
    if "--comments" not in argv or personal_table(root) is None:
        return []
    from check_final_clearance import comments_of  # noqa: PLC0415 - the sidecar reading only
    from check_specs import in_history  # noqa: PLC0415
    from reviewers import derived_only, solo_person, status_moved_only, terminal_shas

    at = argv.index("--comments") + 1
    if at >= len(argv):
        raise CheckError("--comments needs a value")
    mb = base_context(root, NAME, base_arg(argv))
    if mb is None:
        return []
    derived = derived_only(comments_of(Path(argv[at])), agent_apps(root), solo_person(root))
    now = entries((root / PATH).read_text(encoding="utf-8"))
    before = {r["id"]: r["status"] for r in parse_requirements(show(root, mb, PATH) or "")}
    problems: list[str] = []
    for req in reqs:
        rid, entry = req["id"], now.get(req["id"], "")
        observed = any(OBSERVED.match(line) for line in entry.splitlines())
        if req["status"] != "done" or before.get(rid) == "done" or not observed:
            continue
        shas = terminal_shas(derived, rid)
        if not shas:
            problems.append(f"{rid}: SPEC-0041 rule 8: no Confirm line of a terminal confirmation")
        elif not any(
            in_history(root, sha)
            and status_moved_only(entries(show(root, sha, PATH) or "").get(rid, ""), entry)
            for sha in shas
        ):
            problems.append(f"{rid}: SPEC-0041 rule 8: the entry changed after the confirmed sha")
    return problems


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    argv = list(sys.argv[1:] if argv is None else argv)
    root = repo_root()
    path = root / PATH
    if not path.is_file():
        raise CheckError(f"{PATH} is missing")
    reqs = parse_requirements(path.read_text(encoding="utf-8"))
    if not reqs:
        raise CheckError(f"{PATH} defines no requirement")
    dirs = dirs_arg(argv)
    markers = markers_for(root, dirs)
    mode = ac_coverage_mode(root)

    problems: list[str] = []
    seen: set[str] = set()
    for req in reqs:
        rid = req["id"]
        if rid in seen:
            problems.append(f"{rid}: duplicate id (line {req['line']})")
        seen.add(rid)
        if req["status_count"] != 1:
            problems.append(f"{rid}: needs exactly one '- Status:' line")
        elif req["status"] not in ALLOWED_STATUS:
            problems.append(f"{rid}: Status is not one of {', '.join(ALLOWED_STATUS)}")
        elif req["status"] == "done" and rid not in markers:
            problems.append(f"{rid}: done requires a test marker under the test directories")
        elif req["status"] == "retired" and rid in markers:
            # the one block of `retired` (brief 244): the pull request that retires a requirement
            # removes its tests or retags them; the message names files, never the tests' text
            files = ", ".join(markers[rid])
            problems.append(f"{rid}: retired requirement still has a test marker in {files}")
    problems += terminal_failures(root, argv, reqs)
    shortfalls = [text for _, text in ac_shortfalls(reqs, ac_markers_for(root, dirs))]
    problems += shortfalls if mode == "block" else []
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if mode == "warn":
        for text in shortfalls:
            print(f"warn {NAME}: {text}")
    if not problems:
        print(f"ok {NAME} ({len(reqs)} requirements)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
