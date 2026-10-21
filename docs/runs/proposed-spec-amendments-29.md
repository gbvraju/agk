# Proposed spec amendments 29 (SPEC-0012 rules 2 and 11)

Date: 2026-10-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0062. The path: `docs/specs/0012-intake.md`.

1. **SPEC-0012 rule 2, the requirement id.** The rule says `req` is the next number after the highest `### REQ-nnn` heading. In a project the seeded requirements are `REQ-001`..`REQ-003` and
   `REQ-001`..`REQ-099` are reserved for the kit (SPEC-0001 rule 11), so "highest + 1" gave a project `REQ-004`, a kit id, and its intake could not pass. New wording: "`req` is the next number after
   the highest `### REQ-nnn` heading of `docs/requirements.md`, and in a project (`agk.toml` `mode` `init` or `adopt`) not below `REQ-101`, because `REQ-001`..`REQ-099` are the kit's (SPEC-0001 rule 11)".
   In the kit's own repository (no `mode`) the rule is unchanged.
2. **SPEC-0012 rule 11, check C1.** The row says the requirement is the next free `REQ`; it now adds "(in a project not below `REQ-101`)". The check uses the same function as rule 2.
