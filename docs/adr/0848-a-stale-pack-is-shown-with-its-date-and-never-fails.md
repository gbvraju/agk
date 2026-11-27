# ADR-0848: A stale pack is shown with its date and never fails

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2045, 2026-11-27T13:18:15Z)
- Related: ADR-0837, ADR-0838, ADR-0839, ADR-0840, ADR-0544, SPEC-0077, SPEC-0074, REQ-084, brief #2045, brief #2033, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0077 (Approved, ADR-0837) rule 14 build (i) asks for rule 8: a pack whose `reviewed` or `as_of`, or an item whose
access date, is older than `[packs] stale_months` is shown with its date and `(verify)` by `doctor.py` and the weekly
report, a warning that never fails; `packs.py update --check` (build (c), ADR-0840) lists the newer versions with their
change notes and names a withdrawn pack. Build (a) (ADR-0838) already reads `stale_months` (1 to 60, default 12).
`check_domains.stale` (SPEC-0074 rule 12) is the model: calendar months, the day ignored, a `warn` line, never a failure.

## Decision

1. **The lines.** `packs.stale(root, today)` reads the packs of `[packs] use` (`packs.used`) and `stale_months`, and
   gives, in use order, `warn packs: <id> reviewed|as_of <date> is older than [packs] stale_months (verify)` for each
   date over the age, and one `warn packs: <id> <n> item(s) accessed before [packs] stale_months, oldest <date>
   (verify)` line for the access dates of its TOML knowledge entries. It names the pack, the key and the date, never an
   entry's text, a URL or the reviewer, reads files only and raises `Refused` on a refused table or pack.
2. **Where they show.** `doctor.pack_stale_lines` adds them beside the floor lines and on a sidecar beside the pinned
   lines, and gives nothing on a refusal (the `packs-settings` row or the `playbooks` step names it). `metrics.report`
   (with `--today`) and `personal.py report` add `packs.report_lines`: the lines, `packs: none stale`, or
   `packs: stale unknown (setting: ...)`, never 0. No exit code changes; the `playbooks` step does not print them
   (`Q-PI-3`), so governance output is unchanged.
3. **Change notes (`Q-PI-1`).** On the person's yes, each newer exact tag is one line
   `<id> <locked> -> <tag>: <note>`: the first line of the annotated tag's message, fetched with that tag alone into a
   scratch repository, control characters dropped, cut to 120 characters; `(no change notes)` for a lightweight tag or
   a folder source, `(notes withheld: rule 6)` when the data guard flags the message (`Q-PI-4`).
4. **withdrawn (`Q-PI-2`).** When the source answers and the locked tag is not among its tags:
   `<id> <locked>: withdrawn (verify)`. A source that cannot be read is `<id>: cannot check (source: git|folder)`, exit
   4, never `withdrawn`. A withdrawn pack keeps working: `verify` and `packs.files` read only the lock and the
   project's copy.
5. **Wiring.** The `[testing]` map of `packs.py`, `doctor.py`, `metrics.py` and `personal.py` names
   `tests/kit/test_packs_stale.py`.

## Consequences

An outdated pack is seen with its date before it misleads a session; freshness is shown, never enforced: a stale pack
is never refused or lowered a tier, and `update --check` writes no file. No workflow, ruleset, required check, label,
`agk.mk` or `governance_map.CHECKS` changes. `[domain] stale_months` is never read for packs.

## Residual

Build (d)'s instruction scan (#2034) withholds an instruction-shaped note by its own wiring once it merges.
