# Shadow review 3 (SPEC-0003 rule 23)

Date of the run: 2026-10-15 (`date -u`). Third run of the three targets of shadow reviews 1 and 2, now with
`origin/main` fa06529 (PR #26: the reviewer sees `CLAUDE.md` and changed files in full, with a cross-file check; kit
0.6.1). Kit scripts and the `reviewer` subagent definition are from fa06529. Each target was checked out detached in
its own worktree; contexts were built with `--base <the PR's base commit>` and the **same minimal bodies** as shadow
review 2 (only `Advances:` and a dated `Build-state row:`). Each report was saved, and validated, before this
comparison was written. Reports are recorded verbatim. No report is invalid.

| PR | Commit | Base | Context `Truncated:` | Validator |
|---|---|---|---|---|
| #12 | bd381ef | 0114a93 | **yes** (`[truncated: 850 lines omitted]`) | `ok review-report`, `<!-- agk-review: verdict=cleared findings=0 truncated=true -->` |
| #6 | e001628 | b21f79c | **no** | `ok review-report`, `<!-- agk-review: verdict=cleared findings=0 truncated=false -->` |
| #22 | 071ded6 | e78d67d | **yes** (`[truncated: 499 lines omitted]`) | `ok review-report`, `<!-- agk-review: verdict=cleared findings=0 truncated=true -->` |

Each report restates its context's value. The #12 and #22 reports (verbatim):

~~~~
Verdict: cleared
Context truncated: yes

Findings: none
~~~~

The #6 report (verbatim):

~~~~
Verdict: cleared
Context truncated: no

Findings: none
~~~~

## Human verdicts (from shadow review 2, confirmed by the maintainers)

| PR | Commit | Human verdict | Human finding |
|---|---|---|---|
| #12 | bd381ef | fix list | CI no longer runs project tests |
| #6 | e001628 | fix list | CLAUDE.md rule 8 wrong for installed targets |
| #22 | 071ded6 (first commit) | fix list | installed check's tests not installed (principle 4) |

## Comparison

| PR | Agent verdict | Human verdict | Agreement | Human finding | Result | Agent findings |
|---|---|---|---|---|---|---|
| #12 | cleared | fix list | **no** | CI no longer runs project tests | **missed** | none |
| #6 | cleared | fix list | **no** | CLAUDE.md rule 8 wrong for installed targets | **missed** | none |
| #22 | cleared | fix list | **no** | installed check's tests not installed (principle 4) | **missed** | none |

No agent finding exists, so none is marked valid or noise. The result is the same as shadow review 2 on all three
targets: `cleared` against `fix list`, zero of three human findings caught.

### #22: what the agent cited

The agent cited nothing: the report has no findings, so it did not cite ADR-0001 decision 4 (`Checks live in
scripts/agk/ ... and are exercised by tests in tests/kit/`) or any other rule. The material was in its context:
ADR-0001 is embedded under "Referenced specs and ADRs", the diff hunks show the new tests at `tests/kit_dev/`
(H11-H14), and `CLAUDE.md` is now present in full (at the end of the context, after Principles). That decision 4 is
the Approved text that the defect contradicts is read from the ADR; the agent did not make that link, and whether it
is meant to is for the maintainers (principle 1).

### What changed in the context since shadow review 2 (facts)

- `CLAUDE.md` is present for #22 (it was absent). For #6 the file is now embedded in full as a changed file, so
  rule 8 ("8. Product-neutral: nothing names a company, product, person or environment...") is in the context; in
  shadow review 2 it was not. The agent still cleared #6. The human finding on #6 is semantic and outside SPEC-0003
  rule 11, as recorded in shadow review 2.
- Two of three contexts are now cut: the marker `[truncated: N lines omitted]` stands immediately before
  "## Requirements" in #12 and #22, which is the end of the "Changed files" content; the Diff hunks (including the
  `tests/kit_dev/` hunks of #22) are complete. The contexts grew (#12: 2066 to 3684 lines; #6: 1614 to 3055; #22: 2643
  to 4210) and the caps are `review_diff_cap` and `review_other_cap` (defaults 4000 and 1500, optional keys of `agk.toml`). Whether a cut of full-file
  content affected either verdict is not shown by this run.

## Questions

- Q-SR3-1: is the reviewer agent expected to catch the three human findings at all? Each is outside the checks that
  SPEC-0003 rule 11 lists (CI behaviour not stated in Approved text; a semantic wrong in `CLAUDE.md`; principle 4 /
  ADR-0001 decision 4 on where installed checks' tests live). Not decided here.
