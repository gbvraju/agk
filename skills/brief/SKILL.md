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

Then check each saved brief before it is filed:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_brief.py" BRIEF --root .
```

Do not commit or push.
