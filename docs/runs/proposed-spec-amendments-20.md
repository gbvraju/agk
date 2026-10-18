# Proposed spec amendments 20 (SPEC-0008; found while building E1, the upgrade that removes unmodified kit files)

Date: 2026-10-18 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The path:
`docs/specs/0008-upgrade.md`.

**Applied by ADR-0032** (2026-10-18) on the maintainers' ruling recorded as the ADR-0031 residual: upgrade deletes a path the new kit
no longer ships only when its content matches a hash of that path in `kit/hashes.json` history (an unmodified kit file); otherwise it
reports the path and leaves it.

## SPEC-0008 (`docs/specs/0008-upgrade.md`)

1. **Rule 7, the row `removed-in-kit`.** "none; never deleted" becomes: deleted only when the path is a regular file whose bytes equal
   a copy the table lists for that path in any release; the line says `(unmodified, deleted)`. Otherwise nothing is written and the line
   says `(modified, kept)`. A path that is still shipped as an optional file (the experimental reviewer), a path the adopt install
   leaves to the project (its skip list and marked blocks), a symlink and a non-file are kept, with a reason in the line.
2. **Rule 14, the dry run.** The lines are the same as in the real run; the summary says how many files would change and how many would
   be deleted.
3. **Rule 15, order.** The deletions follow the writes, in sorted path order, then the directories they emptied; `agk.toml`'s version
   line stays the last write.
