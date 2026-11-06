# ADR-0328: Pinned CI test tools from one pin file, with pytest-xdist (REQ-051, brief 698)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0192, ADR-0270, ADR-0305, SPEC-0044, SPEC-0047
- Requirements: REQ-051

Protected classes: `.github/`, `config/`, `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

The governance workflow's `Install tooling` step installed `pytest ruff bandit` unpinned, so a new
release of any of them reached every run silently. `[testing] workers = "auto"` (ADR-0305) already
asks the kit's full suite for parallel workers, but the step never installed pytest-xdist, so the
run on the default branch printed `pytest-xdist is not importable, running in one process` and
took 17 minutes in one process. The owner said yes on 2026-11-06 (plan #661, batch A; tracker
#630 decisions 1 and 4) to pinned CI test tools with one weekly update pull request and to the
parallel workers on the default branch, and allowed this brief to change that one step.

## Decision

1. **One pin file.** `config/ci-tools.txt` holds one exact `<name>==<version>` pin per line, in
   name order, one line per tool, `#` comments allowed. It pins `bandit`, `pytest`,
   `pytest-xdist` (3.8.0, the version #642 measured) and `ruff`, at the versions the last green
   run of the default branch installed.
2. **The step installs that file and nothing else.** `Install tooling` runs
   `python -m pip install -r config/ci-tools.txt`, checks pytest, ruff and bandit by
   `--version` as before and pytest-xdist by `import xdist`, and fails naming the tool that did
   not install. A later tool update changes the pin file only, never the workflow text.
3. **`scripts/agk/ci_tools.py check`** (installed) reads the pin file, refuses a line that is not
   an exact pin, a repeated tool, a tool out of name order, an empty or a missing file, naming the
   path and never a value (principle 8), and prints the pins. It makes no network call. With
   `--upstream`, a person's run, it reads the package index's JSON once per pin and prints which
   pins are behind, the gap in days and `unknown` for an upstream it cannot read, never `0`
   (SPEC-0047 rule 8's reading); `--responses DIR` reads saved responses instead. A person opens
   the update pull request from that output.
4. **Installed verbatim.** The pin file and the script are installed with the governance workflow
   that reads them, so a project's step finds its file.
5. **No new workflow job.** The weekly update is not a job of the drift-audit workflow; that would
   be a second workflow change, outside the owner's yes.

## Consequences

The full suite on the default branch runs in parallel workers, and a tool release reaches CI only
through a reviewed change of one file. A project that changes its pins sees the pin file as
locally edited on upgrade, as with any other verbatim file.

## Residual

- 2026-11-06: Q-698-1, SPEC-0047 rule 8 (`Q-S0047-11`) counts the workflow `uses:` lines and the
  `==` pins of `pyproject.toml`; the brief says the scorecard's `pins_behind` reads these pins.
  `ci_tools.py` prints the numbers, and widening the spec's set to `config/ci-tools.txt` is left
  to the scorecard's build (c) and its spec owners (due 2027-01-31).
- 2026-11-06: the package index's JSON shape is read as `info.version` and
  `releases.<version>[].upload_time_iso_8601` `(verify)`; an answer of another shape is `unknown`.
