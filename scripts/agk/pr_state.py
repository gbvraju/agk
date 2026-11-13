"""Is the pull request a draft when the governance run runs? (brief #1174, ADR-0499)

    python3 pr_state.py --pull FILE [--event-draft true|false]

`FILE` holds the answer of one `GET repos/{owner}/{repo}/pulls/<n>` that the workflow made when the
job ran; `--event-draft` is the draft state of the event payload, which can be stale: a builder
pushes and marks its pull request ready within a second, and the run that survives the concurrency
group may carry the payload of the push. Prints `true` only when the read says the pull request is
a draft and the payload, when given, says so too; else `false`. It fails closed: a missing, empty
or unreadable file, an error answer, or a `draft` that is not a JSON boolean prints `false`, so the
heavy steps run. Exits 0; a usage error exits 2. Reads a file only: no network, no model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

USAGE = "usage: pr_state.py --pull FILE [--event-draft true|false]"


def is_draft(pull_text: str, event_draft: str | None = None) -> bool:
    """True only when the run-time read says draft and the payload does not say ready."""
    if event_draft == "false":
        return False
    try:
        pull = json.loads(pull_text)
    except ValueError:
        return False
    return isinstance(pull, dict) and pull.get("draft") is True


def main(argv: list[str]) -> int:
    pull_file: str | None = None
    event_draft: str | None = None
    args = list(argv)
    while args:
        flag = args.pop(0)
        if flag in ("--pull", "--event-draft") and args:
            value = args.pop(0)
            if flag == "--pull":
                pull_file = value
            else:
                event_draft = value
        else:
            print(USAGE, file=sys.stderr)
            return 2
    if pull_file is None or event_draft not in (None, "", "true", "false"):
        print(USAGE, file=sys.stderr)
        return 2
    try:
        text = Path(pull_file).read_text(encoding="utf-8")
    except OSError:
        text = ""
    print("true" if is_draft(text, event_draft or None) else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
