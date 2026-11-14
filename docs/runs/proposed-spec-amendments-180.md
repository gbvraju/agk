# Proposed spec amendments 180 (SPEC-0008; REQ-014)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0521 (brief #1222), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0008-upgrade.md`.
Brief #1222 reserved ADR-0521; the conductor reserved amendment 180 in its verdict on #1225 (answer to Q-1222-1). This
pull request does not edit the spec; the maintainers apply the lines if they approve them.

The sentence (brief #1222): "A kit upgrade arrives as one ready pull request: the files, the ADR with every section and
the body, so the owner only reviews and merges."

## What is on the default branch today

Read in the code by this session on `origin/main`: `scripts/agk/upgrade.py` prints the target's `Protected classes:` line
and an ADR skeleton (title, `Status: Proposed`, the fields with a `YYYY-MM-DD` date, `## Context` and `## Decision`
only) and writes no ADR; `check_adrs.py` fails that skeleton on `## Consequences` and `## Residual`. `/agk:upgrade` runs
`--dry-run`, asks, runs the upgrade on the current branch and prints the body with `--next-steps` after a person wrote
the ADR.

## Items

1. **Rule 16, the sentence "It writes no ADR: the number, the reasons and the decision are the maintainers', and there is
   no `--draft-adr`." becomes:** "With `--write-adr [--date D]`, after a written upgrade that changed anything, it writes
   the upgrade's ADR `docs/adr/<next>-upgrade-agk-to-<version>.md` (one past the highest numbered ADR file; the version's
   characters outside `a-z0-9` become `-`), titled `Upgrade agk from X to Y`, `Status: Proposed`, Date from `--date` or
   today in UTC, Deciders `maintainers`, Related `none`, Requirements `REQ-001`, the `Protected classes:` line and the four
   sections `check_adrs.py` requires; it keeps, and names, an ADR already titled for the same target version; an upgrade
   with no change writes none; with `--dry-run` it names the file and writes nothing; a malformed `--date` is refused
   before anything is written. Accepting that ADR stays the maintainers' decision. Without `--write-adr` it writes no ADR
   and prints the skeleton, which carries the four section headings."
2. **Rule 17, the sentence "It does not commit, push or open the pull request, and does not write the ADR." becomes:**
   "After the person agrees it creates `upgrade/agk-<version>` from `origin/<default branch>` before anything is written
   (and stops on a dirty tree or an existing branch), runs the upgrade with `--write-adr`, runs the local gate (`make
   lint`, `make governance`), prints the commit message and the body that the target's `check_pr_body.py` passed
   (`--next-steps`), and says the upgrade is held for the owner's merge (`merge_cleared.py` holds a release, its rule 5).
   It does not commit, push, open or merge the pull request, and never sets the ADR `Accepted`."
3. **No other change.** Rules 14, 15 and 18 to 23, the summary lines of rule 16 and the `--next-steps` body stay as they
   are.
4. **Tests.** `tests/kit/test_upgrade_adr.py` (ADR-0521's Consequences); `tests/kit_dev/test_distribution.py` keeps the
   skill's first call `upgrade.py . --dry-run`.
