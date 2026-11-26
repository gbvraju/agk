# ADR-0817: The chosen stack turns on the language checks from one standards file

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: brief #1974, SPEC-0072 rules 2 and 6, ADR-0669, ADR-0702, ADR-0739, ADR-0759, ADR-0790, ADR-0259, ADR-0666
- Requirements: REQ-079

## Context

The `[[standards]]` entries of the Python and Node packs live in three playbooks (web-app, api-service and mobile;
ADR-0669, ADR-0739, brief #1638). `check_playbooks.standard` composes entries only from the playbook layers, and
`run_gates.pack_results` runs only the composed entries, so 8 of the 11 shipped work types get no Python checks and 9
no Node checks, whatever stack the project chose. The gap is silent: a data-pipeline project whose Accepted stack
record chose Python has its pack `on`, so the no-pack line of ADR-0702 is not printed, and no `standards` line appears.
The entries cannot move into `config/playbooks/default.toml`, whose test bans the word and any version.

## Decision

This amends ADR-0669's decision that the entries live in the playbooks (Q-19I-2).

1. One stack-keyed file, `config/standards.toml`, holds `[[standards]]` entries in the playbook entry's form with one
   more key, `runtime` (a key of `pins.STACKS`). It holds the `python-pyproject`, `python-pip` and `node` entries as
   `config/playbooks/web-app.toml` holds them. It is a verbatim file of `kit/manifest.json`, read through
   `kit_root.kit_file`: the project's copy in the installed layout, the plugin's in a clean one.
2. `check_playbooks.standard` composes first the file's entries whose `runtime` is the one `pins.chosen` names, then
   the playbook layers as before. A playbook entry for the same stack replaces the file's entry and is held by the
   existing `standards.rules` refusal, so no playbook drops a code of the stack's floor. With no runtime chosen
   nothing of the file is composed. The gate run, doctor's idle-pack line, the standard screen and the layers step all
   read this one list.
3. When a pack module is on and no composed entry is a stack it serves, `run_gates.py` prints `not run standards
   <stack>: no standards entry composed (path class: config/standards.toml)`; the exit code is unchanged, as in
   ADR-0702. `check_playbooks.cmd_check` counts the file's stacks as packed in its warning.
4. `check_playbooks` checks the file's form: the playbook entry's keys plus `runtime`, `runtime` a key of
   `pins.STACKS`, `stack` a stack of `config/stack-signals.toml` that the runtime's pack module serves, and a stack
   once. Each refusal is `SPEC-0072 rule 2: config/standards.toml: <what> (key: standards.<key>)`, never a value; a
   file that is not TOML names the path class; a missing file is no entries.

Every work type follows: mobile, cloud-migration and pilot projects on Python or Node get the checks too (Q-19I-1).
A record that chooses two runtimes still turns on neither pack (Q-19I-3). The playbooks' own entries stay until the
companion build 19I-b moves them out.

Protected path classes changed: `config/` (`config/standards.toml`), `scripts/agk/` (`check_playbooks.py`,
`run_gates.py`), `kit/` (`kit/manifest.json`, `kit/templates/gitattributes`), `agk.toml` (its `[[testing.map]]` entries), `tests/kit/`
(`test_standards_stack.py`) and `tests/kit_dev/` (`test_kit_manifest.py`, the file's row in `SINGLES`; Q-1974-1).

## Consequences

A Python or Node product of any work type gets the pack's lint, format and type checks, and a pack that is on with no
entry is never silent. One more small TOML read per gate run. A new runtime's pack adds its entry to this file once.

## Residual

- Two runtimes in one record (Q-19I-3): a separate brief, 2026-12-31.
- The playbooks' own entries move out in 19I-b, after this merges.
