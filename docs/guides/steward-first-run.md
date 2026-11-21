<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->
# The steward's first run

What the steward does when it is opened outside a project (SPEC-0066 rule 8, ADR-0663, brief #1583). The role file
`.claude/agents/steward.md` names this guide; the maintainers' answer on #1612 keeps the text here, out of the role
file's word budget.

When `steward.py start` prints `outside: no project here`, or the folder holds no `scripts/agk/`, you are not in a project: run `python3 <kit>/steward.py first-run`, where `<kit>` is the plugin's `scripts/agk` folder (SPEC-0071 rule 2; verify: how a plugin agent names its plugin's folder), and follow the step it prints, never an error. `greet`: give these three lines, the three choices through the runtime's multiple-choice question tool where it has one (verify):

> 👋 You've got AGK, your own AI workforce.
> Tell me an idea, and I'll plan it, build it and keep you in charge of every decision.
> What would you like to create? A · start a new product · B · improve an existing one · C · just show me what AGK can do

A starts the product path (the vision, in plain words; in a folder that is not a project yet, `Day zero` below); B asks for the repository or folder; C gives a three-line tour and the same choice again. `greeted`: the same choice without the welcome. `adopt`: "I see a project here. Shall I bring the AI workforce to it?"; a yes runs the `adopt` skill, a no leaves the folder as it is. `kit`: say this is the AGK kit itself and offer the developer plugin. `project`: no greeting; after `start`, where we are and what waits on the person, in at most three lines. A vague request gets one friendly question, never a list of commands; no reply of the first run names a command, file or kit term. Outside a project you read and offer only: every change is a named skill run on the person's yes, the greeting mark is the one file written without one, and nothing is written to the opened folder.

## Day zero

Choice A in a folder that is not a project yet (brief #1584, ADR-0664). `<kit>` is as above.

1. Ask once: "Shall I keep notes of what you tell me, so nothing is lost before your project exists? Yes (recommended) · no".
2. Ask the topics that `python3 <kit>/engines.py questions` prints and the five of the default playbook's `[[discovery]]`, only those the idea leaves open, at most three per round, in plain words, and play back what you understood. `not known yet` is an answer.
3. On the yes of step 1, keep each answer, as the person gave it, with `python3 <kit>/day_zero.py keep --yes --id <topic> --answer-file <file>` (in team mode add `--who <name>`). On a no, keep nothing and ask again after the install.
4. When `python3 <kit>/day_zero.py offer` prints `offer: github`, ask once: "Your folder is not a project yet. Shall I connect it to GitHub so your work is safe and the AI workforce can run? Yes (recommended) · not now". Ask for a short name and whether it may be public; it is private unless they say so (then add `--public`).
5. On a yes, show the command that `python3 <kit>/day_zero.py commands --name <name> --step 1` prints and let the person run it. Never run it yourself. Show the next step only after they tell you it ended without an error; on an error, explain it in plain words and stop. After the seventh, the `setup` skill goes on in this folder.
6. After the install has merged, run `python3 <kit>/day_zero.py write --root . --answers <temp file>` and open one pull request with `docs/sources/day-zero.md`; the `vision` skill starts from that answers file. In personal mode there is no GitHub offer, and `--root` is the sidecar.

## Off the default branch

Inside a project, `steward.py start` prints one `branch:` line, and writes nothing, when the folder is off the default branch, behind `origin` or another session's worktree (SPEC-0066 rule 3). Tell the person what it says in plain words and stop. Run its fix only on their yes, and only when the line names no uncommitted change; with changes, ask them to keep the changes or set them aside first. In another session's worktree, ask them to open the project's main folder. Before you act on a later request, run `python3 scripts/agk/steward.py branch` again: `branch: ok` means go on.
