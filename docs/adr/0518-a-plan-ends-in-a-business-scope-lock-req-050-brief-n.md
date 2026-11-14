# ADR-0518: A plan ends in a business scope lock

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0043, amendment 176, brief #1219, plan #661
- Requirements: REQ-050

## Context

A plan rendered by `plan_intake.py render` is written for the team: `docs/plan/scope.md` and `docs/plan/milestones.md`
carry requirement numbers, source locations and brief keys, and the board carries sizes and hours. In a customer trial
the owner needed one scope lock that business readers and the prototype's owners could read and agree to: what is
delivered at each milestone, by screen and date, what comes after go-live, what is excluded and why, and the questions
with the date each is needed by. The kit had no command for it, so it was written by hand prompts, and builder figures
reached the business text twice before they were removed.

## Decision

1. A new plugin skill `skills/scope-lock/SKILL.md` (`/agk:scope-lock`, `disable-model-invocation: true`, run by the
   person) writes `docs/plan/scope-lock.md` from `docs/plan/scope.md`, `docs/plan/milestones.md`, the brief files of
   `docs/plan/briefs/`, `docs/design/inventory.md` and the `Questions for business` section: per milestone, the screens
   it makes work and what a person can do there, its start and end dates and its estimated hours (the sum of its
   briefs' `Expected:` ranges); the go-live date; after go-live; not included, with reasons; the decisions in plain
   words; the questions with the date each is needed by; and the risks with their answers. A date or a figure the plan
   does not state is written `to be agreed`, never made up. It then runs `check_plan.py` and prints the text of a scope
   lock issue in the same words; it creates no issue and commits nothing.
2. `scripts/agk/check_plan.py`, SPEC-0043 rule 10 with amendment 176: when `docs/plan/scope-lock.md` exists, each of its
   lines fails, once per kind, for a requirement number (`REQ-` and digits), a file path (a word holding `/` whose last
   part has a file extension, or one starting `./`, `../`, `~/` or a repository folder such as `docs/` or `src/`; a
   link holding `://` is not a path), a brief key (the name of a brief file under `docs/plan/briefs/`, as a whole word),
   and a builder or pull request figure (the words `builder`, `pull request` and `PR rate`, whole words, any case, with
   their plurals). Each failure is `rule 10: docs/plan/scope-lock.md:<line>: <kind>`, never the text. Without the file
   nothing changes.
3. A PDF is optional: the skill names a headless browser's `--print-to-pdf` command when one is installed and never
   installs one.
4. SPEC-0043 rules 10 and 25 gain one amendment line each (`docs/runs/proposed-spec-amendments-176.md`);
   `docs/guides/planning.md` gains the step and `docs/guides/reference.md` the plugin row.

## Consequences

A plan can end in a scope lock that business can read, and the check keeps the team's terms out of it in every
governance run. The check reads words, not meaning: a technical term outside the four kinds is the person's to remove.
`tests/kit/test_scope_lock.py` checks a clean scope lock (passes), a plan without one (as before), each kind failing
with the rule and the line number and never the text, several kinds on one line, words that only look alike, and the
skill's text and listings. Protected path classes changed: `scripts/agk/` (`check_plan.py`), `tests/kit/` (the tests),
`tests/kit_dev/` (the plugin's command list in `test_distribution.py`) and `skills/` (the new skill). No workflow
changes.

## Residual

- 2026-11-14: the four kinds are the brief's; other technical words (a framework, a host name) are not refused. The
  maintainers may widen the list after a trial (due 2026-12-31).
