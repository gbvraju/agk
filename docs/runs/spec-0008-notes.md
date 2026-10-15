# Notes on SPEC-0008 (agk upgrade)

Date: 2026-10-15 (from `date -u`). Overnight brief 2, item D. The spec is Draft; nothing is implemented. No protected
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

- The anchor is a hash table inside the kit (`kit/hashes.json`), not old files and not the target. It answers "was this
  file ever a released version's file?" without any old checkout, any network or `git`, and without a lock file in the
  target (rules 1-3). Alternatives not taken: compare with the kit at tag X (no tags today; needs a full clone, and the
  plugin cache may hold only the current version `(verify)`); store hashes in the target (a lock file, SPEC-0005 rule 3).
- Per-file rules as briefed, as a table (rule 7); `deleted-locally` is added for a file the user removed that the kit
  still ships (reported, not recreated).
- A conflict stops the whole run before any write (rule 8). Marked blocks are replaced inside the markers only (rule 13).
- User-owned files are never written; changed templates and new `agk.toml` keys are printed (rules 9-10).
- The command prints the `Protected classes:` line and an ADR skeleton but writes no ADR (rule 16).
- Neither `upgrade.py` nor the table is installed into targets; they run from the kit or plugin root (rules 4, 24).

## Open

- **Q-K3-50.** Is a hash table in the kit acceptable as the one source of truth for "what X was"? It adds a kit file to
  maintain for every release (a kit test enforces the row). The alternative is tags plus a full clone.
- **Q-K3-51.** A single locally edited file stops the whole upgrade (draft). Should the run instead apply the other files
  and report the edited ones? The brief says "stop and report, never overwrite", read as stop.
- **Q-K3-52.** The version stamp is printed, not written, because `agk.toml` values are never rewritten. Without it
  the doctor reports `kit-version` after every upgrade. May the upgrade rewrite exactly the line `version = "..."`?
- **Q-K3-53.** Create tags `v0.1.0` to `v0.6.2` for the past versions (one commit each; 0.1.0 needs a choice between
  `4a66358` and `86868be`)? Tags are a maintainer action (SPEC-0005 rule 13); the draft does not need them.
- **Q-K3-54.** Should the command write a Proposed ADR for the protected classes (`--draft-adr`), or only print the
  line and skeleton (draft)? Writing needs the next ADR number of the target and a decision text that is theirs.
- **Q-K3-55.** The kit changed `Makefile` within 0.1.0 without a bump. Should a rule require a version bump for any
  change to an installed path (a kit test could enforce it from the next release)?
- **Q-K3-56.** The marker `AC5` of `REQ-014` in the test list is proposed; REQ-014 is not yet in
  `docs/requirements.md`. The numbering is for the ADR that adds REQ-014 to settle.

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-15 | SPEC-0008 drafted: upgrade anchored on a hash table in the kit; a conflict stops the run; nothing user-owned is written | no lock file (SPEC-0005 rule 3) and no tags today; criterion c of ADR-0015 | `docs/specs/0008-upgrade.md` | agent |
| 2026-10-15 | Q-K3-50 to Q-K3-56 opened | table as anchor, partial apply, version stamp, tags, ADR drafting, bump rule, marker | `docs/runs/spec-0008-notes.md` | agent |
