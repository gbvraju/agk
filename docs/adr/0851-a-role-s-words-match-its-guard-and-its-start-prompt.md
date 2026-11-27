# ADR-0851: A role's words match its guard and its start prompt

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2053, 2026-11-27T19:12:13Z)
- Related: ADR-0211, ADR-0201, ADR-0495, ADR-0585, ADR-0586, SPEC-0030, SPEC-0064, REQ-071, brief #2053, brief #383, brief #341, plan #661
- Requirements: REQ-071

Protected classes: `tests/kit/`, `agk.toml`

## Context

Each guard and start prompt is tested with forms written in the test, never with the forms the role files name, so a
role line and its guard can drift apart unseen: the conductor's guide step says `conductor.py reprove --pr <n> --apply`
and the conductor's guard refuses it (`Q-1163-1`, since 2026-11-12); a supervised build start does not say it is one
short job; the conductor's agent file orders a `watch` loop and a wake-up timer beside its ban (ADR-0585). Brief #383
(ADR-0211) ran both sides of one rule in one test; this extends that to every command a role's files name.

## Decision

1. **Say matches permission.** `tests/kit/test_role_commands.py` reads the roles from the `PreToolUse` hooks of
   `.claude/agents/*.md`, gathers each role's sources (its agent file, `kit/templates/runtime/<role>.txt`, the skills
   its agent file names, and the guide paragraphs of `ROLE_PARAGRAPHS`), fills the placeholders of every full
   `python3 ... scripts/agk/<script>` form from one `FILL` table, and judges each with that role's own guard's
   `decide`. A refusal fails naming the role, the file:line and the guard rule, never the filled value; a form left
   with a placeholder fails naming its class; an elided form is skipped. A role whose `tools:` line grants no shell
   (the reviewer, the drift auditor, the personal reviewer) runs no command, so the forms its file names are inputs
   and are not judged.
2. **One start, one kind line.** Every call of `launch.prompt_for`, `launch.resume_for` and `launch.start_with` in
   `scripts/agk/*.py`, found by AST, and the `job:` steps of `launcher.txt` are in `START_PATHS` as `supervised` or
   `person`, keyed by file, function and call; a supervised start carries `launch.FIX_JOB`'s opening words
   (`This is one short job (SPEC-0064 rule 4)`), read from the module, in the same sum or by `+=` on the prompt's name,
   and a `job:` step of `launcher.txt` its `one short job`. A `start_with` call without prompts is judged by
   `launch.prompt_for`'s text. A call site not in the table, or an entry with no call, fails naming its file and
   function.
3. **No order beside its ban.** A ban sentence (`never run`, `run no`, `start no`, `schedule no`) of `watch`, `loop`
   or `wake` in one role's sources, and an order of the same form or the banned tool in the front matter, fail naming
   both file:lines; a ban under an all-caps label binds only that label's lines, and `MODE_SPLITS` names the label
   pairs that are modes.
4. **Known cases by name.** `EXPECTED` holds each known mismatch with its Q- id, run as a strict expected failure, so
   the pull request that fixes one removes its entry; `OTHERS_RUN` holds a form a role file names as another actor's.
   An entry without a Q- id or brief, or whose form no longer appears at its file, fails as stale.
5. **Settings.** In fixture projects: `route.py --all` and `evidence.py check` pass with `execution = "local"` and are
   refused with `"ci"` by a message naming the setting, never the value; the merge and adapter forms pass only with
   `auto_merge`, `auto_start` and `launch_adapter` on in the checkout and at `origin/main`; `[kit] layout = "plugin"`
   gives each form the decision of the installed form; `review_mode`, `[personal] forge`, `[flow] builder_start` and
   `[autopilot] mode` change no decision and no start prompt.
6. **Wiring.** The test joins `[testing] whole_tests` and the `[testing]` map of `conductor_guard.py`,
   `steward_guard.py`, `launch.py` and `autopilot.py` (`Q-P0B-3`: no new governance step).

## Consequences

A role text and its guard or start prompt that disagree fail before merge; the known cases stay visible by name until
the briefs that fix them (P2 and P3) remove their entries. No role file, guard, runtime text, launch prompt, workflow,
ruleset, required check, label, `agk.mk` or `governance_map.CHECKS` changes.

## Residual

`Q-2053-1`: in a plugin-layout project the conductor's guard refuses the plugin's form of `route.py --all` and
`evidence.py check`, which it allows only as the project's own file; the three forms are strict expected failures
(`plugin-route`, `plugin-route-pass`, `plugin-evidence`) until the maintainers rule. `Q-P0B-1` (the conductor's `check_brief.py`, `checklist.py` and `metrics.py --save-checklist` lines) and `Q-P0B-2`
(the adapter start's job kind) are decided by the maintainers in P2 and P3; `Q-1163-1` stays due 2027-01-31.
