# ADR-0506: One command makes and fills the plan's Project board

- Status: Accepted
- Date: 2026-11-13
- Deciders: maintainers
- Related: SPEC-0043 rule 25, ADR-0459, brief #1190, plan #661
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `skills/`, `agk.toml`

## Context

`plan_intake.py publish` (SPEC-0043 rule 25, ADR-0459) prints one `gh api` command per milestone and per brief issue
and runs none. Nothing made or filled a GitHub Project board: the release plan and guide of 2026-11-13 told the owner
to create the board in GitHub and add each issue with one `gh project item-add` at a time. Each published brief already
carries `Size:`, `Expected: <low>-<high> hours` and `Milestone:` lines, and its issue has its GitHub milestone. GitHub
Projects are reachable only through GraphQL, which cloud sessions refuse, so the board is made with the owner's own `gh`.

## Decision

1. A plugin skill `/agk:board` runs the kit-only `scripts/agk/board.py [--title TEXT] [--owner LOGIN] [--project N]
   [--yes]` (the plugin's copy, as `/agk:workflow-apply` does) from the repository root, with `gh project` subcommands
   and one REST read of the open `agk-brief` issues; it writes no GraphQL of its own. Without `--yes` it prints each step
   it would take and calls nothing that writes.
2. With `--yes` and no board named (`--project N`, else `[plan] board` of `agk.toml`), it creates a Project titled
   `<repository> plan` (or `--title`) under the repository's owner (or `--owner`) and prints
   `add to agk.toml under [plan], and commit: board = <n>`; it never edits `agk.toml`. `[plan] board` is a positive whole
   number, read by `common.plan_settings` like the table's other keys.
3. Every `--yes` run links the Project to the repository, adds the fields `Size` (single select S, M, L) and
   `Expected hours` (number) when the board lacks them, and adds each open `agk-brief` issue not yet on the board,
   setting `Size` and `Expected hours` (the high end of the range) from the issue's own lines; a brief without one of
   the lines gets a `note:` and that field stays empty. An item already on the board is never edited and nothing is
   ever removed. The built-in Milestone and Status fields are GitHub's. It prints `added #<n>`, `set #<n> Size M`,
   `set #<n> Expected hours 8` and ends `ok board: <a> added, <b> already there`.
4. A missing `project` scope prints `gh auth refresh -s project` and exits 2. A refusal of GraphQL (a cloud session)
   prints the one line `board: needs a machine with your own gh (cloud sessions cannot reach GitHub Projects)` and exits
   0. Any other `gh` failure prints `failed: <the command>` and exits 1. Each step is checked before it is taken (a field
   or an item already there is skipped), so a re-run with the printed board number finishes what a failed run left.
5. Personal mode (a `[personal]` table) has no GitHub issues: the command prints that it needs the GitHub forge, calls
   nothing and exits 0.
6. A conductor on the owner's machine (local or autopilot mode, the owner's `gh`) may run `board.py --yes` after each
   `publish` round and after a new brief is filed, since it only adds; in a cloud session it gets the needs-a-machine
   line and exit 0, so its run is not red.
7. `publish`'s final `ok publish:` line, once nothing is withheld, ends `; next: /agk:board --yes`;
   `docs/guides/planning.md` step 9 and `docs/guides/reference.md` name the command.

## Consequences

One `/agk:board --yes` after the publish round makes the board with every brief, its size and its hours, and each later
run adds only the new briefs. The board is not a record: decisions and sizes stay in the briefs, and a person may move
or edit any item without the command touching it again.

## Residual

- 2026-11-13: `gh project link` is run on every `--yes` run on the reading that linking an already linked repository is
  not an error (verify); if it is, the person runs the command once more with the printed number, and a later build
  reads the board's links first (due 2027-01-31).
- 2026-11-13: the GraphQL refusal is recognised by its message (`GraphQL is not available`, `unknown owner type`), as
  measured in a cloud session on 2026-11-13; a runtime that words it otherwise exits 1 instead of 0 (due 2027-01-31).
