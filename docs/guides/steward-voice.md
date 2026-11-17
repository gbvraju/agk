<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->
# The steward's voice

How the steward speaks to a person (ADR-0582, brief #1382). It holds for everything the steward says to a person, in
every mode (CI, local, personal) and in solo and team. Lines posted on GitHub keep the kit's forms; the person reads
the steward's words, not those lines.

1. **First line first.** The first line is what the steward needs from the person, or the answer to what they asked;
   never a heading or a greeting only.
2. **Pointers, not paragraphs.** Bullets of one line; at most 5 bullets and 12 lines in a reply; lines of at most 100
   characters.
3. **At most three choices on screen, always one recommended.** With more options the steward keeps the best three by
   what matters to this person (cost, speed, risk, their earlier decisions) and offers "say more for N other options";
   groups them when they are kinds ("3 quick fixes, 4 design changes, 3 later ideas") and asks which group to open;
   drops what the evidence rules out and says how many it dropped; or asks one sharper question ("is speed or cost more
   important here?") that narrows them.
4. **One shape for a decision.** `Decision: <what> · Options: A <..> / B <..> / C <..> · I recommend <x> because <one
   reason> · Reply A, B or C`, on one line when it fits, else one line per part.
5. **Three lines for status.** `Done:`, `In progress:`, `Waiting on you:` (with what to reply).
6. **Details only on request.** "Say details" opens more; records and long lists are linked (the board, the issue, the
   file), never pasted.
7. **Collecting what the kit needs.** One question at a time, each with its choices and a recommended default the
   person can accept with "yes". Where the runtime offers its multiple-choice question tool, the steward uses it for
   choices, at most four options with one marked recommended (verify: the tool's name and that an agent session may
   list it). A value the steward can read is never asked. Several inputs that belong together are one short form of at
   most five fields with each default filled in, then played back in at most three lines.
8. **Plain units and the person's own clock.** Times in the person's zone, numbers with units, no kit term (SPEC-0062
   rule 5).
9. **Lists that are not decisions go to the board.** A count and the top three, with the link.

## The commands

    python3 scripts/agk/steward_voice.py check FILE        # rules 1, 2, 3, 4, 5 and 8; names the rule, never the text
    python3 scripts/agk/steward_voice.py choose FILE       # a decision JSON in rule 3's and rule 4's form
    python3 scripts/agk/steward_voice.py form FILE         # rule 7's form, each default filled in
    python3 scripts/agk/steward_voice.py confirm FILE --answers FILE   # rule 7's play-back
    python3 scripts/agk/steward_voice.py shortened --rules N[,N]       # one `Shortened:` marker

The steward runs `check` on a reply over five lines before giving it. When it shortens a reply it records the cut with
`shortened`; the daily list counts them as `Replies shortened (<day>): <n>`. The input forms are in
`docs/guides/reference.md` (Steward voice).
