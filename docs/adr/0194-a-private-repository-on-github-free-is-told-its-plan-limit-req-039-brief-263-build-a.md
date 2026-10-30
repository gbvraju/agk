# ADR-0194: a private repository on GitHub Free is told its plan limit (REQ-039, brief 263 build a)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0183, ADR-0001
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #263 (priority 1) lists the gaps the first organisation project met on 2026-10-26 (a private repository of an organisation on
GitHub Free, Windows 11, kit 0.56.0 then 0.57.0). Build (a) is its answers 1 to 3, the plan and protection messages. The
conductor's field note asks that each item be reproduced on today's main first and that an item fixed since 0.57.0 be recorded,
not rebuilt. All three reproduced on a0d6816 on 2026-10-30, so none was fixed before this build:

- Answer 1: `ruleset.py plan --api-dir` with an admin's repository read and a `/rulesets` answer of 403 "Upgrade to GitHub Pro or
  make this repository public to enable this feature." printed `cannot apply the ruleset from here (no-admin)`, exit 4. The doctor's
  `http_reason` maps every 403 to `no-admin`, and `classify_failure` maps every `HTTP 403` from `gh` to it.
- Answer 2: the same run, in phase 1 (`governance` had not succeeded), printed `branch-rules.txt` whole, with the required status
  check `governance`.
- Answer 3: the "Before you start" section of `docs/guides/getting-started.md` names neither the plan requirement, nor the Actions
  minutes on Free, nor how to install GNU make on Windows.

The tests were written first: 17 failed and 145 passed at the first checkpoint of the pull request (4914bd4).

## Decision

1. **The plan limit is named (answer 1).** A 403 whose message holds "Upgrade to GitHub Pro" or "make this repository public" is the
   reason class `plan-limit`, read from a recorded error body and from `gh`'s output alike, whatever the permissions say, since it
   is the true cause either way. Its hint and `ruleset.py`'s message say that rulesets and branch protection on a private repository
   need a paid plan (GitHub Pro, Team or Enterprise), and that the safe next step is to upgrade the plan or make the repository
   public; `ruleset.py` adds that applying it by hand is refused the same way, so the text it prints is the ruleset to apply then.
   The exact words of GitHub's message are the ones the brief measured `(verify: GitHub may word it differently for other plans)`.
2. **`no-admin` only when the account is not an admin (answer 1).** Any other 403 or 404 on a ruleset read stays `no-admin` unless
   `permissions.admin` in the repository read is true; then it is `forbidden` ("GitHub refused the read although the account is an
   admin"), whose hint says to read GitHub's message with `gh api`. Where the repository read itself failed, `permissions.admin` is
   unknown and the reason stays as it is today (Q-263-A3, accepted). The doctor fixture `no-admin` now records `permissions.admin` false, since
   its 403 with an admin's repository read is the new `forbidden` case (`admin-forbidden`); a fixture `plan-limit` is added.
3. **The hand-apply text follows the phase (answer 2).** When the ruleset cannot be applied, `ruleset.py` chooses the phase as the
   plan does (`--phase` given; otherwise phase 2 only when the runs of `governance` on the default branch show a success, read only
   when the repository could be read) and prints `phase N (...)` and the rules of that phase. Phase 2 is `branch-rules.txt` exactly.
   Phase 1 is the same text without the clause `; required status check `governance``, then one line saying that phase 2 adds it once
   `governance` has succeeded on the default branch. `branch-rules.txt` and `init.py` are unchanged, so the text `/agk:init` prints
   stays ADR-0001's. `/agk:ruleset` (its skill) says the plan prints the cause and the rules of the phase.
4. **The guide's prerequisites (answer 3).** "Before you start" says that a private repository needs a paid plan for rulesets and
   branch protection, that Actions minutes on private repositories are limited on Free, and that on Windows GNU make is installed
   with `winget install ezwinports.make`, after which Claude Code is restarted so that it sees `make`.
5. **The specs.** `docs/runs/proposed-spec-amendments-100.md` proposes the text of SPEC-0006 rules 3, 6 and 15 and SPEC-0013 rule 19
   that this changes (number given by Q-263-A2).
6. **Tests.** `tests/kit/test_pilot_gaps.py` (answer 1, the doctor, live `gh`), `tests/kit_dev/test_pilot_gaps_plans.py` (answers
   1 to 3: `ruleset.py` on recorded and live answers, the text of each phase, the guide). One existing assertion in
   `tests/kit_dev/test_ruleset.py` (the not-an-admin case) now records a successful `governance` run, so that it still sees the
   whole text, which is phase 2's.
7. **Flow mode.** Fragment `changelog.d/plan-limit-messages.md`; no version bump; `kit/hashes.json` is not edited (session rule 14).

## Questions

- Q-263-A1: answered by the verdict on d8f32d6: answer 3 edits only the "Before you start" section of
  `docs/guides/getting-started.md`, which #342 does not change; whichever of the two merges second merges the default branch in.
- Q-263-A2: answered by the verdict on d8f32d6: the amendment is number 100.
- Q-263-A3: answered by the verdict on d8f32d6: the reading of decision 2 is accepted (`no-admin` stays when the repository read
  fails; `forbidden` only when `permissions.admin` is true; `plan-limit` whatever the permissions say).

## Consequences

- A person on GitHub Free with a private repository is told that the plan is the cause and what to do, instead of being sent to
  look for admin rights they already have.
- Text applied by hand in phase 1 no longer requires a check that has never run, which could block the first merge.

## Residual

- 2026-10-30: other doctor checks that read with an admin's token (`drift-workflow-state`, `brief-finished`) still say `no-admin` for
  any 403; the brief names `/rulesets` only (due 2026-12-15).
