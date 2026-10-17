# Proof checks: live run 2, criterion c (SPEC-0010 rules 17, 20 and 22)

Date: 2026-10-17 (from `date -u`). The first real runs of the `proof` job (`.github/workflows/proof.yml`, ADR-0026) on this repository, the
seeded pull request of rule 20, and what the facts document reads from them. Everything below was read from the GitHub REST API
(`gh api --method GET`) and from the job logs of the Actions job-logs tool; nothing was typed in.

## 1. The readings

Each pull request ran the `proof` job on `opened` and again on `edited` (the body was updated); the later run of each head is shown. The
outcome is the one `outcome:` step that ended `success`; the reason is the JSON line `proof.py --json` printed in the step `Red-then-green`.

| Pull request | Head | Base | Outcome | Reason | Cause and note |
| --- | --- | --- | --- | --- | --- |
| #60 (the proof check) | `ac4b563` | `a11eaf3` | `not-proven` | `red-on-head` | both runs printed `python3: No module named pytest`: the runner had no pytest. A **false flag**, fixed by #61 (ADR-0027) |
| #61 (install pytest) | `e604e83` | `6d664b4` | `unknown` | the pull request changes `agk.toml` and an ADR, no test file (rule 12 reads that as `no-test-files`; the reason was not in the log lines read) | expected |
| #62 (seeded probe, closed unmerged) | `4bbc74f` | `8229831` | `not-proven` | `red-on-head` | both runs: `2 failed, 860 passed, 4 skipped`; the two failing kit tests run the installed lint step and the runner had no `ruff`. A **false flag**, fixed by #63 (ADR-0028) |
| #63 (install ruff too) | `f080bdf` | `8229831` | `unknown` | as #61: `agk.toml` and an ADR only | expected |
| **#64 (seeded probe, second try, closed unmerged)** | `096bcc9` | `df001e9` | **`not-proven`** | **`green-on-base`** | **the expected reading**: the base with the new test passes (`862 passed, 4 skipped in 467.44s (0:07:47)`), so the test could not fail. The JSON line: `{"base": "df001e9b04a8d76542ef4a88ba4dccce4b6bd4af", "head": "096bcc963f5652293ecd624b05482eef133b92a5", "outcome": "not-proven", "reason": "green-on-base", "test_files": ["tests/kit_dev/test_seeded_proof_probe.py"]}` |

So: the seeded pull request is flagged as it should be (#64), once the job has the tools the project's tests need. The two earlier
`red-on-head` readings (#60, #62) were the job's environment, not the pull requests; they are the first entries of the weekly record
of rule 22 and are false flags, for the maintainers to mark. No **real** pull request with a test and a change has run since the fix
(#61 and #63 changed no test); the next one (day 13) is the first `proven` expected in CI.

Not shown: a `proven` in CI. Locally `proof.py --base origin/main` read `proven` for #60 on 2026-10-17
(`docs/runs/proof-checks-live-1.md` section 5).

## 2. What the facts document reads (SPEC-0009 rule 14, SPEC-0010 rule 17)

`python3 scripts/agk/facts.py --today 2026-10-17 .` on `main` at `df001e9` (clean work tree, `gh` as the source), the field `pull_requests[].proof`:

| Pull request | State | Head | `proof` |
| --- | --- | --- | --- |
| #56 to #59 | merged | `154764b`, `f32ce9b`, `cc0266b`, `7786503` | `unknown` (no `proof` workflow existed on those heads) |
| #60 | merged | `ac4b563` | `not-proven` |
| #61 | merged | `e604e83` | `unknown` |
| #62 | closed | `4bbc74f` | `not-proven` |
| #63 | merged | `f080bdf` | `unknown` |
| #64 | open | `096bcc9` | `not-proven` |

Over all 63 pull requests of the window: `unknown` 60, `not-proven` 3. The reader found the `proof` run by `head_sha`, the job named
`proof` and the one `outcome:` step that succeeded, on real data, with no change to `facts.py`. `drift` at the same commit: D1 to D7 all 0, total 0.

## 3. The jobs API on a real `proof` job (the `(verify)` of SPEC-0010 rule 17)

`GET repos/gbvraju/agk/actions/runs/39029670944/jobs` (the `proof` run of #64, `status: completed`, `conclusion: success`) returned the job
`proof` (id 117387433427) with every step, name and conclusion:

| Step | Name | Conclusion |
| --- | --- | --- |
| 1 | Set up job | success |
| 2 | Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262 | success |
| 3 | Run actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 | success |
| 4 | Red-then-green | success |
| 5 | outcome: proven | skipped |
| 6 | outcome: not-proven | success |
| 7 | outcome: skipped | skipped |
| 8 | outcome: unknown | skipped |

(followed by the post steps and `Complete job`). Names and conclusions are returned for every step, `skipped` included, so exactly one
`outcome:` step ends `success` and the reader needs nothing else. The fallback residual of SPEC-0010 (the job summary) is not needed
and stays only as a record. Recorded earlier on a `governance` job: `docs/runs/proof-jobs-api.md`.

## 4. Cost

`governance` runs the kit tests twice since #60 (the step `Tests of the checks` and the step `Project tests`, which runs the same command, ruled
`Q-K4-135`: keep), and each `proof` run runs them twice more. On the runner one run of the suite takes about eight minutes
(`467.44s` for the last run above), so a pull request now uses about 16 minutes of `governance` and about 16 of `proof`, in parallel jobs.
The register has the residual "duplicate kit-test run in this repository (CI minutes)", due 2027-01-31.
