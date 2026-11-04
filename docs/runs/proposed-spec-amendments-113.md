# Proposed spec amendments 113 (principle 10, SPEC-0005, two guides, a new session rule; REQ-048)

Date: 2026-11-04 (from `date -u`). Approved specs and the constitution change only through a proposal like this one
(principle 6). Written for ADR-0267 (brief #536), which stays `Proposed` for the maintainers' decision; SPEC-0041 rule 29
lists these changes. The paths: `constitution/principles.md`, `docs/specs/0005-distribution.md`,
`docs/guides/existing-codebase.md`, `docs/guides/security.md`, `config/session-rules.md` and `config/core-rules.md`. The
number 113 is the one the conductor reserved on #536. This intake applies none of the items: each is applied by the build
of SPEC-0041 rule 30 named below, with its own ADR, and an item that changes SPEC-0005 needs a person's
`Approve: SPEC-0005` on that build's pull request; no session posts it. No rule of team mode, local mode or solo mode
changes what it says, and no safety rule weakens: each item adds the personal-mode case beside the rule as it stands.

1. **Principle 10 (build (b)).** "Dates come from `date -u`; PR bodies state what they advance; tests carry REQ markers."
   becomes "Dates come from `date -u`; PR bodies state what they advance; tests carry REQ markers or, in personal mode,
   the state's test map." Nothing else of `constitution/principles.md` changes. Because it changes `constitution/`, the
   owner merges build (b) by hand. `check_requirements.py` counts a test-map entry only in a sidecar (SPEC-0041 rules 16
   and 29, build (e)); in a team-mode repository it counts markers in tests exactly as today (`Q-S0041-6`).
2. **A new session rule 36 (build (b)).** `config/session-rules.md` gains, as rule 36 (the next free number,
   `session.py ids` on 2026-11-04): "In personal mode (a sidecar with `forge = "files"`, SPEC-0041) a session never pushes
   to a remote of the product, never runs `personal.py confirm` or `sync`, and never strips, rewrites or amends an
   attribution trailer; the developer pushes, confirms and syncs." `config/core-rules.md` gains one line under its safety
   rules: "`session rule 36`: in personal mode a session never pushes to the customer, never confirms and never strips
   attribution." A number moved by a later merge is a mechanical conflict (session rule 15).
3. **SPEC-0005 rule 1, where the law lives (build (c)).** One sentence is added at its end: "In personal mode
   (SPEC-0041) the law lives in the developer's state folder, a private sidecar repository outside the product with the
   same layout, and nothing of it is in the product repository." The hybrid recommendation for team mode is unchanged.
4. **SPEC-0005 rule 2, the repository works without the plugin (build (c)).** One sentence is added at its end: "In
   personal mode the product repository holds nothing of AGK and the sidecar's checks run from the plugin's scripts
   (SPEC-0041 rule 26), so personal mode needs the plugin; team mode is unchanged."
5. **SPEC-0005 rule 7, the footprint (build (i)).** "the plugin ships no copy of it, so there is no second
   `agk:reviewer`" becomes "the plugin ships no copy of it for team mode, so there is no second `agk:reviewer` there; for
   personal mode only, where the product has no `.claude/agents/`, the plugin ships one reviewer agent, advisory and
   experimental (SPEC-0041 rule 17, `Q-S0041-10`)". The rule's first two sentences stay: the plugin still ships no hook,
   no MCP or LSP server, no monitor and no `bin/` in the first release of personal mode (`Q-S0041-9`). Where a plugin's
   agents live in its layout is `(verify)` and is read from the Claude Code documentation by build (i).
6. **`docs/guides/existing-codebase.md` (build (n)).** Step 2's "Do not invent behaviour you do not document." gains:
   "In personal mode, behaviour observed in the code is also an allowed source of a `Proposed` record, with citations
   `path:lines@blob` that exist, and it is never `done` until a test asserts it (SPEC-0041 rules 13 and 14)." The
   closing "AGK does not read your product code for meaning." gains: "except in personal mode, where the survey reads a
   budgeted sample, never runs it, and states its coverage (SPEC-0041 rules 10 and 11)."
7. **`docs/guides/security.md` (build (n)).** Under "What AGK stores", "Nothing outside your repository." is rewritten
   as: "In team mode, nothing outside your repository. In personal mode, nothing inside it: the state lives in a private
   folder under `AGK_HOME` on your machine, `0700` on POSIX, holding paths, line ranges, blob shas and summaries but no
   code excerpt by default and no credential, and it leaves the machine only by a sync you name (SPEC-0041 rules 2, 5
   and 28)." The "One account for every role" section gains one sentence: "In personal mode the agent-app mark is
   written by the kit, not by GitHub, so it is a label and not proof (SPEC-0041 rule 8, `Q-S0041-16`)."
8. **Tests.** Build (b): `tests/kit/` checks that principle 10 carries the new clause and nothing else of the
   constitution changed, that session rule 36 and its core-rules line exist, and that `check_requirements.py` in a
   team-mode repository still counts only markers in tests. Builds (c) and (i): `tests/kit_dev/test_distribution.py`
   checks the plugin ships no hook and, for personal mode only, one reviewer agent. Build (n): a test reads the two
   guides for the new sentences. Their marker is `REQ-048`.
