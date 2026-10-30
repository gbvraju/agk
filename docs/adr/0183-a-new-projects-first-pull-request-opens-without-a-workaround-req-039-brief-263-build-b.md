# ADR-0183: a new project's first pull request opens without a workaround (REQ-039, brief 263 build b)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0131, ADR-0178
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #263 (priority 1) lists the gaps the first organisation project met on 2026-10-26 (a private repository of an organisation on
GitHub Free, Windows 11, kit 0.56.0 then 0.57.0). Build (b) is its answers 4 to 6, the first pull request. The conductor's field
note asks that each item be reproduced on today's main first (0.59.0 with #316 and #317, head 60d87c9) and that an item fixed since
0.57.0 be recorded, not rebuilt. All three reproduced on 60d87c9 on 2026-10-30, so none was fixed before this build:

- Answer 4: `check_pr_body.py --issues` with a saved copy that holds only the router's red-branch issue printed
  `FAIL pr-body: rule 9: 'Brief: #n' line is required (the repository has a brief)` and exit 1. The governance workflow also saved
  only one open brief (`per_page=1`).
- Answer 5: `git switch -c start/x origin/main` set the upstream to `origin/main`; a plain `git push` then refused and offered
  `git push origin HEAD:main`. `skills/start/SKILL.md` and `skills/spec/SKILL.md` gave exactly that command, and the scripts printed
  `git push -u origin <branch>`.
- Answer 6: `playbook.py next-steps` printed the commit message, the push command and the body, but neither the charter nor a way to
  open the pull request with the body file.

The tests were written first: 11 failed and 7 passed at the first checkpoint of the pull request (3c4d9f0).

## Decision

1. **The red-branch issue is not a brief for rule 9 (answer 4).** `check_pr_body.has_brief` leaves out the issue that
   `session.is_red` names: the router's own red-branch issue, read by its title, its `Priority: 0` line and the router's token as
   its author, so that an issue of the same shape written by hand still counts as a brief. `pr_body.open_briefs`, which the next
   steps of `/agk:start`, `/agk:spec` and the engines use, reads the same function, so the body they print passes. The governance
   workflow's step `Open briefs` saves up to 100 open briefs instead of one, since with one per page the red-branch issue could
   hide another open brief and a body without `Brief:` would pass. `session` is imported inside the function, because `session`
   imports `check_specs`, which imports this module.
2. **The start and intake branches do not track the default branch (answer 5).** `/agk:start` and `/agk:spec` create their branch
   with `git switch --no-track -c ... origin/<default branch>`, and `/agk:vision` says the same by reference. `playbook.py
   next-steps` and `intake.py next-steps` print `git push -u origin HEAD`. The skills do not name the push command itself, since
   their tests refuse a push verb in a skill; they say the script prints a push of `HEAD` to its own branch. The approving-commit
   step of `intake.py` keeps `git push origin <branch>`, which names its own branch and so never reaches the default branch.
3. **The first pull request shows the charter and offers the body file (answer 6).** `playbook.py next-steps` prints the vision and
   the charter, each with its path and its full text, under `The vision for your approval` and `The project charter for your
   approval`, before the commit message. Where `gh auth status` succeeds it also prints, after the body, one command
   `gh pr create --base <default branch> --title "<commit title>" --body-file "<body file>"`, so that the repository's pull request
   template does not replace the body; where `gh` is missing or not logged in it prints none. The start and vision skills tell the
   session to show both texts before the commit steps and to offer that command, which the person runs; the skills still never
   commit, push or open a pull request.
4. **The specs.** `docs/runs/proposed-spec-amendments-98.md` proposes the text of SPEC-0034 rule 9, SPEC-0012 rule 3 and SPEC-0013
   rules 3 and 4 that this changes. Its number is asked as Q-263-B1.
5. **Tests.** `tests/kit/test_pilot_gaps.py` (answer 4, the installed check) and `tests/kit_dev/test_pilot_gaps_first_pr.py`
   (answers 4 to 6: the prepared body, the workflow's page size, the skills, a real clone pushed with the printed command, the
   next steps with a `gh` that is logged in and one that is not). Three existing tests that pinned `git push -u origin <branch>`
   now pin `git push -u origin HEAD`.
6. **Flow mode.** Fragment `changelog.d/first-pull-request.md`; no version bump; `kit/hashes.json` is not edited (session rule
   14).

## Consequences

- A new project whose default branch is red can open its first intake or start pull request with the body the kit prints.
- A start or intake branch cannot be pushed to the default branch by following git's own hint.
- The person sees the charter they approve by merging before they commit it, and can open the pull request with the checked body.

## Residual

- 2026-10-30: `engines.py stack-next-steps` and `design-next-steps` still print `git push -u origin <branch>`, which works but is
  not the `HEAD` form; their skills create no branch of their own. Left as they are, outside the brief's answers 5 and 6
  (Q-263-B2; due 2026-12-15).
- 2026-10-30: `intake.py next-steps` does not offer `gh pr create --body-file`; answer 6 names `/agk:start` only (Q-263-B2; due
  2026-12-15).
