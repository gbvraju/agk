# ADR-0124: capacity, overlap, numbers, claims, demand and push-check (REQ-041 build (b), SPEC-0034 rules 1, 3 to 6 and 7b)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0120, ADR-0114, ADR-0117
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0034 (Approved) rule 13 splits its build in four; this is (b): `session.py` (rules 1, 3 to 6 and 7b). It is built from the default branch in flow mode (SPEC-0031) after (a) (ADR-0120). ADR-0124 was reserved
for it by the conductor on #176. The tests were written first (`tests/kit/test_session_flow.py`, and the fixtures of `tests/kit/test_session.py` that `next` now needs); on the unchanged `session.py` 27 of them failed
(`27 failed, 39 passed`), after the build all pass.

The size is about 730 changed lines of code and tests, above the 600 of rule 13: the capacity, the overlap, the numbers, the claims and the demand read one survey of GitHub (every pull request, every open brief and its comments), so they were built together and not split.

## Decision

1. **The capacity (rule 1).** `next` reads every pull request (`GET pulls?state=all`) and counts the open ones with a line `Brief: #n`; at `max_builders` (the `[flow]` table of `agk.toml`, 3 by default) it prints
   `full <open>/<max>`, posts nothing and exits 1. An unreadable list ends `next` and `demand` with `FAIL session: rule 1`. An invalid `max_builders` or `claim_hours` (not a whole number, 1 or more) is refused naming
   the setting and never the value. A takeover of a stalled pull request (SPEC-0033) comes before the count, as before: it adds no builder pull request.
2. **The overlap and the order (rule 3).** `next` reads every open brief and its comments first. A brief is skipped, with its reason, when a glob of its `Touches:` matches a path changed by an open builder pull
   request (`GET pulls/N/files`, a glob being `*`, `?`, `**` and `dir/`) or shares a literal prefix with the globs of a brief taken by another session that no pull request names yet. The paths that count as
   shared-mechanical never overlap: `changelog.d/` and the files marked `merge=union` in `.gitattributes`. The briefs left are ordered by `Priority:` (1 first, 2 when absent), then by number.
3. **The numbers (rule 4).** `ids` prints one JSON line `{"req", "spec", "adr"}` of the next free numbers: the highest of the default branch (`next_free_ids` of `origin/<default_branch>`), the ADR and spec files an open
   builder pull request adds, the `### REQ-nnn` lines it adds to `docs/requirements.md`, and the numbers reserved by live takes, plus one. `next` writes the numbers its brief needs into its one take comment
   (`taken: <id> <date> reserves REQ-nnn, SPEC-nnnn, ADR-nnnn` for `Advances: new`, `reserves ADR-nnnn` for a build). When the default branch cannot be read the take is made with no reservation and a note on stderr.
4. **The claims (rule 5).** A take is live for `claim_hours` (4 by default), and after that only while an open pull request has the line `Brief: #n` for it (a merged one counts for `claim_hours` after its merge: the brief's next build, since a brief spans several pull requests); `released: <session>` ends that session's takes at once.
   The take that follows an expired one says `retakes`; a live take is never taken twice.
5. **The demand (rule 6).** `demand` prints `{"ready", "open", "max", "start"}`: `ready` the briefs `next` would not skip, `open` the open builder pull requests, `start = min(ready, max - open)`, 0 when negative.
   It posts nothing. The guide's contract for a launcher is build (c).
6. **The push-check (rule 7b).** `push-check` fetches `origin/<default_branch>`, runs `git merge-tree --write-tree --name-only` of the head against it, exits 0 and prints nothing when it is clean, and exits 1
   printing `conflict: <files>` otherwise. It changes no file and no ref except the fetch.
7. Amendment 61 (`docs/runs/proposed-spec-amendments-61.md`) is applied to SPEC-0030 rule 3. A flow-mode fragment `changelog.d/req-041-b-flow.md` records the change; no version bump; `CHANGELOG.md` and
   `kit/hashes.json` are as on `main`. The manifest is unchanged (`session.py` is installed). `agk.toml` is not changed: the `[flow]` table is read, and its defaults apply.
8. **Readings taken where the spec leaves a point open** (questions in the pull request, the most conservative reading each): a brief with an open `Depends-on` is skipped, as before, not only ordered later;
   shared-mechanical paths are those named above because `config/session-rules.md` lists none yet (build (c)); two globs overlap when their literal prefixes (up to the first `*` or `?`) nest; `released:` is
   honoured but no command posts it here.

## Consequences

- A launcher can ask `demand` how many sessions to start; two sessions started together take briefs whose `Touches:` do not overlap and whose numbers differ.
- `next` reads every open brief and its comments before it takes one, which costs a few more GETs than before.

## Residual

- 2026-10-25: `intake.py`, `playbook.py start-ids` and `engines.py stack-ids` do not read `session.py ids` yet (the last sentences of rule 4); they keep their offline default (due 2026-12-31).
- 2026-10-25: two globs whose literal prefixes nest are read as overlapping even when they do not (`docs/a` and `docs/ab.md`); the error is on the side of skipping (due 2026-12-31).
- 2026-10-25: no command posts `released:`, so a session that ends without a pull request frees its brief by hand or after `claim_hours` (due 2026-12-31).
