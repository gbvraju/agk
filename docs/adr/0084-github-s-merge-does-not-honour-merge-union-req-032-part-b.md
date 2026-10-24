# ADR-0084: the append-only logs merge by union; GitHub's check does not honour it, so a local merge resolves it (REQ-032 part b, SPEC-0025 rule 3)

- Status: Accepted
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

The maintainers ruled option 1 (the verdict on #143, Q-K4-239). The conflict is real on GitHub but mechanical: bringing the default branch in locally resolves it with no hand edit, so it costs one command, which a
session can run unattended. Built:

- `kit/templates/gitattributes` and this repository's `.gitattributes` mark `docs/runs/decisions-log.md`, `docs/runs/residuals.md` and `docs/runs/architect-catches-*.md` `merge=union`; `docs/requirements.md` is not marked.
  The template keeps its `scripts/agk/**` line; this repository's file carries only the three union lines (it does not mark its own scripts as generated). A test in `tests/kit_dev/test_kit_manifest.py` pins the lines in both
  files and the absence of `docs/requirements.md`; the two older tests that pinned the template to one line and this repository to no `.gitattributes` follow the ruling.
- `docs/guides/getting-started.md`: one bullet in "When something goes wrong": when GitHub reports a conflict only in those logs, run `git fetch origin && git merge origin/<default branch>` locally; git keeps both rows;
  push. Any other conflicting file is resolved by hand as before.
- Kit 0.46.0 to 0.47.0: `kit/manifest.json` `kit_version`, `kit/hashes.json`, `.claude-plugin/plugin.json`, `agk.toml`.

Protected path classes changed: `.claude-plugin/`, `agk.toml`, `kit/`, `tests/kit_dev/`.

## Options (as put to the ruling)

1. **Keep `merge=union` for local merges** (ruled, built). Git honours the lines when a developer merges the default branch locally (measured above); GitHub shows `dirty` until that push.
2. **One file per log entry, with a generated index** (not built). It migrates three logs and every reader of them (`common.py`, `facts.py`, `product_report.py`, `drift_audit.py`, `init.py`, the architect's file and the
   manifest) to remove one command.

## Consequences

- Two pull requests that append to the same log show a conflict on GitHub until one runs the local merge; the web merge button stays blocked until then.
- `intake.py renumber` (part a) does not touch log lines; the local merge does.
- Part (c) of SPEC-0025 does not depend on the logs.

## Residual

- 2026-10-24: option 2 is not built; revisit only if the count of such merges says so.
- 2026-10-24: the two throwaway measurement branches `ccr-7649d887-m9hvn7-mu-a` and `ccr-7649d887-m9hvn7-mu-b` could not be deleted from a session (proxy 403); they are left for the maintainers (due 2026-12-31).
