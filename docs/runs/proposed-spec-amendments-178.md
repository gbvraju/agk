# Proposed spec amendments 178 (SPEC-0006; REQ-014)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0522 (brief #1223), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0006-doctor.md`.
Brief #1223 reserved ADR-0522 and no amendment number; the conductor reserved 178 in its verdict on pull request #1228
(answer to Q-1223-1). This file proposes the lines and does not edit the spec; the maintainers decide them.

The sentence (brief #1223): "A project set up on Windows works on the first run: the kit names the missing python3, make
and gitleaks with their fixes, reads admin rights correctly, and leaves no placeholder owners."

## What the spec says today

- Rule 3 lists the reason classes of `cannot-check`: `gh-missing`, `gh-unauthenticated`, `no-admin`, `not-github`,
  `no-kit-root`, `version-mismatch`, `offline`, `bad-response`, `no-ruleset`. It does not list `forbidden`, which brief
  #263 added to the code, nor `admin-unknown`, which ADR-0522 adds.
- Rule 6: "a 403 or 404 on a ruleset read is `cannot-check` (`no-admin`), and never `ruleset-missing`", and "A missing
  `allow_auto_merge` or `delete_branch_on_merge` key (shown only to users with push access) is `cannot-check`
  (`no-admin`)."

## Items

1. **Rule 3, the reason list.** Add two classes after `no-admin`: "`forbidden` (GitHub refused a read although
   `permissions.admin` in the repository read is true), `admin-unknown` (GitHub refused a read without naming the cause,
   and `permissions.admin` could not be read)".
2. **Rule 6, the refused reads.** Replace "a 403 or 404 on a ruleset read is `cannot-check` (`no-admin`), and never
   `ruleset-missing`" with: "a 403 or 404 on the repository read or a ruleset read is `cannot-check`, and never
   `ruleset-missing`: `no-admin` when GitHub's message names admin rights or `permissions.admin` in the repository read
   (what `gh api repos/{o}/{r} --jq .permissions.admin` prints) is false, `forbidden` when it is true, and
   `admin-unknown` when it could not be read". Replace the merge-key sentence's "(`no-admin`)" with "(`no-admin` with
   `permissions.admin` false, `forbidden` with true, `admin-unknown` when it could not be read)".
3. **No other change.** Every other reader of the doctor's GitHub reads, and `ruleset.py`, still names a refusal
   `no-admin`; the `no-admin` and `no-admin-empty-list` fixture cases of rule 15 keep their results (both have
   `permissions.admin` false).
4. **Tests.** `tests/kit/test_doctor_windows.py` answer 2: a failed repository read and a refused ruleset read without
   `permissions` are `admin-unknown`; an admin refused stays `forbidden`; `no-admin` with `permissions.admin` false or
   GitHub's "admin rights" message; missing merge keys are not `no-admin` for an admin; other readers keep `no-admin`.

The `windows-tools` check (ADR-0522 decision 1) and the CODEOWNERS cleanup (decision 3) change no rule of SPEC-0006 as
written: rule 6 lists the GitHub reads only, and `windows-tools` reads none.
