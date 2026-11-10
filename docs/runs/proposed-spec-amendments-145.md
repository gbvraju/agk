# Proposed spec amendments 145 (SPEC-0045, SPEC-0034, SPEC-0006; REQ-052)

Date: 2026-11-10 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written
for brief #798, answer 6 (spec first). The paths: `docs/specs/0045-each-kind-of-work-runs-on-the-model-it-needs.md`
(rules 2, 3, 5, 8 and 10), `docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md` (rule 6)
and `docs/specs/0006-doctor.md` (rule 5, item 9 only). The number 145 is the one brief #798 reserved. This amendment is
not applied to the spec text in this pull request; the owner decides it, and it needs a person's `Approve: SPEC-0045`,
`Approve: SPEC-0034` and `Approve: SPEC-0006`; no session posts them, and no build starts before them.

Answer 4 of the brief (measured capacity) moved to brief #842 on 2026-11-09 (the co-owner's comment on #798) and is in
amendment 149; nothing here records capacity, and build (c) of the brief is dropped. The items below are answers 1, 2,
3 and 5.

The baseline, read on the default branch at f829c51: `config.model_settings` accepts only the five kinds, `names` and
`providers` in `[models]` (amendment 157); `launch.py` hands `AGK_KIND`, `AGK_TIER`, `AGK_EFFORT` and `AGK_MODEL` to an
adapter; `metrics.usage_of` sums the `Usage: <n> tokens` figure that ends the first line of a builder's `Report:`, and
`metrics.py --usage-by-kind` prints the sums per kind; no `[models.routes]`, `[models.prices]` or `usage.py` exists.
This repository sets `[flow] builder_start = "assign"` (ADR-0402): no session starts a builder; slots `s1` to
`s<builder_slots>` run from the owner's scheduled starts and take the briefs of the conductor's `Assign:` lines, which
`session.py plan` lists. With `builder_start = "start"` the conductor starts each builder, as before.

## The tier reaches the runtime (answer 1)

1. **SPEC-0045 rule 3, the routes table.** After the sentence on `[models.names]`, rule 3 gains: "An optional
   `[models.routes]` table maps a tier to how a session of that tier is started, as `<tier> = { task = "<label>" }`
   (a scheduled task of the runtime, named by a plain label of SPEC-0053 rule 3's shape) or `<tier> = { flag = true }`
   (a local command that takes the model flag, with the model name from `[models.names].<tier>` or the label
   `session.py fallback` prints, so the name stays in one place), or, with `builder_start = "assign"`, `<tier> = {
   slots = ["s1", ...] }` (the slots whose scheduled starts the owner runs on that tier). A table that routes any tier
   routes `strongest`. A tier outside the three, a key other than `task`, `flag` or `slots`, a route with more or fewer
   than one of them, a label of the wrong shape, a `flag` route for a tier with no `[models.names]` entry and no
   provider list, a table without `strongest`, a `slots` route under `start` or a `task` or `flag` route under
   `assign`, and under `assign` a slot outside `s1` to `s<builder_slots>`, in two routes or in none, are refused naming
   the setting (`setting: models.routes` or `setting: models.routes.<tier>`), never the value. The kit's
   `agk.toml` and its templates carry no `[models.routes]`." (`Q-798-2`, `Q-798-3`.)
2. **SPEC-0045 rule 2, the table's keys.** `[models]` accepts `routes` and `prices` (item 9) beside `names`,
   `providers` and the five kinds; any other key stays refused as today (`setting: models.<key>`).
3. **SPEC-0045 rule 5, the route of a start.** Rule 5 gains: "A session is started on the route of its tier. A tier
   with no route is started on the route of the next stronger tier (`fast` to `mid` to `strongest`), never a weaker
   one, and every `Report:` of that session carries one line `Route: <kind> <tier> via <tier>` beside its `Usage:` line;
   a session on its own tier's route carries none. With `builder_start = "assign"` the route of a start is a slot:
   `session.py plan` pairs a brief with a free slot of its tier, else with a free slot of the next stronger tier, never
   with a slot of a weaker one, and a brief with no such free slot waits; the slot's builder carries the `Route:` line
   when its slot's tier is stronger than the brief's. With no `[models.routes]` table every session starts on today's
   one route and nothing changes. An escalation restarts the work on the route of the tier one up." (`Q-798-4`,
   `Q-798-11`.)
