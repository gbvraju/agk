# ADR-0179: solo mode, one yes per pull request for a project with one person (REQ-039, brief 277)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0173, ADR-0175, ADR-0178, SPEC-0021, SPEC-0025, SPEC-0032
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `agk.toml`, `config/`, `.claude/`, `CLAUDE.md`, `skills/`

## Context

Brief #277 (priority 1), from a project pilot on 2026-10-26: one person ran every role, and each spec pull request needed a
verdict naming a 40-character ID, a separate `Approve:` line in the browser, a re-run of the red check, a Final commit and a merge,
about six manual steps, twelve times. The field note on the brief adds that `verdict_authors` was empty for the whole pilot and
that one account did everything. The conductor's note reserves this number and asks that solo mode stay off by default, that every
project which does not opt in stay unchanged, and that this ADR stay `Proposed` for the maintainers, because it changes who
approves. The tests were written first (`tests/kit/test_solo_mode.py`, 36 failed at checkpoint f58803a).

## Decision

1. **The setting (answer 1).** `review_mode = "team" | "solo"` in `agk.toml`, `team` by default; any other value is refused naming
   the setting. `mode` stays the install stamp (Q-277-1). `reviewers.py --check`, run by governance, refuses solo mode when
   `verdict_authors` and `spec_approvers` together list nobody or more than one person, naming the setting (answer 1 and the field
   note). `reviewers.solo_person` gives the one person, and without exactly one nothing is a confirmation.
