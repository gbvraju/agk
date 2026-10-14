# K1 live proof (SPEC-0001 rule 24)

Source of the sandbox facts: the day-4 brief from the maintainers. This agent has no access to
`gbvraju/agk-sandbox`; those facts are recorded as reported and were not re-checked here. Kit facts were checked in
this repository.

## Record

- Kit: `main` at 86868be (PRs #1–#7 merged).
- Target: `gbvraju/agk-sandbox`, a public repository.
- Sandbox PR #1, adopt agk: 32f893f.
- Sandbox PR #2, wordcount with ADR-0002: aa1bc61.
- Sandbox PR #3, accept ADR-0002: 88337bd.
- `init` created 41 files with no conflicts.
- Sandbox `make test`: 95 passed before the project's code, 98 after, with the project's own tests collected.
- Governance green in CI on the sandbox pull requests.
- Reviewer's negative test: removing ADR-0002 made `check_protected_changes` fail, naming `docs/requirements.md`.

## Lessons

- Running a cloned `init.py` from an agent session is blocked as external code until a maintainer authorizes it in the
  session; at K1 init is a human-approved step (the K3 plugin form removes this).
- An empty repository needs one direct first commit (there is no base branch for a PR); record it in the target's
  ADR-0001.
- A maintainer merge can overtake an agent's final commit: briefs say "final commit, then merge", and agents check PR
  state before pushing.
- The deny list held: the agent could not delete a branch and did not look for a way around.
- pytest may be missing in a session; a throwaway venv outside the repository is acceptable; CI installs its own.
- Agent scripts use quoted heredocs (`<<'EOF'`); unquoted ones expand backticks.
- CODEOWNERS renders duplicate lines when a path is in two classes (fixed in PR #9, ADR-0006).

## Questions

- Q-K1-15: the brief dates the K1 Decisions line `2026-10-15`, but `date -u` in this session reads 2026-10-14. The
  line is recorded as given; this PR's own rows use `date -u`. Maintainers to confirm which date is authoritative.
