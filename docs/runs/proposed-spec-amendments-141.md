# Proposed spec amendments 141 (SPEC-0050 and SPEC-0030; REQ-057)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0358 (brief #772), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0050-overlapping-work-never-runs-at-once-and-a-second-change-re-proves.md` and
`docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md`. The number 141 is the one brief #772
reserved. This amendment is not applied to the spec text in this pull request; the owner decides it, and it needs a
person's `Approve: SPEC-0050` and `Approve: SPEC-0030`, and, for items 9 and 10, `Approve: SPEC-0006` and
`Approve: SPEC-0007` (`Q-772-2`); no session posts them. No build of brief #772 starts before them.

Measured on the default branch at e05411d, 2026-11-09 (`gh api` of the open issues labelled `agk-brief`, entries matched
against `git ls-files`): of 21 open briefs, 13 have a folder or wildcard `Touches:` entry that matches more than 5 files.
7 of those 13 are only `changelog.d/*.md` (116 files), which never holds a brief, so item 1 counts only files that can
hold (`Q-772-3`); 6 briefs remain (#459, #647, #762, #763, #768, #837).

1. **SPEC-0030 rule 4, exact `Touches:` and `Adds:` (answer 1).** Added to the rule:
   - `Touches:` names the existing files the brief edits. One optional line `Adds:` names, in the same comma-separated
     form, the new files or new folders the brief creates. Every reader of `Touches:` reads both lines as one list (the
     overlap of rule 2 of SPEC-0050, `kind` of SPEC-0045 rule 4, the UI test of SPEC-0037 rule 10), so moving a new file
     to `Adds:` never lowers a kind or hides a UI brief. Only the two refusals below read them apart.
   - With `--root DIR`, a `Touches:` entry that is a folder or holds a wildcard and matches, in the tree under `DIR`,
     more than `[flow] max_touch_glob` files that can hold a brief (the last row of the table in item 3) is refused:
     `rule 4: Touches entry <entry> matches more than flow.max_touch_glob files`. It names the rule, the setting and
     the entry, never a count. The default is 5; a value that is not an integer of at least 1 is refused naming the
     setting, never the value. A brief with one line `Broad: <reason>` is a sweep and passes for every entry; that line
     is its own statement and no check judges the reason.
   - With `--root DIR`, an `Adds:` entry that matches a file already in that tree, shared-mechanical files aside, is
     refused: `rule 4: Adds entry <entry> names an existing file`. `Adds:` is therefore no way round the count above
     (`Q-772-4`).
   - One function holds both, so `check_brief.py --root`, the event job of amendment 140 (which already passes `--root .`
     from a checkout of the default branch; no workflow changes) and `session.py next` and `plan` agree. `plan` prints a
     refusal on its `MALFORMED:` line (amendment 140 item 3). Without `--root` only the shape of the lines is checked.
2. **SPEC-0050 rule 2, what an entry holds on (answer 1).** Added: an entry of `Adds:` is judged like any other, by
   `session_plan.clash` and `file_conflict`, no second matcher: an added file holds only on its exact path, as today (rule
   1), and a new folder holds on what lies under it. An entry that keeps a folder or wildcard under a `Broad:` line holds
   as a folder does today.
3. **SPEC-0050 rule 3, file classes in one table (answer 2).** The rule gains the table; the first row that matches wins.

   | Class | Set by | Two pieces of work at once | Re-prove (rule 6) |
   | --- | --- | --- | --- |
   | Shared-mechanical | rule 1, session rule 14 | never held | yes |
   | Shared index | `[flow] shared_indexes` (rule 3 as today) | never held | yes |
   | Prose git merges by line | `[flow] reprove_paths` | never held; the later one re-proves | yes |
   | Everything else: code, data, specs, ADRs | nothing | held (rule 2) | yes |

   - `[flow] reprove_paths` is a list of globs, read in order, where an entry that starts with `!` takes matches away
     again. Default: `["**/*.md", "!docs/specs/**", "!docs/adr/**"]` (`Q-772-5`). A set value replaces the default; a
     value that is not a list of non-empty strings is refused naming the setting (`setting: flow.reprove_paths`), never
     the value.
   - The re-prove is rule 6 as it stands, so the rule-budget and document tests run again in the required checks of the
     new head; nothing is added to it. The exemption needs no ordering clause like rule 3's last sentence, because the hold
     of rule 8 is on the default branch (ADR-0339, `merge_cleared.reprove_check`).
   - A folder or wildcard entry is in a class only when every file it matches in the tree is; one that matches no file is
     read as held, the safe side.
   - `merge_set` of `plan` keeps counting a shared prose file as a reason to merge one after the other: they do not merge
     together, as with a shared index today.
4. **SPEC-0050 rule 4, the holders ranked (answer 3).** Added: `session.py plan` prints, for each open pull request that
   holds briefs, one line `Holds <k>: #<pr> (<state>, idle <m> min) for #<a>, #<b>`, highest `k` first, then lowest pull
   request number. `<state>` is the `agk:` label without its prefix, or `draft`, or `open`. `<m>` is the minutes since the
   pull request's `updated_at`, a field the plan already reads. A brief held by two pull requests is counted under each,
   since merging one does not free it (`Q-772-6`). The conductor's work list reviews, unblocks and asks the owner to merge
   in that order. A holder with `k` of at least 2 idle over `[flow] stall_minutes` (new, an integer of at least 1, default
   30, `Q-772-7`) also prints `Stall: #<pr> holds <k>, idle <m> min`; `plan` still posts nothing, and the conductor posts
   that line once on the plan issue in the same pass, and again only after the pull request's head or state changes
   (`Q-772-8`).
5. **SPEC-0050 rule 4, reservation clashes (answer 4).** Added: `session.py plan` refuses an open brief whose `Reserved:`
   number an open pull request other than the pull request of that brief (its `Brief: #n` line) adds, or that another
   open brief reserves. Of two briefs the later issue is refused; a
   brief always yields to a pull request. The line is `MALFORMED: #<n> rule 4 of SPEC-0050: Reserved <number> is also
   held by #<m>`. A number is `ADR-nnnn`, `SPEC-nnnn`, `REQ-nnn` or `amendment n`, read only from the text of the line
   before its first `(` (`Q-772-9`). `check_numbers.py` gains an optional `--briefs FILE`, a saved list of open briefs,
   and fails when a number the pull request adds is reserved by an open brief other than its own, naming both; the
   governance step is unchanged and does not pass it, so a clash between two briefs never turns an unrelated pull
   request red. The conductor posts a `Correction:` on the later brief giving it the next free number.
6. **SPEC-0050 rule 4, plan before filing (answer 5).** Added: `session.py plan --what-if DIR` reads saved brief files
   (`*.md`, one brief each, not filed) with the open work, orders them by `Priority:` then file name, judges them with the
   same function as `plan` and prints `What-if: <k> of <n> can start together.`, one line `<file> waits for <holder>
   (<why>)` for each held one, `MALFORMED: <file> <rule>` for one that fails the shape, and `File in this order: ...`. It
   reads capacity from nothing (it answers about overlap only), posts nothing and records nothing. The conductor's filing
   step runs it and files in that order.
7. **SPEC-0050 rule 4, every hold measured (answer 6).** Added: each recorded plan pass appends one JSON line per held
   brief and holder (`at`, `brief`, `holder`, `file`, `minutes` since that pair was first recorded) to
   `docs/runs/holds.jsonl`. After both pieces of work merge, one more line marks the hold `false` when the two merged
   diffs of that file (`git diff -U0`, the later one's lines mapped back over the commits between) change no common line,
   a file only one of them changed included, and `true` otherwise, or `unknown` when the mapping cannot be made, as for a
   rename. `unknown` is left out of the rate. Lines are only ever appended. `metrics.py` reports held builder-minutes per
   day and the false-hold rate, and the weekly report names the entry or class behind the most false holds. An absent or
   empty file reports `unknown`, never 0. **Where this file lives and who writes it is `Q-772-1`, which the owner decides
   before build (c).**
8. **SPEC-0050 rule 5, what the sweep prints.** The first bullet's "share a file under rule 2" takes in the classes of
   item 3, so `overlap:` prints no pair that shares only prose. Its `re-prove:` and `BEHIND` lines do not change. Today
   `conductor.proof_lines` leaves out only the shared-mechanical files, so a pair that shares only a shared index does
   print `overlap:`, against the rule; build (b) reads the one table of item 3 there and that gap closes with it.
9. **SPEC-0006 rule 5 (a consequence of item 1).** A new row after `brief-invalid-label`: `brief-broad-touches` | warn |
   an open brief has a `Touches:` entry item 1 refuses; the row names the brief and the entry. One read of the open
   briefs doctor already makes.
10. **SPEC-0007, the weekly body (a consequence of item 7).** One more line in the weekly report: held builder-minutes
    per day, the false-hold rate and the entry or class with the most false holds, under SPEC-0007's rule of no inference.
11. **Every mode (answer 7).** GitHub, local and personal projects read the same `[flow]` keys with the same defaults:
    `max_touch_glob`, `reprove_paths` and `stall_minutes` are optional and none needs a line in `agk.toml`. Nothing here
    needs a workflow, a ruleset, a required check or a network call in a check.
12. **REQ-057, the same words (a consequence of item 3; `Q-772-10`).** AC1 and AC3 read "outside the shared-mechanical
    files, the shared indexes and the prose of `reprove_paths`". New acceptance lines, one for each of items 1 and 3 to 7:
    AC8 a broad entry is refused unless the brief says `Broad:`, and `Adds:` names only new files; AC9 two pieces of work
    on prose run at once and the later re-proves; AC10 `plan` ranks the holders and reports a stall; AC11 a reservation
    that another open brief, or a pull request of another brief, holds is refused naming both; AC12 `plan --what-if` names how many can start
    and what holds the rest, and posts nothing; AC13 each hold is recorded and the false-hold rate is reported, `unknown`
    when there is no record.
13. **The builds, three, each tests first and about 300 changed lines or fewer (answer 8).** (a) items 1, 2, 5, 9 and 12 and
    the repair of answer 1; (b) items 3, 4 and 8; (c) items 6, 7 and 10. Item 12 is one change, in the first build, so
    that each build's tests can cite their acceptance line and AC1 and AC3 are right before (b) exempts prose; it is
    subject to `Q-772-10`, as `docs/requirements.md` is outside the brief's `Touches:`. They are the builds of brief #772, not those of
    SPEC-0050 rule 10. **The repair:** brief #634 is closed and needs none; #459, #647, #762, #763
    and #768 get exact `Touches:` and `Adds:` lines, one comment on each saying which lines changed, and #837 is reported
    (`Q-772-11`).
14. **Not in this amendment.** Rule 6, rule 7 and rule 8 of SPEC-0050 are not changed: the re-prove state has no exemption.
    SPEC-0034 rules 2, 3, 15 and 17 are not changed: rule 2 still gives the shape of `Touches:`, and SPEC-0050 already
    rules overlap (`Q-772-2`). `[flow] shared_indexes` stays exact paths. `[flow] stall_hours` (SPEC-0033 rule 5, four
    hours, a builder's stall) keeps its meaning. A number already on the default branch is caught by `check_numbers.py` as
    today and is not added to item 5 (`Q-772-12`).

## Questions

Each is open until a person rules; the reading after it is the conservative one the items apply.

- **Q-772-1, for the owner before build (c):** where do the records of item 7 live? `plan` posts and writes nothing today;
  the conductor's guard refuses every write outside a scratch folder and every command but `plan --json`; a file rewritten
  on every pass is a generated file (principle 5), and the weekly report runs in a workflow, where a local file is absent
  and a committed one would need a pull request (SPEC-0007 rule 11). Reading: `plan`
  appends only with a new `--record` flag, to the path the brief names, kept out of git, and the weekly report says
  `unknown` wherever the file is absent, so on this repository the rate stays `unknown` until the owner picks: (a) a
  tracked file that a docs commit batches, once a day; (b) one comment a day on the plan issue, read back; or (c) local only.
- **Q-772-2:** the brief reserves amendment text for SPEC-0050 and SPEC-0030; the code also ties doctor rows to SPEC-0006
  rule 5 and the weekly report to SPEC-0007. Reading: this amendment carries those two as consequences, as amendment 140
  did for SPEC-0006, each needing its own `Approve:`; SPEC-0034 is left unchanged.
- **Q-772-3:** does a `changelog.d/*.md` entry count against `max_touch_glob`? Read literally it refuses 13 of the 21 open
  briefs. Reading: no; only files that can hold count, since a broad entry over files that never hold costs nothing.
- **Q-772-4:** may `Adds:` name a file that exists? Reading: no, or a brief could move `tests/kit/**` to `Adds:` and escape
  answer 1.
- **Q-772-5:** how does a list of globs say "less"? Reading: a `!` entry, the form `.gitignore` readers know; no second key.
- **Q-772-6:** a brief with two holders? Reading: it counts under each, and answer 6 records one line per pair; the first
  holder alone would hide a second and credit a false hold to the wrong pull request.
- **Q-772-7:** the default of `stall_minutes`? The brief gives none. Reading: 30, below the 50 idle minutes of its evidence;
  to be tuned by the measure of item 7.
- **Q-772-8:** who posts the stall? Reading: the conductor, since `plan` posts nothing; the guard's allowed comment on the
  plan issue is checked in build (b), and if it is not allowed the build stops and asks.
- **Q-772-9:** what is a reservation? Reading: text before the first `(`, because #768 reads `Reserved: none (Covered-by:
  ADR-0303; ...)` and that ADR is not reserved. `session.reserved_numbers` does not read this way today and build (a) fixes it.
- **Q-772-10:** the brief's `Touches:` omits `docs/requirements.md`, `scripts/agk/conductor.py` (the sweep,
  `proof_lines`), `.claude/hooks/conductor_guard.py` and the intake's filing text. Reading: each named build adds what it
  needs only if the owner's `Approve:` of this amendment stands for it; otherwise it stops and asks.
- **Q-772-11:** who repairs the other briefs? A builder edits only its own brief's work. Reading: as for brief #770, the
  conductor applies the lines build (a) prints, on the owner's word.
- **Q-772-12:** should item 5 also refuse a number already on the default branch? Brief #798 reserves ADR-0375, which merged
  for brief #802. Reading: not added; `check_numbers.py` fails that build, and the owner may widen item 5.