2. **The confirmation (answer 2).** In solo mode one comment by the one listed person counts as the verdict, its `Final:` lines and
   the spec approval of the head it names: `Confirmed: <40-hex sha>`, then `Verdict: cleared|fix list|rejected <the same sha>`,
   then any lines (`Final:`, findings, `Approve: SPEC-nnnn`), then `Shown:` and exactly three lines (the summary the person was
   shown), and last `confirmed by <login> in a session at <YYYY-MM-DDTHH:MM:SSZ>`, where the login is the comment's author (the
   shape is confirmed by the verdict on f58803a, Q-277-4). One reading, `reviewers.confirmed_comments`, adds what it stands for
   after it, as the same author at the same time: the verdict (its lines up to `Shown:`) and, for each `Approve: SPEC-nnnn` line,
   `Approve: <confirmed sha> SPEC-nnnn`. The sha must be the head when read: the router (`route.decide`, from the `solo_person`
   fact that `read_facts` reads) takes the head or the parent of a head that may be its covered final commit; `check_specs.py`
   reads it by the rule of a team short `Approve: SPEC-<n>` line, the `head_sha` of the latest `pull_request` run created before
   the comment (GitHub's times), and then requires the spec at the head to equal the text at that sha apart from its status line;
   `check_final_clearance.py` keeps its own rule (the head one commit past the reviewed sha) and the weekly report (`metrics.py`)
   reads the record as it stands. Every later rule is the one that holds today. In team mode nothing reads it.
3. **Agent apps (answer 3).** A comment that GitHub records as posted through an app of `agent_apps` is never a confirmation, in
   solo mode too.
4. **The person posts it; a session never does (the verdict on f58803a, condition 1).** GitHub cannot tell a comment the person
   typed from one a session posted under the same account, so a session that posted `Confirmed:` would give the one yes itself.
   A session prints the exact text (`/agk:confirm`, `skills/confirm/SKILL.md`), and the person posts it from the browser or the
   GitHub app. Session rule 29, `CLAUDE.md` rule 2 (the builder's rules; there is no builder role file) and the conductor's role
   file say a session never posts a comment whose first line is `Confirmed:`, and `.claude/hooks/conductor_guard.py` refuses such
   a comment by name in both of its modes. The session may make the `Final:` commit once the person's confirmation is on the pull
   request.
5. **The re-run (answer 4) is held (Q-277-2, the verdict on f58803a).** Re-running a workflow run needs `actions: write`, which
   SPEC-0032 rule 1 and REQ-039 AC2 exclude from the router's token; the router keeps its five permissions. Amendment 97 item 6
   states the change for the maintainers. Until then the person re-runs governance or pushes after posting a confirmation, and
   the guide (`docs/guides/getting-started.md`) says so in one line.
6. **The Final commit (answer 5)** is the one of today: status lines only, pushed alone, checked by `check_final_clearance.py`
   against the confirmation's `Final:` lines.
7. **The specs (answer 6).** `docs/runs/proposed-spec-amendments-97.md` amends SPEC-0021 rules 5 and 6, SPEC-0025 rule 4 and
   SPEC-0032 rules 5 and 6; this ADR applies items 1 to 5 when the maintainers accept it. Merging stays the person's.
8. **Tests (answer 7).** `tests/kit/test_solo_mode.py` covers:
   - a solo confirmation clears and approves;
   - the same comment in team mode counts for nothing;
   - an agent-app comment never counts;
   - a confirmation naming an old head, another login, another account or another shape counts for nothing;
   - the setting, the one person and the one-person check;
   - the router end to end;
   - the final-clearance check;
   - the spec check and its refusals: another account, an agent app, two people listed, another head than the runs show;
   - the weekly report;
   - the rules and the setting's text.

   `tests/kit/test_conductor_guard_confirmed.py` covers the guard refusing a `Confirmed:` comment by name.
   `tests/kit_dev/test_confirm_skill.py` covers the skill and the guide. `tests/kit/test_agk_config.py` gains the new default, and
   `tests/kit_dev/test_distribution.py` lists the new skill.
9. **Files outside the brief's `Touches:` (Q-277-3, accepted by the verdict on f58803a):**
   - `scripts/agk/common.py`: the setting.
   - `scripts/agk/check_specs.py`: without it a solo spec pull request fails governance.
   - `agk.toml` and `kit/templates/agk.adopt.toml`: the setting.
   - `config/session-rules.md`, `CLAUDE.md`, `.claude/agents/conductor.md` and `.claude/hooks/conductor_guard.py`: decision 4.
   - `skills/confirm/SKILL.md`, `docs/guides/getting-started.md` and `docs/guides/reference.md`.
   - The tests named in decision 8.

   `config.py` prints the setting as it prints every key of the defaults, so it is unchanged.
10. **Flow mode.** Fragment `changelog.d/solo-mode.md`; no version bump; `kit/hashes.json` is not edited (session rule 14).

## Log

- 2026-10-30, verdict on f58803a: Q-277-1 answered, `review_mode = "team" | "solo"`, default `team`; `mode` stays the install
  stamp.
- 2026-10-30, verdict on f58803a: Q-277-2 answered, the re-run is not in this pull request; the router keeps its five
  permissions; the `actions: write` re-run is a proposed amendment only (amendment 97 item 6), and the guide says the person
  re-runs governance or pushes.
- 2026-10-30, verdict on f58803a: Q-277-3 answered, the split is accepted. `check_specs.py` reads a confirmation's `Approve:` line
  only in solo mode, only at the head and only from the single listed person, with the three refusals tested. The `review-queue`
  and `watch` residuals and the empty-`verdict_authors` warning stay residuals, and the conductor files them as briefs.
- 2026-10-30, verdict on f58803a: Q-277-4 answered, amendment number 97 and the confirmation's shape confirmed, with three
  tightenings, each tested:
  - the sha is the head when read;
  - the last line's login is the author and the single listed person;
  - a comment from an agent app or another account counts for nothing.
- 2026-10-30, verdict on f58803a, condition 1: the person posts the confirmation, a session never does (decision 4).
- 2026-10-30, verdict on 1ae4fd4: items 1 to 3 built. These are the texts of decision 4, `check_specs.py`'s person and head rule
  with its refusal tests, the stale line of amendment 97, the body's list of files and the guide line.

## Consequences

- A project of one person who opts in gets, per pull request, one confirmation it posts itself and the merge, instead of a
  verdict, an approval in the browser, a Final commit after a wait and a merge; a project that does not opt in is unchanged.
- A session in solo mode prepares the confirmation but never posts it.

## Residual

- 2026-10-30: the kit cannot prove who typed a comment posted from the person's account: GitHub records the account and an app,
  not the hand. Session rule 29 and the conductor's guard are what hold "the person posts it"; a builder session has no guard, so
  for it the rule is the only boundary. The person is the only merger, and a separate comment-only identity for sessions is the
  later fix (the field note's item 2; due 2026-12-15).
- 2026-10-30: the router does not re-run the red governance run after a confirmation (decision 5, Q-277-2); the person re-runs it
  or pushes (due 2026-12-15).
- 2026-10-30: `session.py review-queue` and `watch` still read only `Verdict:` comments, so a conductor or a waiting session does
  not see a confirmation as a verdict; `doctor` and `init` do not yet warn on an empty `verdict_authors` (the field note's item 1;
  governance's `reviewers.py --check` does refuse it in solo mode). The conductor files both as briefs (due 2026-12-15).
