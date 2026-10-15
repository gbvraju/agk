# Notes on SPEC-0008 (agk upgrade)

Date: 2026-10-15 (from `date -u`). Overnight brief 2, item D. The spec was written Draft and set Approved on the maintainers' rulings of 2026-10-15 (final commit of the pull request); nothing is implemented. No protected
path is changed by this pull request.

## What exists today (read on 2026-10-15)

- Tags: none. `git tag` is empty, `git ls-remote --tags origin` is empty, and `gh api repos/gbvraju/agk/tags` and
  `/releases` return 0 entries. SPEC-0005 rule 13 fixes tags `vX.Y.Z` for the future; no past version is tagged, not
  even 0.1.0.
- Versions in the history of `kit/manifest.json` (first-parent history of the default branch): 0.1.0, 0.2.0, 0.3.0,
  0.4.0, 0.4.1, 0.4.2, 0.5.0, 0.6.0, 0.6.1, 0.6.2 (current). Each version after 0.1.0 has exactly one commit that
  changed kit-installed paths.
- 0.1.0 has two such commits, #6 (`4a66358`, the first `kit_version`) and #7 (`86868be`, which changed the verbatim
  `Makefile` without a version bump). A target installed at "0.1.0" can hold either `Makefile`. This is why the table
  lists a set of hashes per path per version (spec rules 2, 22).
- Missing for 0.1.0, then: a tag `v0.1.0`; a single commit that defines it; the hash table; and the identity of the
  commit the sandbox was installed from (the maintainers know it; nothing in the repository records it, because there is no
  lock file).

## Decisions taken in the draft (each is a numbered rule)

- The anchor is a hash table inside the kit, a committed generated file (rule 2) (`kit/hashes.json`), not old files and not the target. It answers "was this
  file ever a released version's file?" without any old checkout, any network or `git`, and without a lock file in the
  target (rules 1-3). Alternatives not taken: compare with the kit at tag X (no tags today; needs a full clone, and the
  plugin cache may hold only the current version `(verify)`); store hashes in the target (a lock file, SPEC-0005 rule 3).
- Per-file rules as briefed, as a table (rule 7); `deleted-locally` is added for a file the user removed that the kit
  still ships (reported, not recreated).
- A conflict stops the whole run before any write (rule 8). Marked blocks are replaced inside the markers only (rule 13).
- User-owned files are never written; changed templates and new `agk.toml` keys are printed (rules 9-10).
- The command prints the `Protected classes:` line and an ADR skeleton but writes no ADR (rule 16).
- Only the `version = "..."` line of `agk.toml` is rewritten, as the last write (rule 11).
- Neither `upgrade.py` nor the table is installed into targets; they run from the kit or plugin root (rules 4, 24).

## Rulings (maintainers, 2026-10-15)

| Q | Ruling | Where in the spec |
| --- | --- | --- |
| Q-K3-50 | Accepted with a condition: `kit/hashes.json` is a committed generated file, a principle-5 exception that needs its own decision in the implementation ADR; acceptable because it is one file, in the kit only, never written into targets, and fully regenerable from history. The kit test regenerates every row from git history and compares; the kit-dev tests need `fetch-depth: 0` in CI | rule 2 |
| Q-K3-51 | Stop the whole run on a conflict, as drafted | rule 8 |
| Q-K3-52 | Yes: the upgrade rewrites exactly the `version = "..."` line of `agk.toml`, as its last write and only when every other write succeeded; every other line stays untouched | rules 9, 11, 15 |
| Q-K3-53 | No retroactive tags; the first tag is the K3 release; tagging is a maintainers' step at each release | rules 3, 22 |
| Q-K3-54 | Print only, as drafted (no `--draft-adr`) | rule 16 |
| Q-K3-55 | Yes, a bump rule: from the next release a change to any installed path needs a `kit_version` bump in the same PR, enforced by the full-history regeneration test (fails if any version other than 0.1.0 gets a second hash for a path); 0.1.0 is the one recorded exception | rule 25 |
| Q-K3-56 | Keep `REQ-014 AC5`; list the REQ-014 criteria the markers imply (below) | Tests section |

No question is open.

## REQ-014 acceptance criteria implied by the markers (for the ADR that adds REQ-014)

- AC1: the plugin manifest and the marketplace file are valid and `plugin.json` carries the kit version (`claude plugin validate .`; SPEC-0005 rules 12, 13, 19).
- AC2: the plugin has one skill per command (`/agk:<command>`), no hooks, servers, monitors or `bin/`, user-invoked writers, and no skill runs a forbidden verb (SPEC-0005 rules 7-10, 19; SPEC-0006 rule 20; SPEC-0008 rule 17).
- AC3: the repository's own checks, hooks, workflow and reviewer run with no plugin installed (SPEC-0005 rule 2).
- AC4: GitHub issues are intake only; no script or workflow reads an issue for a decision (SPEC-0005 rule 17).
- AC5: `agk upgrade` brings an init or adopt target from kit version X to the current kit, never overwriting an edited file or a user-owned file (SPEC-0008).

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-15 | SPEC-0008 drafted: upgrade anchored on a hash table in the kit; a conflict stops the run; nothing user-owned is written | no lock file (SPEC-0005 rule 3) and no tags today; criterion c of ADR-0015 | `docs/specs/0008-upgrade.md` | agent |
| 2026-10-15 | Q-K3-50 to Q-K3-56 ruled (hash table accepted as a principle-5 exception with full-history regeneration; version line rewritten last; no retroactive tags; bump rule); SPEC-0008 Approved | maintainers' rulings | `docs/runs/spec-0008-notes.md`, SPEC-0008 | reviewer |