4. **SPEC-0045 rule 7, the prompt and the adapter.** `launch.py prompts` names the route beside the tier (`route: task
   <label>`, `route: flag` or `route: none`, and `via <tier>` when item 3 moved it), and the adapter gets it as
   `AGK_ROUTE` (`task:<label>`, `flag` or `none`). A prompt built with no routes table is byte for byte as today. With
   `builder_start = "start"`, the conductor's start step and the re-fire line of `conductor.py sweep` use that route:
   in cloud mode the conductor fires the scheduled task the route names, and in local mode the adapter passes the model
   flag. With `builder_start = "assign"`, `launch.py` still starts nothing; the conductor posts the `Assign:` lines of
   the plan, whose form is unchanged, so the route is the slot the plan chose, and a stall's restart and a merge of
   main are assigned the same way. No session starts, stops or fires another on its own (SPEC-0034 rule 6), and a
   builder never fires a scheduled task.
5. **SPEC-0034 rule 6, the launcher contract.** The sentence "The guide shows the contract with two examples" gains:
   "Where `[models.routes]` names a task per tier, the scheduled-task example is one task per routed tier, each with the
   same stored prompt; the owner creates each task once, and `demand` is unchanged. Under `builder_start = "assign"`,
   the owner runs each slot's scheduled starts on the tier of the route that names the slot." The guide says which tier
   the kit's own examples use and that a missing `mid` task, or no `mid` slot, means `mid` work runs on `strongest`.
6. **SPEC-0006 rule 5 (a consequence of items 1 and 3).** `doctor.py` gains one row `model-routes`, severity `warn`:
   it warns on a refused `[models.routes]` (naming the setting) and on a tier that a kind of `[models]` or rule 2's
   defaults uses and that has no route of its own while a routes table exists, naming the tier and the route it will
   use instead (under `assign`, a tier with no slot); with no table it prints `ok (one route)`. It never fails the
   run, and the `slot-schedule` row of ADR-0402 is unchanged.

## The real usage (answer 2)

7. **SPEC-0045 rule 8, the figure.** "when the runtime shows the figure" becomes: "as `python3 scripts/agk/usage.py`
   prints it". `usage.py` (installed, read-only: it writes no file, posts nothing and makes no network call) reads the
   running session's own transcript file, found by the runtime's session id variable under the runtime's home folder
   `(verify: the variable and the folder are read from this cloud runtime, not from its documentation, Q-798-5)`, or
   the file `--transcript FILE` names. It sums, over the entries with a distinct message id, the four token counts of
   each entry's usage record: input, cache creation input, cache read input and output (`Q-798-6`). It reads no other
   field of an entry than its id, its timestamp and those counts, and prints no text of the transcript. Its one line
   is `Usage: <n> tokens`, or `Usage: not shown` when no transcript is found, none can be read or it holds no usage
   record; never 0 for a missing figure and never an estimate. `--since <UTC time>` sums only entries at or after that
   time, so a builder passes the time of its previous `Report:` and each figure is the tokens since then, as session
   rule 8 already says of `Progress:` lines (`Q-798-7`). The `Report:` line of session rule 17 and the `Progress:`
   line of session rule 8 take its line as printed.
8. **SPEC-0045 rule 8, what is counted.** The session's own transcript only: a helper agent's tokens are counted only
   where the runtime writes them into that file (`Q-798-8`). The reader of rule 8 (`metrics.usage_of`) is unchanged:
   it sums the `Report:` figures of one pull request, and with item 7's `--since` no token is counted twice.

## Cost per pull request (answer 3)

9. **SPEC-0045 rule 8, the prices.** An optional `[models.prices]` table maps a tier to a price per million tokens, as
   `<tier> = <number>` (0 or more, an integer or a decimal); a tier outside the three or a value that is not such a
   number is refused naming `setting: models.prices` or `setting: models.prices.<tier>`, never the value. The kit's
   `agk.toml` and templates carry none. It names no currency; the output says `cost <x> at the prices table`.
