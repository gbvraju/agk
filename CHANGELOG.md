# Changelog

The changes to the kit of this repository, newest first. In flow mode a build pull request adds one line under `## Unreleased`; a release pull request moves the lines under the new version (SPEC-0028). The history before 0.54.0 is in the git log and in `docs/runs/`.

## Unreleased

## 0.55.0 (2026-10-25)

- #175 the conductor role: `.claude/agents/conductor.md` with its seven pre-verdict steps and `.claude/hooks/conductor_guard.py`, which allows reads and one comment POST (REQ-037 rule 6)
- #174 design check: `check_design.py` fails a mockup with a script, an external request, a colour outside the token block or a contrast under 4.5:1, and reads a theme as not approved yet or at risk (SPEC-0029 rule 7, REQ-036)
- #172 `check_brief.py` checks the shape of a brief, and `session.py watch` ends with `conflict #N` when the pull request conflicts with its base (REQ-037 rule 4 and the verdict on #169)
- #173 stack: `/agk:stack` writes one Proposed ADR of two or three stack options with checked and judged practices, and `engines.py stack-check` checks its shape (SPEC-0029 rule 5, REQ-036)
- #170 vision: `/agk:vision` keeps the idea unchanged and the charter records ten answers (SPEC-0029 rule 4, REQ-036)
- #169 session rules and `session.py`: `watch` ends on a verdict, a merge or a close, `next` takes the first free brief (REQ-037 rules 1 to 3 and 5)
- #168 engines: `[engines]` in `agk.toml` and five `doctor` checks that report each engine as present, absent or missing (SPEC-0029 rules 1 to 3, REQ-036)
- #178 design: `/agk:design` writes the theme and a mockup folder from templates with four screenshots when a headless browser exists, and `check_design.py` is now a step of `make governance` and the workflow (SPEC-0029 rules 6, 7 and 9, REQ-036)
- #181 flow mode: a build adds its changelog line as `changelog.d/<slug>.md` and leaves `CHANGELOG.md` and `kit/hashes.json` to the release, which gathers the fragments with `changelog_fragments.py gather` (SPEC-0031, REQ-038)
- #184 a late clearance fails `check_final_clearance`, the report lists open pull requests ready to merge first (`report.json` schema 4), and the guide shows how to run the loop (REQ-037 rules 7 to 9)
- #186 no installed file holds a literal date any more (the conductor role, the two hook docstrings and a refusal message), and a kit test fails one that does, so the suite no longer depends on the day it runs (brief #185, ADR-0112)
- #188 the checks of a pull request compare it with the first parent of the merge ref GitHub checked out, set by one step of the governance and proof workflows, not with the event's older base sha, so a pull request is never failed for files another one merged (brief #180, ADR-0111)
- #192 a builder commits `checkpoint:` steps and opens a draft pull request, the body and final-clearance checks ignore a draft until it is ready (`--draft`), and the workflow runs on `ready_for_review` (SPEC-0033 rules 1 to 3, REQ-040)
- #193 router: `agk-route.yml` and `route.py` set one `agk:` label on every pull request from GitHub events (state, review, fix, approve, ready), and write nothing else (SPEC-0032 rules 1, 2 and 8, REQ-039)
- #195 `session.py resume --pr N` prints where a pull request stands, and `session.py next` offers and takes over a pull request that has waited on its builder for `stall_hours` before any new brief (SPEC-0033 rules 4 and 5, REQ-040)
- #197 session: `watch --pr` ends on a change of the router's `agk:` label, `queue --role` lists a role's pull requests so a restarted session resumes from GitHub, and the session rules say how `watch` is started so its end wakes the session (SPEC-0032 rules 3 and 4, REQ-039)
- #198 the facts carry the usage figure of a pull request from its `Report:` comments and the cost lines of the weekly report sum it, `not reported` when there is none (`report.json` schema 5), and the guide says what happens when the credits run out (SPEC-0033 rules 7 and 8, REQ-040)
- #199 check_brief.py also requires the `Advances:` and `Touches:` lines of a brief (and an optional `Priority:`), `--root DIR` fails a requirement that does not exist; check_pr_body.py requires `Closes #n` when a row sets `REQ-nnn done`, and `Brief: #n` when the governance workflow's new `Open briefs` step finds an `agk-brief` issue; doctor reports a missing `agk-brief` label (SPEC-0034 rules 2 and 9, REQ-041)
- #200 the router opens, updates and closes the one brief `The default branch is red` from the checks of the default branch, and `session.py next` hands out only that brief while it is open (SPEC-0032 rule 7, REQ-039)
- #201 session: `next` takes no brief at `max_builders` open builder pull requests (`full n/m`), skips a brief whose `Touches:` overlap open work, orders by `Priority:`, reserves numbers in its take and frees a take after `claim_hours` or `released:`; new `ids`, `demand` and `push-check` (SPEC-0034 rules 1, 3 to 6 and 7b, REQ-041)
- #202 a person approves every spec: `spec_approvers` in `config/reviewers.yaml`, `check_final_clearance.py` reads `Approve: <sha> SPEC-<n>` from comments and reviews, the conductor ends an intake verdict with an `Approval:` line, and the router sets `agk:approve` on it (SPEC-0032 rules 2, 5 and 6, REQ-039); without `spec_approvers` in `config/reviewers.yaml`, a covered fix list that sets a spec `Approved` now fails `final-clearance`, so add your user handles there
- #203 the session rules gain push-check before every push, the shared-mechanical files, mechanical conflicts only, the Question and Report shapes and the hand-off of a finished builder (per-build claims, claim, after, watch --assign, [flow] assign); the conductor reads and answers them; the guide shows the launcher contract with two examples (SPEC-0034 rules 6, 7c and 11, REQ-041)
- #205 governance: a pull request that sets a spec to Approved, by a `Final:` line or an ordinary commit, needs an `Approve: <sha> SPEC-<n>` line by a listed person for the text of the spec at its head (SPEC-0032 rule 5, REQ-039)
- #206 a cause is measured and a correction travels the same channel: `check_brief.py` fails a `Priority: 0` brief without a `Measured:` line, `session.py watch` ends on a `Correction:` comment of a listed author on the pull request or on its brief, and the session rules and the conductor role file say how (SPEC-0032 rules 9 and 10, REQ-039)
- #208 report: schema 6 adds the Flow section (open builders against max_builders, the median hours of each step, conflicts, renumbers, retakes), the At risk lines for stalled pull requests, idle briefs and requirements without a brief, and the conductor's corrections beside its verdicts (SPEC-0034 rule 10, SPEC-0033 rule 5, SPEC-0032 rule 11)

## 0.54.0 (2026-10-24)

- #165 flow mode: a kit build adds a changelog line instead of bumping the version, one release pull request bumps it, and `check_release.py` checks that pull request
