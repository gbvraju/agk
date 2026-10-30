# ADR-0213: one kit command enters and leaves local mode, and lists the merges that need a catch-up run (REQ-039, brief 371)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0182, ADR-0184, ADR-0191
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude/`

## Context

Brief #371 (priority raised by the conductor: the pilot runs in local mode now), from #287 answer 8. The local-mode guide (#322,
ADR-0182) and the heavy-step lock (#337, ADR-0191) made local mode safe, but entering and leaving it is one `gh` command per
workflow typed by hand, and nothing checks that the merges made on local evidence are run in CI afterwards. The brief names no
`Measured:` line. The tests were written first (`tests/kit/test_local_mode.py`: every case fails without
`scripts/agk/local_mode.py`, 24 failed, at the first checkpoint of the pull request).

## Decision

1. **`scripts/agk/local_mode.py enter|leave [--write] [--since DATE] [--repo OWNER/REPO] [--api-dir DIR]` (answer 1).**
   Standard library only. It reads the repository's workflows with `gh api` (GET, paged) and lists, for `enter`, every workflow
   in the state `active` and, for `leave`, every workflow in the state `disabled_manually`, the kit's and the project's alike,
   each with the one call `gh api --method PUT repos/<owner>/<repo>/actions/workflows/<id>/disable` (or `enable`). It is a dry
   run by default and changes nothing. `--write` makes the calls one by one and prints one line per workflow, `disabled <file>
   (id <n>)` or `refused <file> (id <n>): HTTP <status>`; a refused call is reported with the call to run by hand and the rest are
   still made (exit 3). `gh` holds the credential and the script holds none; the person runs `--write` with a token that may
   change workflows (Actions write is enough). A session's own `gh` may hold such a token, so wording alone does not hold
   session rule 30 (finding 1 of the verdict on 7c0028a): `--write` is refused with exit 1 while the environment setting
   `CLAUDECODE`, which an agent session sets in its shell `(verify)`, is set and not empty, and the message names the setting,
   never its value; the dry run still runs in a session. `.claude/settings.json` denies `local_mode.py` with `--write` in the
   spellings a session types (`python3 ...`, `python ...`, and any command naming both). A workflow GitHub disabled for
   inactivity (or on a fork) was not disabled for local mode and is left as it is, named in one line (Q-371-1). Recorded responses (`--api-dir`, one `<name>.json`
   per read or `<name>.status` for a refused one; each write is appended to `calls.log` and answered by `put-<id>-<verb>.status`
   when present) let the tests run with no network.
2. **The start and the merges on local evidence (answer 2).** `leave` takes the start of local mode from `--since
   YYYY-MM-DD` (midnight UTC) when given, else from the one open record issue (an issue, not a pull request, whose title starts
   `Local mode since`; the oldest when several are open): midnight UTC of the day its title names, or of the day it was opened.
   Midnight, because the guide disables the workflows before it opens the issue. A workflow's `updated_at` never sets the start
   (finding 3 of the verdict on 7c0028a: a workflow a person turned off a year before would move the start back a year).
   `leave` enables only a workflow disabled by hand whose `updated_at` is at or after the start, the time GitHub records for its
   last change `(verify)`; an older one, or one without the time, is named `left as is: <file> (id <n>, disabled before local
   mode)`. Without a start, `leave` enables nothing, names each workflow as left because the start is unknown, and says to give
   `--since` (Q-371-2). It lists every pull request merged into the default branch since then, oldest first, as `#<n> <merged
   at> <sha7> <title>`, read from the closed pull requests sorted by update (newest first) until a page is older than the start.
   A list that cannot be read is `unknown` with its reason class (`refused`, `missing`, `unreadable`), never 0, and the command
   exits 4 when the start, the merges or the catch-up are unknown (finding 4), after 3 (a refused call or a red catch-up). With
   `--write` the list is read before the workflows are enabled.
3. **The catch-up run (answer 2).** For each check of `required_checks` (agk.toml), `leave` reads the latest check run of that
   name on the head commit of the default branch (`latest_runs` of the router) that started at or after the start of local mode:
   a run before it, such as a run refused by a billing block before the workflows were disabled, is no catch-up (Q-371-3). It
   prints `catch-up <check>: <conclusion> on <sha7>`, `running` or `not run yet`; one line `catch-up: not run yet` when no
   required check ran, `catch-up: green` when every one succeeded (or was neutral or skipped), and `catch-up: red on <sha7>
   (<checks>): file a priority-0 brief ...` (exit 3) when one failed. A green run on the head covers every merge before it,
   since the head holds them all. A head commit or check runs that cannot be read print `catch-up: unknown (...)` (exit 4), and
   so does an unknown start.
4. **The guide (answer 3).** `docs/guides/local-mode.md` runs `local_mode.py enter` and `leave`, a dry run first and `--write`
   to make the calls, in its enter and leave sections, and keeps the one-line `gh workflow` form for a person without the kit.
   `tests/kit_dev/test_local_mode_guide.py` checks both forms and the catch-up lines. `docs/guides/reference.md` (outside
   `Touches:`) names the command under Local mode, which `tests/kit_dev/test_reference_commands.py` requires of every installed
   script, and `kit/manifest.json` (outside `Touches:`) lists `scripts/agk/local_mode.py` so a project has it, as ADR-0191 did
   for `lock.py` (Q-371-4).
5. **Tests (answer 4).** `tests/kit/test_local_mode.py`, saved responses and no network: the dry run writes nothing; `--write`
   makes one call per workflow; a refused call (403) is reported and the rest still made; `leave` with merges and no catch-up,
   with a green and with a red one; a run before local mode, a run in progress and a check with no run; `--since`; unreadable
   pull requests and check runs; the setting `required_checks`; usage. From the verdict on 7c0028a: `--write` refused inside a
   session for both verbs, the dry run allowed, the deny entries; a workflow disabled in 2025 left as it is and not setting the
   start; the start from the record issue's title or its opening day; no start without either; exit 4 on an unreadable head
   commit, pull request list or issue list. The tests build the scripts' path from their own file, never from `conftest`, which
   resolves to `tests/kit_dev/conftest.py` when both folders are collected together (finding 2).
6. **Flow mode.** One fragment `changelog.d/local-mode-command.md`; no version bump; `kit/hashes.json` not edited (session rule
   14).

## Consequences

- A person enters and leaves local mode with two commands, sees each call before it is made, and learns on leaving which merges
  rest on local evidence and whether the catch-up run on the default branch is green.
- The start of local mode is read from the open record issue, so a person who never opened it gives `--since`; a workflow
  turned off for good earlier on the same day as local mode began would be enabled again.

## Residual

- 2026-10-30: Q-371-1 to Q-371-4 asked on the pull request; the readings above are the most conservative ones.
- 2026-10-30: Q-371-4 accepted in the verdict on 7c0028a (comment 6530994041).
- 2026-10-30: the verdict on 7c0028a, findings 1 to 4: `--write` refused inside a session and denied in `.claude/settings.json`;
  the tests' script path no longer imports `conftest`; the start comes from `--since` or the record issue, and only workflows
  disabled since then are enabled; an unknown start, merge list or catch-up exits 4 (decisions 1 to 3, 5). The optional note on
  "admin" is taken: the texts say a token that may change workflows; the one with no `required_checks` needs nothing, since the
  setting is refused when empty.
