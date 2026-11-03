# ADR-0259: The playbook format and its check (REQ-045, brief 513)

- Status: Proposed
- Date: 2026-11-03
- Deciders: maintainers
- Related: ADR-0251, ADR-0260, SPEC-0038
- Requirements: REQ-045

Protected classes: `scripts/agk/`, `agk.mk`, `.github/`, `kit/`, `tests/kit/`

## Context

SPEC-0038 rule 12 build (a) turns a delivery playbook into checked data: a playbook under
`config/playbooks/` is read and checked in governance with no network, so a missing or unknown
section, an unknown work type, an unsupported speed claim or any attempt to lower a gate fails,
naming the rule and the file and never a value (rules 1 to 4, REQ-045 AC1 and AC4). Brief #513
gives the build; ADR-0251 sets the direction and lists the classes the builds of SPEC-0038 change.
This ADR number was reserved for brief #513 by the conductor (the field note on #513).

Two points of the brief disagreed with the repository, and the conductor ruled on both on pull
request #515. `scripts/agk/playbook.py` already exists as the kit-only `/agk:start` helper
(SPEC-0013) and reads `kit/templates/playbook/`, which a project does not have (Q-513-1). And
`tests/kit/test_workflow.py` requires the `check_*` steps of `.github/workflows/governance.yml` to
equal the commands of `agk-governance` in order, while ADR-0251 decision 3 says no build of
SPEC-0038 changes `.github/` (Q-513-2).

## Decision

1. `scripts/agk/playbook_format.py` (new, installed, in `verbatim` of `kit/manifest.json`) holds
   `FORMAT = 1`, `WORK_TYPES`, the eight work types of SPEC-0038 rule 1 as it stands on main
   (with `pilot`, ADR-0260) in one constant, and `problems(path, root)`, which returns one line per
   problem of a playbook, each naming the rule and the file and never a value. It reads the file
   with `tomllib` and, for a `measured` claim, only that its record is a file under `docs/runs/`.
   Later builds of SPEC-0038 (b and f) read a playbook through this module. The kit-only
   `scripts/agk/playbook.py` is not changed and stays kit-only (ruling on Q-513-1, option a).
2. Rule 4 is implemented as worded: a key outside the format; `[testing] profile = "fast"` or a
   `pr_tests` key; a governance setting of `agk.toml` named as a setting in any value (a backticked
   token, or the `<setting> =` or `<setting>:` form) or a principle, a session rule or a
   `CLAUDE.md` item named by its number (Q-513-3, conservative reading); and a gate whose text
   names signing, an apply of infrastructure, a release or a secret with `owner_only = false`.
   The same word in plain English passes.
3. `scripts/agk/check_playbooks.py` (new, installed) checks every `config/playbooks/*.toml` and
   prints `ok playbooks (<n> playbooks)`, `ok playbooks (none)`, or one `FAIL playbooks:` line per
   problem with exit 1. It is one line of `agk-governance` in `agk.mk`, after `check_design.py`,
   and one matching `check_playbooks` step of `.github/workflows/governance.yml` after
   `check_design`, so that `agk.mk` and the workflow stay equal; `tests/kit/test_workflow.py`
   counts 14 steps. This narrows ADR-0251 decision 3 for this one governance step only; nothing
   else under `.github/` changes (ruling on Q-513-2).
4. No playbook file is added (web-app is build c). `kit/hashes.json` is not edited.

## Consequences

Every project that installs the kit runs one more governance step, which passes with
`ok playbooks (none)` until a playbook is shipped. A shipped playbook that could lower a gate
cannot pass governance. No setting, flow or reader changes: a project that declares no work type
sees only the new passing step.

## Residual

- 2026-11-03: SPEC-0038 rule 12 still names `scripts/agk/playbook.py` for builds (a), (b) and (f);
  the module is `scripts/agk/playbook_format.py` by the ruling on Q-513-1. The next amendment of
  SPEC-0038 corrects the name (due 2026-12-31).
- 2026-11-03: the owner-action match of rule 4 is a word list (sign, apply with infrastructure,
  release, secret); a gate that names an owner's action in other words is held by the review of
  the pull request that adds the playbook (due 2026-12-31).
