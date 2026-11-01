# Proposed spec amendments 108 (SPEC-0025, SPEC-0034; REQ-032, REQ-041)

Date: 2026-11-01 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for ADR-0246
(brief #387), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0025-a-team-can-run-independent-pull-requests-in-parallel-without.md` and
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`. The number 108 is the next free one on the
default branch when the brief was taken (Q-387-1). It needs a person's `Approve: SPEC-0034` on the pull request; no session posts
it. No rule changes what it says and no safety rule weakens: the rules move, and a merged number stays as a pointer line.

1. **SPEC-0034, a new section of `## Rules`: "Independent pull requests (from SPEC-0025)".** After rule 14, rules 17 to 27 are
   SPEC-0025 rules 1 to 11, rule n of SPEC-0025 becoming rule n + 16, their text unchanged word for word. Numbers 15 and 16 stay
   for the new rules that amendments 88 (`session.py plan`) and 89 (`/agk:launch`) propose. A paragraph above the rules says
   where they came from and that, inside rules 17 to 27, "rule n" with no spec named means the SPEC-0025 number (rule n + 16
   here), and "parts 1 to 5", "part (a)" to "(c)" and "answer 7" are those of SPEC-0025.
2. **SPEC-0034 rule 24 (SPEC-0025 rule 8), the release model.** Its first two sentences are unchanged. Its last sentence, "The
   release model in answer 7 (...) is a later intake of this repository only and is not built here.", becomes the text that
   SPEC-0028 gave it by amendment 50, item 2: "The release model, as SPEC-0028 amended it (amendment 50, item 2): Kit build pull
   requests do not bump the version in flow mode; one release pull request bumps `agk.toml`, `kit/manifest.json` and the plugin
   together, moves the Unreleased lines of `CHANGELOG.md` under the new version and adds the new row of `kit/hashes.json`;
   `scripts/agk/check_release.py` checks it (SPEC-0028 rules 4 and 5)."
3. **SPEC-0025 `## Rules`.** SPEC-0025 keeps its number, its title, its status, its opening paragraphs and its `## Tests`,
   `## Proof`, `## Residual` and `## Open questions` sections as they are. Its rules are replaced by one sentence that says where
   they went and one line per old rule, `N. Now SPEC-0034 rule M.`, for N from 1 to 11 and M = N + 16. Any script, test, ADR,
   amendment or verdict that cites `SPEC-0025 rule N` still resolves, through its pointer line.
4. **Earlier amendments of SPEC-0025.** Amendments 94 (rule 5) and 97 (rule 4) and item 3 of amendment 50 (rule 6) stay as they
   were written and are not applied by this one (Q-387-2); they now name SPEC-0034 rules 21, 20 and 22 through the pointer lines.
5. **Tests.** `tests/kit/test_core_parallel_specs.py`: each rule of SPEC-0025 is in SPEC-0034 after the change, word for word
   (pinned by digest and, where the history has it, checked against SPEC-0025 before the fold); rule 24 carries amendment 50
   item 2; SPEC-0034 keeps rules 1 to 14 and leaves 15 and 16 free; each pointer line names a rule that exists; both specs stay
   Approved and keep their other sections; `check_specs.py` passes the change with this file and fails it without; the rules
   that scripts cite resolve. Its marker is `REQ-041`.
