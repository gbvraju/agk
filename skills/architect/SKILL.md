---
name: architect
description: Print how to start the architect session (claude --agent architect) and check its prerequisites, read-only. Writes nothing.
argument-hint: ""
---

# /agk:architect

Show how to start the architect role of the playbook and check what it needs. This command reads and writes nothing.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/playbook.py" architect
```

The script prints the command that starts the role, `claude --agent architect`, and checks read-only that `agk.toml` is present, that
`gh` is logged in and which branch is the default. Show its output.

If the role cannot be started that way (for example in a session that is already running), the same instructions are in
`.claude/agents/architect.md`. Read that file and follow it in this session, and say plainly that in this session the tool list and the
guard hook of the role are **not** enforced: only the rules of the file bind you.
