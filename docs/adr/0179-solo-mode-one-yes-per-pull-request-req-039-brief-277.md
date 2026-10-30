# ADR-0179: solo mode, one yes per pull request for a project with one person (REQ-039, brief 277)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0175, ADR-0178, SPEC-0021, SPEC-0025, SPEC-0032
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

Brief #277 (priority 1), from a project pilot on 2026-10-26: one person ran every role, and each spec pull request needed a
verdict naming a 40-character ID, a separate `Approve:` line in the browser, a re-run of the red check, a Final commit and a merge,
about six manual steps, twelve times. The field note on the brief adds that `verdict_authors` was empty for the whole pilot and
that one account did everything. The conductor's note reserves this number and asks that solo mode stay off by default, that every
project which does not opt in stay unchanged, and that this ADR stay `Proposed` for the maintainers, because it changes who
approves. The tests were written first (`tests/kit/test_solo_mode.py`, 36 failed at checkpoint f58803a).

## Decision

1. **The setting (answer 1).** `review_mode = "team" | "solo"` in `agk.toml`, `team` by default; any other value is refused naming
   the setting. The brief's name `mode` already holds the install stamp (`init` or `adopt`), so the setting has its own name
   (Q-277-1). `reviewers.py --check`, run by governance, refuses solo mode when `verdict_authors` and `spec_approvers` together
   list nobody or more than one person, naming the setting (answer 1 and the field note).
2. **The confirmation (answer 2).** In solo mode one comment counts as the verdict, its `Final:` lines and the spec approval of the
   head it names: `Confirmed: <40-hex sha>`, then `Verdict: cleared|fix list|rejected <the same sha>`, then any lines (`Final:`,
   findings, `Approve: SPEC-nnnn`), then `Shown:` and exactly three lines (the summary the person was shown), and last `confirmed by
   <login> in a session at <YYYY-MM-DDTHH:MM:SSZ>`, where the login is the comment's author (the shape is Q-277-4). One reading,
   `reviewers.confirmed_comments`, adds what it stands for after it, as the same author at the same time: the verdict (its lines up
   to `Shown:`) and, for each `Approve: SPEC-nnnn` line, `Approve: <confirmed sha> SPEC-nnnn`, the long form that approves the text
   at that sha. The router (`route.decide`, from a `solo` fact that `read_facts` reads), `check_final_clearance.py`,
   `check_specs.py` and the weekly report (`metrics.py`) apply it in solo mode only, and every later rule is the one that holds
   today: a listed author, the head named, a covered final commit, the text approved. In team mode nothing reads it.
3. **Agent apps (answer 3).** A comment that GitHub records as posted through an app of `agent_apps` is never a confirmation, in
   solo mode too.
4. **The re-run (answer 4) is held (Q-277-2).** Re-running a workflow run needs `actions: write`, which SPEC-0032 rule 1 and
   REQ-039 AC2 exclude from the router's token, and the workflow is outside the brief's `Touches:`. A requirement's criterion is the
   maintainers' to change, so this pull request does not build it; amendment 97 item 6 states the change for their decision.
   Until then a person re-runs the red check after a confirmation.
5. **The Final commit (answer 5)** is the one of today: the session makes it right after the confirmation, status lines only,
   pushed alone, and `check_final_clearance.py` checks it against the confirmation's `Final:` lines.
6. **The specs (answer 6).** `docs/runs/proposed-spec-amendments-97.md` amends SPEC-0021 rules 5 and 6, SPEC-0025 rule 4 and
   SPEC-0032 rules 5 and 6; this ADR applies items 1 to 5 when the maintainers accept it. Merging stays the person's.
7. **Tests (answer 7).** `tests/kit/test_solo_mode.py`: a solo confirmation clears and approves; the same comment in team mode
   counts for nothing; an agent-app comment never counts; a confirmation naming an old head, another login or another shape counts
   for nothing; the setting and the one-person check; the router end to end; the final-clearance check, the spec check and the
   weekly report. `tests/kit/test_agk_config.py` gains the new default.
8. **Files outside the brief's `Touches:` (Q-277-3).** `scripts/agk/common.py` (the setting, beside `pr_mode`),
   `scripts/agk/check_specs.py` (without it a solo spec pull request fails governance), `agk.toml` and
   `kit/templates/agk.adopt.toml` (the setting beside `kit/templates/agk.toml`), `tests/kit/test_agk_config.py`. `config.py` prints
   the setting as it prints every key of the defaults, so it is unchanged.
9. **Flow mode.** Fragment `changelog.d/solo-mode.md`; no version bump; `kit/hashes.json` is not edited (session rule 14).

## Consequences

- A project of one person who opts in gets, per pull request, one confirmation and the merge instead of a verdict, an approval in
  the browser, a Final commit after a wait and a merge; a project that does not opt in is unchanged.
- A confirmation is checked for its shape and its head, not for who typed it.

## Residual

- 2026-10-30: in solo mode the one account posts both the work and the confirmation, so nothing tells a person's yes from a
  session's; the last line and the three summary lines record what was shown, not who decided. The person is the only merger, and
  a separate comment-only identity for the conductor is the later fix (the field note's item 2; due 2026-12-15).
- 2026-10-30: the router does not re-run the red governance run after a confirmation (decision 4, Q-277-2); a person re-runs it
  (due 2026-12-15).
- 2026-10-30: `session.py review-queue` and `watch` still read only `Verdict:` comments, so a conductor or a waiting session does
  not see a confirmation as a verdict; `doctor` and `init` do not yet warn on an empty `verdict_authors` (the field note's item 1;
  governance's `reviewers.py --check` does refuse it in solo mode). Both are later briefs (due 2026-12-15).
