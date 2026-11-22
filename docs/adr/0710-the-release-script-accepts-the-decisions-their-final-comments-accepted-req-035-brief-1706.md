# ADR-0710: The release script accepts the decisions their Final comments accepted (REQ-035)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0277, ADR-0510, ADR-0575, SPEC-0021, SPEC-0028, brief #1706, note #1197, plan #661
- Requirements: REQ-035

Protected classes this pull request changes: `scripts/agk/` (`changelog_fragments.py`, `check_adrs.py`), `kit/`
(`templates/runtime/builder.txt`), `tests/kit/` (`test_runtime_templates.py`) and `tests/kit_dev/`
(`test_changelog_fragments.py`). `kit/hashes.json` is not edited by hand.

## Context

SPEC-0021 rule 3a (ADR-0277) keeps a decision file at `Proposed` after the merge whose Final comment accepted it, and
SPEC-0028 rule 4 has the release pull request set its Status line to `Accepted`, changing nothing else. No script
wrote those flips: the 0.64.0 release made 145 of them by hand (note #1197), and a temporary RELEASE EXCEPTION in the
builder's task text (brief #1202, ADR-0510) let a session edit Status lines in a release pull request. On 2026-11-22,
150 decision files on main read `Proposed`. `check_adrs.py --pending` already lists the files to flip, and
`check_release.py` already checks the result.

## Decision

1. `python3 scripts/agk/changelog_fragments.py accept --comments FILE [--base REF]` (kit-only) takes the files that
   `check_adrs.pending_paths` returns, the same list `check_adrs.py --pending` prints (imported, not copied), and in
   each replaces the one Status line with `- Status: Accepted`, byte for byte otherwise (line ends kept). It prints
   `accepted: <path>` per file and `accept: <n> decisions`, or `accept: none pending`.
2. Without `--comments` while a record exists it refuses as `--pending` does, naming the option, never a value. Every
   file is read before the first write, so any refusal writes nothing.
3. The release pull request runs `accept` beside `gather`; `check_release.py` is unchanged and checks the result.
4. The RELEASE EXCEPTION paragraph of `kit/templates/runtime/builder.txt` becomes one line under the kit-only
   section: in a release pull request the builder runs `accept`; FINAL LINES holds, and no session edits a Status line.
5. Every setting flips the same set: `pr_mode` flow and strict, `execution` hosted and local, `review_mode` solo and
   team. Personal mode and a project using AGK are not affected: the script is not installed. No new `agk.toml` key.

## Consequences

A release flips its decisions with one command, and no session text lets a session edit a Status line. The merger,
SPEC-0021 rule 3a and `check_release.py` are unchanged. Option 1 of note #1197 (the merger flips at merge) is not
taken: it would reverse rule 3a, touch `merge_cleared.py` and add a commit and a CI run to every merge with a Final
line.

## Residual

None (2026-11-22).
