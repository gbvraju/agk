# ADR-0092: the getting-started fixes of rehearsal 1 (issue #156), kit 0.53.0

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0091
- Requirements: REQ-009

Protected classes: `.claude-plugin/`, `agk.toml`, `kit/`, `scripts/agk/`, `skills/`, `tests/kit_dev/`

## Context

Rehearsal 1 (`docs/runs/getting-started-rehearsal-1.md`, #155) followed the getting-started guide on a fresh local repository and proposed ten fixes. The brief in issue #156 adopts eight of them (fix 9 is not adopted:
the guide keeps installing from `main`; fix 10 is a record). The tests were written first (`tests/kit_dev/test_origin_message.py` and `test_guide_fixes.py`; on unchanged `main`: 12 failed).

## Decision

1. **Guide** (`docs/guides/getting-started.md`): "Before you start" says which steps need `gh` logged in (fix 1); one sentence names the script behind each slash command (fix 2); step 3 drops the file count and size
   (fix 3); step 4 describes today's `make governance` output: ten `ok`, two `skipped` in either order, one `specs:` line (fix 4); steps 6 and 7 say they need `origin` (fix 5); step 6 says `/agk:start` asks about the
   six topics, at most three questions a round, and that `not known yet` is valid (fix 6).
2. **Messages** (fix 5): `common.next_free_ids` refuses with `origin/<branch> cannot be read; steps 6 and 7 need the repository's remote` when the ref starts with `origin/` and does not resolve; the missing-file message stays for a
   ref that resolves. `intake.py ids` and `playbook.py start-ids` use it; one test for each.
3. **Template** (fix 7): `docs/specs/TEMPLATE.md` gains `## Proof` and `## Residual`; a test pins the headings and that the skill names the same sections.
4. **Skill** (fix 8): `skills/spec/SKILL.md` says `answered no questions` only when a person confirmed it, and that with nobody to ask the intake stops before writing any file and says so.
5. Amendment 49 (`docs/runs/proposed-spec-amendments-49.md`) is applied to SPEC-0012 and SPEC-0013.
6. **Kit 0.53.0**: the manifest `kit_version`, the hashes (`common.py`, the template, the skill and the guide are kit files), the plugin version and `version` in this repository's `agk.toml`.

## Consequences

- A newcomer without `origin` is told why `ids` and `start-ids` refuse. The guide no longer carries figures that go stale.

## Residual

None.
