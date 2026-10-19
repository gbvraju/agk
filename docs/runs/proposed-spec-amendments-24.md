# Proposed spec amendments 24 (SPEC-0013 rule 17; SPEC-0005 rule 8)

Date: 2026-10-19 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0042. The paths:
`docs/specs/0013-playbook.md`, `docs/specs/0005-distribution.md`.

1. **SPEC-0013 rule 17, the wording of the `CLAUDE.md` line.** The rule says the line names `gh pr view` ("`gh pr view` uses GraphQL, which cloud
   sessions block") and that a test fails if `gh pr view` appears in `CLAUDE.md`. Both cannot hold. Conservative reading (Q-K4-181): keep the test, which
   protects every instruction file, and reword the line so that it does not name the command: "Check the state of a pull request with
   `gh api repos/{owner}/{repo}/pulls/{n}` (a GET); the GraphQL form of the command is blocked in cloud sessions." The meaning is unchanged.
2. **SPEC-0005 rule 8, the `/agk:architect` row** (item 1 of `proposed-spec-amendments-15.md`, the `architect` part): `playbook.py architect`; it reads and
   writes nothing, so rule 9's list of user-invoked commands does not gain it (a reader, like `doctor` and `review`). Q-K4-182 records the choice against
   SPEC-0013 rule 7's words "user-invoked".
