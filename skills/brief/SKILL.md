---
name: brief
description: Start a brief from docs/briefs/TEMPLATE.md (new_spec.py). Writes one new file.
disable-model-invocation: true
argument-hint: "TITLE"
---
<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->

# /agk:brief

Create one brief in `docs/briefs/` from `docs/briefs/TEMPLATE.md`. The script runs in the repository root and refuses to
overwrite.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/new_spec.py" brief "TITLE"
```

Then show the playbook's proposal for the goal before filling the items (SPEC-0038 rule 7). With a declared work type
(`[delivery] work_type` in `agk.toml`) it prints the brief kinds in the playbook's `brief_order`, each with its `Kind:`
line, the `Depends-on:` lines its dependences give and its lane; without one it prints nothing and the brief is filled
as today. It writes no file.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/playbook.py" split --goal "TITLE"
```

`--kind KIND` shows one kind alone. A brief's `Kind:` line names one kind of `brief_order`; its `Depends-on:` names the
earlier brief once that brief is filed. Then help the user fill in the items; the maintainers decide their content.

Before an `Adds:` line names a new folder or file, write one base per line to FILE, by the convention
`<feature>-m<milestone>-<part>` (never a counter such as `gaps1`), name the whole batch in one pass and use the names it
prints (brief #1442, ADR-0603); one new brief alone uses `next --base PATH` instead.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/plan_names.py" batch FILE
```

Before the brief is checked, study it (brief #1800, ADR-0752). Print the earlier record its `Touches:` and `Wiring:`
lines meet (ADRs, specs, unapplied amendments and overlapping open briefs), read each one, and fill the brief's
`Impact:` block (`Speed:`, `Quality:`, `GitHub:`, `Cost:`, `Tests:`), `Wiring:`, `Prior:` and `Class:` lines.
Each candidate ends `strong` or `weak`, the strong ones first (brief #1819); `Prior:` names the records of the same kind,
each with why, and never lists records read and found unrelated. The check warns for at most `[flow] brief_prior_warnings`
(10 when unset) strong ones:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/brief_study.py" BRIEF --root .
```

Write one line `Existing:` before the Answers (brief #2052, ADR-0850; a project's too, brief #2065, ADR-0857), searching
in this order: the project's own code and tests; its decisions, specs and open briefs; its parts (`docs/parts.md`, else
the build files' dependencies); the kit features and packs in use. Write an item `- <path>:<line> (<name>): <what it
does>; not enough: <unused, blocked, defeated, partial or why>` for each script, function or setting that already does part of the job, or `Existing: none: <the search>` with the
backquoted `grep`, `git grep`, `rg` or `brief_study.py` command and its `<n> matches`. The study prints each script,
function and setting the brief names as `code <path>:<line>: <term>`, and the check warns on each one `Existing:`
leaves out. A kit feature with no file in the project is named by its command in backquotes, without a line.

Then fit it to its specs (brief #2002, ADR-0828). For each Approved spec its Answers name, or whose `- Requirements:`
line names a requirement of its `Advances:`, open the spec and read every rule the Answers touch, above all each rule
with a limit, `only`, `never` or `at most`. Write one line `Spec fit: SPEC-<nnnn> rule(s) <list> within` naming every
rule of that spec the brief names. Where the brief needs what a rule does not allow, write `rule(s) <list> change by
amendment <m>` instead of an answer that departs, reserve the amendment in `Reserved:` and quote its items right
under the line (`> 1. ...`, each with its `> Class:` line); the person's filing yes approves it only when it names it
(`Yes, file the <NAME> brief with amendment <m>`). The check cannot tell whether a `within` is true: you read it.

Then check each saved brief before it is filed:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_brief.py" BRIEF --root .
```

Do not commit or push.
