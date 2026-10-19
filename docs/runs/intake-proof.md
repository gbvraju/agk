# Intake proof: this repository (SPEC-0012 rule 17)

Date: 2026-10-19 (from `date -u`). The one real intake in this repository: the maintainers gave a sentence, a session ran the `/agk:spec` sentence form exactly as
`skills/spec/SKILL.md` says, the session committed and opened the pull request with the body that `intake.py next-steps` printed, and the maintainers reviewed and merged it. The pilot's
intake (from the issue form, by the pilot's own session) is a later brief and is not recorded here.

## The sentence (verbatim, 129 characters, one sentence)

> The weekly product report names the kit version it was rendered with in its footer, so a reader can tell which rules produced it.

## The run

| Step of the skill | What happened |
| --- | --- |
| 1. Clean work tree; fetch | the work tree was clean; `git fetch origin main` |
| 2. `intake.py ids --sentence ...` | `{"req": "REQ-021", "spec": "0014", "adr": "0045", "slug": "the-weekly-product-report-names-the-kit-version-it-was-rende"}` (read from `origin/main` at `33b3aea`) |
| 3. Branch | `git switch -c intake/req-021-the-weekly-product-report-names-the-kit-version-it-was-rende origin/main` |
| 4. Questions (at most three, one message, before any file was written) | two, below |
| 5. `intake.py stub --req REQ-021 --title "The weekly product report footer names the kit version" --sentence ...` | `created docs/adr/0045-add-req-021-the-weekly-product-report-names-the-kit-version-it-was-rende.md` |
| 6. The two model-written pieces | the section of REQ-021 appended to `docs/requirements.md` (3 criteria, one negative) and `docs/specs/0014-the-weekly-product-report-names-the-kit-version-it-was-rende.md` (Draft, one open question `Q-S0014-1`) |
| 7. `intake.py check`, then `make governance` | both passed on the first try (below) |
| 8. `intake.py next-steps` | printed the commit message, the push command and the body used for the pull request (below) |

### The two questions and the maintainers' answers (verbatim)

1. *Where does the footer's kit version come from? The renderer is a pure function of the facts file and reads no other file, so the facts would have to carry it.*
   Answer: "Option 1. Read the version the same way upgrade.py reads the installed stamp (agk.toml, or the legacy [tool.agk] in pyproject.toml), so there is one reader of the
   installed version, not two. A missing or unreadable version prints unknown" (Option 1 was: the facts carry it from `agk.toml`).
2. *Is the version number alone enough for "a reader can tell which rules produced it"?*
   Answer: "Option 1. The release notes the reader looks the number up in don't exist as one file today. Record that as an open question Q-S in the spec, not a fix in this
   intake" (Option 1 was: the number alone). It is `Q-S0014-1` in the spec.

The answers became rules 1 to 3 of the spec and the open question; the session did not guess an answer for anything left open.

### `intake.py check --base origin/main`, on the three files

```
ok intake
```

### `make governance`, on the three files

```
ok protected-changes (protected change covered by an ADR)
ok requirements (21 requirements)
ok adrs (45 ADRs)
specs: no pull request body; the lifecycle rule for Advances is skipped
ok specs
ok neutrality (0 tokens)
ok build-state
ok kit-tests (8 checks, 29 test files)
ok reviewers
ok reviewers (.github/CODEOWNERS matches)
```

### `intake.py next-steps --base origin/main --date 2026-10-19`

```
Commit message:

intake: add REQ-021 The weekly product report footer names the kit version

Push command:

git push -u origin intake/req-021-the-weekly-product-report-names-the-kit-version-it-was-rende

Open the pull request from that branch into the default branch with this body.

Pull request body:

Advances: REQ-021
Build-state row: 2026-10-19 REQ-021 proposed (planned), intake only
Decisions taken: none; the sentence became a requirement, a Draft spec and an ADR stub
Questions: see `## Open questions` of the spec
Verified: `python3 scripts/agk/intake.py check` printed `ok intake`

The checks cannot tell that the criteria are the right ones, that they say what you
meant, or that the spec can be built. That is the review of the pull request.
```

## The pull request

PR 84: https://github.com/gbvraju/agk/pull/84, branch `intake/req-021-the-weekly-product-report-names-the-kit-version-it-was-rende`, opened with the body printed above (the printed lines, a
sentence naming the run, and the attribution lines). It was **exactly the three files of rule 4**: the first head (`05a7ffc`) had the three files, `make test` on it `1406 passed, 3 skipped in
586.10s` and `1406 passed, 3 skipped in 525.87s`; the second head (`7a90b3e`) added this record as a fourth file; the final head, `2cbd648`, deleted it again (3 commits), with `intake.py check
--base origin/main` printing `ok intake`, `make governance` 9 checks ok and `make test` `1406 passed, 3 skipped in 710.49s` and `1406 passed, 3 skipped in 521.85s`. The pull request
was merged with the ADR `Proposed` and the spec `Draft` (SPEC-0012 rule 14).

## Verdict

- Verdict lines on the pull request: one comment, `Verdict: cleared 2cbd648`, 2026-10-19T10:41:46Z, https://github.com/gbvraju/agk/pull/84#issuecomment-6265345548 (posted by the session
  on the maintainers' instruction).
- The earlier verdict, on head `7a90b3e`, was a fix list with one item (remove this record from the pull request: rule 4 says an intake pull request is exactly three files; the maintainers
  said the fourth file was their instruction's fault). It was given to the session in the conversation and was not posted as a comment on the pull request, so it is not a line there.
- Outcome: **merged**, 2026-10-19.

## The merge

Merge commit on `main`: `f019bb61452e23c8bd86d401606841912753705e`, `intake: add REQ-021 The weekly product report footer names the kit version (#84)` (a squash merge; the parent is
`33b3aea`, the merge of PR 83).

## What the facts show on `main` after the merge

`python3 scripts/agk/facts.py --today 2026-10-19 --repo gbvraju/agk .` run in a checkout of `f019bb6` (`dirty` false), read:

| Section | Entry | Value |
| --- | --- | --- |
| `requirements` | REQ-021 "The weekly product report footer names the kit version" | status `planned` |
| `specs` | SPEC-0014, `docs/specs/0014-the-weekly-product-report-names-the-kit-version-it-was-rende.md` | status `Draft`, `requirements` `["REQ-021"]` |
| `adrs` | ADR-0045, `docs/adr/0045-add-req-021-the-weekly-product-report-names-the-kit-version-it-was-rende.md` | status `Proposed` |
| `questions` | Q-S0014-1 | `ruled` false, `named_in_log` false, `open_in` `["docs/specs/0014-…-rende.md"]` |

`python3 scripts/agk/product_report.py --facts <that document> --today 2026-10-19 --inbox` lists, as waiting: `Draft spec SPEC-0014 "The weekly product report footer names the kit version" waits for
approval`, `Proposed ADR-0045 "Add REQ-021: The weekly product report footer names the kit version" waits for a decision` and `Question Q-S0014-1 is waiting`, each with a link at the merge
commit. Before the merge, on the intake branch, none of them was in the facts of `main` (the test of SPEC-0012 rule 14, `test_intake.py`, shows it on a fixture; this is the same on the real
repository). Merging approved the requirement as `planned`; the spec stays `Draft` until `Q-S0014-1` is ruled.

## Observations (none was changed in this record)

- **The slug is cut at 60 characters**, so the file names and the branch end in `rende` (the word "rendered" cut). SPEC-0012 rule 2 takes the slug rule of `new_spec.py`. A small fix later:
  cut at a word boundary (a change to `new_spec.py` and `intake.py`, and the spec's rule 2).
- **`intake.py check` allows exactly three files** (rule 4). Adding this record to the same pull request (rule 17 as written asks for the record in this repository) made `check` fail C2; the
  maintainers ruled the pull request must be the three files and that the record lands in its own docs pull request. Rule 17's wording ("the record is in `docs/runs/`") is satisfied that way.
- **`Q-S0014-1` is also named in `docs/specs/0012-intake.md`**, as the example id of rule 10 (`Q-S0014-1`, "built from the spec number that rule 2 allocated"). The facts list both files for the
  question but `open_in` only the Draft spec 0014, because SPEC-0012 is Approved and is not an open place; the inbox shows one waiting question. If the example id and a real id ever clash in a
  way that matters, rule 10's example should use a number no spec has.
- **The skill's step 4 asks the questions after the branch is cut.** No file existed yet, so nothing was written before the answers; the order of the skill is workable.
- **The pull request touched `docs/` only**, so lifecycle rule a (SPEC-0013 rule 23) did not apply; rule b did not apply (the spec is Draft).
- **The implementation of REQ-021** (the `kit_version` fact, the shared reader, the footer line) is not built; it is a later brief.
