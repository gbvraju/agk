# ADR-0624: /agk:setup build (g): the steward hands off to /agk:setup, and back undoes only what it added

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: SPEC-0065, ADR-0619, ADR-0621, brief #1466, plan #661
- Requirements: REQ-072

## Context

SPEC-0065 (Approved) names eight builds of `/agk:setup` (rule 18); this is build (g): the steward's hand-off of rule 2
and `/agk:setup back` of rule 13, with rule 17's change to `.claude/agents/steward.md`, which rule 18 says comes with
its own ADR. A person who asks the steward in plain words to be set up gets the same command a developer runs, and a
person who wants it undone gets back the machine and the project settings as they were, with nothing uninstalled and
no data deleted.

## Decision

1. **The steward's hand-off.** `.claude/agents/steward.md` gains one paragraph and one row of its stage-to-skill
   table (`setup`): when a person asks in plain words to set up this machine, or to undo it, the steward follows the
   `setup` skill's steps, asks its questions in its own voice, acts only on the person's yes and never runs the
   commands the skill prints for the person (commit, `prepush.py --record`, push).
2. **The record.** `setup.py` keeps what it added on this machine in `<git dir>/agk/setup.json`
   (`git rev-parse --absolute-git-dir`): `tasks`, the names of the scheduler tasks its WSL pass added (the pass's
   `watchdog` row `done`; the name is `wsl_setup.ps1`'s WSL task, or autopilot's WSL task when `[autopilot]` is
   set), and `settings`, each setting `settings --yes` proposed with its value and the value it replaced (`null`:
   absent). Nothing is recorded twice; a folder that is not a clone records nothing.
3. **`setup.py back`.** Without `--yes` it names what it would do and changes nothing (exit 1). With `--yes` it
   deletes each recorded task by its name (`schtasks /Delete /TN <name> /F`) and drops it from the record; a refused
   delete is `failed` and stays recorded for the next run. It then prepares the reverse change: each recorded setting
   whose value on the default branch is still the one setup proposed goes back to the value it replaced (a key setup
   added is removed), on a new branch `agk/setup-back-<date>` with the project's next ADR and a body, built by the
   same code as the settings change, and prints the commands the person runs; it commits, pushes and merges nothing.
   A setting changed since, or never merged, is left as it is; when none is left, no branch is made. A record that
   cannot be read is refused naming `setup.json`, and nothing is done. `back` uninstalls no tool, removes no worktree
   and deletes no file of the project.
4. **The skill.** `skills/setup/SKILL.md` gains the `/agk:setup back` form: show what it would do, ask one yes, run
   it with `--yes` and show the printed commands for the person.

## Consequences

A business user can ask the steward to be set up, and anyone can undo a setup without losing a tool, a worktree or a
file. Protected path classes changed: `scripts/agk/` (`setup.py`), `tests/kit/` (`test_setup_back.py`), `.claude/`
(`.claude/agents/steward.md`), `skills/` (`skills/setup/SKILL.md`) and `agk.toml` (the `[[testing.map]]` entry for
`setup.py` gains the new test file).

## Residual

- 2026-11-18 (verify): the task delete by name has run only against a stub runtime; a person's run on Windows confirms
  it (due 2027-03-31).
- 2026-11-18: the WSL script disables, and never deletes, the Windows watchdog task when it adds its own; `back` does
  not re-enable it, since rule 13 names only the removal of the tasks setup added (Q-1466-1).
