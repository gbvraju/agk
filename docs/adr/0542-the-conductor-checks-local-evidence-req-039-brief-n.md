# ADR-0542: The conductor checks local evidence

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0233, ADR-0536, SPEC-0030, SPEC-0039, brief #982, brief #1269, brief #1281, plan #661
- Requirements: REQ-039

## Context

ADR-0536 (brief #1269) keeps each builder's local-mode record in `<git common dir>/agk-evidence/<head>.json` and lets
`python3 scripts/agk/evidence.py check --head <sha>` find it from the head alone. The review agent's guard allows that
command (brief #982), but the conductor's guard (`.claude/hooks/conductor_guard.py`, SPEC-0030 rule 6) allowed no
`evidence.py` command, so a guarded conductor could not write the `Evidence check:` line that `merge_cleared.py` reads in
local mode, and a cleared, green pull request stayed held. The maintainers answered Q-1269-1 on #1271 (2026-11-14): allow
the evidence check in the conductor's guard.

## Decision

1. `.claude/hooks/conductor_guard.py`, without `--shadow`: allow exactly
   `python3|python scripts/agk/evidence.py check --head <7 to 40 lower-case hex> [--sample <n>] [--json]` and
   `... check <RECORD> --head <hex> [...]`, the project's own regular file of the script, each option at most once and in
   any order. RECORD is an existing regular file named by its absolute path, with no link and no `..`, in a scratch
   directory (`agk-conductor-<name>` in the system temp directory) or directly in the clone's shared evidence folder,
   found with one `git rev-parse --git-common-dir`. Without a matching record the check runs the head's governance and a
   sample of its tests in a temporary worktree with the conductor's environment, so it is not a read: both forms are
   allowed only while the project is in local mode, judged as for `route.py` (`route.record_open`, ADR-0534), and in CI
   mode they are refused with a message naming the setting (`execution`, or the one local-mode record issue). Every other
   subcommand or option, a second RECORD, a record elsewhere, a shell character and another copy of the script stay
   denied; the shadow reviewer gets none of it.
2. `.claude/agents/conductor.md`: the local-mode paragraph says to run the check before a clearing verdict, and the list
   of what the guard allows names `evidence.py check`. The role file stays within its rule budget (4496 words, 37 rules;
   `config/rule-budget.txt` lowered from 4498).

No workflow file, ruleset or `constitution/` file changes.

## Consequences

In local mode a guarded conductor runs the evidence check itself, so its verdict carries the `Evidence check:` line and
the guarded merge is no longer held for it. In CI mode no record is read and the command is refused, naming the setting.
In personal mode there are no pull requests and nothing changes. The check makes a temporary worktree outside the
repository, runs the head's governance and a test sample there and removes it (ADR-0233), so nothing is written in the
project. Tests: `tests/kit/test_conductor_guard.py` (a) both forms allowed in local mode and refused in CI mode, (b)
every other form refused, (c) the existing cases stay green. Protected path classes changed: `.claude/` (`.claude/hooks/conductor_guard.py`, `.claude/agents/conductor.md`),
`config/` (`config/rule-budget.txt`) and `tests/kit/` (`tests/kit/test_conductor_guard.py`).

## Residual

- 2026-11-14: a session on another machine still hands the conductor a RECORD file; the guard allows it only from a
  scratch directory or the shared folder, so the conductor copies it into a scratch directory first (its one `Write`).
- 2026-11-14: unlike the conductor's bounded run (`env -i PATH="$PATH" HOME=<scratch>`), the evidence check's re-run of
  the head's governance and tests is not started from an empty environment; whether it should be is for the maintainers
  (Verdict on 09f9127).
