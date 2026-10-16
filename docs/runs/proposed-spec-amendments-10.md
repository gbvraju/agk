# Proposed spec amendments 10 (SPEC-0007)

Date: 2026-10-15 (from `date -u`). Found while building SPEC-0007 (day 9, item B; ADR-0016). Approved specs change
only through a proposal like this one (principle 6). **Applied on 2026-10-15, on the maintainers' instruction, by the docs pull
request that also adds `docs/runs/metrics-run-1.md`**; before that, the code was ahead of the Approved text of the rules below.

## SPEC-0007 (`docs/specs/0007-metrics.md`)

1. **Rule 8, `protected_classes` "at the merge base".** Now: the classes of `config/protected-paths.txt` "at the merge
   base". Built: the file is read at the parent of the merge commit (`merge_commit_sha^1`) for a merged pull request
   and at `base.sha` of the pull request for a closed one. Reason: a squash merge keeps no branch, so the fork point is
   not in the history of the default branch; the parent of the squash commit is the tip the pull request was merged onto.
   Proposed: replace "at the merge base" with "at the parent of the merge commit (merged) or the pull request's base
   commit (closed)".
2. **Rules 14, 15 and 16, the first line.** Rule 14 says the first line of the body is `agk metrics ...`; rules 15 and 16
   say the duplicate and `INCOMPLETE` flags are printed "on the first line". Built: flag lines come first (`duplicate
   metrics issues: #a,#b; #a is the one updated`, then `INCOMPLETE: closed in window N, recorded M`), and the `agk metrics
   ...` header follows; a clean body starts with the header. Proposed: say so in rule 14.
3. **Rule 20, "recorded" fixtures.** Now: "recorded GitHub responses". Built: the files have the shape of real responses
   (probed with GET on `gbvraju/agk` on 2026-10-15: `pulls/N`, `issues/N/comments`, `pulls/N/files`, `pulls/N/commits`,
   `commits/SHA/check-runs`, `actions/jobs/ID`) with the values written for each case, because cases such as a failed
   `governance` run and a `Verdict: rejected` comment do not exist in this repository. Proposed: "responses in the shape
   of the recorded ones".
4. **Rule 6, `(verify)` resolved.** The check run `id` equals the Actions job id and `actions/jobs/ID` returns
   `steps` with `name` and `conclusion` (one GET on 2026-10-15). Proposed: drop the `(verify)` in rule 6.
5. **Rule 15, options.** Built: `--repo OWNER/REPO` (default: `GITHUB_REPOSITORY`, then the `origin` URL) is added for
   live runs; `--print-body` is the default mode. Proposed: add `--repo` to the list in rule 15.
6. **Rule 19, protected classes.** Built: the ADR also names `tests/kit_dev/` (the wiring tests) and `docs/requirements.md`
   (REQ-012 text), which check_protected_changes requires; rule 19 names `.github/`, `scripts/agk/`, `tests/kit/`, `kit/`.
   Proposed: add the two classes.
7. **Rule 17, `fetch-depth: 0` and the workflow input.** Built as stated; one addition: the `today` input reaches the
   shell through an environment variable (`INPUT_TODAY`), never interpolated into the script text. Proposed: say so.
7b. **Rule 20, the verdict-suffix case.** Added at the maintainers' fix list on the build pull request: a fixture case whose
   verdict lines carry trailing text (`Verdict: cleared <sha> (#N)`, `Verdict: fix list (round 2)`) shows they are not
   verdicts. Applied to the list of cases in rule 20.

## Question (answered)

None.
