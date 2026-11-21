# Proposed spec amendments 196 (SPEC-0065; REQ-072)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0664 (brief #1584), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0065-one-command-sets-up-any-machine-as-a-ready-correctly-sized-ai-workforce.md` (rule 8 and the `## Tests`
section). The number is the brief's `Reserved:` one. This file proposes the lines and does not edit the spec; they are
applied word for word on a person's `Approve: SPEC-0065`, which no session posts. Amendment 197 carries the steward's side
(SPEC-0066 rule 4).

The sentence (brief #1584): "In an empty folder the steward talks the idea through first, keeps the person's answers on
their yes, offers to connect GitHub with the commands to run one at a time, and after the install writes those answers as
the plan's first source, so nothing waits on a developer guide."

## What is on the default branch today

Read on main at b633566 (2026-11-21): rule 8 starts "When the folder is not a clone, it clones the repository the person
names (`gh repo clone`)". It never creates one, and no kit file printed `gh repo create` before this build. The only route
was a repository made on the GitHub website (`docs/guides/getting-started.md` step 1).

## Items

1. **Rule 8, one sentence added after its first clause.** "When the folder is not a clone and the person has no
   repository, it prints the commands to create one, one at a time (`day_zero.py commands`, ADR-0664): `gh auth status`,
   `git init -b main`, a one-line README, the first commit, `gh repo create <name> --private --source . --remote origin
   --push`, `git remote set-head origin --auto` and `gh repo edit --enable-issues`, in a POSIX and a PowerShell form; the
   person runs each, the next is shown only after an exit of 0, the repository is private unless the person chooses
   otherwise, and then setup goes on from the clone-has-no-`agk.toml` step." (brief answer 3, Q-1584-3)
2. **The `## Tests` section, one line added.** "- Rule 8, no repository yet: the seven commands print one at a time and
   in order in both shell forms, the PowerShell form writes no file with `echo >`, a name outside letters, digits, `.`,
   `_` and `-` is refused naming the setting, and a folder that is a git repository with `origin` gets no offer;
   REQ-072." (brief answer 7)
3. **Unchanged:** every other rule, the Proof, the Residual and the Contexts. Hosted and local run the same commands;
   only rule 10's step after them differs.

## Questions

- Q-1584-3 (private by default): the recommendation taken, `--private`, with `--public` only on the person's own choice.
