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
conductor with no confirmed standard. Brief #1601's question 1 recommends two pull requests; this ADR covers the first
(the screen, the confirmation and the work-type path) and the second (the personal floor, the SPEC-0037 amendment and
the guide) adds its own decisions here before this ADR is accepted.

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
6. The role file's `Setup.` paragraph names the four commands and the order: work type or draft, the screen, the
   yes, then the plan.

Protected path classes changed: `.claude/` (`agents/steward.md`), `scripts/agk/` (`steward_owner.py`), `tests/kit/`
(`test_standard_confirm.py`) and `agk.toml` (the `[testing]` map entry of the new test).

## Consequences

A person sees what the product is held to before anything is applied, and one yes is the only way in; the yes can be
read back as a Setup entry. A no or an unclear reply leaves the project as it was. The web search carries only a
generic description. The drafted playbook cannot drop or weaken a gate of `default.toml`, since composition refuses it.

## Residual

- 2026-11-21: a drafted playbook is recognised only with a research record whose options carry web sources
  (SPEC-0048 rule 22), so the no-search path of rule 8 cannot yet draft one from the requirements alone; asked as
  `Q-1601-2` (due 2027-03-31).
- 2026-11-21: the second pull request of brief #1601 adds the personal floor, amendment 210 and the guide.
