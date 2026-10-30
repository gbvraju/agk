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
An unreadable response and no full run fail, and the next push re-runs in full. A cancelled full
run is never the latest while another full run of the head is not cancelled, and runs created in
the same second are ordered by run id (brief #272, ADR-0162).

A red full run fails unless only body steps failed in it: a failure of the steps that read the pull
request body (`BODY_STEPS`, the steps of the workflow that run on an edit and take the body) is
cured by editing the body, and the partial run repeats those steps and decides. For that the
script exits 4 and prints `jobs <run id>` (digits only), the workflow makes one more `GET` of
`actions/runs/<id>/jobs` and calls the script again with `--jobs FILE`. The red run then passes
when it has at least one failed step and every failed step is a body step; any other failed step,
no failed step (an infrastructure failure) and an unreadable response fail.

A skipped step hides a check that never ran (brief #261, ADR-0159): GitHub shows a step skipped by
its own `if:` and one skipped because an earlier step failed alike. So a red run with a skipped
step that is not a body step (which the partial run repeats) is not cured, unless the step is
skipped on every full run by its own condition (`OWN_CONDITION`), or it is `Project tests` in the
kit's own repository (the run's `Release check` ran: `KIT_ONLY`). A skipped step whose name starts
with `Post ` is a clean-up step that GitHub skips in any failed job and hides no check (brief #349).
Otherwise the message names those steps: "the last full run did not reach <steps>; push a commit
or re-run it". Every other message names the rule, never a value or a step.
File only: no network, no model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

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
# Skipped on a full run by their own condition only, never by an earlier failure (pinned to the
# workflow by a test): `Latest full run` runs on an edit only; `Release check` (with `!cancelled()`)
# runs only where `kit/agk-kit.mk` is.
OWN_CONDITION = ("Latest full run", "Release check")
# `Project tests` is skipped by its own condition where `kit/agk-kit.mk` is, which a run shows by
# its `Release check` having run; anywhere else a skipped `Project tests` never ran.
KIT_ONLY = ("Project tests", "Release check")
# GitHub skips some post steps in any failed job (the cache action saves only after a job that
# succeeded; `actions/setup-python` skips its post step): a skipped step whose name starts with
# `Post ` hides no check (brief #349, ADR-0197).
POST = "Post "


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


def not_reached(jobs: Path) -> list[str]:
    """The skipped steps of a run that the partial run does not repeat and that no own condition
    of theirs explains, in the order of the run."""
    listed = json.loads(jobs.read_text(encoding="utf-8"))["jobs"]
    hidden = []
    for job in (j for j in listed if isinstance(j, dict)):
        steps = [s for s in (job.get("steps") or []) if isinstance(s, dict)]
        conclusion = {str(s.get("name")): s.get("conclusion") for s in steps}
        kit = conclusion.get(KIT_ONLY[1], "skipped") != "skipped"
        for s in steps:
            name = str(s.get("name"))
            if s.get("conclusion") != "skipped" or name in BODY_STEPS or name in OWN_CONDITION:
                continue
            if name.startswith(POST):
                continue
            if name == KIT_ONLY[0] and kit:
                continue
            hidden.append(name)
    return hidden


def newest(run: dict) -> tuple[str, int]:
    """The order of runs: `created_at`, ties broken by the larger run id (brief #272)."""
    rid = run.get("id")
    return str(run.get("created_at") or ""), rid if isinstance(rid, int) else 0


def live(full: list[dict]) -> list[dict]:
    """The full runs that may be the latest: a cancelled run (one the concurrency group replaced)
    never is while another run of the head is not cancelled; with only cancelled runs, all of them
    (brief #272)."""
    kept = [r for r in full if r.get("conclusion") != "cancelled"]
    return kept or full


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
    latest = max(live(full), key=newest)
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
        hidden = not_reached(jobs) if jobs is not None else []
        if hidden:
            raise CheckError(
                f"rule 2: the last full run did not reach {', '.join(hidden)}; "
                "push a commit or re-run it"
            )
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
