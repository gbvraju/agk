# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The grill's questions (SPEC-0073 rules 2, 3 and 11; REQ-080; brief #1933, ADR-0801).

Usage: python3 scripts/agk/grill.py questions [--depth light|standard|deep] [--playbook KIND]
           [--answers FILE] [--root DIR]

Prints the grill items to ask, in order: the items of `config/playbooks/default.toml` at or below
the depth, then the work type's own items (KIND, else the declared `[delivery] work_type`, else
none), then `success` among the critical items. Each item is one line `<id> (critical|-) <text>`
followed by `Recommended: <steward fills>`, the placeholder the grill skill fills. The last line is
`budget: <n>`, the depth's question budget. An id the answers file holds (its `answers` list, and
its `grill` list) is never printed. Without `--depth` the depth is `[quality] grill`. Reads files
only: no network, no model. Exit 0 ok, 1 refused, 2 usage. `record` and `ready` come later.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import playbook_format  # noqa: E402
from common import CheckError, run, utf8_output  # noqa: E402

from config import quality_settings  # noqa: E402

NAME = "grill"
USAGE = __doc__.split("\n\n", 2)[1]
FLAGS = ("--depth", "--playbook", "--answers", "--root")
BUDGET = {"light": 5, "standard": 12, "deep": 20}  # SPEC-0073 rule 11
RECOMMENDED = "Recommended: <steward fills>"
SUCCESS = "success"  # SPEC-0073 rule 3: a discovery id, the fifth critical item
WORK_TYPE = "(setting: work-type)"


def _checked(path: Path, root: Path) -> Path:
    if not path.is_file():
        raise CheckError(
            f"rule 3: the work type has no playbook under {playbook_format.FOLDER}/ {WORK_TYPE}"
        )
    if playbook_format.problems(path, root):
        raise CheckError(f"rule 3: the playbook fails check_playbooks.py {WORK_TYPE}")
    return path


def _work_type(root: Path, kind: str | None) -> Path | None:
    """The work type's playbook: KIND, else the declared one, else None."""
    if kind is None:
        kind, found = playbook_format.declaration(root)
        if found:
            raise CheckError(found[0])
        if kind is None:
            return None
    elif kind not in playbook_format.WORK_TYPES:
        raise CheckError(f"rule 3: the work type is not one of the work types {WORK_TYPE}")
    return _checked(playbook_format.path(root, kind), root)


def answered(path: str | None) -> set[str]:
    """The ids the answers file holds; refused naming `--answers`, never read as empty."""
    if path is None:
        return set()
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise CheckError("rule 2: the answers file cannot be read (setting: --answers)") from None
    lists = [data.get(k, []) for k in ("answers", "grill")] if isinstance(data, dict) else [None]
    rows = [r for found in lists if isinstance(found, list) for r in found]
    if any(not isinstance(f, list) for f in lists) or any(not isinstance(r, dict) for r in rows):
        raise CheckError("rule 2: the answers file is not an object of lists (setting: --answers)")
    return {r["id"] for r in rows if isinstance(r.get("id"), str)}


def questions(root: Path, depth: str | None, kind: str | None, answers: str | None) -> list[str]:
    """The lines `questions` prints, the budget line last."""
    depth = depth or quality_settings(root)["grill"]
    base = playbook_format.default_playbook(root)
    if base is None:
        raise CheckError(f"rule 3: there is no default playbook under {playbook_format.FOLDER}/")
    _checked(base, root)
    own = _work_type(root, kind)
    rank = playbook_format.GRILL_DEPTHS.index(depth)
    items = [*playbook_format.grill_items(base), *(playbook_format.grill_items(own) if own else [])]
    texts = dict(playbook_format.discovery(base))
    items.append((SUCCESS, texts[SUCCESS], playbook_format.GRILL_DEPTHS[0], True))
    done = answered(answers)
    lines = []
    for item_id, text, item_depth, critical in items:
        if item_id in done or playbook_format.GRILL_DEPTHS.index(item_depth) > rank:
            continue
        lines += [f"{item_id} {'(critical)' if critical else '-'} {text}", RECOMMENDED]
    return [*lines, f"budget: {BUDGET[depth]}"]


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] != "questions" or len(args) % 2 == 0:
        print(USAGE, file=sys.stderr)
        return 2
    words = iter(args[1:])
    opts = dict(zip(words, words, strict=True))
    depth = opts.get("--depth")
    if any(flag not in FLAGS for flag in opts) or (depth is not None and depth not in BUDGET):
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(opts.get("--root", "."))

    def body() -> int:
        found = questions(root, depth, opts.get("--playbook"), opts.get("--answers"))
        print("\n".join(found))
        return 0

    return run(NAME, body)


if __name__ == "__main__":
    sys.exit(main())
