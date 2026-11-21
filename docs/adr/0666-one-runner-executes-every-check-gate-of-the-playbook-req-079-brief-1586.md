# ADR-0666: One runner executes every check gate of the playbook (REQ-079)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0048, SPEC-0038, SPEC-0007, brief #1586, plan #661, ADR-0665
- Requirements: REQ-079

Protected classes this pull request changes: `config/` (`config/playbooks/`), `scripts/agk/` (the new `run_gates.py`
and `gates/`, and `check_playbooks.py`), `tests/kit/` (the new `test_run_gates.py` and the playbook tests whose gate
kinds change), `tests/kit_dev/` (`test_reference_commands.py`, `test_stack_playbook.py`), `kit/` (`kit/manifest.json`)
and `agk.toml` (two `[[testing.map]]` entries). `agk.mk` is not changed (decision 2). `kit/hashes.json` is not edited:
`kit_hashes.py` reports it current.

## Context

SPEC-0072 (Approved, REQ-079) rule 12 build (b) builds rule 3: a governance runner runs each check gate's `step` from a
registry under `scripts/agk/gates/`, refuses a step with no implementation naming the gate id, and gives each of the
25 check steps of rule 1 an implementation or a restatement as `judgement` with a reason. On the default branch at
28ddd04e (2026-11-20) the ten playbooks hold 27 check gates: rule 1's 25 and the two of `default.toml` that ADR-0665
added (`secrets`, `environment-settings`). No script runs any of them. The `governance` workflow runs each command of
`agk.mk` `agk-governance` as its own step, and `tests/kit/test_workflow.py` (SPEC-0007 rule 13) holds the two lists
equal; a session never changes a workflow.

## Decision

1. `scripts/agk/run_gates.py` composes the playbook of `[delivery] work_type`, or `default.toml` alone when none is
   declared, with `check_playbooks.composed`, and runs each check gate's step from `scripts/agk/gates/<step>.py` (the
   step's `-` as `_`). Each module holds `RULE` and `check(root, playbook)`, reads only the project's files, offline,
   and returns the failing path classes. The runner prints `ok <gate id>` or `FAIL gates: <gate id>: <rule> (path
   class: <class>)`, never a value (`Q-2` of the brief: one line per gate), and a step with no module is refused
   naming the gate id and the path class `scripts/agk/gates/`.
2. `check_playbooks.py` runs the runner once the playbooks pass, in the same process, and returns its exit code; with
   no check gate it adds no line. So the steps run in the existing `check_playbooks` step of the `governance` job, in
   `make governance` and in `prepush.py`'s governance step, with no workflow, `agk.mk`, ruleset or `required_checks`
   change (`Q-1586-3`: rule 3 names a call from `agk.mk`, which would need a workflow step).
3. Two steps are implemented, the two whose text names only the playbook's own split: `cut-over-order`
   (cloud-migration: inventory, then wave plan, then cut-over, each depending on the one before) and `rollback-order`
   (data-pipeline: a rollback brief before every cut-over brief, which depends on it). Each fails naming
   `config/playbooks/`.
4. The other 28 are restated as `judgement` with a reason of 20 characters or more ending `(ADR-0666)`, and lose their
   `step`: `contract-tests` and `mock-parity` (web-app) and `contract-tests` (api-service) name brief #1597; `secrets`
   and `environment-settings` (`default.toml`, and api-service's own two) name brief #1593, which changes ADR-0665 decision 5 and SPEC-0072 rule 2's base until that brief
   builds them; the 21 whose files have no path named by any playbook or spec (data-pipeline 2, mcp-server 3, mobile 2,
   multi-agent 2, pilot 6, rag-app 3, voice-agent 3) say so, and `pilot-report` says a step would be red until the
   pilot's end. A later build that adds a step restates its gate as `check` again.
5. No step of this build reads a project's existing files, so none is held in `mode = "adopt"` (`Q-1` of the brief);
   the hold lands with the first step that does (brief #1593), before build (g)'s baseline.

## Consequences

A project's governance runs every check gate of its playbook, and a gate whose step has no module is red naming the
gate id. The kit's own repository, with no work type, runs `default.toml`'s part, now no check, and its output is
unchanged. A project's own playbook that drops the cut-over or rollback order is red. No workflow, ruleset, required
check or `agk.mk` changes.

## Residual

- 2026-11-20: `Q-1586-3` (the runner from `check_playbooks.py`, not an `agk.mk` line) and decision 4's restatement of
  `secrets` and `environment-settings`, on the pull request of brief #1586.
- 2026-11-20: `Q-1586-5` (conductor's correction on the pull request of brief #1586): the three api-service check gates
  that #1610 added (`contract-tests`, `secrets`, `environment-settings`) are restated as decision 4 says, so this ADR
  supersedes ADR-0682's residual (a check gate "without its step on disk") for those three gates; the count is 28.
