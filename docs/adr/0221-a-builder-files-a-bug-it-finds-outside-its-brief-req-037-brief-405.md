# ADR-0221: a builder files a bug it finds outside its brief instead of fixing it in its pull request (REQ-037, brief 405)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0170, ADR-0216
- Requirements: REQ-037

Protected classes: `config/`, `tests/kit_dev/`

## Context

The field notes of 2026-10-27 and 2026-10-28 on #286 (found-bug protocol, memory) record builders that found bugs outside
their pull requests (a flaky test, a sign-in stub race, lint errors on the default branch). Some fixed them inside unrelated
pull requests, which made those pull requests larger and mixed two reviews; others re-investigated what a second builder had
already found. Builders also left the probe images they built on a shared laptop. Brief #405 (split from #286, part 6) gives
the answers: one new session rule and its tests.

## Decision

1. **One session rule, rule 34 (answer 1).** `config/session-rules.md` gains rule 34, the next free number (`session.py ids`),
   with four parts: a bug outside the brief is not fixed in the pull request, unless it blocks the pull request's own gate and
   the fix is one line; the builder first searches the open issues by the test name or the symptom, and when one exists adds
   its evidence there as a comment; otherwise it files one bug brief labelled `found-bug`, with the evidence and how to
   reproduce it, and says in its `Report:` that the failure is known and unrelated; builders never take a `found-bug` brief
   unless the conductor assigns it with an `Assign:` line (rule 18).
2. **Probe clean-up (answer 2).** The same rule says the builder removes the images and build cache it made for a probe when
   the check ends.
3. **The label (answer 3, Q-405-1).** The brief says the label is "the one the brief skill writes", but `skills/brief` writes a
   file in `docs/briefs/` and no label, and no skill, template or script of the kit writes `found-bug`. Read conservatively,
   within the brief's `Touches:` line: the rule names `found-bug` and says the brief is not labelled `agk-brief`, the label
   `session.py next` reads, so `next` never offers a found-bug brief and part 4 holds without a change to the script;
   `session.py claim` reads the brief's comments and not its labels, so an assigned found-bug brief can still be taken. A test
   checks that the rule's label differs from `session.LABEL` and that the brief skill names no other label.
4. **Tests first.** `tests/kit_dev/test_session_rules_found_bug.py` checks that one rule names the label, each of the four parts
   and the clean-up, the order (search first), the rules' numbering and the label of decision 3.

## Consequences

Pull requests stay within their briefs, and a bug found twice is found once: the second builder adds its evidence to the
first one's issue. A found-bug brief waits for the conductor's `Assign:`. The router's closing of a brief by `Finishes:`
reads `agk-brief`, so a found-bug brief that keeps only its own label is closed by its pull request's `Closes #n` (where
GitHub's closing keywords apply) or by a person.

## Residual

- 2026-10-31: Q-405-1 (decision 3): whether a skill or script should write the `found-bug` label, and whether a found-bug
  brief also carries `agk-brief` with `session.py next` taught to skip it, is a later brief; nothing in this one creates the
  label on GitHub.
