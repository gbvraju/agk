# SPEC-0025: A team can run independent pull requests in parallel without colliding

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-032

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "A team can run independent pull requests in parallel without colliding on numbers or logs, a pull request that needs another one's unmerged change says so and cannot merge before it, and each repository chooses a strict or a flow mode for how many pull requests a person may have open." It is the first phase of the brief for teams (issue #133), generic and project-agnostic: it holds for every project the kit is installed in and names no project and no reader. The working rule "one open pull request at a time" guarded against undeclared stacking, a pull request built on another's unmerged change; phase 1 makes independent work collide-free, makes dependence explicit and lets each repository choose its mode. It changes how many pull requests may be open, never what a pull request must prove: tests first, proof, review, a listed author's verdict and a person's merge are the same in every mode. This intake takes the pre-L2 path (SPEC-0012): it merges with the spec `Draft` and the ADR `Proposed`, and the next pull request is the approval alone, the two status lines and nothing else, cleared by the maintainers before part (a) starts.
The maintainers gave seven answers before it was written, in the issue and not as an interview: (1) duplicate numbers are a governance failure and `intake.py renumber` moves a pull request's own numbers, no number being edited by hand; (2) the append-only logs are marked `merge=union` in the shipped `.gitattributes`, with GitHub's behaviour verified at the build; (3) with two or more listed verdict authors a verdict by the pull request's own author does not count; (4) a body may declare `Depends-on: #n` and a check fails while a named pull request is not merged; (5) `pr_mode` in `agk.toml` is `strict` (the default) or `flow`; (6) this repository switches to `flow` by a separate pull request after parts 1 to 5 are released; (7) release pull requests for this repository in flow mode have their own intake after part 6.

## Rules

The rules of this spec moved to SPEC-0034, in its section "Independent pull requests (from SPEC-0025)" (brief #387, ADR-0246, `docs/runs/proposed-spec-amendments-108.md`), the text unchanged and rule 8 in the text SPEC-0028 amended it to. Each line says where a rule went; a script, test, ADR or verdict that cites a rule of this spec reads it there.

1. Now SPEC-0034 rule 17.
2. Now SPEC-0034 rule 18.
3. Now SPEC-0034 rule 19.
4. Now SPEC-0034 rule 20.
5. Now SPEC-0034 rule 21.
6. Now SPEC-0034 rule 22.
7. Now SPEC-0034 rule 23.
8. Now SPEC-0034 rule 24.
9. Now SPEC-0034 rule 25.
10. Now SPEC-0034 rule 26.
11. Now SPEC-0034 rule 27.

## Tests

- Rule 1: a tree with two requirements, two specs or two ADRs of the same number fails with the rule and the id; unique numbers pass; REQ-032 AC1.
- Rule 2: `renumber` moves the pull request's own numbers, renames the files, rewrites the ids and the references it added, leaves the default branch's files alone, and is idempotent; REQ-032 AC2.
- Rule 3: the template marks the append-only logs and not the requirements file; REQ-032 AC3.
- Rule 4: with two listed authors the pull request author's verdict clears nothing, covers nothing and is no round; with one it does; REQ-032 AC4.
- Rule 5: the check fails while a named pull request is not merged and skips without the file; REQ-032 AC5.
- Rule 6: strict fails on an older open pull request and on `Depends-on`, skips without the file, and the default is strict; REQ-032 AC6.
- Rule 6: flow passes both, and `doctor` reports the mode; REQ-032 AC7.
- Rule 7: the workflow's permissions are three `read`, its new fetches are GET-only steps that write files, and the checks import no network module; REQ-032 AC8.

## Proof

REQ-032 AC1 and AC2: *two pull requests can be developed in parallel and the second to merge renumbers itself by a command.* Rules 1 and 2. REQ-032 AC3: *appended log lines do not collide.* Rule 3. REQ-032 AC4: *a person cannot clear their own pull request when others are listed.* Rule 4. REQ-032 AC5 to AC7: *dependence is declared and enforced, and the mode is the repository's choice.* Rules 5 and 6. REQ-032 AC8: *the workflow still only reads.* Rule 7. The first pull request built under flow mode in this repository, with the number of maintainer actions it took, is recorded by the maintainers in `docs/runs/method-weight-2.md`.

## Residual

- 2026-10-24: GitHub's merge conflict check may not honour `merge=union`; the build of part (b) measures it and, if it does not, raises a question before building (due 2026-12-31).
- 2026-10-24: ruled in the verdict on this intake: the measurement of GitHub's merge is a step of build part (b): two throwaway branches from the default branch, each appending one line to a `merge=union` file, one draft pull request titled "measurement: merge=union (to be closed)", its `mergeable` and `mergeable_state` read with GET, then the pull request closed without merging and both branches deleted; the result goes in part (b)'s ADR (due 2026-12-31).
- 2026-10-24: ruled in the verdict on this intake: this intake takes the pre-L2 path (`Draft` now, approval by the next pull request); widening `intake.py check --final` to "The maintainers gave N answers before it was written" for any N is in the brief of issue #137 (due 2026-12-31).
- 2026-10-24: the maintainers' docs-only exception lapses when part (c) is installed in this repository, since the strict check cannot tell a docs-only pull request apart; this repository then switches to flow by its own pull request (rule 8) (due 2026-12-31).
- 2026-10-24: in strict mode "one open pull request at a time" is checked by author login, so a developer working through two accounts, or an agent posting under a shared login, is not told apart (due 2026-12-31).
- 2026-10-24: `Depends-on` is read from the body, so a stale line stays until the body is edited; the check re-runs on `edited` events (due 2026-12-31).

## Open questions

none
