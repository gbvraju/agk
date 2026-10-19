# Intake proof: this repository (SPEC-0012 rule 17)

Date: 2026-10-19 (from `date -u`). The one real intake in this repository: the maintainers gave a sentence, a session ran the `/agk:spec` sentence form exactly as
`skills/spec/SKILL.md` says, the session committed and opened the pull request with the body that `intake.py next-steps` printed, and the maintainers review and merge it. The pilot's
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

PR 84: https://github.com/gbvraju/agk/pull/84, branch `intake/req-021-the-weekly-product-report-names-the-kit-version-it-was-rende`, opened with the body above (the printed lines, a
sentence naming this record, and the attribution lines). `make test` on the head of the three files: `1406 passed, 3 skipped in 586.10s` and `1406 passed, 3 skipped in 525.87s`.

## Verdict

To be recorded by the maintainers after the review: the verdict comment, and merged or not.

## Observations (what the run showed; none was changed here)

- The slug is cut at 60 characters, so the file and branch names end in `rende` (the word "rendered" cut). The rule is SPEC-0012 rule 2 (the rule of `new_spec.py`); a long sentence
  gives an odd name. A residual, not a defect of the checks.
- `intake.py check` allows exactly three files (rule 4). This record is a fourth file of the same pull request (rule 17 asks for it), so `check` run now on the whole pull request
  fails C2; it was run, as the skill says, on the three files before this record was added. A pull request that carries its own proof record is the only case.
- The skill's step 4 asks the questions after the branch is cut; no file existed yet, so nothing was written before the answers.
- The pull request touches `docs/` only, so lifecycle rule a (SPEC-0013 rule 23) did not apply; rule b did not apply (the spec is Draft).
- The implementation of REQ-021 (the facts property, the shared reader, the footer line) is not in this pull request; merging approves the requirement as `planned`, and the spec
  stays Draft until `Q-S0014-1` is ruled (SPEC-0012 rule 14).
