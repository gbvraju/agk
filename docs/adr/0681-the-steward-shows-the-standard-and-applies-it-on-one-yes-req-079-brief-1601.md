# ADR-0681: The steward shows the standard and applies it on one yes

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1601, SPEC-0072, SPEC-0062, SPEC-0059, SPEC-0048, ADR-0665, ADR-0667, ADR-0679, plan #661
- Requirements: REQ-079

## Context

SPEC-0072 (Approved) rule 12 build (h) builds rule 8: before the foundation brief is filed the steward presents the
standard the product will be held to, one plain screen for a business user and the full list for a team, and applies
it only on one explicit yes, recorded as one Setup entry with the person's quoted words and time (`Q-S0072-13`). When
no shipped playbook fits, the steward asks permission to search the web with only a generic description of the product
type, and drafts a project playbook on `default.toml` with a Proposed project ADR (`Q-S0072-18`). On the default branch
the role file has no standard screen, nothing records a confirmation, and `steward_owner.py ready` starts the
conductor with no confirmed standard. Rule 11 asks `personal.py floor` to run the gate runner after its secret scan,
and rule 10 asks this build to propose a SPEC-0037 amendment. Brief #1601's question 1 recommends two pull requests;
the session's rule is one pull request per brief, so this ADR covers the whole build.

## Decision

1. `steward_owner.py standard [--playbook SLUG]` prints the composed standard of the declared `[delivery] work_type`
   (or of the named playbook, a drafted one included): in solo mode (`review_mode = "solo"`) one plain screen, one
   sentence per part with no kit term (`KIT_TERMS`), ending with the one yes question; in team mode the full list,
   the layers with their allowed directions, each stack pack with its tool and rule codes, and each gate as `check`
   with its step or `judgement` with its reason. With no work type and no `--playbook` it prints the work-type path's
   question instead and nothing else.
2. `steward_owner.py confirm --said FILE --at TIME [--by LOGIN]` records one memory entry
   `Setup: standard: confirmed because the person said "<words>" at <time>` only when the words of FILE are an
   explicit yes (SPEC-0062 rule 14, `steward_voice.is_yes`). Any other reply records nothing, prints
   `not confirmed: nothing applied`, and exits 1. In team mode the yes counts only with `--by` naming one of
   `spec_approvers` of `config/reviewers.yaml`; a steward started by the conductor (`AGK_STEWARD_START=conductor`)
   confirms nothing (exit 2). Refusals name the setting, never the value.
3. `steward_owner.py ready` adds one check: with a declared work type, no `Setup: standard: confirmed` entry in the
   memory is `not ready: the standard is not confirmed (setting: the confirmation Setup entry)`, so the conductor
   does not start and the role file files no foundation brief before the yes. With no work type nothing changes
   here (`check_plan.py` already holds the foundation brief, `Q-S0072-17`).
4. `steward_owner.py research --said FILE --at TIME --describe TEXT` records one
   `Setup: web-research: yes|no because the person said "<words>" at <time>` entry. Only on an explicit yes, and only
   when TEXT is a generic description (one line of at most 120 characters with no address, link, number, capitalised
   name after its first word, or anything the outbound data guard matches), it hands TEXT, and nothing else, to the
   search (`search: <TEXT>`, which the steward runs with its web tool); otherwise no search is made.
5. `steward_owner.py draft --slug SLUG` writes the project playbook with `front_door.py derive-write`'s skeleton
   (composed on `default.toml`, so every gate of `default.toml` is kept at its kind) and one Proposed project ADR,
   the next free number of `docs/adr/`, that names the playbook and the sources of its research record. It never
   writes `[delivery] work_type`, and refuses in the kit's own repository.
6. The role file gains one `Standard.` paragraph naming the four commands and their order (research and draft when
   no work type is set, the screen, the yes, then the plan), and stays within its word budget
   (`config/rule-budget.txt`, ADR-0310) by cutting three phrases its scripts or checks already carry.
7. `personal.py floor --approve` runs `run_gates.results` on the head tree (written under the sidecar's
   `cache/trees/`) after the secret scan and before the no-regression step, at every `[personal] level`; a red gate
   fails the floor; without `--approve` it prints `floor: gates not run`, as the test step does, and writes nothing.
   Files only, no command and no forge call.
8. Amendment 210 proposes to SPEC-0037 rule 11 that a signed-off prototype is a reference only (SPEC-0072 rule 10),
   for its spec approver; applied word for word to rules 11 and 13 on the maintainer answer of 2026-11-21
   ("Maintainer answer: amendment 210 approved", #1644 comment 7062667113).
9. The guide `docs/guides/engineering-standard.md` (installed, `kit/manifest.json` `verbatim` and `snapshot`) says
   what the standard holds, the present-confirm-implement path, the team's own choices, the business owner's request,
   every mode and the settings.

Protected path classes changed: `.claude/` (`agents/steward.md`), `scripts/agk/` (`steward_owner.py`,
`personal.py`), `tests/kit/` (`test_standard_confirm.py`, `test_personal_baseline.py`), `tests/kit_dev/` (`test_kit_manifest.py`),
`kit/` (`manifest.json`) and
`agk.toml` (the `[testing]` map entries).

## Consequences

A person sees what the product is held to before anything is applied, and one yes is the only way in; the yes can be
read back as a Setup entry. A no or an unclear reply leaves the project as it was. The web search carries only a
generic description. The drafted playbook cannot drop or weaken a gate of `default.toml`, since composition refuses it.

## Residual

- 2026-11-21: a drafted playbook is recognised only with a research record whose options carry web sources
  (SPEC-0048 rule 22), so the no-search path of rule 8 cannot yet draft one from the requirements alone; asked as
  `Q-1601-2` and answered 2026-11-21: a later brief lets the research record cite the project's requirement
  files (#1644 comment 7062670742).
- 2026-11-21: a business owner's plain request becoming one project requirement and one Proposed project ADR is the
  guide's and the architect's existing path (intake, then the architect agent's draft); no command records it yet,
  asked as `Q-1601-3` (due 2027-03-31).
