# Proposed spec amendments 137 (SPEC-0039; REQ-057)

Date: 2026-11-08 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0339 (brief #727, SPEC-0050 build (b)), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 137 is the one
the conductor reserved for brief #727 in its answer to Q-727-1. This amendment is not applied to the spec text in this
pull request; the owner decides it, and it needs a person's `Approve: SPEC-0039`; no session posts it.

1. **The re-prove hold (rule 6).** Before the governance run on the would-be merge, after every hold of rules 3 to 5 and 7
   passes and once the merge is built, the command reads the fetched default branch and the head with local `git`. When
   a file the head changed since its merge base with the default branch was also changed by the default branch after
   that merge base (`--no-renames`, so a rename counts by both paths; added, modified and removed files all count, with
   no exemption), it holds with `held: re-prove (rule 6 of SPEC-0050)`, exit 3, and nothing is merged, recorded or
   filed. A read that fails holds as `held: re-prove (unknown)`, never as a pass.
2. **The behind hold (rule 6).** Only when `[flow] max_behind_merges` is set (agk.toml on the default branch) and
   `git rev-list --count --first-parent <merge base>..<default>` is above it, the command holds with
   `held: behind the default branch (setting flow.max_behind_merges)`, exit 3, and nothing is merged, recorded or filed.
   The key is optional and opt-in: absent, there is no such hold; set, it is an integer of at least 0. Any other value is
   refused before any GitHub read, naming the setting. No line of either hold names a file, a count or a sha
   (principle 8); the red-branch fix of rule 5 is held like any other.
3. **Tests.** The Tests line of rules 6 and 7 gains the cases of SPEC-0050 rule 8: a branch and a default branch that each
   change the same file are held with the re-prove line and nothing merges; a head four first-parent commits behind with
   `max_behind_merges = 3` holds with the setting line, and with the key absent reaches the governance run; a malformed
   value is refused naming the setting; the clean case merges as today.
