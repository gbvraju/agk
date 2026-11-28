# ADR-0873: A lesson names its prevention and the steward reads a memory digest

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers
- Related: SPEC-0059, SPEC-0063, ADR-0557, ADR-0708, ADR-0726, ADR-0594, ADR-0562, ADR-0678, ADR-0679, brief #2098,
  brief #1765, brief #1741
- Requirements: REQ-066

Protected classes: `scripts/agk/`, `.claude/`, `config/`, `tests/kit/`, `agk.toml`

## Context

The steward's memory is one comment per note on the open `agk-steward` issue (SPEC-0059 rule 8). A cloud steward
clones afresh, so its cache is empty and every start reads every page; the start then prints 253 lines (about 7,300
tokens), most of them the full bodies of unfiled drafts. A roll-over at 500 comments carries only the open owner
questions and the drafts, so the `Onboarded:`, `Person:`, `Setup:`, decisions and lessons of a closed issue are read
by no later start. A `Lesson:` may be any text: none names what stops it, and the same lessons repeat (brief #2098,
Evidence).

## Decision

1. **The digest.** `steward.py` folds the notes into a digest kept as the memory issue's body: a first line
   `Memory in force (schema 1, through <comment id> <UTC time>, checked <date>)`, a `Hash:` line over the rest, a
   `Chain:` line naming the memory issues, a count line per kind and reason (`Decision: 130 older, on #1362 (40),
   ...`) and one line per note kept, each at most 200 characters with its comment id, its issue and its time, at most
   30,000 characters in all. What it keeps is brief #2098 answer 3's table. The comments stay the truth; the digest
   is derived from them.
2. **Reading.** `start` takes the digest from the listing it already makes, reads the comments `since` its `through`
   time less 120 seconds and folds them in by id, then prints a summary built from the digest only (at most 80 lines).
   The other readers read the digest's notes from the start's cache, as they read the cache before. A missing,
   unparsable, other-schema or hand-edited digest, and the first start of a UTC day, read every page and rebuild it
   (`digest: rebuilt (<reason>)`, `digest: drift <kind> <count>`). `start` writes the body when its read folded
   anything, `end` at every pass; in team mode `end` re-reads the body first and folds its notes by id.
   `steward.py show <id>` prints one note with one GET; `steward.py find <word>` searches the digest with no call.
3. **Lessons.** `record --kind Lesson` refuses a text with no `Prevent:` line of the forms `done <check|tool|skill>
   <path> <sha7|#pr>`, `brief #<n>`, `draft F-<session>-<n>` (a recorded draft) and, in a project, `kit-defect #<n>`;
   in a project a prevention naming a kit path takes the `kit-defect` form. A leading `Lesson:` is dropped. A repeat
   is a new note `Lesson: repeat of <id>: ...` (`--repeat <id>`), never an edit; the digest counts it as `seen <n>`,
   and from the second sighting the start prints `owner: lesson <id> seen <n> times; prevention <state>`. A repeat of
   a lesson whose prevention is `done`, or whose brief is closed, needs a new `Prevent:` line; a repeat whose brief is
   open posts one `Lesson repeat: <id> seen <n> times` on it. `--prevent-of <id>` gives an older lesson its
   prevention.
4. **Roll-over.** At 500 comments, unchanged, the new issue's body is the digest, so what is in force carries over;
   the first comment links the old issue and lists the open owner questions, and one `Memory continued in #<new>`
   comment goes on the old issue before it is closed. Unfiled drafts are carried in the digest by id and first line
   and are no longer posted again.
5. **Personal mode.** The digest is `docs/runs/steward/memory-digest.md` of the sidecar; nothing is posted.
6. **No setting.** The bounds are constants; the `[steward]` table keeps its keys and still refuses any other.
7. **The signal.** `config/signals.toml` gains `lesson-prevent`, a comment signal on `^Prevent: `.

## Consequences

A quiet cold start makes 3 counted calls and prints at most 80 lines. What is in force survives a roll-over. A
lesson cannot be recorded without its prevention, and a repeat reaches the owner. The first start of a UTC day pays
one full read to keep the digest true.

## Residual

The scheduled steward task that names the closed issue #1515 is the owner's to change (`Q-S4-4`); the
`Memory continued in` comment points its reader to the open issue. A `Prevent: brief #<n>` is checked against the
issue only at a repeat.
