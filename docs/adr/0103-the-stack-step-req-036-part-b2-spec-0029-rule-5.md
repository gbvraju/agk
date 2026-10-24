# ADR-0103: the stack step (REQ-036 part b2, SPEC-0029 rule 5)

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0097, ADR-0099, ADR-0101
- Requirements: REQ-036

Protected classes: `kit/`, `scripts/agk/`, `skills/`, `tests/kit_dev/`

## Context

SPEC-0029 (Approved, #166) splits its build into (a) engines and doctor (ADR-0099), (b) vision and stack and (c) design. Part (b) was split again at its measure (ADR-0101, the maintainers read the split as intended on #170): (b1)
the vision is merged, and this is (b2), the stack. The tests were written first (`tests/kit_dev/test_engines_stack.py`; on unchanged `main`: 20 failed, 1 passed, the one being that an unknown command is a usage error). This
pull request branches from the default branch and does not stack on lane A's open #172 (ADR-0102 is that build's), so this ADR takes 0103.

## Decision

1. **The script** (kit-only, `scripts/agk/engines.py`, which ADR-0101 added): `stack-ids`, `stack-write` and `stack-check`; the three are in the command list and nothing falls through to another command (an unknown command exits 2 with the
   usage line). No network, no model. An engine (the skill named by `stack` in `[engines]`, ADR-0099) only drafts; the script writes through the template and the check refuses what does not fit; nothing here accepts an option.
2. **The skeleton**: `stack-ids` prints the next free ADR number read from the default branch (never the work tree) and the branch name `stack/options`; `stack-write` writes `docs/adr/<next>-stack-options.md` from
   `kit/templates/stack-adr.md` (Proposed, the date from `date -u`, `TODO(architect)` marks, `Chosen: none yet`) and refuses when a stack ADR already exists.
3. **The shape** (`stack-check`, rule 5): the ADR passes the ADR format check; its Decision has the numbered items **Options**, **Practices** and **Chosen**; **Options** has two or three bullets `Option A — ...` to `Option C`, each with
   `Trade-offs:` and `Practices:` naming at least one practice; every practice an option names is a bullet of **Practices**, marked `check (step: ...)` (a check exists, and the build that adopts the stack adds the governance step: pinned
   actions, least privilege, security headers, a host-boundary test) or `judgement` (recorded only); a Proposed ADR has `Chosen: none yet`; an Accepted one names exactly one existing option. A skeleton with a `TODO(architect)` mark is
   "not drafted yet". Messages name the rule and never quote an option or a practice. No stack ADR is "nothing to check".
4. **The skill**: `skills/stack/SKILL.md` (user-only; it writes one file and never commits) says that the engine or the template drafts, that an engine never decides, never accepts an option and never edits a protected file, and that the
   architect accepts one in a later change. `docs/guides/reference.md` lists the command and the two kinds of practice.
5. **No default engine, no version bump** (flow mode, SPEC-0028): one line under Unreleased in `CHANGELOG.md`; the script, the skill and the template are plugin files, so no installed file changes (the table of hashes is refreshed by the script).

## Consequences

- The architect gets one Proposed ADR with two or three options and the practices told apart as checked or judged, and accepts one; the ADR then locks it.
- The governance steps of the checked practices are built by the build that adopts the stack, not here.

## Residual

- 2026-10-24: `stack-check` runs from the skill; it is not a governance step, so a stack ADR edited outside that flow is caught by review (due 2026-12-31).
- 2026-10-24: whether a practice named `check` has a real governance step is not tested here; the adopting build adds and tests it (due 2026-12-31).
