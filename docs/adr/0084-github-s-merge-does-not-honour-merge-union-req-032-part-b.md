# ADR-0084: GitHub's merge check does not honour merge=union (REQ-032 part b, SPEC-0025 rule 3)

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0082
- Requirements: REQ-032

## Context

SPEC-0025 rule 3 marks the append-only logs (`docs/runs/decisions-log.md`, `docs/runs/residuals.md`, the catch logs) `merge=union` in the shipped `.gitattributes`, so that two pull requests that each append a line
merge without a conflict, and it makes the behaviour of GitHub's merge conflict check a step of this part: "if it does not honour `merge=union`, the build raises a question with the measured behaviour and two
options and builds neither until it is ruled". The maintainers ruled the method (the verdict on #139): two throwaway branches from the default branch, each appending one line to a `merge=union` file, one draft
pull request titled "measurement: merge=union (to be closed)", its `mergeable` and `mergeable_state` read with GET, then the pull request closed without merging and both branches deleted.

## Measurement (2026-10-24)

- Base: `main` at `58ccb29`. Branch `ccr-7649d887-m9hvn7-mu-a` (`269588a`) and branch `ccr-7649d887-m9hvn7-mu-b` (`aedb628`) each add a `.gitattributes` with the one line `docs/runs/decisions-log.md merge=union`
  (the same bytes on both) and append one different row to `docs/runs/decisions-log.md`.
- Local git (2.43.0): `git merge-tree --write-tree` of the two branches succeeds (exit 0, tree `0139cd7`), with both rows kept.
- GitHub: the draft pull request #142 (head `-mu-b`, base `-mu-a`) read, six times over about fifty seconds, `mergeable: false` and `mergeable_state: dirty`. GitHub's merge conflict check does **not** honour
  `merge=union`: it reports a conflict on the append that local git merges cleanly.
- #142 was closed without merging (`merged: false`, closed at 2026-10-24T07:47:34Z). The two branches could not be deleted by this session: the proxy refuses the deletion (`git push --delete` hangs up; the
  REST call answers 403 "Write access to this GitHub API path is not permitted through this proxy"). They remain on the remote until a maintainer deletes them.

## Decision

None is taken: SPEC-0025 rule 3 builds neither option until the maintainers rule. This pull request records the measurement and the question. The `.gitattributes` template and every other file are unchanged, and there
is no kit change.

## Options (for the ruling; neither is built)

1. **Keep `merge=union` for local rebases only.** The shipped `.gitattributes` gets the lines. Git honours them when a developer rebases or merges the default branch locally (measured above), so the developer
   resolves the collision on their machine and pushes; GitHub keeps showing `dirty` (and blocks the web merge) until that push, because its check ignores the attribute. Cost: a few lines and a test of the template;
   the developer's local step is required every time two pull requests append to the same log. A repository that merges through the GitHub button never gets the benefit.
2. **One file per log entry, with a generated index.** Each decisions-log row, residual line and catch row is its own file (for example one folder per log, one file per entry), and the log a person reads is generated
   from them. Two pull requests then add different files and never touch the same lines, so GitHub's check is clean. Cost: a migration of the existing logs and a change of every reader of them (`common.py`,
   `facts.py`, `product_report.py`, `drift_audit.py`, `init.py`, the architect's file and the manifest all name the logs), a generator and its check, and a new rule for how a ruling is recorded.

## Consequences

- Until the ruling, two pull requests that append to the same log still collide on GitHub; `intake.py renumber` (part a) does not help with a log line.
- Parts (b) and (c) of SPEC-0025 continue independently of this: part (c) does not depend on the logs.

## Residual

- 2026-10-24: the two throwaway measurement branches remain on the remote until a maintainer deletes them (due 2026-12-31).
