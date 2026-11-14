# ADR-0522: A Windows setup works on the first run

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0006 rules 3 and 6, amendment 178, ADR-0160, brief #263, brief #1223, plan #661
- Requirements: REQ-014

## Context

A customer set a project up on Windows 11, once for each of the two owner scenarios of brief #1223. The hooks failed
because `python3` was the Microsoft Store shortcut (an alias under `WindowsApps` that opens the Store), then because
`make` was missing, and gitleaks had to be installed by hand; nothing named the three fixes. `doctor.py` reported
`cannot check (no-admin)` with the hint "use an account with admin rights" for an account that GitHub shows as an admin:
every 403 or 404 without a stated cause was `no-admin` unless the repository read had shown `permissions.admin` true,
so a failed or partial repository read turned into a claim about the account. After `adopt.py`, `.github/CODEOWNERS`
kept 13 `@REPLACE-ME` lines above the generated block: `reviewers.py --codeowners --write` in adopt mode replaces only
the marked block.

## Decision

1. `doctor.py` adds one check, `windows-tools` (warn), reported only when the doctor runs on Windows (`sys.platform`
   starts with `win`) and placed after the checks of `CHECKS`, so the report elsewhere is unchanged. It fails, naming
   each tool, when `python3` is absent or resolves under `WindowsApps`, when `make` is absent and when `gitleaks` is
   absent, and its printed fix is the fix of each missing tool alone: turn off the App execution aliases for
   `python.exe` and `python3.exe` and copy `python.exe` to `python3.exe`; `winget install ezwinports.make`;
   `winget install gitleaks.gitleaks --version <GITLEAKS_PIN>`, the version the governance workflow pins.
2. The account's admin rights are `permissions.admin` of the repository read, the REST GET `repos/{owner}/{repo}`
   (what `gh api repos/{owner}/{repo} --jq .permissions.admin` prints; the doctor passes an argument list, so no shell
   quotes the braces). A 403 or 404 that does not say why is, for the repository read, the ruleset reads and the two
   merge keys, `no-admin` only when `permissions.admin` is false, `forbidden` when it is true (brief #263), and the new
   reason `admin-unknown` (`cannot check (admin-unknown)`) when it could not be read; its hint names the `--jq` read. A
   refusal whose message says `admin rights` stays `no-admin`, since GitHub names the cause. Every other reader of
   `Reads.get` (and `ruleset.py`) sees `no-admin` as before.
3. In adopt mode, `reviewers.py --codeowners --write` removes the plain rule lines outside the marked block whose owners
   are all the installed placeholder `@REPLACE-ME` (any case, a trailing comment allowed), and keeps every other line:
   comments, blank lines and any line that names another owner.

## Consequences

A Windows machine is told, in one doctor run, the exact command that fixes each missing tool; an admin is no longer
told to find admin rights; and an adopted project's CODEOWNERS names no owner nobody holds. SPEC-0006 rule 6 still reads
`no-admin` for a refused ruleset read and a missing merge key; this ADR narrows that to a known non-admin, as brief
#263 did with `forbidden`, and adds the reason class `admin-unknown` to rule 3's list; the spec lines are proposed in
`docs/runs/proposed-spec-amendments-178.md` (amendment 178, reserved in the answer to Q-1223-1), not applied here.
Protected path classes changed: `scripts/agk/` (`doctor.py`, `reviewers.py`), `tests/kit/`
(`test_doctor_windows.py`, new), `agk.toml` (the new test file added to the `[[testing.map]]` entries of
`scripts/agk/doctor.py` and `scripts/agk/reviewers.py`, nothing else) and `docs/adr/` (this file).

## Residual

- 2026-11-14: the winget ids `ezwinports.make` and `gitleaks.gitleaks` and the App execution aliases path are the
  brief's, not run on Windows by the session that wrote this `(verify)`.
- 2026-11-14: amendment 178 (SPEC-0006 rules 3 and 6) waits for the maintainers' decision.
