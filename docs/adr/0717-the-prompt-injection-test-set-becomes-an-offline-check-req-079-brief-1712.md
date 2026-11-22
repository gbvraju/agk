# ADR-0717: The prompt-injection test set becomes an offline check (REQ-079)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1712, SPEC-0072, ADR-0666, ADR-0670, plan #661
- Requirements: REQ-079

Protected classes: `scripts/agk/`, `config/`, `kit/`, `agk.toml`, `tests/kit/`

## Context

On the default branch at f1d2f05 (2026-11-22) `config/playbooks/mcp-server.toml` holds the gate `prompt-injection-set` as
`kind = "judgement"`, with the reason that no path is named for the set, so a reviewer reads it (ADR-0666). An MCP
server's defence against prompt injection (OWASP LLM01) therefore rests on a reviewer remembering it. This replaces that
reason for this one gate; the two other mcp-server gates stay judgement.

## Decision

1. The set is the folder `injection/` directly under a `test_dirs` entry (`tests/injection/` by default), holding one or
   more test files in any form of the stack.
2. The gate becomes `kind = "check"` with `step = "injection-set"` and no `reason`. The step is
   `scripts/agk/gates/injection_set.py`, run by `run_gates.py` (ADR-0666), offline, files only, listed in
   `kit/manifest.json`.
3. It fails, naming the rule and the path class (`<first test_dirs entry>/injection/; setting: test_dirs` or
   `setting: testing.map`) and never a file, when no entry holds the folder (a file of that name is not a folder), when
   the folders hold no file but a README, and when no `[testing] map` entry of `agk.toml` has a `tests` glob that
   matches a file of the set. A generated map file does not count, for either `map_source` (Q-1712-2).
4. It is not run (`no foundation yet`) while `docs/architecture.md` is absent, as the tests floor (ADR-0670).
5. A `test_dirs` value that is not a non-empty list of folders inside the repository is refused naming `test_dirs`; a
   malformed `[testing]` setting is refused naming it, as `impact.testing_table` does. It writes no baseline (no
   `counts`), so `mode` changes nothing.

## Consequences

An mcp-server product after its foundation is red in `governance`, `make governance`, `prepush.py` and the personal floor
until it holds the set and one map entry names it; an existing one turns red on upgrade (Q-1712-1), and the changelog
says what to add. Every other work type, and the kit's own output, is unchanged. No workflow, ruleset or required check
changes.

## Residual

- The tool schema and permission scope gates stay judgement until a path is named for each (ADR-0666).
