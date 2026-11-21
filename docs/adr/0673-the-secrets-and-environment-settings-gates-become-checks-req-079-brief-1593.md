# ADR-0673: The secrets and environment-settings gates become checks (REQ-079)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1593, SPEC-0072, ADR-0666, brief #1586, brief #1594, brief #1600, SPEC-0042, plan #661
- Requirements: REQ-079

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `agk.toml`

## Context

On the default branch at f5c1c29 (2026-11-21) `config/playbooks/default.toml` and `config/playbooks/api-service.toml`
hold `secrets` and `environment-settings` as `judgement`, each with the reason "brief #1593 builds it (ADR-0666)". The
runner `scripts/agk/run_gates.py` (ADR-0666) runs each `kind = "check"` gate's step from `scripts/agk/gates/`. gitleaks runs
in `prepush.py` over the branch's commits; no offline step reads the tracked tree, an unignored environment file, an
example settings file or the setting names the code reads.

## Decision

1. Both gates become `kind = "check"`, with the steps `committed-secrets` and `environment-settings`, in `default.toml` and
   `api-service.toml`. Every work type inherits them, the kit's own repository runs both, and both are green on its tree.
2. **`committed-secrets`** (`scripts/agk/gates/committed_secrets.py`; the brief's `secrets.py` would match the data
   guard's `secrets.*` secret-file name, so the step and its module are named apart from the gate id) fails on a tracked
   file that the data guard's secret names cover (`guard.secret_file_name`), on an `.env` or `.env.*` file on disk that `.gitignore` does not ignore, on a tracked file
   with a secret shape (`guard.scan_text`) or a `[guard] patterns` entry, and on an example settings file whose values are
   not empty or `<placeholder>`. A SECRET, TOKEN or JWT shape needs at least one digit: one with only letters and separators
   is an identifier (the ten such hits on the kit's tree on 2026-11-21 are all names in code). This is part of the
   step's design. No ignore entry is added and no pattern list grows (principle 9). gitleaks stays as it is.
3. **`environment-settings`** (`scripts/agk/gates/environment_settings.py`) reads, with `ast`, each literal name that the
   tracked Python code reads through `os.environ[...]`, `os.getenv(...)` or `os.environ.get(...)`. It fails on a name that
   the example settings file does not list, and on a name read with no default in one place and with a default in another.
   The kit's installed folders (`scripts/agk/`, `.claude/`) and the `test_dirs` folders are not the project's code.
4. The example settings file is `.env.example` at the root, the one example name the data guard already allows
   (Q-1593-1). A required setting is one the code reads with no default (Q-1593-2).
5. Each failure is one line `FAIL gates: <gate id>: SPEC-0072 rule 2: ... (path class: <class>)` and never a path, a
   name or a value (principle 8). Environment file names are case-folded on every platform. With `mode = "adopt"` both
   steps hold their findings until brief #1600's baseline, so nothing existing goes red.

## Consequences

A committed key, a tracked or unignored environment file, a value in the example file and a setting the code reads that
the example does not name are red in `governance`, `make governance` and `prepush.py`. No workflow, ruleset or required
check changes. The tracked tree scan adds about ten seconds to the playbook check on the kit's tree.

## Residual

- Non-Python setting readers come with each stack's pack (due 2027-03-31).
- An adopted project's held findings are baselined by brief #1600 (due 2027-01-31).
- The example file name per stack is confirmed or changed by the maintainers' answer to Q-1593-1 (due 2026-12-15).
