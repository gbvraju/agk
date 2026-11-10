# ADR-0436: A builder installs the pinned test tools before the full run

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: brief #1021, plan #661, Q-1021-1, SPEC-0044 rules 4 and 5, ADR-0305 (brief #631), ADR-0422 (brief #980), ADR-0328 (brief #698)
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `agk.toml`, `tests/kit/`

## Context

On 2026-11-10 #994 and #1011 each ended the full `prepush.py` tests step at `proof_timeout = 1800` twice in a row on a
2-CPU cloud session. A fresh cloud session has no pytest-xdist, so `prepush.pytest_workers` leaves every pytest run in
one process; only the governance workflow installs `config/ci-tools.txt`, which pins it. The builder and the conductor
measured on main 0bbbab4 that the full run never gets workers here even with xdist: this repository's `project_tests`
starts with an install step and a `;`, which `pytest_interpreter` refuses, and `parallel_command` is not set
(`tests: the command is not a simple pytest command and parallel_command is not set, running in one process`). The
owner ruled Q-1021-1 (b) as the conductor recommended on #661: build the install, allow its `impact.py` key, and give
the full run its parallel command through `[testing] parallel_command`.

## Decision

1. A new optional `[testing] tools_file`, a file path inside the repository (`impact.py` `KEYS`; a bad value is
   refused naming `testing.tools_file`), unset by default.
2. When it is set, `[testing] workers` is above 1 and the run's interpreter cannot import xdist, `prepush.xdist_ready`
   runs `<python> -m pip install -q -r <tools_file>` once per interpreter and file, again with
   `--break-system-packages` only when pip refuses with `externally-managed-environment`, then checks again. A failed
   install prints one line, `tests: the install of the test tools failed, running in one process (setting:
   testing.tools_file)`, and the run is the command of today. The full run and the selected runs share the one rule.
3. A full run that takes `parallel_command` gets the same install before it when the setting is set and the command's
   last part (`prepush.last_pytest`) is a pytest command; when xdist is still missing it runs the command of today
   after the line. A non-pytest `parallel_command` never reaches the install.
4. This repository sets `tools_file = "config/ci-tools.txt"` and a `parallel_command` that is its `project_tests`
   with `-n {workers}` at its end.

## Consequences

Without the key nothing changes: the kit installs nothing (SPEC-0044 rule 4 by default). With it, a session's first
pre-push run may install the pinned tools (seconds, from the package index the session already reaches); the checks
of CI never install, since CI's interpreter already imports xdist. `project_tests.py` and the `agk-test` chooser call
`full_command` too, so they get the same rule; in CI this repository's full `project_tests` run now uses workers, as
`make agk-test` already did. The chooser in `kit/agk-kit.mk` filters only `NO_PARALLEL` and `NO_XDIST` from a full
plan's lines, so a failed install may print its line twice there (the brief allows no change to that file).

## Residual

- 2026-11-10: the after-measure is the brief's: the next builder run of #994 or #1011 finishes `prepush.py` inside
  1800 s.
