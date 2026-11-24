# ADR-0764: An adopted project's whole history is scanned for secrets once, and doctor reports the record

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers
- Related: brief #1835, plan #661, ADR-0008, ADR-0017, ADR-0158, ADR-0306, ADR-0372, ADR-0673, ADR-0680, ADR-0743, SPEC-0002, SPEC-0056
- Requirements: REQ-063

Protected classes: `scripts/agk/`, `kit/`, `skills/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

Every secret scan the kit has reads a range or the tracked tree: prepush and the governance workflow scan the merge
base to the head, the committed-secrets gate reads `git ls-files`, and doctor names only whether gitleaks is installed.
A credential committed and removed before adoption is therefore found by no kit step (AD-07 on #1771), while every
later scan is green. The leaked-secret page and SPEC-0056 rule 10 name the gap; nothing filled it.

## Decision

1. **One scan, offline.** `scripts/agk/history_scan.py` (installed, a `kit/manifest.json` `verbatim` entry) runs one
   fixed argument list, `gitleaks git --no-banner --redact --exit-code 1 --log-opts=--all --report-format json
   --report-path <file> <root>`, with the report in a `tempfile.mkstemp` file outside the repository, removed after.
   It reads only `RuleID` and `File` of each finding and prints one line per rule id and path class with its count,
   then the leaked-secret page; gitleaks' own output is never shown. No fetch is run. That gitleaks 8.30.1 passes
   `--all` to its `git log -p` was checked here: a key on a side branch only is found.
2. **Recorded once.** `--write` writes `config/agk-baseline/history-scan.json` (with `--sidecar`, the sidecar's
   `records/history-scan.json` by `write_private`), keys sorted, after the data guard finds no secret shape in it. A
   `clean` or `findings` record is never rewritten and nothing scans again; an `incomplete` one is replaced by a later
   complete scan; a scan that could not run writes nothing. A symbolic link at the record or its folder is refused.
3. **Adopt stays git-free.** `adopt.py` prints, as its last line after a write, the command that runs the scan
   (`python3 scripts/agk/history_scan.py run --write` installed; in the clean layout the script's name and step 5 of
   `/agk:adopt`, since a clean print names no `scripts/agk` path, brief #1665) and `history scan: not run (dry run)` on a
   dry run; `skills/adopt/SKILL.md` step 5 runs it (SPEC-0002 rules 1 and 7 kept, Q-HB-1).
4. **Never a silent pass.** gitleaks missing or failing, a shallow clone, the 600 s bound (a constant, Q-HB-2) and no
   commit each print one line with the exit code of brief #1835 answer 4.
5. **Doctor reads the record.** In `mode = "adopt"` only, doctor prints one `history-scan` line (never scanned,
   incomplete, findings, clean, unreadable), also under `history_scan` in `--json`; a warn line changes no exit code
   (Q-HB-3), as ADR-0743 decided for the held baseline. `personal.py baseline --approve` runs the scan into the
   sidecar and `personal.py status` prints the same line.
6. **The class stays closed.** `tests/kit/test_history_scan.py` lists every function under `scripts/agk/` that builds
   a gitleaks argument list; a new one fails until the test names it.

## Consequences

A credential committed before adoption is named on day 0 by rule id and path class with the page to follow, and doctor
keeps saying so until a complete scan is recorded. No workflow, check, ruleset or API call changes; the kit posts
nothing. `agk.toml` gains one `[[testing.map]]` entry for the new script.

## Residual

- 2026-11-23: Q-HB-1 (adopt running the scan in process) and Q-HB-3 (doctor failing on findings) stay the owner's call.
