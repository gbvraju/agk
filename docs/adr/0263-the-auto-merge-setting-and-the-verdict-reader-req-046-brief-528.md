# ADR-0263: The auto-merge setting and the verdict reader (REQ-046, brief 528)

- Status: Accepted
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0261, SPEC-0039
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `kit/`, `agk.toml`, `tests/kit/`

## Context

SPEC-0039 (Approved on #519, ADR-0261) splits the guarded merge command into the builds of its rule
12. This is build (a): the setting of rule 1 and the verdict reader of rule 3, with no merge. The
pilot's hand-written merge loop lost a `--jq` filter to Windows shell quoting, would have read a
multi-line fix list as cleared and could not tell whose verdict it read (#498). This ADR number was
reserved for brief #528 by the conductor (the field note on #528).

## Decision

1. `scripts/agk/merge_cleared.py` is new and installed (listed in `verbatim` of `kit/manifest.json`,
   sorted). `merge_cleared.py --pr <n> --sha <40-character lower-case sha>`, exactly those two
   options in that order, prints one line `merge-cleared #<n> <sha12>: ...` and exits 0 for
   `cleared (merge not yet built)`, 3 for `held: <reason>` and for `refused: head moved`, 1 for any
   other `refused: <reason>` and 4 when GitHub cannot answer one read five times in a row. A
   malformed command line prints `merge-cleared #? ?: refused: usage ...` before any read. Reasons
   name a rule, a setting or a path class, never a value.
2. The setting is read only from `agk.toml` as committed on the default branch of the remote, as last
   fetched: `refs/remotes/origin/HEAD` when it is set, else `refs/remotes/origin/main`, and refused
   unless that file's `default_branch` (`main` when unset) names the same branch. The work tree and a
   pull request's head are never read. Merging is possible only when `[flow] auto_merge` is the TOML
   boolean `true` and `auto_merge_method` is exactly `"squash"`; absent or `false` is off, and every
   other value, a method other than `squash`, or `true` without a method is refused naming the
   setting. Nothing depends on `pr_mode`, `review_mode` or `execution`. With the setting not on, the
   command reads nothing from GitHub. `auto_merge_setting` is the one reading, which `doctor.py`
   uses.
3. The verdict is the comment with the latest `created_at` (then the highest id) whose first line
   starts `Verdict:`. It clears only when that first line equals `Verdict: cleared <sha>`, with the
   `--sha` given, which also equals the pull request's head as GitHub reports it. A head that differs
   from `--sha` is `refused: head moved`; a missing verdict, or one of any other form, is `held`.
4. `scripts/agk/reviewers.py` gains `conductors_of`, the optional top-level list
   `conductor_accounts` (absent or empty is none), refusing, by the setting's name only, a list that
   is not user handles, the placeholder `@REPLACE-ME` or an entry also in `spec_approvers`. The
   command reads it from `config/reviewers.yaml` on the same default-branch commit as the setting;
   with it set, a cleared verdict by an author not listed is `held`. `config/reviewers.yaml` is not
   changed.
5. Reads are `gh api --method GET <REST path>` argument lists with no shell and no `--jq`; the JSON
   is parsed by the script, the comments page by page (`per_page=100`). A failed read, or an answer
   of the wrong shape, is retried and never taken as an empty list or a pass.
6. `scripts/agk/doctor.py` gains the check `auto-merge-setting` (severity `error`), printing
   `auto-merge: off` or `auto-merge: on, method squash` from the checkout's `agk.toml`, and failing a
   malformed value by the setting's name.
7. `kit/templates/agk.toml` and this repository's `agk.toml` carry the two keys commented, with
   `auto_merge = false`. This repository does not turn the setting on.
8. In this build the command makes no merge call, takes no lock, writes no file and pushes nothing.
   `docs/guides/reference.md` is not changed: `doctor.py` imports the script, which the reference
   check accepts, and the guide of build (e) describes the command.

## Consequences

The verdict reader that builds (b) to (e) extend exists and is tested on saved responses, on POSIX
and on a fake Windows platform. A conductor may run the command already; it only reports.

## Residual

- 2026-11-04: `doctor.py` reads the setting from the checkout, as its other lines do, while the
  command reads the default branch of the remote (Q-528-1); a checkout of a branch may show a
  different line from what the command would do (due 2026-12-31).
