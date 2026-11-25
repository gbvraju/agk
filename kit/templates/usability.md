# Usability

The usability record of the product's screens (SPEC-0073 rule 8; SPEC-0038 rule 10). For a `web-app` or `mobile`
project, `check_design.py` reads it beside the prototype: one `## <version>` section per prototype or imported version
(`v<n>` or `i<n>`), and in it one `### <screen id>` per screen of `docs/design/inventory.md`, each with the ten lines
below in this form. Each line is `pass`, `finding: <what the screen gets wrong>` or `not applicable: <reason>`. A
finding never fails the check by itself; fixing it is the design's. The newest version must have its section; an older
section stays as it was. The file lives outside the version folders, so a signed-off version stays frozen.

| Heuristic | What the screen is asked |
| --- | --- |
| `status` | Does it show what is happening (loading, saved, offline) in time? |
| `real-world` | Does it use the person's words and order, not the system's? |
| `control` | Can the person undo, go back or leave without loss? |
| `consistency` | Does it follow the standard's patterns and the other screens? |
| `error-prevention` | Does it stop a mistake before it happens? |
| `recognition` | Are the options in view, so nothing must be remembered? |
| `flexibility` | Is there a faster way for a frequent user? |
| `minimal` | Does it show only what the task needs? |
| `error-recovery` | Does an error say in plain words what went wrong and how to fix it? |
| `help` | Is help or an example there when the task needs one? |

## v1

### <screen id>

- status: pass
- real-world: pass
- control: pass
- consistency: pass
- error-prevention: pass
- recognition: pass
- flexibility: pass
- minimal: pass
- error-recovery: pass
- help: pass
