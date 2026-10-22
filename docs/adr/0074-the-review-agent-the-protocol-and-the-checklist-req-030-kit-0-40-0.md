# ADR-0074: the review agent, the protocol and the checklist (REQ-030 part a, SPEC-0023), kit 0.40.0

- Status: Accepted
- Date: 2026-10-22
- Deciders: maintainers
- Related: ADR-0073, ADR-0053
- Requirements: REQ-030

Protected classes: `.claude/`, `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

SPEC-0023 (Approved, #124) makes every review follow one written protocol that names what it read, walks the spec's rules, says what the tests do not prove and where a gap belongs, and measures its catch rate
before any claim. Its build is split in three; this part (a) builds the review agent, the guard mode, the nine steps in both agent files, the shape of a verdict and the checklist (rules 1 to 5; AC1 to AC4). The
tests were written first and run on unchanged `main` (64 failed, 89 passed; the output is in the pull request body).

## Decision

1. **The review agent**: `.claude/agents/architect-review.md`, `tools: Read, Grep, Glob, Bash`, with the `PreToolUse` hook `architect_guard.py --review`. The file forbids editing, building and merging, and reviewing
   in the session that built the change (a written rule), says the builder's report is not evidence, and that the verdict is a comment, never a commit.
2. **The guard mode**: `architect_guard.py --review` denies `Edit`, `Write`, `MultiEdit` and `NotebookEdit` for every path, `docs/` and the vision included, with the message "architect guard rule 9: the review agent
   writes nothing"; `Bash` is judged as for the deciding architect; without the argument the guard is unchanged. It cannot tell which pull request a comment goes to.
3. **The protocol**: the nine steps are one block, between `<!-- protocol -->` and `<!-- /protocol -->`, word for word the same in `architect.md` and `architect-review.md` (a test compares them), followed by the
   shape of a verdict (`Read:`, `Rules:`, `Not proven:`, `Lens:` with five lines, `Gaps:` as `project:` or `kit:`, `Checklist:`). `architect.md` keeps its tools, its guard and its writes; its old sentences stay.
   `kit/templates/playbook/verdict.md` shows the shape and keeps a first line that `metrics.VERDICT` matches.
4. **The checklist**: `config/review-checklist.md`, twelve questions, one for each kind of `docs/runs/architect-catches-1.md` and in its order, each naming its kind, each answered in the verdict with evidence or
   `n/a`. It states that it changes only by a pull request whose decision record cites a row of a catch log. It is a verbatim kit file, so `agk upgrade` brings it, and in a project the change touches the class
   `config/`, which needs that project's own decision record as for any protected change.
5. **Amendment 37** (`docs/runs/proposed-spec-amendments-37.md`) is applied to SPEC-0013 rules 9, 11 and 29. The security guide's account of the architect guard names the review agent.
6. **Tests, first** (`tests/kit/test_architect_review_guard.py`, new, installed; `tests/kit_dev/test_architect_review.py`, new, kit-only): the guard in review mode over every write tool and path and the Bash table of
   the deciding architect; the review agent's tools, hook and prohibitions; the protocol block equal in both files with its nine steps and the lens in order; the shape lines in both files and the template; the
   deciding architect unchanged; the checklist against the catch log; the manifest and the hashes; no project, reader or plugin variable named.
7. **Kit 0.40.0**: the manifest `kit_version` and its two new verbatim files, the hashes, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7).

## Consequences

- A project that upgrades gets the review agent and the checklist; `claude --agent architect-review` starts the read-only reviewer in a separate session. Nothing the deciding architect did changes.
- Part (b) (discovery and the slicing rule) and part (c) (the shadow record and the counting script) follow with kits 0.41.0 and 0.42.0; L3b (kit 0.43.0) follows them.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-227 | Is the checklist a template (copied once, owned by the project) or a verbatim kit file? | Verbatim (SPEC-0023 rule 5: "installed verbatim"): the kit grows it from its catch log and `agk upgrade` brings the new questions; a project's change to it needs the project's own decision record, as for any file of `config/`. Proposed for ruling. |

## Residual

None.
