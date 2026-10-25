# Proposed spec amendments 76 (SPEC-0012, SPEC-0030, SPEC-0036; REQ-043)

Date: 2026-10-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0140.

1. **SPEC-0012 (intake), the next steps.** `intake.py next-steps` and `playbook.py next-steps` print a body that also has a line `Summary: <one plain sentence>`, because the pull request body check (SPEC-0036 rule 1) requires one; the sentence is fixed text, not a value of the project. Path: `docs/specs/0012-intake.md`.
2. **SPEC-0030 rule 1, the session rules.** `config/session-rules.md` also holds, as SPEC-0036 says: every pull request body that is not a draft has one line `Summary: <one plain sentence>` of 1 to 120 characters that says what the change does for a person, not how (rule 27). Path: `docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md`.
3. **SPEC-0030 rule 6, the conductor.** `.claude/agents/conductor.md` gives no clearing verdict while the `Summary:` line is missing or written for developers (SPEC-0036 rule 6).
4. **SPEC-0036 rule 1, the line.** A body has exactly one `Summary:` line: two such lines fail, and the line starts at the beginning of a line. Path: `docs/specs/0036-whenever-a-pull-request-changes-state-the-project-publishes.md`.