10. **SPEC-0045 rule 9, the sums.** `metrics.py --usage-by-kind` prints, under each kind's line, one line per merged
    pull request (`#<n> <tokens or not reported>`), and with a prices table one cost line per kind. A pull request is
    priced at the tier of its kind, or at `strongest` when one of its `Report:` comments is an `escalate` or names a
    `Route:` of item 3 (`Q-798-9`); a pull request with `not reported` adds no cost and is counted as such; a tier with
    no price makes that kind's cost `unknown`. Without the table only tokens are printed, as today. Nothing is added to
    `report.json` or to the metrics columns, as rule 8 already says.

## Every mode, the builds (answers 5 and 6)

11. **Every mode.** GitHub, local and personal projects read the same tables with the same defaults. A project with no
    `[models.routes]` keeps today's one route, and one with no `[models.prices]` prints tokens only. Personal mode
    starts no builder session, so routes do not apply there; `usage.py` works in any session. Nothing here needs a
    workflow, a ruleset, a required check or a network call in a check.
12. **SPEC-0045 rule 10, the builds.** Each is tests first and about 300 changed lines or fewer, from the default
    branch, with its own ADR (`Q-798-1`).
    - (a) Items 7 to 10: `scripts/agk/usage.py` (new and installed: `kit/manifest.json`, a `[[testing.map]]` entry in
      `agk.toml`), the prices reader in `scripts/agk/config.py`, the per pull request and cost lines in
      `scripts/agk/metrics.py`, the `Usage:` sentences of session rules 8 and 17 within `config/rule-budget.txt`,
      `tests/kit/test_usage_transcript.py` with invented transcripts in `tmp_path`, one `changelog.d/` fragment. No
      dependence.
    - (b) Items 1 to 6: the routes reader in `scripts/agk/config.py`, `scripts/agk/launch.py`, the slot pairing of
      `session.py plan` in `scripts/agk/session.py`, the re-fire line of `scripts/agk/conductor.py`, the `model-routes`
      row of `scripts/agk/doctor.py`, one sentence in `.claude/agents/conductor.md` and the `Route:` sentence of session
      rule 17 within the budget, the guide's example, `tests/kit/test_model_routes.py`, one `changelog.d/` fragment.
      `Depends-on` (a), for the shared `config.py` and `config/session-rules.md`.
