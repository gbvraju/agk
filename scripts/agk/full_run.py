"""Did the latest full `governance` run on this head succeed? (brief #216)

    python3 full_run.py --runs FILE --head SHA [--jobs FILE]

An edited description starts a partial `governance` run: only the steps that read the pull request
body. The required check reads the latest `governance` run on the head, so a partial run that is
green on the body steps alone must not replace a failed full run of the same commit. The partial
run therefore starts with this check. FILE is the saved response of one `GET` of the workflow runs
of the head (`actions/runs?head_sha=...`, which the workflow makes); a run counts as full when its
run name is `governance full` (the `run-name` of the workflow). The check passes when the latest
full run of this head succeeded. When that run is still queued or in progress it prints `waiting`
and exits 3, and the workflow polls the same GET again (every 30 seconds, for at most 20 minutes).
An unreadable response and no full run fail, and the next push re-runs in full.

A red full run fails unless only body steps failed in it: a failure of the steps that read the pull
request body (`BODY_STEPS`, the steps of the workflow that run on an edit and take the body) is
cured by editing the body, and the partial run repeats those steps and decides. For that the
script exits 4 and prints `jobs <run id>` (digits only), the workflow makes one more `GET` of
`actions/runs/<id>/jobs` and calls the script again with `--jobs FILE`. The red run then passes
when it has at least one failed step and every failed step is a body step; any other failed step,
no failed step (an infrastructure failure) and an unreadable response fail. Messages name the
rule, never a value or a step.
File only: no network, no model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from common import CheckError, run

NAME = "full-run"
USAGE = "usage: full_run.py --runs FILE --head SHA [--jobs FILE]"
FULL = "governance full"
WAITING = 3  # the latest full run is still running: the caller polls again
JOBS = 4  # the latest full run is red: the caller reads its jobs and calls again with --jobs
BODY_STEPS = (
    "PR body file",
    "PR states and open pull requests",
    "check_specs",
    "check_pr_mode",
    "PR body shape",
)
OK_STEP = frozenset({None, "success", "skipped", "neutral"})


def failed_steps(jobs: Path) -> list[tuple[str, str]]:
    """(name, conclusion) of the failed steps of the jobs of a run (`actions/runs/<id>/jobs`)."""
    try:
        listed = json.loads(jobs.read_text(encoding="utf-8"))["jobs"]
        if not isinstance(listed, list):
            raise TypeError
    except (OSError, ValueError, KeyError, TypeError):
        raise CheckError(
            "rule 2: the jobs of the latest full governance run cannot be read"
        ) from None
    return [
        (str(s.get("name")), str(s.get("conclusion")))
        for job in listed
        if isinstance(job, dict)
        for s in job.get("steps") or []
        if isinstance(s, dict) and s.get("conclusion") not in OK_STEP
    ]


def check(runs: Path, head: str, jobs: Path | None = None) -> int:
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
        if isinstance(r, dict) and r.get("display_title") == FULL and r.get("head_sha") == head
    ]
    if not full:
        raise CheckError("rule 2: the head has no full governance run")
    latest = max(full, key=lambda r: str(r.get("created_at") or ""))
    if latest.get("status") != "completed":
        print(f"waiting {NAME}")
        return WAITING
    if latest.get("conclusion") != "success":
        number = latest.get("id")
        if jobs is None and isinstance(number, int) and not isinstance(number, bool) and number > 0:
            print(f"jobs {number}")
            return JOBS
        failed = failed_steps(jobs) if jobs is not None else []
        # only a run that failed, in steps that failed (not cancelled or timed out), in body steps
        curable = latest.get("conclusion") == "failure" and bool(failed)
        if not curable or any(c != "failure" or n not in BODY_STEPS for n, c in failed):
            raise CheckError("rule 2: the latest full governance run of the head did not succeed")
        print(f"ok {NAME} (the failed steps read the body only)")
        return 0
    print(f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    opts = dict(zip(args[::2], args[1::2], strict=False))
    if len(args) % 2 or not {"--runs", "--head"} <= set(opts) <= {"--runs", "--head", "--jobs"}:
        print(USAGE, file=sys.stderr)
        return 2
    jobs = Path(opts["--jobs"]) if "--jobs" in opts else None
    return run(NAME, lambda: check(Path(opts["--runs"]), opts["--head"], jobs))


if __name__ == "__main__":
    sys.exit(main())
