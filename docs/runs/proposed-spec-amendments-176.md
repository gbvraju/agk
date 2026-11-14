# Proposed spec amendments 176 (SPEC-0043; REQ-050)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0518 (brief #1219), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md`. Brief #1219
reserved ADR-0518 and amendment 176. The two amendment lines are applied in the same pull request, under rules 10 and
25, as amendment 173 was. The owner decides them with `Approve: <head> SPEC-0043` on the pull request; no session posts
that line.

The sentence (brief #1219): "A plan ends in a scope lock that business can read: what is delivered at each milestone,
by screen and date, what comes after go-live, what is excluded and why, and the questions with their dates."

## What is on the default branch today

Read in the code by this session on `origin/main` (76fcd1b):

- `scripts/agk/plan_intake.py render` writes `docs/plan/scope.md`, `docs/plan/milestones.md`,
  `docs/plan/requirements-proposed.md` and the brief files; each carries requirement keys, source locations and brief
  keys, written for the team. No kit command writes a text for business readers.
- `scripts/agk/check_plan.py` checks the plan's files (rules 10, 11 and 20 to 22) and reads no other file of
  `docs/plan/`.

## Items

1. **Rule 10, one amendment line.** "When `docs/plan/scope-lock.md` exists, `check_plan.py` also fails each of its
   lines, once per kind, that holds a requirement number (`REQ-` and digits), a file path (a word holding `/` whose last
   part has a file extension, or one starting `./`, `../`, `~/` or a repository folder; a link holding `://` is not
   one), a brief key (the name of a brief file under `docs/plan/briefs/`, as a whole word) or a builder or pull request
   figure (the words `builder`, `pull request` and `PR rate`, whole words, any case, plurals too), as
   `rule 10: docs/plan/scope-lock.md:<line>: <kind>`, never the text; without the file nothing changes."
2. **Rule 25, one amendment line.** "`docs/plan/` also holds `scope-lock.md`, the business scope lock that the person's
   `/agk:scope-lock` writes from the plan (per milestone its screens, what a person can do there, its dates and
   estimated hours; the go-live date; after go-live; not included, with reasons; the decisions; the questions with the
   date each is needed by; the risks with their answers), a value the plan does not state written `to be agreed`; the
   skill prints the text of a scope lock issue and creates none, and names a browser's print command for an optional
   PDF without installing one."
3. **No other change.** Rules 9, 11, 20 to 22 and 26, `plan_intake.py` and every workflow stay as they are.
4. **Tests.** `tests/kit/test_scope_lock.py`: a clean scope lock passes; a plan without one is checked as before; a
   requirement number, a file path, a brief key and a builder or pull request figure each fail with the rule and the
   line number and never the text; several kinds on one line fail once each; words that only look alike pass; the
   skill is run by the person, runs the check, prints the issue text and creates no issue, names a print command and
   installs nothing, and is listed in the reference and the planning guide.
