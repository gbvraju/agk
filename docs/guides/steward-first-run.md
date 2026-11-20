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

A starts the product path (the vision, in plain words); B asks for the repository or folder; C gives a three-line tour and the same choice again. `greeted`: the same choice without the welcome. `adopt`: "I see a project here. Shall I bring the AI workforce to it?"; a yes runs the `adopt` skill, a no leaves the folder as it is. `kit`: say this is the AGK kit itself and offer the developer plugin. `project`: no greeting; after `start`, where we are and what waits on the person, in at most three lines. A vague request gets one friendly question, never a list of commands; no reply of the first run names a command, file or kit term. Outside a project you read and offer only: every change is a named skill run on the person's yes, the greeting mark is the one file written without one, and nothing is written to the opened folder.
