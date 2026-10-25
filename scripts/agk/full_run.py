"""Did the latest completed full `governance` run on this head succeed? (brief #216)

    python3 full_run.py --runs FILE --head SHA

An edited description starts a partial `governance` run: only the steps that read the pull request
body. The required check reads the latest `governance` run on the head, so a partial run that is
green on the body steps alone must not replace a failed full run of the same commit. The partial
run therefore starts with this check. FILE is the saved response of one `GET` of the workflow runs
of the head (`actions/runs?head_sha=...`, which the workflow makes); a run counts as full when its
run name is `governance full` (the `run-name` of the workflow). The check fails unless the latest
completed full run of this head succeeded; an unreadable response, no full run and a full run that
is still running all fail, and the next push re-runs in full. Messages name the rule, never a value.
File only: no network, no model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from common import CheckError, run

NAME = "full-run"
USAGE = "usage: full_run.py --runs FILE --head SHA"
FULL = "governance full"


def check(runs: Path, head: str) -> int:
    try:
        data = json.loads(runs.read_text(encoding="utf-8"))
        found = data["workflow_runs"]
        if not isinstance(found, list):
            raise TypeError
    except (OSError, ValueError, KeyError, TypeError):
        raise CheckError("rule 2: the workflow runs of the head cannot be read") from None
    full = [
        r
        for r in found
        if isinstance(r, dict)
        and r.get("display_title") == FULL
        and r.get("head_sha") == head
        and r.get("status") == "completed"
    ]
    if not full:
        raise CheckError("rule 2: the head has no completed full governance run")
    latest = max(full, key=lambda r: str(r.get("created_at") or ""))
    if latest.get("conclusion") != "success":
        raise CheckError("rule 2: the latest full governance run of the head did not succeed")
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    opts = dict(zip(args[::2], args[1::2], strict=False))
    if len(args) % 2 or set(opts) != {"--runs", "--head"}:
        print(USAGE, file=sys.stderr)
        return 2
    return run(NAME, lambda: check(Path(opts["--runs"]), opts["--head"]))


if __name__ == "__main__":
    sys.exit(main())
