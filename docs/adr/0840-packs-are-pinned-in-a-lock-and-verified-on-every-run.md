# ADR-0840: Packs are added on a recorded yes, pinned in a lock and verified on every run

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2033, 2026-11-27T07:25:55Z)
- Related: ADR-0837, ADR-0838, ADR-0839, ADR-0171, SPEC-0077, SPEC-0029, REQ-084, brief #2033, brief #1842, plan #661
- Requirements: REQ-084

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0077 (Approved, ADR-0837) rule 14 build (c) asks for rule 4: `packs.py add|verify|update --check`, a lock,
`config/packs.lock`, that records every file of every pack in use with its SHA-256, and `verify` inside the existing
`playbooks` step (`Q-S0077-12`). Build (a) (ADR-0838) checks a pack's manifest and its listed files; build (b)
(ADR-0839) reads the packs of `[packs] use`. Nothing pinned a pack's files outside its own manifest, and nothing added
a pack. ADR-0171 is the form to copy: a version and a hash, checked on every use, never skipped.

## Decision

1. **The lock.** `config/packs.lock` is TOML: one `[[pack]]` per pack with `id`, `version`, `sha256` (the hash of its
   `agk-pack.toml`) and `files = [{ path, sha256 }]`, every file of the pack's folder, the manifest included.
2. **verify (offline).** `packs.verify(root, use)` fails, each as `rule 4: config/packs/<id>: <what> (key|setting: ...)`
   and never a value: a locked file whose hash differs or that is missing (`files`), the manifest's hash against the
   entry's (`sha256`), a file in the folder the lock does not hold (`files`), a lock entry whose folder is missing
   (`pack`), a locked pack `[packs] use` does not list and a use entry the lock does not hold or whose version or hash
   differs from it (`packs.use`). A lock that is not TOML or out of form is one line naming `config/packs.lock`.
   `check_packs.findings` adds the lines, so they run in the `playbooks` step in CI, `prepush.py` and
   `make -f agk.mk agk-governance`, with no new step. A refused `[packs]` table (build (a)'s `rule 12:` line) skips
   only the use comparisons.
3. **add (on a yes).** `packs.py add SOURCE [--tag TAG] --said FILE --at TIME [--by LOGIN]` reads the person's words
   through `steward_owner.yes_of` and `steward_voice.is_yes`, as `research` does, and records the yes or the no as a
   `Setup` note through `steward.record` (the sidecar's file in personal mode, nothing posted). Only on a yes is the
   source read: a folder, or a public `https` git URL with an exact version tag, cloned at depth 1 (`Q-PC-1`). The
   pack is staged in a temporary folder, `check_packs.problems` runs on it, and only then is it copied to
   `config/packs/<id>/` and the lock written. It prints the `[packs] use` entry and never writes `agk.toml`: that
   line and its ADR are the person's protected change (`Q-PC-2`, `Q-S0077-10`). A builder session is refused
   (`AGK_AGENT` or `AGK_ROLE` `builder`); the steward runs it on the person's yes.
4. **update --check (on a yes).** It lists each locked pack's newer exact tags at its manifest's `source` and changes
   nothing; a real update is `add` of the new tag in its own pull request with its ADR (rule 8).
5. **Wiring.** The `[testing]` map of `packs.py` and `check_packs.py` names `tests/kit/test_packs_lock.py`.

## Consequences

A pack file changed by one byte fails governance offline; for a pack in use, the playbooks step's resolver
(ADR-0839) already stops at the first `check_packs` problem, so the lock's own lines show where the manifest and the
use entry were changed together and the lock was not. No workflow, ruleset, required check, label, `agk.mk` or
`governance_map.CHECKS` changes. A test asserts that no other kit script writes the lock or copies under
`config/packs/`.

## Residual

The adoption scans of rule 6 (instruction scan, licence, size, kinds of file) before the copy are build (d); the
`kit` range and `[packs] trust` at `add` and `verify` are rule 6's and wait for it. `update --check`'s change notes
and the `withdrawn` mark (rule 8) are build (i).
