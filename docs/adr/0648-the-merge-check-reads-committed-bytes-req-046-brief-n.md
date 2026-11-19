# ADR-0648: The merge check reads committed bytes

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: ADR-0257, ADR-0550, ADR-0572, SPEC-0039, brief #1291, brief #1540, plan #661
- Requirements: REQ-046

## Context

On Windows (Git for Windows, `core.autocrlf=true`) the owner's `python3 scripts/agk/merge_cleared.py --pr 1533 --owner`
printed "3 failed, 51 passed" and held the merge, while the same merge of #1533's head with main at d6d21c02 passed on
Linux. Measured on Linux (brief #1540): `git -c core.autocrlf=true worktree add --detach` of d6d21c02 writes
`config/stack-signals.toml` with CRLF (SHA-256 `741323fb…`) while its blob is LF (`c61b5c59…`). The merge check's
temporary tree took the person's line-end settings; `evidence.py` alone avoided them (ADR-0550). Two of the failures were
test helpers that built names with `str(path.relative_to(root))`, which on Windows gives `\`, against the kit's `/`-only
globs. The kit repository's own `.gitattributes` pinned no line ends, a hash taken from the working tree
(`kit_hashes.py`, `plan_intake.py`'s re-render) differed by checkout, and the check's temporary folder could carry an 8.3
short name.

The options weighed: (A) make only the failing tests tolerant, which hides a real CRLF install and leaves the hashes and
the other checkouts wrong; (B) pin LF in the kit repository, needed but blind to a project's files and to a checkout the
person's settings still reach; (C) one committed-bytes checkout for every temporary tree, hashes taken as committed and
`/` names in the kit's tests; (D) a Windows job in CI, the only real proof on Windows per pull request, but a workflow
change for the owner (session rule 30) that adds minutes to every run.

## Decision

1. The kit repository's root `.gitattributes` carries `* text=auto eol=lf` above its `merge=union` lines. Every blob is
   already LF, so no file's content changes. `kit/templates/gitattributes`, what a project gets, is unchanged.
2. `scripts/agk/common.py` holds `CHECKOUT` (`-c core.autocrlf=false -c core.eol=lf`, moved from `evidence.py`, value
   unchanged). Every git call that writes files into a temporary tree of the kit passes it before its command: the
   `worktree add` of `merge_cleared.py`, `lock.py` (the heavy-queue job), `proof.py`, `batch.py`, `workflow_apply.py`
   and `evidence.py`; the `checkout` of the clones of `plugin_snapshot.py`, `release_pack.py` and `drift_audit.py`; and
   the later `merge`, `checkout` and `reset --hard` that `batch.py` and `drift_audit.py` run in their trees, since a
   worktree shares the person's configuration. Each site keeps its own git wrapper (its error handling, and the tests
   that slow or fake it), so there is no shared `add_worktree` function. So each tree holds the committed bytes whatever
   the person's git configuration says; a project's own `eol` attributes still win, in the check as in CI. A structural
   test refuses a `worktree add` or a `checkout` argument list under `scripts/agk/` without `*CHECKOUT`; `setup.py`'s
   branch checkout of the person's own WSL clone is not a temporary tree and is named as the one exception.
3. A hash taken from the working tree is taken as committed: `kit_hashes.py snapshot_worktree` and `plan_intake.py`'s
   re-render read through `common.committed_bytes` (ADR-0550), so a file whose checkout changed only its line ends
   hashes as its blob, and a file committed with CRLF keeps its own hash. The re-render also accepts the digest of the
   bytes on disk, so a digest recorded before this change still matches, and the render writes LF on every system.
   `design_prototype_check.py`'s runtime hash reads the same way (Q-1540-4, ADR-0550's residual): a tracked runtime
   whose blob is LF checks on a CRLF checkout; an untracked one keeps its bytes on disk.
4. The merge check's temporary folder is made under `common.long_temp_dir()`, and on Windows its runs get `TEMP` and
   `TMP`, where set, in their long form (`common.long_form`, ADR-0257). The run's environment is a clean one that never
   kept `TMPDIR` (brief #1290), so no short name reaches a run through it, and no name is invented.
5. The kit's own tests compare names with `/` (`.as_posix()`); a structural test refuses `str(<x>.relative_to(<y>))`
   under `tests/kit/` and `tests/kit_dev/`. A project's own tests are its own (Q-1540-5).
6. In the kit repository only, on Windows and a clean tree, when a tracked file whose attributes say `eol=lf` is CRLF
   on disk, `doctor.py`'s line-endings row prints the one command that renormalises a checkout made before rule 1:
   `git rm --cached -r -q . && git reset --hard` (verify: this exact form on Git for Windows; it is tested with git on
   Linux). The doctor never runs it, and a project is told nothing new (Q-1540-6).
7. Option (D) is not taken here (Q-1540-3): the edge cases run on Linux with a real `core.autocrlf=true` checkout and
   `PureWindowsPath` names, plus one recorded owner run on Windows.

No workflow file, ruleset, spec, `constitution/` file or `kit/hashes.json` row changes. SPEC-0039 rule 6 is unchanged
(Q-1540-1): the committed bytes are the would-be merge it tests.

## Consequences

The check before the merge gives the result CI on Linux gives, on Windows, macOS, Linux and WSL, in the kit and in every
project; a hash written on one system checks on another. Hosted runs on Linux are unchanged. Tests:
`tests/kit/test_windows_checkout.py` and the tests named in the pull request. Protected path classes changed:
`scripts/agk/`, `tests/kit/` and `tests/kit_dev/`.

## Residual

- 2026-11-19: `prepush.py` still runs in the person's own checkout (Q-1540-2); a Windows CI job is the owner's to brief
  (Q-1540-3).
