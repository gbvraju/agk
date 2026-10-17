# ADR-0027: this repository's project tests install pytest when it is missing

- Status: Accepted
- Date: 2026-10-17
- Deciders: maintainers
- Related: ADR-0026
- Requirements: REQ-016

Protected classes: `agk.toml`

## Context

The `proof` job (SPEC-0010 rule 16, ADR-0026) ran for the first time on a real pull request, #60 at head `ac4b563`. It ended
`outcome: not-proven`; the job log shows why: in both runs, `/opt/hostedtoolcache/Python/3.12.15/x64/bin/python3: No module named
pytest`, so the base was red and the head was red, `reason: red-on-head`. The job installs no toolchain by design (rule 16: "the kit
installs no language toolchain, and `project_tests` may install what it needs"), and the `governance` job installs `pytest` and `ruff`
in its own step, which the `proof` job does not have. The same run on the pull request's earlier head (`29c1595`) shows the same
reading. Locally the check read `proven` for #60 (`docs/runs/proof-checks-live-1.md` section 5) because pytest was installed.

Left as it is, every pull request of this repository would read `not-proven (red-on-head)` in CI: a false flag for criterion c.

## Decision

1. **`project_tests` in this repository's `agk.toml` installs pytest when it is missing**, then runs the kit tests exactly as before:
   `python3 -m pytest --version >/dev/null 2>&1 || python3 -m pip install -q pytest; AGK_KIT_TESTS=1 python3 -m pytest -c
   tests/kit/pytest.ini tests/kit tests/kit_dev -q`. Where pytest is present (the `governance` job, a developer machine) nothing is
   installed and nothing changes. No kit test uses `ruff`, so only pytest is needed.
2. **The `proof` workflow is not changed**: it is a verbatim kit file, and an install step in it would be wrong for projects in other
   languages. The command that needs a tool installs it, as rule 16 says.
3. **No kit file changes**, so the kit version is not bumped; `agk.toml` is this repository's own configuration, not a manifest path.

## Consequences

- The `proof` job of the next pull request here runs the kit tests twice for real (about ten minutes each, inside `proof_timeout`
  900) and reads `proven`, `not-proven (green-on-base)` or `unknown`, not a constant `red-on-head`.
- The seeded and the real pull request of SPEC-0010 rule 20 can then be recorded as planned (`docs/runs/proof-checks-live-2.md`).

## Residual

- 2026-10-17: the `proof` job needs network access to `pip` the first time on a runner without pytest; an air-gapped runner would read
  `red-on-head` again (due 2026-12-31).
- 2026-10-17: the proof job has only the runner's preinstalled tools; a project whose tests need more must set it up inside
  `project_tests`; the playbook and the existing-codebase guide say so, with one example per language the kit has proven (Python, Go)
  (due 2026-11-07, the SPEC-0013 build).
