# The jobs API returns every step name and conclusion (SPEC-0010 rule 17; ruling Q-K4-30)

Date: 2026-10-16 (from `date -u`). SPEC-0010 rule 17 has `facts.py` read the outcome of the `proof` job from the step names and
conclusions of its job, and marks it `(verify)` that GitHub returns them for every step. This record proves it on this repository,
read-only, before the reader is relied on.

## What was read

`GET repos/gbvraju/agk/actions/runs?head_sha=e35d4323fba984f21e1e46477477df43effeb163` and
`GET repos/gbvraju/agk/actions/runs/38967967041/jobs` (`gh api --method GET`, the caller's own login): the `governance` run of the
push that merged #58, `status: completed`, `conclusion: success`. Its one job (`id` 117199053163, `name: governance`) has 21 steps.
Only `name`, `conclusion` and `number` of each step are shown.

| Step | Name | Conclusion |
| --- | --- | --- |
| 1 | Set up job | success |
| 2 | Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262 | success |
| 3 | Run actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 | success |
| 4 | Install tooling | success |
| 5 | check_protected_changes | success |
| 6 | check_requirements | success |
| 7 | check_adrs | success |
| 8 | check_specs | success |
| 9 | check_neutrality | success |
| 10 | check_build_state | success |
| 11 | check_kit_tests | success |
| 12 | reviewers --check | success |
| 13 | reviewers --check-codeowners | success |
| 14 | PR body shape | skipped |
| 15 | Lint | success |
| 16 | Tests of the checks | success |
| 17 | Project tests | success |
| 18 | Secret scan | success |
| 35 | Post Run actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 | success |
| 36 | Post Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262 | success |
| 37 | Complete job | success |

## What it shows

- Every step of a completed job is returned with its `name`, its `number` and its `conclusion`: 21 of 21. Twenty ended `success` and one
  (`PR body shape`, guarded by `if: github.event_name == 'pull_request'` on a push) ended `skipped`. A skipped step is therefore
  listed with the conclusion `skipped`, which is what rule 17 needs: of the four `outcome:` steps of the `proof` job, three end
  `skipped` and one `success`, and the reader takes the one that succeeded.
- The run list answers `?head_sha=` with the runs of that commit, each with `name` (the workflow's name), `event`, `status` and
  `conclusion`; the reader selects the run named `proof` and its job named `proof`.
- A run that is still in progress returns `null` conclusions for the steps that have not finished (read on the run of the next
  push, `status: in_progress`). The reader treats a missing conclusion as "no step succeeded" and so reads `"unknown"`, never an outcome.

## What it does not show

- The `proof` workflow does not exist on `main` yet. The first real `proof` job is read after the pull request that adds it is
  merged, and recorded in `docs/runs/proof-checks-live-2.md`. The residual of SPEC-0010 (the fallback is the job summary) stays open until
  then, with its date.
