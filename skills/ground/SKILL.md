---
name: ground
description: Ground the rule set by the tools that exist (agk ground): measure, sort every rule, plan the cut, ask the owner once, apply on a yes, re-measure.
disable-model-invocation: true
---
<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->

# /agk:ground

Grounds the rules an agent reads by the tools that exist (brief #2094, ADR-0875). It builds no measure and no cutter:
each step runs an existing command. The steward runs it monthly and before any pull request would raise a line of
`config/rule-budget.txt`. A session that finds two rules that contradict runs steps 1 and 2 only, read-only, and posts
the finding as a `Question:` (a builder) or a `Triage:` (the steward), never a cut. A project grounds its own rules only.

The commands below are the plugin form (`[kit] layout = "plugin"`); in an installed project run the project's own copy,
`python3 scripts/agk/<script>.py` with the same arguments. Every read is GET only. Dates come from `date -u`.

## 0. One at a time

When an open pull request or brief of an earlier grounding exists (its title starts `Grounding:`), stop and say so:
one grounding at a time.

## 1. Measure

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/rules.py" budget
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/rules.py" consolidate --plan
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/rules.py" dropped --since YYYY-MM-DD
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/metrics.py" --signals
```

`--since` is 30 days ago. Keep the `before:` line of `consolidate --plan`. In the kit only, also read:

```
python3 scripts/agk/core_audit.py --since YYYY-MM-DD
```

(when a `core_audit --write` page of today exists, read it instead), the newest `agk-drift-audit` issue, the `EXPECTED`
table of `tests/kit/test_role_commands.py`, and the method of `docs/runs/core-overlap-1.md` for duplicates. In a
project `core_audit` is `cannot-check (kit-only: core_audit)` and the before figure is `rules.py budget` alone.
With `execution = "local"`, `core_audit`'s check counts are `cannot-check` and the signals' log and run rows
`unknown (setting: execution)`, so none of them makes a rule unused.

## 2. Sort

Every rule line and paragraph of the files `[rules] files` names goes into exactly one class:

- **checkable**: a check, test or guard can refuse the case. The check takes it, its refusal names the rule and the
  text goes: `retire <check>` when the check exists, else one brief for the check first.
- **judgement**: kept, at most two sentences; a longer one is shortened.
- **duplicate**: merged into one; the other keeps its number as `N. Merged into <file> <m>.` (ADR-0243).
- **unused**: retired only on all of zero citing verdicts in `core_audit`, zero `dropped` items, no check, test or
  guard naming it, and its feature not `used` in the signals. A count `unknown` or `cannot-check` is never unused.
- **contradicting**: fixed so one text stands; when two decisions disagree the owner chooses, never this skill.

A rule that `config/core-rules.md` names, or a check's refusal cites, keeps its number with a pointer. With
`rule_tags_from` set, untagged fix-list items before its date are references only; say `untagged: <n>`.

## 3. Plan

Write the rows into `config/rule-plan.txt` of a scratch copy of the default branch, in its own format
(`<file> <n> retire <check>` or `<file> <n> guide`), never in the project, and print them with their hash:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/rules.py" consolidate --plan --root SCRATCH
```

Merges, fixes, bullets and paragraphs, which the format cannot name, are hand edits listed as `<file>:<line>`. In a
project, a row on a file the plugin's `kit/manifest.json` `verbatim` list holds is a kit finding: send it with
`steward_evidence.py triage` as an `agk-kit-defect` issue, never into the product owner's list:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/steward_evidence.py" triage --finding FINDING.json
```

An empty sort: record the note of step 6 saying so; no brief, no pull request.

## 4. Packet

One owner question: the three choices, the recommendation, the words and rule lines before and after, each row's
class and evidence, the cost and how it is undone (a revert of one pull request; every number keeps a pointer), as
kit impact and project impact in the kit, project impact only in a project:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/steward_owner.py" ask --qid Q-GROUND --file PACKET.md
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/steward_owner.py" park --pr N
```

`park` parks an unanswered packet past `[flow] owner_wait_minutes`. `review_mode = "solo"`: the one person's yes;
`"team"`: a `spec_approvers` login's yes. `[personal] forge = "files"`: the packet is printed only.

## 5. Apply

On the owner's yes, file one brief titled `Grounding: <date>` under the short name you offered, with the owner's
recorded words (`--said`, the file of their yes, and `--at`, its UTC time; add `--by LOGIN` in team mode), so it
carries the `Owner said` line that a `Priority:` above `[steward] auto_file` needs:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/steward_owner.py" file-brief --file BRIEF.md --title "Grounding: YYYY-MM-DD" --said SAID.txt --at YYYY-MM-DDTHH:MM:SSZ --name NAME
```

Its builder writes the plan, runs `--plan` (the same hash) and the apply, makes the listed hand edits and opens one
pull request with its ADR naming each path class:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/rules.py" consolidate --plan
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/rules.py" consolidate --apply --hash HASH
```

When the default branch moved, `--apply` refuses the changed hash: run `--plan` again, and when a row no longer
names its rule, post a `Question:` instead of applying. A dirty tree, or a `retire` whose check is missing, is refused.

## 6. Re-measure

After the merge, run `consolidate --plan` again and record the note (personal mode: in the sidecar):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/rules.py" consolidate --plan
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/steward.py" record --kind Note --text "grounding YYYY-MM-DD: W0 to W1 words, R0 to R1 rule lines"
```

The note reads `Note: grounding <date>: <w0> to <w1> words, <r0> to <r1> rule lines`; the weekly metrics count it.
