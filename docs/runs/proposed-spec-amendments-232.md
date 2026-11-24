# Proposed spec amendments 232 (SPEC-0054; REQ-061)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0789 (brief #1907), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0054-every-dependency-is-scanned-and-listed-in-a-standard-bill-of-materials.md` (rules 2 and 3 and its
`## Tests` section). This file proposes the lines and does not edit the spec. A later pull request applies them word
for word, on a person's `Approve: SPEC-0054`; no session posts it (`Q-SB-1`).

The sentence (brief #1907): "An adopted Node product makes its bill of materials: with a chosen node stack and no
pyproject.toml at the commit, the bill takes the product's name from package.json and lists its lock; every other
repository, the kit's own included, reads pyproject.toml as today."

## Items

1. **SPEC-0054 rule 2, after "A file the bill reads that cannot be read at the commit, or that cannot be parsed, is
   refused naming the path class, and no bill is written."** Add: "In a project with a `[delivery] work_type` whose
   chosen stack is `node`, a `pyproject.toml` absent at the commit is not read and lists nothing; elsewhere it is
   refused as a file the bill reads" (amendment 232).
2. **SPEC-0054 rule 3, "`component`, the repository's kit or project name with its `version` of `agk.toml`".**
   Replace with: "`component`, the repository's kit or project name (the `[project] name` of `pyproject.toml`, else, in
   rule 2's `node` case, the `name` of `package.json`) with its `version` of `agk.toml`" (amendment 232).
3. **SPEC-0054 `## Tests`, one line.** Add: "A `node` project with no `pyproject.toml` gives a bill named from
   `package.json` that `check` accepts, and a repository with no work type and no `pyproject.toml` is refused naming
   `pyproject.toml` (amendment 232)."

No other rule changes.
