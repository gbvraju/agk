# ADR-0521: A kit upgrade arrives as one ready pull request with a complete ADR

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0008 rules 16 and 17, ADR-0018, brief #273, brief #1222, plan #661
- Requirements: REQ-014

## Context

SPEC-0008 rule 16 has `agk upgrade` print the target's protected classes and an ADR skeleton (title, `Status: Proposed`,
empty Context and Decision) and write no ADR; rule 17 has `/agk:upgrade` write no ADR either, and it runs on whatever
branch the target is on. The skeleton lacks `## Consequences` and `## Residual`, which `check_adrs.py` requires
(`SECTIONS`), and its date is `YYYY-MM-DD`, so a pasted skeleton fails governance until a person completes it. In a
customer trial and a rehearsal the upgrade took several manual rounds. The owner asks that an upgrade arrive as one ready
pull request: the files, the ADR with every section and the body, so that the owner only reviews and merges (brief #1222).

## Decision

1. `scripts/agk/upgrade.py TARGET --write-adr [--date D]`, after a written upgrade that changed anything, writes the
   upgrade's ADR `docs/adr/<next>-upgrade-agk-to-<version>.md`: the number is one past the highest numbered file in
   `docs/adr/`, the version's characters outside `a-z0-9` become `-` (the file name `check_adrs.py` accepts), the title is
   `Upgrade agk from X to Y` (the one `--next-steps` reads), Status `Proposed`, Date from `--date` or today in UTC,
   Deciders `maintainers`, Related `none`, Requirements `REQ-001` (protected paths change only with an ADR, which every
   init and adopt install lists), a `Protected classes:` line naming in backticks each class the upgrade changed (the
   classes of the `Protected classes:` line it prints), and the four sections. An ADR already titled for this
   upgrade's target version is kept and named (`adr: kept ...`); an upgrade with no change writes none; with `--dry-run`
   it names the file (`adr: would write ...`) and writes nothing; a malformed `--date` is refused before anything is
   written. Without `--write-adr` nothing changes but the skeleton, which now carries the four section headings and
   says that `--write-adr` writes it.
2. `/agk:upgrade` previews, then, after the person agrees, creates `upgrade/agk-<version>` from
   `origin/<default branch>` before anything is written (and stops on a dirty tree or an existing branch), runs the
   upgrade with `--write-adr`, runs the local gate (`make lint`, `make governance`), prints the commit message and the
   body that the target's `check_pr_body.py` passed (`--next-steps`), and says the upgrade is held for the owner's merge:
   it raises `version` in `agk.toml`, which `merge_cleared.py` holds as a release (its rule 5). The skill still never
   commits, pushes or merges, and never sets an ADR `Accepted`.
3. This decision replaces, for SPEC-0008, the sentences "It writes no ADR ... there is no `--draft-adr`" of rule 16 and
   "and does not write the ADR" of rule 17; the spec's text is the reviewers' to amend (principle 6).

## Consequences

An upgrade pull request carries a Proposed ADR that passes `check_adrs.py` and names each class that the target's
`check_protected_changes` asks for, so governance is green without a hand-written ADR; the maintainers still decide by
accepting it. Protected path classes changed: `scripts/agk/` (`upgrade.py`), `skills/` (`skills/upgrade/SKILL.md`) and
`tests/kit/` (`test_upgrade_adr.py`, new) and `agk.toml` (the new test added to the `[[testing.map]]` entries of
`upgrade.py`, `check_adrs.py`, `check_pr_body.py` and `merge_cleared.py`, the scripts it imports or names). No workflow,
ruleset, `config/` or `.claude/` change.

## Residual

- 2026-11-14: SPEC-0008 rules 16 and 17 still say the upgrade writes no ADR; the amendment that brings them in line
  with this decision needs a reserved amendment number (Q-1222-1), due 2026-11-30.
