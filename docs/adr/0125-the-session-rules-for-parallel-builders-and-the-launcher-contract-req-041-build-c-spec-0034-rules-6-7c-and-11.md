# ADR-0125: the session rules for parallel builders and the launcher contract in the guide (REQ-041 build c, SPEC-0034 rules 6, 7c and 11)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0124, ADR-0120, ADR-0100
- Requirements: REQ-041

Protected classes: `.claude/`, `config/`, `scripts/agk/`, `agk.toml`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0034 (Approved) rule 13 makes build (c) the session rules and the guide's launcher contract (rules 6, 7c and 11); the conductor assigned it on #176 with this ADR number and amendment 63 reserved, and with `Depends-on: #201` (build (b) adds `push-check` and `demand`, which the rules text names). The tests were written first (`tests/kit/test_flow_rules.py`, `tests/kit_dev/test_launcher_guide.py`; on the unchanged tree: 10 failed, 1 passed).

## Decision

1. **The session rules** (`config/session-rules.md`, installed verbatim): rule 13 (`push-check` before every push; on a conflict merge the default branch first, never rebase or force-push), rule 14 (the shared-mechanical files: those marked `merge=union` in `.gitattributes` and `changelog.d/`, the maintainers' list; `kit/hashes.json` is a release file a build never edits), rule 15 (only a mechanical conflict is resolved; any other ends the work with one comment `conflict needs a person: <files>` and no push) and rule 16 (the `Question:` and `Report:` shapes on the pull request, the answer only by a `Verdict:` naming the head, `watch` restarted after every push and event) (Q-K4-293, Q-K4-294).
2. **The conductor role** (`.claude/agents/conductor.md`): it reads the `Question:` and `Report:` comments of each pull request and answers each by a verdict.
3. **The guide** (`docs/guides/getting-started.md`, "Running the loop"): item 7 states the launcher contract of rule 6 with the output of `session.py demand`, `start = min(ready, max - open)`, and two examples that only read `demand`: a scheduled task of a session runtime and a CI schedule. AGK ships no launcher; the step that starts the sessions in the second example is a placeholder of the team's own (Q-K4-296).
4. **The hand-off design** (approved by the maintainer on #176, the comment that replaces the Idle/Next one; Q-K4-297 is answered by it). (A) `session.py` takes a build: `taken: <id> <date> build (<x>)`, `released: <id> [build (<x>)]`, and the new `claim --session ID --brief N [--build X]`; a live take of a build is never taken twice, a take without a build part claims the whole brief, a `released:` of the session frees its take. (B) `session.py watch --assign ID` reads the one open issue labelled `agk-conductor` and ends on the first `Assign: <id> ...` line after the session's `Request:` by a listed verdict author, or on `assign-timeout` after `claim_hours` (4 by default, read from the `[flow]` table here until build (b) of ADR-0124 reads it). (C) `[flow] assign` is `"conductor"` or `"next"` (default `"next"`), an invalid value is refused naming the setting, `session.py after --session ID` acts on it, and this repository's `agk.toml` sets `"conductor"`. (D) Session rules 17 and 18 say where each comment lives and what a finished builder does. (E) The conductor role file answers each `Request:` with one `Assign:` line (Q-K4-298, Q-K4-299).
5. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-sc.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 63 (`docs/runs/proposed-spec-amendments-63.md`) is applied to SPEC-0030 rules 1 and 6.

## Consequences

- A team that installs the kit gets the rules a parallel builder follows, and a launcher author gets a written contract with no launcher to maintain.
- The rules name `push-check`, which exists only once build (b) (ADR-0124) is merged; this pull request declares `Depends-on: #201` for that reason.

## Residual

- 2026-10-25: `session.py` has no command that posts `released:`, `Request:`, `conflict needs a person:`, `Question:` or `Report:` (SPEC-0034 rule 12 lists them among its POSTs); sessions post them with their runtime's own tools until a build adds the commands (due 2026-12-31).
