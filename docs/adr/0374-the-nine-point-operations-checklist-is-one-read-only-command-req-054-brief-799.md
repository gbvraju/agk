# ADR-0374: The nine-point operations checklist is one read-only command

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0311, ADR-0327
- Requirements: REQ-054

## Context

The owner asks for the nine operations points by a word, `AGK-NINE-CHECKLIST` (brief #799). Reading them by hand from `agk.toml`, the
scripts, the merger runs and the comments took 30 minutes and three of the nine came out wrong. REQ-054 already makes a scorecard
of numbers with lines; this is a second, shorter face of the same records, for a person who wants the state of the operation in
nine lines. This decision is new (a new installed command, a new settings table and a new sentence of the conductor's role), so
this build has its own ADR. It changes the protected path classes `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml` and `.claude/`.

## Decision

1. `scripts/agk/checklist.py [--root DIR] [--days N] [--saved FILE]` prints nine lines `<n>. <name>: <yes|partly|no|unknown> <measure>`
   and exits 0. It imports only the standard library and `common.py`, writes nothing, and makes no network call. `unknown` is never
   shown as 0 and always says why.
2. In GitHub mode it reads one saved file, by default `agk-checklist.json` in the checkout's git directory (not tracked, so no
   ignore entry is added). `python3 scripts/agk/metrics.py --save-checklist [--to FILE] [--days N]` writes that file with GET
   requests only: the document of `facts.py`, the repository's comments and Actions runs of the window, the briefs, the newest
   weekly `pr tests:` line and whether a local-mode record issue is open. The saved time ends the window, so a late read never
   misdates a record. A part that could not be read is saved as null and its points print `unknown`.
3. The points are the owner's nine, in his order, each from a record AGK keeps: capacity from the takes and the conductor's
   `Builders started` and `Refused` figures; tests from the weekly `pr tests:` line; auto-merge from the setting, the failed
   `merger` runs and cleared heads unmerged over 20 minutes; conflicts from `docs/runs/holds.jsonl`; assignment from free slots
   while a brief with no open dependency stood untaken; cost from `Report:` usage figures. A take ends at its first `Report:`,
   its `released:`, the brief's close or `stall_hours`, whichever is first.
4. The thresholds are one optional table `[checklist]` of `agk.toml`, with kit defaults marked (verify) until measured:
   `capacity_use`, `conductor_share`, `selected_share` and `usage_share` (shares from 0 to 1), `parallel_peak`, `merge_late`,
   `merge_failed_runs`, `false_hold_rate` and `idle_minutes`. A point is `yes` only past its threshold; an unknown key or a
   wrong value is refused naming the setting, never the value. A change of a threshold needs an ADR (`agk.toml` is protected).
5. Personal mode prints `unknown` with the reason on each point but the file-based one: a sidecar keeps no comment or run
   records. Local mode prints `unknown` for the points that need Actions runs and measures the rest.
6. The conductor's hourly report ends with the nine lines, and the owner's word in chat means: run the command and give its lines.

## Consequences

A person gets the nine points in one command, the same in every project and mode. Saving costs the GET requests of `facts.py` and
three listings. A weekly `pr tests:` line means point 3 shows the last full week rather than `--days`.

## Residual

- 2026-12-09: Point 6 (models) always prints `unknown`: no start records the runtime model it ran on (`Q-799-2`). Recording it is a
  separate brief.
- 2026-12-09: The conductor's guard allows neither `metrics.py --save-checklist` nor `checklist.py`, and `.claude/hooks/` is not in the
  brief's `Touches:` (`Q-799-1`); the role file says so.
- 2026-12-09: Whether the full suite ran in workers is read from the `[testing] workers` setting, not from a run's log (point 4).
- 2026-12-09: The thresholds are the kit's first guesses (verify) until four weeks of readings exist.
