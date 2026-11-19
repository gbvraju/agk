# Proposed spec amendments 184 (SPEC-0034; REQ-041)

Date: 2026-11-19 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0645 (brief #1531), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`. Brief #1531 reserved amendment 184.
This file proposes the lines and does not edit the spec; the owner approves the amendment.

The sentence (brief #1531): "When two builds each add or remove tests in the same testing-map list, the builder settles
the conflict with one kit command that proves the merged settings parse and lose no test, so no person is needed, in the
kit and in every project."

## Why

Measured on the default branch at 5a5a0abe (2026-11-19), the brief's figures reproduced (session rule 19): of the 200
commits before 6f7288da, 102 changed `agk.toml` and 91 of those changed lines of its `[[testing.map]]`; the map has 146
entries, 126 of them with a `scripts/agk/` code path. #1523 (`Report: 52827fe80e5f escalate: conflict needs a person:
agk.toml`, 2026-11-18 18:20Z) and #1521 each waited for `Maintainer answer: the agk.toml conflict is mechanical; keep
both lines` (18:59Z and 2026-11-19 02:53Z). Two appends at the end of one wrapped `tests` list touch the same lines, so
git cannot merge them, and rule 7 (c) does not let the builder settle it. `test_map.py build` writes 88 entries and none
has a `scripts/agk/` code path, so a generated map cannot replace the kit's curated one.

## Items

1. **Rule 7 (c)** becomes: "A session resolves only a mechanical conflict: an appended line in a shared-mechanical file,
   a file a kit script regenerates, a number moved by `intake.py renumber`, and a change of the `[testing] map` of
   `agk.toml` that the kit's map resolver (d) settles and whose check passes (amendment 184, ADR-0645); any other
   conflict ends the work with one comment `conflict needs a person: <files>` and no push."
2. **Rule 7 gains (d), the map resolver:** "(d) After `git merge origin/<default branch>` leaves `agk.toml` conflicted,
   the builder runs one subcommand of `session.py`, beside `push-check` (no new installed script). It reads the three
   versions (`git show :1:agk.toml`, `:2:` and `:3:`) and splits each, as `impact.py` `_map_split` does, into the map
   and the rest. It writes the file only when every check holds, else prints `conflict needs a person: agk.toml
   (<reason>)`, names the failed check and writes nothing:
   - each of the three versions parses as TOML, and the written result parses;
   - outside the map, the result equals the side that changed it (both sides equal, or one side equal to the base); any
     other change outside the map refuses;
   - for each `code`, the result's tests are the base's, plus each side's additions, less each side's removals; a test
     both sides add appears once; the order is the base's, then ours, then theirs;
   - a new entry from either side is kept where that side put it; two new entries with the same new `code` become one
     entry with their tests united; an entry one side deletes while the other changes it refuses; a changed `code` glob
     refuses; a `code` that appears in two entries and is touched refuses; a test that one side removes from an entry
     while the other side adds the same name to any entry refuses;
   - no line outside the conflicting hunks differs from what git merged; the file keeps its own line endings (LF or
     CRLF) and its comments, including a comment inside a `tests` list;
   - both map forms are read: `[[testing.map]]` tables and an inline `map = [ ... ]` list with one entry per line or per
     block; any other shape refuses.
   On success it prints one line `resolved: agk.toml testing map: <n> entries`, which the builder copies into its
   `Report:`, then the builder commits the merge and pushes as (b) says; it never rebases or force-pushes. The
   shared-mechanical list of (a) is unchanged: the map is not a shared-mechanical file, so `overlap`, `shared_patterns`
   and `push-check` are unchanged."
3. **Rule 7 gains, after (d), the options weighed** (recorded so a later reader sees why (d) was chosen):

   | Option | What it is | Why not, or why |
   | --- | --- | --- |
   | (A) One file per map entry | A folder of entry files, as `changelog.d/` | Two tests added to one entry still conflict; changes every reader, moves 146 entries, adds a second source in each project and a protected folder |
   | (B) A kit merge driver | `merge=<driver>` in `.gitattributes` | The command lives in git config, which no committed file sets: each clone, fresh cloud session and Windows machine needs setup, an unset driver silently falls back, the forge's check ignores it |
   | (C) A kit resolver and an amended rule | Item 2 | No git config, no layout change, no migration; the same in the kit and projects, local and cloud; full cover of the observed case. **Chosen** |
   | (D) Generate the map | `map_source = "generated"` | Exists for projects; covers 0 of the kit's 126 script entries |
   | (E) One test per line, sorted | A one-time reformat | Still conflicts when two names sort next to each other; the reformat conflicts with every open pull request |

4. **Rule 7 gains the settings, each with its impact:**

   | Setting | Impact on the resolver |
   | --- | --- |
   | `execution` local or cloud | git and files only, in the builder's own checkout; a fresh cloud session needs no setup |
   | `pr_mode` strict or flow, `max_builders` | more open pull requests mean more conflicts in the same lists; each merge is settled pairwise; no setting changes |
   | `review_mode` solo or team | the merge commit is reviewed as any other; the `resolved:` line tells the reviewer only list lines moved; no new approval or comment kind |
   | personal mode (`forge = "files"`) | the same local merge; the line goes to the forge file; nothing is posted |
   | local mode (`docs/guides/local-mode.md`) | the merge still moves the head, so the evidence is recorded again and a new accept is needed, as today; only the person's ruling is removed |
   | `mode = "adopt"` | the map may be inline or absent; absent means nothing to settle |
   | `layout = "plugin"` | the command runs from the plugin and the guards allow its plugin form (brief #1500); `agk.toml` stays the project's file |
   | `[testing] map_source` | `generated` adds a git-ignored file that never conflicts; the resolver acts on the curated list only |
   | `[testing] pr_tests = "selected"`, `profile` | the map chooses which tests a pull request runs, so a lost pair would skip a test silently; the no-loss check is the safety, and a doubt refuses |
   | `[testing] always_full`, `pre_merge_tests` | outside the map: a change on both sides refuses; a person keeps them |
   | protected paths | `agk.toml` stays protected; a merge of the default branch adds no change of its own, so it needs no ADR or `Covered-by:` |

5. **Tests** gains: "Rule 7 (d): both sides add the same test (kept once); one side removes a test the other leaves
   (removed); one side removes a test the other adds again (refused); a new entry next to an entry the other side
   changed (both kept); both sides add an entry with the same new `code` (one entry, tests united); a result that would
   not parse (refused, nothing written); a conflict that also changes a setting outside the map (refused, naming it);
   CRLF on one or all three versions (kept, no line rewritten); a comment inside a `tests` list (kept); the inline form;
   a merge git settled itself (nothing to do); REQ-041 AC7."
6. **Proof** gains: "Rule 7 (d), measured: on a scripted repository with two branches that each add a test to the same
   entry, `push-check` exits 1 naming `agk.toml` before; after, the resolver settles it, `impact.py`'s selection on the
   merge selects both tests, and no `conflict needs a person` is posted; the same in a project made from
   `kit/templates/agk.toml` with an inline map."
7. **Residual** gains: "2026-11-19: `[testing] always_full` and `pre_merge_tests`, `docs/guides/reference.md`,
   `kit/manifest.json`, and the append-only `docs/runs/flakes.md` and `docs/design/signoffs.md` (not marked `merge=union`
   in `kit/templates/gitattributes`) are not covered by (d); each waits for the owner's word (due 2026-12-31)."
8. **Contexts**, the `kit` entry gains: "the map resolver of rule 7 (d) is a subcommand of the installed `session.py`, the
   same in every project"; `github`: "the forge's conflict check and merge are unchanged; the builder merges and pushes
   as rule 7 (b) says"; `local`: "the same command in the builder's checkout, LF and CRLF alike; the evidence is recorded
   again after the merge"; `personal`: "the same local merge, its line in the forge file, nothing posted"; `stacks`
   unchanged (`agk.toml` is the same for every stack).
9. **Unchanged:** rule 7 (a) and (b); session rule 14 and its shared-mechanical list; `.gitattributes` and
   `kit/templates/gitattributes`; `session.py` `overlap`, `shared_patterns` and `push_check`; every reader of the map
   (`impact.py`, `test_map.py`, `check_kit_tests.py`, `engines.py`, `prepush.py`).

## The builds

Each tests first, about 250 changed lines or fewer, each filed later by the `brief` skill with a Settings section:

- (a) the resolver of item 2 and its tests (item 5): `scripts/agk/session.py`, `tests/kit/`, the new test file's
  `[[testing.map]]` line in `agk.toml`, one `changelog.d/` fragment.
- (b) session rule 15 names the fourth mechanical conflict in the words of item 1; the builder template
  (`kit/templates/runtime/builder.txt`) names the command; the conflict paragraph of `docs/guides/getting-started.md`
  names it beside the `merge=union` note.

## Questions (brief #1531), each with the reading this proposal takes

- Q-1531-1: may a builder settle a map conflict without a person seeing it first? Only when every check of item 2 passes
  and the `resolved:` line is in its `Report:`; any refusal goes to a person as today.
- Q-1531-2: do `always_full` and `pre_merge_tests` get the same treatment? No; a person keeps them.
- Q-1531-3: should `kit/templates/gitattributes` mark `docs/runs/flakes.md` and `docs/design/signoffs.md` `merge=union`?
  Not here; session rule 14's list is the maintainers'.
- Q-1531-4: reformat the kit's map to one test per line, sorted? Not now; only on the owner's word after (a) lands.
- Q-1531-5: does an accept survive a head move whose only change is a resolved merge? No; evidence and accept are taken
  again.
- Q-1531-6: under `map_source = "generated"`, should builder.txt stop asking for a curated entry? Unchanged here; a later
  project-side build.
- Q-1531-7: add a merge driver as an opt-in? No.
- Q-1531-8: priority? 1.
- Q-1531-9: the subcommand's name. The brief names none; build (a) proposes `session.py resolve-map` and its brief
  settles it.
