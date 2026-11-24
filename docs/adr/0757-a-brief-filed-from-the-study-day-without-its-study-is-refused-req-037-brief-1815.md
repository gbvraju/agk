# ADR-0757: A brief filed from a day set in agk.toml without its study lines is refused (REQ-037)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1815, ADR-0752 (brief #1800), ADR-0756 (brief #1813), ADR-0112, ADR-0699, ADR-0750, found bug #1783,
  plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `agk.toml`, `kit/`, `tests/kit/`

## Context

ADR-0752 put the day the study lines start to fail in one dated constant, `brief_study.STUDY_FAILS_FROM`, left unset
(Q-1800-1). A dated constant is installed in every project: a project that upgrades after the day would refuse its own
open briefs at once, and every kit test that checks a brief without study lines would turn red on that day (PR #1804
measured 35 failures in 16 files with the day forced to the past). That is the clock class of ADR-0112, found bugs
#446 and #1497 and ADR-0750. The plan's brief shape (`session.brief_shape`) never read the study, so a brief the
workflow labels `agk-brief-invalid` was still handed out (found bug #1783), and the router's red-branch brief was held
to no study line. The owner's word (2026-11-23, the steward chat, quoted as data): "Yes, brief the study refuse day".

## Decision

1. The day is a setting: `[flow] brief_study_fails_from` (a TOML date or a `"YYYY-MM-DD"` string, UTC), read by
   `config.brief_study_fails_from(root)` and listed in `config.TABLE_KEYS["flow"]`. Unset is `None`: warnings only,
   as before. Any other value (a number, a boolean, a date with a time, an impossible date, a list) is refused as
   `rule 4: the setting is refused (setting: flow.brief_study_fails_from)`, never the value, by `check_brief.py`,
   `session.py plan` and `session.py next`. `brief_study.STUDY_FAILS_FROM` is removed.
2. A brief is judged by the day it was filed: the issue's `created_at` (UTC date) when there is one (the `issues`
   event, the plan's listing, the files forge's record), else `today`, which the caller passes from
   `common.utc_day()`. `brief_study.enforced(root, today, filed)` is true when the day is set and the judged day is on
   or after it. A brief filed before the day stays warned only, whatever later edits it gets.
3. `check_brief.brief_result` takes `today` (default `common.utc_day()`) and `filed`; `check_brief.event_result`
   passes the issue's `created_at`. From the day the study's problems are failures (`FAIL brief: study: ...` and the
   `agk-brief-invalid` label through the existing workflow path); the `Prior leaves out` lines stay warnings.
4. `session.brief_shape` adds, after the shape passes and only when the day is set, the study's failures of
   `brief_study.study_failures(body, root, filed, today)` (no ADR or cache scan), each prefixed `rule 4: `, so
   `session.py plan` lists the brief `MALFORMED` and `session.py next` skips it. `session.judge` passes the listing's
   `created_at`; the router's red brief is still skipped by `is_red`.
5. `route.red_body` writes `Prior: none: ...` and `Class: a red default branch; seen 0 (...)`, naming no ADR or spec
   id, and `brief_study.held` holds the router's pair, as any `Priority: 0` brief, to `Class:` and `Prior:` only.
   `route.write_red` patches an open red issue once, because its body differs.
6. The kit's own `agk.toml` sets `brief_study_fails_from = "2026-12-14"`: the later of 14 days after brief #1813's pull
   request merged (#1817, 2026-11-23) and 7 days after this pull request's last commit, never before 2026-12-14
   (Q-B2-1). `kit/templates/agk.toml`, `agk.adopt.toml` and `personal.toml` set none (Q-B2-2): a project or a sidecar
   warns until its owner sets its own day, and the kit's day never reaches it.
7. Neither `brief_study.py` nor `check_brief.py` holds a date literal or reads the live clock;
   `tests/kit/test_brief_refuse_day.py` fails when one does, and runs the brief test files with the kit's day in the
   past, expecting each still to pass.
8. Path classes changed: `scripts/agk/` (`brief_study.py`, `check_brief.py`, `config.py`, `common.py`, `session.py`,
   `route.py`), `agk.toml` (the kit's day), `kit/` (`kit/hashes.json`, regenerated) and `tests/kit/` (the new test file
   and the tests that set the day through the setting instead of the constant). `review_mode`, `pr_mode`, `execution`
   and personal mode read the same day from the same function; a change of the kit's day needs an ADR.

## Consequences

From the day, a brief filed without its study is refused within seconds of filing and is no longer handed out to a
builder; the briefs open before the day stay warned. No check or test result depends on the calendar: the day comes
only from a root's `agk.toml`, and tests build their roots without it unless they set it.

## Residual

Open briefs filed before the day are warned only (Q-B2-3, conservative reading); the steward's `fix_brief` can add
their lines. The kit's day may move by a `Maintainer answer:` on Q-B2-1.
