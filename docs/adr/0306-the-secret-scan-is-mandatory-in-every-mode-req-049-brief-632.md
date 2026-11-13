# ADR-0306: The secret scan is mandatory in every mode: a missing gitleaks fails the run, never skips it (REQ-049, brief 632)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0186, ADR-0158, ADR-0208, ADR-0233, ADR-0280
- Requirements: REQ-049

Protected classes: `scripts/agk/`, `tests/kit/`, `config/`

## Context

Brief #632, item 4 of tracker #630 (the owner's yes of 2026-11-06 to the delivery strategy review): "The secret scan
never passes by being skipped: in every mode, a run that needs it fails, naming the missing tool, when gitleaks is not
installed." Until now `prepush.py` printed `gitleaks is not installed; secret scan: not run` and ended `prepush: passed;
not run: secret-scan` when gitleaks was not on `PATH` (ADR-0186, the reading of Q-326-3). In local or solo mode, where
no CI scan follows, a secret could then be pushed with every local gate green. This changes that one reading of
ADR-0186; every other decision of ADR-0186 stands.

## Decision

1. **prepush.** The `secret-scan` step of `scripts/agk/prepush.py` is a `FAIL`, never `skipped` or `not run`, when
   `gitleaks` is not on `PATH`. Its one line names the tool and how to install it: `gitleaks is not installed, so the
   secret scan cannot run and the run stops (tool: gitleaks); install gitleaks <pin> (the version the governance
   workflow pins) from the gitleaks releases on GitHub and put it on PATH`. The run stops there, as at any failure,
   and exits 1. The record of `--record` holds the step as `FAIL` with `not_run` false and the result `failed`.
2. **The pin.** `<pin>` is `GITLEAKS_PIN` in `scripts/agk/common.py`, today `8.30.1`, the version that
   `.github/workflows/governance.yml` pins with its SHA-256 (ADR-0158). A test keeps the two equal, so a new gitleaks is
   still taken by one change of the workflow's version and digest, with the constant beside it.
3. **`--quick`.** `--quick` keeps its meaning: it skips the tests step only. It never skipped the scan and does not now;
   a test says so both ways (missing: FAIL; present: the scan runs).
4. **The other commands.** No other kit command runs the scan: `make governance` (`agk.mk`) and `proof.py` do not, and
   the governance workflow downloads the pinned binary and fails when it cannot (ADR-0158, ADR-0171). `evidence.py
   check` repeats a sample of a record and never runs a scan in place of one: a record whose scan step did not run
   already differs (its argv is empty), and after this change such a record is also `failed`; a gitleaks missing on the
   checking machine keeps the unit `not repeatable`, listed and not sampled, because the record itself carries the scan.
   The local-mode guide and the reference guide say what prepush now does. A test keeps any kit script from printing
   `secret scan: not run`.
5. **doctor.** `doctor.py` prints one information line after its checks, before the `tidy:` line and the summary,
   and the same text as `secret_scan` in `--json`: `secret scan: gitleaks <version> is installed`, with `; the
   governance workflow pins <pin>` when the version that `gitleaks version` prints is another, or `secret scan: gitleaks is not installed; prepush fails until it is
   (tool: gitleaks); install gitleaks <pin> ...`. It changes no exit code and adds no check id, like the `tidy:` line.
   The doctor runs `gitleaks version` with a fixed argument list and no shell; it installs and downloads nothing.
6. **Unchanged.** The data guard (SPEC-0042) is unchanged; no scanner ignore entry is added; the governance workflow's
   scan is unchanged.

## Consequences

A machine without gitleaks can no longer pass `prepush.py`; the session or person installs the pinned binary first.
Every builder and conductor machine needs gitleaks on `PATH`. A record made without the scan can no longer read as a
pass. The personal-mode floor of SPEC-0041 rule 18 already fails without gitleaks, so both modes now agree; this answers
`Q-562-2` for `prepush.py` in team mode in the direction the owner chose.

## Residual

- 2026-11-06: session rule 31 (`config/session-rules.md`) now says a missing gitleaks fails the run; the conductor ruled
  `Q-632-1` that a build may correct a rule sentence the build makes false. SPEC-0006 rule 11 gains the `secret_scan`
  key by `docs/runs/proposed-spec-amendments-127.md` (`Q-632-3`), which needs the owner's `Approve: SPEC-0006`.
- 2026-11-06: the doctor line is information only; whether a missing gitleaks should be a failing doctor check is left
  open (`Q-632-2`).
