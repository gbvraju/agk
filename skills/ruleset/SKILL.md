---
name: ruleset
description: Apply the kit's branch ruleset and two repository settings to the default branch with the caller's own gh login (add-only, two phases). Shows the plan and asks before it writes.
disable-model-invocation: true
argument-hint: "[--phase 1|2|auto] [--repo OWNER/REPO]"
---

# /agk:ruleset

Protect the default branch with the kit's ruleset (ADR-0001 decision 3) and set the two repository settings (allow auto-merge,
automatically delete head branches). Phase 1 is every element except the required status check `governance`; phase 2 adds it once
`governance` has succeeded on the default branch. The credential is the person's own `gh` login; none is stored or asked for.

1. Make a temporary directory for the payload files (for example with `mktemp -d`) and print the plan. This reads with GET only and
   writes nothing to GitHub:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/ruleset.py" plan --payload-dir DIR
```

2. If the plan says the ruleset cannot be applied from here (not an admin, a private repository on a plan without rulesets, `gh`
   missing or not logged in), it prints the cause, the rules of the phase it chose and the place in the settings; show that and
   stop. Do nothing else.
3. Show the plan to the person: the phase, each finding and each numbered command. A finding is a value looser than the kit's or a
   bypass actor; it changes only if the person asks for it, by running the plan again with `--tighten`. Never pass `--tighten` on your own.
4. Ask the person whether to apply the plan. Only after a clear yes, run the commands the plan printed, one by one, exactly as printed
   (`gh api --method POST|PUT|PATCH ... --input FILE`; each names the repository). Run no other write.
5. Print the plan again. It must say `nothing to do` (or only the findings the person left alone).

The plan is add-only: it never removes a rule, a setting or a bypass actor. Do not commit or push.
