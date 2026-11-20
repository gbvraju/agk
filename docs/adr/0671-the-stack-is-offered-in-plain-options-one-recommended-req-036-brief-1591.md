# ADR-0671: The stack is offered in plain options, one recommended, accepted by one yes (REQ-036, REQ-069)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1591, SPEC-0029, amendment 199, SPEC-0062, SPEC-0072, SPEC-0057, ADR-0103, ADR-0163, ADR-0667, brief #1587, brief #1577, brief #1602, plan #661
- Requirements: REQ-036, REQ-069

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `config/`, `skills/`

## Context

On the default branch at 57787aa (2026-11-20) `engines.py` `stack_problems` checks two or three options A to C, each
with `Trade-offs:`, `Practices:` and, when present, one `External services:` list. It asks for no recommendation and
no effect on cost, speed, security or uptime, so a record written for an architect passes: measured on this branch, a
Proposed record with no `(recommended)` option and no effects passes `stack-check`. SPEC-0062 rule 6 asks the steward
for each choice "in plain words with its effect on cost, speed and security and its recommendation"; SPEC-0029 rule 5,
the record's form, says nothing of one. No default stack per shape exists (`config/playbooks/` carry gates and a test
map, `config/stack-signals.toml` only detects eight stacks), and the accepting change of `skills/stack/SKILL.md` step 4
is a printed prompt for two hand-made commits that a business person cannot make alone.

## Decision

1. SPEC-0029 rule 5 changes only through amendment 199, which this build writes and does not apply; it is applied word
   for word on the owner's approval of SPEC-0029.
2. **Four effects and one recommendation.** In a Proposed stack record, each option's `Trade-offs:` holds the four
   labels `Cost:`, `Build speed:`, `Security:` and `Uptime:`, each followed by a plain phrase, and exactly one option
   carries `(recommended)` in its name, with a `Why:` after its trade-offs that names a need from the charter or the
   discovery document. `stack-check` refuses each failure naming the rule and the option letter, never a value. An
   Accepted record is checked as before, so no record written before this change is refused (Q-1591-3, principle 11).
3. **A default per shape.** `config/stack-defaults.toml` (a kit file, installed verbatim) holds one `[[default]]` row
   per shape: `work_type`, `stack` (a `[[stack]]` name of `config/stack-signals.toml`), `description`, the four effects
   and `reason`. `stack-write` writes the row of the declared `[delivery] work_type`, else the `default` row, as Option
   A marked `(recommended)` with `Why: <reason>`, so two runs for one shape recommend the same option. The rows this ADR
   proposes, for the maintainers to accept or change here (Q-1591-2):
   - `default`: one small Python application with a file database on one machine, while the shape is not known;
   - `web-app`: one Python web application with a managed database;
   - `data-pipeline`: a scheduled Python job that reads a file and writes the report, with no server.
   Each names `python-pyproject`, the stack whose tools the kit already pins (SPEC-0072 `Q-S0072-3`). A shape with no
   row of its own takes the `default` row; brief #1602 adds the API service row.
4. **The honest effect of a missing pack.** No standards pack is built yet (SPEC-0072 build (e)), so each row's
   `Build speed:` says "code checks for this choice come later"; the build that adds a stack's pack changes its rows.
5. **The repository's own stack first.** When `front_door.py` detection finds exactly one stack in the committed tree
   and it is not the row's stack, Option A is that stack, kept, with its effects left for the drafter: a rewrite is
   never proposed (SPEC-0057).
6. **One yes accepts it.** `engines.py stack-accept --option X --reason TEXT` checks that the one stack record is
   Proposed and passes, that X is one of its options and that the reason is one line, then makes the two ordinary
   commits of `skills/stack/SKILL.md` step 4: the first changes only `- Status:` to `Accepted` and the `Chosen` line to
   `Option X — <reason>`; the second copies the option's `test selection` profile and `always_full` paths into the
   `[testing]` table of `agk.toml` and changes nothing else (none when they already match). A refusal writes nothing.
   It runs in a builder's session from a mechanical brief that the steward drafts after the person's one plain yes
   (Q-1591-1); the person types no line. In team mode the yes is a spec approver's (SPEC-0063).
7. **The steward presents it in plain words.** `docs/guides/steward-voice.md`, which the steward's role file already
   follows for every reply, shows the options with the four effects and the recommendation and asks one yes; the role
   file itself is unchanged, as its word budget holds (`config/rule-budget.txt`).

## Consequences

A business person sees two or three choices with what each costs, how fast it is built, how safe it is and how often it
may stop, one recommended for their shape, and accepts with one word; the record stays the project's. A project's own
engine (`[engines] stack`) still drafts, and its record passes the same check. Hosted, local and personal modes run the
same check; personal mode prints the yes for the developer (SPEC-0062 rule 16).

## Residual

- The rows for the other shapes of `playbook_format.WORK_TYPES` (mobile, cloud migration, RAG, MCP server, multi-agent,
  voice agent, pilot) are not proposed; they take the `default` row until a maintainer adds theirs (due 2026-12-31).
- The `Why:` is checked for presence only; that it names a real need of the charter is review (due 2026-12-31).
