---
name: doctor
description: Report what is misconfigured in a repository governed by agk (agk doctor). Read-only.
argument-hint: "[OWNER/REPO]"
---

# /agk:doctor

Report the repository's ruleset, required check, placeholder team, drift-audit workflow, kit version, vendored files and
`[engines]` (each engine present, absent or missing; an engine only drafts and never decides).
The script reads GitHub with the user's own `gh` (GET only) and writes nothing. It prints `??` for a check it could not
make, never `ok`.

Run it from the repository root. `--kit-root` is this plugin, so each vendored file is compared with the plugin's copy:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/doctor.py" --kit-root "${CLAUDE_PLUGIN_ROOT}"
```

Add `--repo OWNER/REPO` when the repository cannot be read from `origin`. Show the report, then explain each `FAIL` and
each `??` in plain words: which setting or path class it names and why it matters. When the plugin version and the
version in `agk.toml` differ, the report says so: suggest `/agk:upgrade`. Do not run the fix that a line prints and do
not change any setting; the change is the maintainers'.
