# ADR-0171: the secret scan survives a GitHub download outage and says so in plain words (REQ-039, brief 275)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0158, ADR-0159
- Requirements: REQ-039

Protected classes: `.github/`, `tests/kit/`

## Context

Brief #275 (priority 1): in a project pilot (2026-10-26) the step `Secret scan` of `.github/workflows/governance.yml` failed with
four raw `curl: (22) ... 504` lines when GitHub's release download server timed out. The step failed closed, as ADR-0158 decided,
but the person could not tell that it was an outage, and every pull request of that hour would have failed the same way. The tests
were written first (the download cases of `tests/kit/test_secret_scan.py` and the cache test of `tests/kit/test_workflow.py`) and
failed on the unchanged workflow (checkpoint bc3b4d1).

## Decision

1. **The cached copy.** A step `Restore the secret scanner` runs `actions/cache`, pinned by commit
   (`0057852bfaa89a56745cba8c7296529d2fc39830`, tag v4.3.0, read with `git ls-remote` on 2026-10-29), before `Project tests`, with
   the scan's condition (`!cancelled()` and not an `edited` run). Its key is `gitleaks-${{ env.GITLEAKS_VERSION }}-${{
   env.GITLEAKS_SHA256 }}`, from the step's own `env:`, which repeats the scan's two pins; a test keeps them equal, so they change
   together. The key is not written out: a literal 64-character value after `key:` is a finding of the scan's default
   `generic-api-key` rule, which failed the first run of this change (a test now scans the workflow file where a gitleaks binary is
   present). Its path is `${{ runner.temp }}/gitleaks-cache`. The action restores the directory there and saves it at the end of
   the job (its `post-if` is `success()`, read in the action's `action.yml` at that commit).
2. **Checked on every use.** The scan uses the cached archive only when it matches the digest (`sha256sum --check --strict`);
   a cached copy that does not match is deleted and the archive downloaded, so a bad cache entry, whose key cannot be
   overwritten, never blocks every later run. The archive in use, cached or downloaded, is then checked against the digest as
   before, and only after that check is it copied into the cached directory; a mismatch fails the step and leaves nothing for the
   cache to save.
3. **A failed download.** curl runs without `-S` and `-f`, writes the HTTP status, and keeps `--retry 3`. Any status but 200 (or
   `000` when no answer came) prints the one line `could not download the secret scanner from GitHub (HTTP <code>); re-run the job`
   and fails the step. The scan is never skipped.
4. **What does not change.** The step `Secret scan` keeps its name, its last place after `Project tests`, its condition, the pinned
   version and digest, the commits it scans and its flags; the workflow's permissions are unchanged and no secret is used (the cache
   action uses the runner's own token). Reading Q-275-2: saving with the combined action rather than a separate save step after
   the scan keeps the scan last (ADR-0158 decision 3, ADR-0159); the cost is that a job that fails saves nothing, and the next
   green run of the branch saves it.
5. **Flow mode.** Fragment `changelog.d/secret-scan-cache.md`; no version bump. `kit/hashes.json` and `kit/templates/` are not
   edited, although the brief's Touches lists them: the hashes are a release file (session rule 14) and no template carries the
   step. `docs/guides/security.md` says what the cache does.

## Consequences

- During a GitHub release download outage, a branch whose cache holds the archive (one green run of that branch, or of the default
  branch, which every branch can read) still runs its secret scan.
- With no cached copy, the person reads one line that names the cause and the fix instead of raw curl errors.
- The cache holds about 8 MB per gitleaks version; a new version or digest is a new key.

## Residual

- 2026-10-29: the restore and save were checked against the action's `action.yml`, not on a run of GitHub Actions; the first green
  run of this pull request shows `Cache saved with key: gitleaks-8.30.1-…` in its post step (due 2026-11-30).
- 2026-10-29: the action's commit was read with `git ls-remote` of its tags; no signature or attestation was verified, as for the
  other pinned actions (ADR-0006) (due 2026-12-15).
