# ADR-0802: The grill skill asks, grill.py records each answer and prints readiness

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0073, SPEC-0048, SPEC-0062, SPEC-0059, ADR-0801, ADR-0793, ADR-0664, amendment 235, brief #1934, brief #1933, plan #661
- Requirements: REQ-080

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0073 (Approved) rule 15 build (b) follows build (a) (ADR-0801), which left `grill.py questions` as the only
command and no skill. Before this build, on the default branch at 95324e7, `skills/grill/` did not exist,
`day_zero.py write` kept only rows whose id is in `front_door.ORDER` (so a kept `riskiest` answer was dropped), and
`front_door.auto_pilot_wait` named no question for the conductor's rounds. Amendment 235 (SPEC-0048 rules 4 and 13) was
approved by the owner on #1920 (`Maintainer answer: amendment 235 approved`, 2026-11-25 10:25 UTC); its text is applied
by build (c).

## Decision

1. `skills/grill/SKILL.md`, a skill of kind `design` at `strongest`/`high`, runs one interview per problem from
   `/agk:vision` step 4 (before the topics), a problem issue's discovery and day zero. It reads first the person's
   sources, day zero, `front_door.py detect` and the playbook, says in one line what it read, and asks each item that
   `grill.py questions` prints with one recommendation, one question per message, at most three per round. A vague
   answer gets one follow-up; a second is recorded as given and marked `assumption`. A contradiction is shown side by
   side once; nothing is overwritten. It names no kit term to the person and offers three choices, one recommended.
2. `grill.py record --answers FILE --id ID (--stated F | --assumption F --test T | --open | --risk-accepted)
   [--accepted WHERE] [--source T] [--replace] [--playbook KIND] [--root DIR]` appends one row to the answers file's
   `grill` list, the claim quoted as given: `{id, claim, status, test?, source?, accepted?, revised?}`, or for a risk
   `{id, risk: "Risk accepted: <id> (<UTC time>)"}`. It refuses an id that is not a grill item of the composed playbook
   (its items at every depth, and `success`), an `assumption` with no test, a second row for one id without `--replace`
   and the person's words (the earlier row stays; the new one is added after it with `revised: true`), and an answer in
   which the data guard finds anything, naming the class. `--accepted` (a plain yes, `accepted recommendation (<where>,
   <UTC time>)`) and `--risk-accepted` are refused with `review_mode = "team"`, naming `review_mode`. `record` never
   writes `answers`, so `discovery-write` reads the file as before.
3. `grill.py ready --answers FILE [--depth D] [--playbook KIND] [--root DIR]` prints `critical <settled>/<total>; risk
   accepted: <ids or none>; questions <asked>/<budget>; accepted recommendations <n>` and exits 1 while a critical item
   is open with no accepted risk. Settled is an id's last row `stated`, or `assumption` with a test, or a risk row for
   the id; `success` with no grill row reads its `answers` row. The critical total is the composed playbook's critical
   items and `success`; asked is the ids with a row; the budget is the depth's.
4. `skills/vision/SKILL.md` step 4 runs `/agk:grill` first. In auto-pilot the round wait line of
   `front_door.auto_pilot_wait` ends `; grill items: <ids>`, the next at most three items that `grill.py questions`
   prints and that no earlier `Discovery: round <n>` names as `- <id>:`; with no default playbook the line reads as
   before. `.claude/agents/conductor.md` and `MAX_ROUND` are unchanged.
5. `day_zero.write` keeps, beside `answers` (on `ORDER` as before), a `grill` list of the kept rows whose id is a grill
   id and not an `ORDER` id (`grill.grill_ids(root)`), each `stated` with `where: in session <date>`; any other id is
   dropped as before, and with no grill row the file is as before.
6. `grill.py` stays one `kit/manifest.json` `verbatim` row and the skill ships under `skills/`, already a folder row;
   `kit_hashes.py` reports no change, since the table is the release's. `tests/kit_dev/test_distribution.py` lists
   `grill` among the skills, user-invoked, running `grill.py`.

## Consequences

An idea's grill answers are kept as the person's, marked `stated`, `assumption` or `open`, and readiness is a printed
line with an exit code that build (c) writes into the discovery document and holds on. Every existing answers file,
discovery document and auto-pilot fixture reads as before. No workflow, label, required check, `agk.mk` recipe or
governance step changes.

## Residual

- 2026-11-25: team routing by area and risk acceptance by a reviewer of the area are build (d)'s; until then
  `--risk-accepted` and `--accepted` are refused in team mode.