13. **Tests.** Rule 8's tests gain: an invented transcript with repeated message ids sums each id once; `--since` drops
    the earlier entries; no file, an unreadable file and a file with no usage record print `Usage: not shown`; the
    output never holds a transcript's text (a marker string in a fixture message is absent from stdout); the command
    runs with the network blocked. The tests of rules 2 and 3 gain each refused shape of items 1 and 9, naming the
    setting and not the value, and no routes or prices table in the kit's `agk.toml` or templates. Rule 5's and 7's
    tests gain: no table gives today's prompt and adapter environment byte for byte; `mid` with no route goes `via
    strongest`; no route is ever weaker than the tier; under `assign`, the plan never pairs a brief with a slot of a
    weaker tier, pairs it with a stronger one only when none of its own tier is free, and with no table lists what it
    lists today; the doctor row's three cases.
14. **Not in this amendment.** Capacity (amendment 149), the provider fallback (SPEC-0053), the review floor (rule 6)
    and every gate, check and reading list are unchanged. `constitution/`, the workflows, the ruleset and the required
    checks are not touched. No model name enters a tracked file of the kit.

## Questions

Each is open until a person rules; the reading after it is the conservative one the items apply.

- **Q-798-1:** the reserved `ADR-0375` is already on the default branch (brief #802's governance step, merged). Reading:
  this pull request adds no ADR and takes no new number; builds (a) and (b) each change a decision of SPEC-0045 and so
  each asks the conductor to reserve its own ADR on the brief.
- **Q-798-2:** what is a cloud route's value? The brief says "a scheduled task per tier"; a task's id or link may name
  an account. Reading: a plain label of SPEC-0053 rule 3's shape (the task's name), never an id, a link or an
  address; the conductor finds the task by that name.
- **Q-798-3:** what does a local route hold? The brief says "the command's model flag", but SPEC-0045 rule 3 keeps a
  model name in `[models.names]` alone. Reading: `flag = true`, with the name taken from `[models.names]` or the
  provider label; no second place for a name.
- **Q-798-4:** what if a routes table has no route at or above a tier? Reading: impossible, since a table without
  `strongest` is refused (item 1); "next stronger" then always ends at `strongest`.
- **Q-798-5:** how does `usage.py` find the transcript? Read in this session (2026-11-10): the runtime sets a session
  id variable, and a file named by that id lies in a per-project folder under the runtime's home. Reading: that lookup,
  marked `(verify)` until build (a) reads it from the runtime's documentation, with `--transcript FILE` for any other
  runtime; nothing found prints `Usage: not shown`.
- **Q-798-6:** which counts make the figure? The brief says "input, cached input, output". Measured in this session at
  that time: 36 entries with a usage record, 20 distinct message ids, so a plain sum counts some messages twice; and
  cache reads were about 96 percent of the total. Reading: one figure, the sum of the four counts per distinct id, so
  the `Report:` form and `metrics.usage_of` are unchanged; splitting it is a later decision.
- **Q-798-7:** a session posts several `Report:` comments and may build several pull requests (session rule 18), and
  `usage_of` sums every `Report:` of a pull request. A whole-transcript figure in each would count tokens again.
  Reading: each `Report:` carries the tokens since the session's previous `Report:` (`--since`), the first one the
  tokens since the session started.
- **Q-798-8:** are helper agents' tokens counted? Reading: only those written into the session's own transcript file;
  the residual records the possible under-count, never filled by an estimate.
- **Q-798-9:** a pull request may have run on a stronger tier than its kind's (an escalation, item 3's `via`), and the
  facts do not say which. Reading: price it at `strongest` whenever either shows, the higher of the two readings; and
  one price for every token, cached or not, as the brief says, so the cost line is an upper bound and says so.
- **Q-798-10:** the brief's Measured line says 0 `Report:` lines with a token figure since build (d). Reproduced on
  2026-11-10: the first page (100 comments since 2026-11-09) of the repository's issue comments holds 18 `Report:`
  lines, each ending `Usage: not shown`; the next page could not be read (the session's proxy refused it). Reading: the
  cause holds; the full count is for build (a)'s `Verified:` line.
- **Q-798-11:** the brief was filed when the conductor fired each builder's task; since ADR-0402 merged (2026-11-10
  02:53Z) this repository starts builders from `Assign:` lines read by slots `s1` to `s<builder_slots>`. How does a
  route apply there? Reading: under `assign` a route is a list of slots (item 1), every slot in exactly one; a brief is
  assigned only to a free slot of its tier or, when none is free, of a stronger one, never a weaker one (item 3); the
  `Assign:` form is unchanged; the `task` and `flag` routes stay for `builder_start = "start"`.

## Residual

- 2026-11-10: a runtime that writes no transcript, or writes helper agents elsewhere, under-counts or shows nothing;
  `Usage: not shown` is printed, never an estimate (due 2027-01-31).
- 2026-11-10: the cost line prices cached tokens at the full price of the tier, so it is an upper bound (due
  2027-01-31).
- 2026-11-10: the kit cannot read which model a slot's scheduled starts run on, so a slot's tier is the owner's word
  in `[models.routes]`; a slot set up on a weaker model than its route says is not seen (due 2027-01-31).

## Applied

2026-11-10 (from `date -u`), brief #798: the items above are applied to
`docs/specs/0045-each-kind-of-work-runs-on-the-model-it-needs.md` (item 2 to rule 2, item 1 to rule 3, item 3 to rule 5,
item 4 to rule 7, items 7 to 9 and item 8's reader sentence to rule 8, item 10 to rule 9, items 11 and 12 to rule 10 as
builds (e) and (f), item 13 to the Tests section and the three residual lines to its Residual section), to
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md` (item 5, rule 6) and to
`docs/specs/0006-doctor.md` (item 6, one `model-routes` row in the table of rule 5), on the owner's `Approve:` lines for
SPEC-0045, SPEC-0034 and SPEC-0006 on #939 at 316d229. SPEC-0045 gains the `## Contexts` section amendment 142 asks of
an amended Approved spec, from the brief's `Contexts:` line. The items are unchanged; item 14 changes nothing, so it
adds no text.
