# ADR-0158: the secret scan runs the pinned gitleaks binary, no licence key (REQ-039, brief 258)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0006
- Requirements: REQ-039

Protected classes: `.github/`, `tests/kit/`

## Context

Brief #258 (priority 0): the step `Secret scan` of `.github/workflows/governance.yml` used `gitleaks/gitleaks-action` (v2.3.9),
which needs a paid licence key, the secret `GITLEAKS_LICENSE`, on a repository owned by an organisation. `governance` was then red
on the first push of every organisation project that installs the kit, and the required check blocked every merge. The gitleaks
command-line tool is open source (MIT, read from the `LICENSE` file of the release archive) and needs no key. This is the
replacement that the ADR-0006 residual (Q-K1-17) proposed. The tests were written first (`tests/kit/test_secret_scan.py` and the
secret-scan tests of `tests/kit/test_workflow.py`) and failed on the unchanged tree.

## Decision

1. **The binary.** The step downloads one pinned release of the official gitleaks binary for linux x64,
   `gitleaks_8.30.1_linux_x64.tar.gz`, from the project's GitHub releases. Its SHA-256,
   `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`, is written in the workflow (`GITLEAKS_SHA256`) and checked
   with `sha256sum --check --strict` before the archive is unpacked; a mismatch fails the step. The digest equals the line of the
   release's `gitleaks_8.30.1_checksums.txt` and the digest of the archive as downloaded on 2026-10-26. 8.30.1 is the newest
   release found that day (reading Q-258-1).
2. **The commits scanned.** On a pull request, from the merge base of the base (`AGK_BASE`, the first parent of the merge
   checkout) and the head to the head; on a push, from `before` to the head; on the first push of a repository, or when `before` is
   all zeros or is not in the history (a forced push), the whole history reachable from the head. `gitleaks git` runs with
   `--redact --exit-code 1`, so any finding fails the step and the log never shows the value found. The default rules of the pinned
   version apply; no configuration file and no ignore entry is added.
3. **What does not change.** The step keeps its name `Secret scan`, its place (last, after `Project tests`) and its condition; the
   job, the workflow and the required check keep their names. The step uses no secret, no licence key and no action, and the
   workflow's permissions are unchanged; the job no longer passes `secrets.GITHUB_TOKEN` to the scan.
4. **The tests.** The workflow is checked as text: the pinned version, a 64-character digest, the check before the unpacking, no
   `gitleaks-action`, no `GITLEAKS_LICENSE`, no `secrets.`, the permissions, the step's name and place. The step's own shell is run:
   its first part with a stand-in `curl` that writes a wrong archive (the step fails and unpacks nothing, with no network call); its
   second part in throwaway repositories with a fake token built when the test runs, where a gitleaks binary is on `PATH` or named by
   `AGK_GITLEAKS`, and skipped with a reason where none is (in CI the binary exists only inside the step, after the tests).
5. **The guides.** `docs/guides/security.md` says what the scan runs and that no key is needed; the README's limits say nothing of
   a key. No spec rule changes, so no amendment. Flow mode: fragment `changelog.d/secret-scan-binary.md`; no version bump.

## Consequences

- Governance's secret scan passes on any repository, personal or organisation, with no licence key and no secret to set, and still
  fails on a leaked secret in the commits of the change.
- Each run downloads about 8 MB from the gitleaks releases on GitHub; a release that cannot be downloaded fails the step, never
  passes it.
- A newer gitleaks is taken only by a change of the version and the digest together, in a pull request.

## Residual

- 2026-10-26: the after measurement of the brief (the first push of an organisation project shows `Secret scan` green with no
  secret set) is to be taken on an organisation repository; this session can reach none. The residual of ADR-0006 on the licence
  (Q-K1-17) stays open in `docs/runs/residuals.md` until it is (due 2026-12-15).
- 2026-10-26: the digest was confirmed against the release's own checksums file only; no signature or attestation of the archive
  was verified (as for the action SHAs in ADR-0006) (due 2026-12-15).
