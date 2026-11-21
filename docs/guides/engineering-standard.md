<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->
# The engineering standard

What a product built with the kit is held to, who sets it and how it is confirmed (SPEC-0072, REQ-079; brief #1601,
ADR-0681). The standard is the composed playbook of the project's work type: `config/playbooks/default.toml`, then the
work type's playbook, then the project's own module.

## What the standard holds

- **The architecture.** The layers of `[architecture]`, their paths and the directions one layer may import another;
  the `layers` step fails an import that `allow` does not list, and `docs/architecture.md` records them (rule 5).
- **The standards pack.** For each stack the Accepted stack record chose, the pack's lint, format and type steps over
  `project_lint_paths`, with the pinned rule codes; a team's own configuration must keep every rule code (rule 6).
- **The gates.** Each gate is a `check` that `run_gates.py` runs inside `make governance` and CI's `governance` job,
  or a `judgement` with its reason that a reviewer reads (rules 2 and 3).
- **The baseline.** An adopted project's existing findings are counted first and may only fall (rule 7).

## Present, confirm, then implement

Before the foundation brief is filed, the steward shows the standard and applies it only on one yes (rule 8):

1. With no `[delivery] work_type`, the steward asks permission to look the product type up, in general words only:
   `python3 scripts/agk/steward_owner.py research --said FILE --at TIME --describe TEXT`. A yes records the permission
   and prints `search: <TEXT>`, the only words the web search carries; a no, or a description with a name, an
   address, a link or a number, means no search. Then `steward_owner.py draft --slug SLUG` writes the project's own
   playbook on `default.toml` (every gate kept at its kind) with a Proposed ADR naming the sources. The owner, never
   the steward, names it in `[delivery] work_type`.
2. `python3 scripts/agk/steward_owner.py standard` prints the screen: in solo mode one plain screen with no kit term;
   in team mode the full list of layers, directions, packs and every gate with its step or reason.
3. `python3 scripts/agk/steward_owner.py confirm --said FILE --at TIME [--by LOGIN]` records one
   `Setup: standard: confirmed because the person said "<words>" at <time>` entry, only on an explicit yes. In team
   mode only a spec approver's yes counts, and a steward the supervisor started confirms nothing.
4. `steward_owner.py ready` is `not ready` while a work type is declared and the entry is missing, so nothing is
   applied and no foundation brief is filed before the yes.

## The team's own choices and the owner's requests

- A team's architect or designer may keep every default or define their own layers, pack configuration or stricter
  gates in the project's playbook module and its ADRs. Loosening a gate, an `allow` entry or a pack rule needs an ADR.
- A business or product owner may ask for a standard in plain words ("an audit trail of every change"). The steward
  records it as a requirement of the project; the architect drafts the project ADR, Proposed, with the gate or pack it
  changes; the project's maintainers accept it, never an agent.
- Which standard work comes first follows the person's priority in the project's plan; the kit fixes no order.

## Every mode

- **CI and local:** the same checks in `governance`, `make governance` and `prepush.py` (`docs/guides/local-mode.md`).
- **Personal:** `python3 scripts/agk/personal.py floor --approve` runs the gate runner on the head tree after its
  secret scan and before the no-regression step, at every `[personal] level`, with no forge call (rule 11).
- **Solo and team:** only who confirms changes. No mode changes a workflow, the ruleset or a required check.

## The settings

| Setting | Default | Impact |
|---|---|---|
| the confirmation (Setup entry) | absent | absent: nothing applied, no foundation brief; present: the shown standard applies |
| the web-research permission (Setup entry) | absent | absent or no: no web search; the playbook is drafted from the requirements |
| `[delivery] work_type` | absent | absent in a new project: the work-type path above; the kit's own repository: `default.toml` only |
| `[personal] level` | `light` | printed only; the floor runs the gates at every level |
| `review_mode` | `team` | `solo`: one plain screen and the person's yes; `team`: the full list and a spec approver's yes |
