# Proposed spec amendments 101 (SPEC-0033; REQ-040, REQ-016)

Date: 2026-10-30 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is recorded by
ADR-0186 (brief #326), which leaves SPEC-0033 and session rule 7 unchanged, and it would change
`docs/specs/0033-when-a-session-stops-in-the-middle-of-its-work-for-any-reaso.md` and `config/session-rules.md` rule 7. The number
101 was given by the verdict on f9ba218 (Q-326-4). It waits for the maintainers' decision; nothing here is applied.

Why: brief #326 answer 3 asks that a builder push at milestones, not every step, so that each push runs the fast checks once and
CI rounds are fewer (#288 tier T0). A builder that pushes only at milestones must still lose nothing when it stops (REQ-040).

1. **SPEC-0033 rule 1, the first sentence replaced.** "A builder commits and pushes its branch at every step that leaves the tests
   it has written so far green or expected-red (tests first, then each part)." becomes "A builder commits its branch at every step
   that leaves the tests it has written so far green or expected-red (tests first, then each part), and pushes at milestones
   (tests red, then green, then ready) and always before it pauses, ends or asks a question, so that a stopped session loses
   nothing."
2. **Session rule 7, the first sentence replaced to match.** "A builder commits and pushes its branch at every step that leaves the
   tests it has written so far green or expected-red, with a commit subject that starts `checkpoint:`." becomes "A builder commits
   its branch at every step that leaves the tests it has written so far green or expected-red, with a commit subject that starts
   `checkpoint:`, and pushes at milestones (tests red, then green, then ready) and always before it pauses, ends or asks a
   question, so that a stopped session loses nothing."
