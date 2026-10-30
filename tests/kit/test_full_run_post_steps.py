"""An edited description cures a full run that failed only on the description (brief #349).

GitHub skips some `Post …` steps in any failed job: the cache action saves only after a job that
succeeded, and `actions/setup-python` skips its post step after a failure. `full_run.py` counted
those as steps the run never reached, so an edit could never cure a run that failed only on the
body (measured on #339 head a5439ff, job 123926216899). A `Post …` step that was skipped is now
ignored; every other step is judged as before. And the workflow's `PR body file` step runs unless
the run is cancelled, so the body steps after a failed `Latest full run` can read the body.
Saved responses; no network.
"""

from __future__ import annotations

import re

from test_full_run import FULL_STEPS, HIDDEN, check_jobs, jobs_with
from test_workflow import WORKFLOW, step_blocks

SETUP_PYTHON = "Run actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
# The steps of the measured job that `FULL_STEPS` does not list, in the order of the job.
CACHE = "Restore the secret scanner"
POSTS = (
    "Post Restore the secret scanner",
    f"Post {SETUP_PYTHON}",
)


def measured(skipped=(), posts=("skipped", "skipped")) -> dict:
    """The jobs of the measured full run: `PR body shape` failed, the cache restored, and the two
    `Post …` steps of the cache and of setup-python with the given conclusions."""
    jobs = jobs_with(skipped=skipped, project=False)
    steps = jobs["jobs"][0]["steps"]
    names = [s["name"] for s in steps]
    at = names.index("Project tests")
    steps.insert(at, {"name": CACHE, "status": "completed", "conclusion": "success"})
    end = names.index(FULL_STEPS[-2]) + 1  # before `Post Run actions/checkout…`
    for offset, (name, conclusion) in enumerate(zip(POSTS, posts, strict=True)):
        steps.insert(end + offset, {"name": name, "status": "completed", "conclusion": conclusion})
    return jobs


def test_the_measured_run_a_body_failure_with_skipped_post_steps_is_cured(tmp_path):
    """REQ-039: brief #349 answers 1 and 3. The run of #339 a5439ff, cured by an edit."""
    out = check_jobs(tmp_path, measured())
    assert (out.returncode, out.stdout) == (
        0,
        "ok full-run (the failed steps read the body only)\n",
    )


def test_a_run_that_stopped_before_a_real_step_is_still_not_cured(tmp_path):
    """REQ-039: brief #349 answers 1 and 3. A skipped real step still blocks, and the message names
    it and never a `Post …` step."""
    out = check_jobs(tmp_path, measured(skipped=HIDDEN))
    assert out.returncode == 1
    assert out.stdout == (
        "FAIL full-run: rule 2: the last full run did not reach Lint, Tests of the checks, "
        "Secret scan; push a commit or re-run it\n"
    )


def test_a_post_step_that_failed_is_judged_as_today(tmp_path):
    """REQ-039: brief #349 answer 1. Only a skipped `Post …` step is ignored; a failed one is a
    failed step that is not a body step."""
    out = check_jobs(tmp_path, measured(posts=("failure", "skipped")))
    assert out.stdout == (
        "FAIL full-run: rule 2: the latest full governance run of the head did not succeed\n"
    )


def test_a_skipped_step_named_like_a_post_step_only_in_part_is_not_ignored(tmp_path):
    """REQ-039: brief #349 answer 1. The name must start with `Post ` (with the space)."""
    out = check_jobs(tmp_path, measured(skipped=("Lint",)))
    assert "did not reach Lint;" in out.stdout
    jobs = measured()
    jobs["jobs"][0]["steps"].append(
        {"name": "Postscript", "status": "completed", "conclusion": "skipped"}
    )
    out = check_jobs(tmp_path, jobs)
    assert out.stdout == (
        "FAIL full-run: rule 2: the last full run did not reach Postscript; "
        "push a commit or re-run it\n"
    )


def test_the_body_file_step_runs_unless_the_run_is_cancelled():
    """REQ-039: brief #349 answers 2 and 3. After a failed `Latest full run` the body file is still
    written, so the body steps read the body instead of failing on a missing file."""
    blocks = step_blocks(WORKFLOW.read_text(encoding="utf-8"))
    head = blocks["PR body file"].split("\n        run:", 1)[0]
    # brief #348: and not while the kit is paused
    paused = r" && steps\.paused\.outputs\.paused != 'true'"
    assert re.search(r"(?m)^        if: \$\{\{ !cancelled\(\)" + paused + r" \}\}$", head)
