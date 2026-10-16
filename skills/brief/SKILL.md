---
name: brief
description: Start a brief from docs/briefs/TEMPLATE.md (new_spec.py). Writes one new file.
disable-model-invocation: true
argument-hint: "TITLE"
---

# /agk:brief

Create one brief in `docs/briefs/` from `docs/briefs/TEMPLATE.md`. The script runs in the repository root and refuses to
overwrite.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/new_spec.py" brief "TITLE"
```

Then help the user fill in the items; the maintainers decide their content. Do not commit or push.
