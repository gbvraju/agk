# Proposed spec amendments 213 (SPEC-0007; REQ-012)

Date: 2026-11-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0687 (brief #1618), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0007-metrics.md`.
Brief #1618 reserved amendment 213. This file proposes the lines and does not edit the spec. They are applied word for
word, on a person's `Approve: SPEC-0007`; no session posts it.

## Why

Rule 27 lists the figures of `measures.py`. Brief #1618 asks for one measured solo trial from AGK's own records: speed
(brief to merge, the owner's wait, park time), quality (fix lists, red spells of the default branch, reverts) and cost
(tokens per merged pull request by tier). The owner's wait of rule 27 counts only a `Question:` for the maintainers, not
the conductor's `Owner needed:`, and no figure reads park time, the red-branch issues, reverts or a tier.

## Items

1. **Rule 29 (new),** after rule 28 and before `## Tests`:

   ```
   29. **The trial table.** `measures.py ... --trial` adds one `trial` row (text and `--json`) over the same reads and
       the same range: `merged` (pull requests merged in the range); `lead_hours_median` and `lead_hours_p90` (nearest
       rank); `owner_items` and `owner_wait_minutes`, each item `session.open_owner_items` opens on a feature's brief
       or pull request (a `Question:` for the maintainers or an `Owner needed:` by a listed verdict author) up to the
       answer that closes it, else the finishing merge; `park_minutes` (`Parked-by: wait` to `Unparked-by:`, an open
       park up to the end of `--to`, marked `(<n> open)`); `cleared_to_merge_minutes` (median, the last clearing
       verdict to the merge); `fix_rounds_per_merged`; `red_spells` and `red_hours` (the issues titled `The default
       branch is red` that overlap the range, opened to closed, cut to the range); `reverts` (merged pull requests
       whose merge commit, read by local git, starts `Revert "`); `confirmations` (in solo mode the `Confirmed:` lines
       of the one person, else `none (team mode)`); `tokens_per_merged` and `tokens_per_merged_<tier>`, the tier being
       the configured tier of the brief's kind (`session.kind_of`, `[models]`), labelled `(configured)`, and
       `unknown` for a pull request tied to no brief. With no merged pull request a per-merged figure is `unknown`,
       never 0. Personal mode prints `none (personal mode)` for the owner, park, red and confirmation figures. No cost
       is estimated. `--trial` takes no value and is given once, else it is refused naming the option.
   ```

2. **`## Tests`,** one line after the line of rule 24:

   ```
   - Rule 29: `tests/kit/test_measures_trial.py`, marker `REQ-012 AC1`.
   ```

No existing rule changes.
