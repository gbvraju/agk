# ADR-0643: Add REQ-079: Each playbook carries its architecture, a standards pack and enterprise checks

- Status: Accepted
- Date: 2026-11-18
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0002, SPEC-0037, SPEC-0038, SPEC-0041, SPEC-0059, SPEC-0071, ADR-0007, brief #1400, brief #1524, plan #661
- Requirements: REQ-079

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-18:

> Each work-type playbook carries its architecture, a stack standards pack and enterprise defaults as checks, applied on Day 0 by a foundation build, so a business user using only the steward gets an enterprise-grade product with no engineering choice; existing code is baselined and only improves.

The brief is issue #1524, under plan #661. On the default branch at 1359dc0e a project's code gets no lint, format, type,
architecture or enterprise check: `lint_paths` covers only the kit's folders (SPEC-0002 rule 10, ADR-0007 decision 8), the
stack record leaves its practices as `TODO(architect)`, and none of the 25 `kind = "check"` gates of the ten playbooks
under `config/playbooks/` has a step that any script, make target or workflow runs. No playbook names the enterprise
concerns, no foundation build precedes the first feature, and an adopted project has no baseline of its findings.

## Decision

1. REQ-079 is added to `docs/requirements.md` as `planned`, and SPEC-0072 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. The engineering standard ships in the playbook and is on by default: each playbook, and `default.toml` for every one,
   carries an architecture (layers over the `[testing] map` paths and the allowed dependency directions), a standards pack
   per stack (a lint, format and type step with a pinned rule set and its configuration file) and eight enterprise gates,
   each a check whose step runs or a judgement with its reason; composition never weakens a gate without an ADR.
3. Every check gate's step is executed offline by a governance runner inside the existing `governance` job and `make
   governance`; a step with no implementation is refused, and `required_checks` does not change.
4. Every playbook's `[split] brief_order` starts with `foundation`, which every feature brief depends on, and the stack
   record's practices are written from the playbook, never as `TODO(architect)`.
5. The kit's own lint (`lint_paths`, `AGK_RUFF_FLAGS`, `agk-lint`) is unchanged; a project's code is read through a new
   setting, `project_lint_paths`.
6. An adopted or upgraded project gets a committed baseline of today's findings and a ratchet: green first, red on a new
   or rising finding, lowered on a fixed one; nothing existing is rewritten.
7. When nobody has discussed a standard, the steward presents the choices it applies (one plain screen for a business
   user, the full list for a team) and applies them only on the person's yes, one yes accepting all; a team may keep the
   defaults or define its own architecture, pack configuration (accepted when it covers the pack's floor rules) or
   stricter gates; a business or product owner's plain request becomes a requirement and a Proposed project ADR; the
   person's priority orders a project's standard work; every work-type build brief names its layers in a `Layer:` line
   and builders read the architecture record and the pack before writing code (brief #1524 answer 9).
   No new project proceeds to its foundation build without a work type: where the requirements identify no playbook,
   the steward asks the person's permission to research the product type on the web with only a generic description and
   never customer data, then drafts a project playbook on `default.toml` that keeps every gate, recorded with a Proposed
   project ADR and confirmed by the person (the maintainer's answer to `Q-S0072-4`, #1525 comment 7000020901).
8. The review checklist is unchanged; a prototype's markup is a reference only, by an amendment to SPEC-0037 that its
   spec approver approves.
9. This ADR names the protected classes of this intake only. Builds (a) (`config/playbooks/`), (b) (`agk.mk`), (d) (the
   project's protected paths, the builder prompt), (e) (the new `agk.toml` setting) and (h) (the steward's role file and the SPEC-0037
   amendment) change decisions held elsewhere, so each writes its own ADR. Builds (c), (f) and (g) will change
   `scripts/agk/`, `tests/kit/`, `skills/` and `kit/`; each may cite this ADR with `Covered-by: ADR-0643` once it is
   Accepted only if it changes no other class and no decision named here (session rule 36). No build changes a workflow
   file (`.github/`), the ruleset or `config/reviewers.yaml`; `kit/hashes.json` and the version stay the release's
   (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the playbook parts, the runner, the foundation kind, the architecture record, the packs, the enterprise steps and
the baseline are built by SPEC-0072's builds (a) to (h).

## Residual

None beyond SPEC-0072's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.
