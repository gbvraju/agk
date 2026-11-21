# Proposed spec amendments 206 (SPEC-0054; REQ-061)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0676 (brief #1596), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0054-every-dependency-is-scanned-and-listed-in-a-standard-bill-of-materials.md` (rules 2, 3, 4 and 6 and the
`## Tests` section). Brief #1596 reserved amendment 206. This file proposes the lines and does not edit the spec. They are
applied word for word, on a person's `Approve: SPEC-0054`; no session posts it.

The sentence (brief #1596): "A product's own dependencies are listed in a standard bill of materials from its lock file,
each licence is checked against an allowed list, and known weaknesses are reported in one issue, so a forbidden licence
or a weak version never goes unseen."

## Why

On the default branch at 11fa8bc (2026-11-21) rule 2 reads no lock file, rule 4 runs no check in governance and no rule
reads a dependency's licence (gap G18, brief #1596).

## Items

1. **Rule 2, one class added after `kit-file`.** "- `python` or `node` from the lock: in a project with a `[delivery]
   work_type` and one Accepted stack record, each package of the chosen stack's committed lock (`requirements.lock`,
   `package-lock.json`; ADR-0672), with its exact version and its licence, the lock's where it states one, else the
   record's `Parts:` entry of that name; a lock entry replaces the `pyproject.toml` entry of the same reference. A
   repository with no work type, the kit's own, reads no lock." The words "a lock file of another tool" in the rule's
   first sentence become "a lock file other than this class's".
2. **Rule 3, the component fields.** `licenses` is added after `hashes`: one CycloneDX expression,
   `[{"expression": "<SPDX expression>"}]`, where the class states a licence; `type` `library` for `node`; the package URL
   `pkg:npm/<name>@<version>`.
3. **Rule 4, its last sentence becomes:** "In a project with a chosen stack and its lock, the gate runner of SPEC-0072
   runs the `bom` step, the bill of `HEAD` made and checked in memory, and the `licences` step, which fails on a package
   licence outside `allowed` of `config/licences.toml` (absent: `kit/templates/licences.toml`, written once by the
   foundation; widening it is a project ADR) and on a package whose licence it cannot read, as `unknown`, each line
   naming the rule and the component class, a list of another form refused naming the setting; with `mode = "adopt"`
   its findings are held until the baseline. Elsewhere, the kit's own repository included, no governance step,
   `make governance` or `prepush.py` runs it (`Q-S0054-5`)."
4. **Rule 6, one sentence added at its end (on the owner's yes to Q-1596-2).** "Where no workflow runs (`execution =
   "local"`, the clean layout), the same pinned scanner runs weekly and on each lock change as a scheduled job of the
   supervisor (SPEC-0064) on the person's machine, outside every check; its result is read by rule 7 and opens or edits
   rule 8's issue, and in personal mode it stays in the sidecar and nothing is posted."
5. **The `## Tests` section, one line added:** "- Rules 2 and 4, the product: a fixture lock gives a bill `sbom.py check`
   accepts; an invented licence off the list, and a package with no licence as `unknown`, are red naming the class; a
   list of another form is refused naming the setting; no check opens a socket; REQ-061 AC2, REQ-079."
6. **Unchanged:** rules 1, 5 and 7 to 10, the Proof, the Residual and the Open questions.

## Questions (brief #1596), each with the reading this proposal takes

- Q-1596-1: the template's allowed licences. Reading: `MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, `ISC`,
  `PSF-2.0`; `MPL-2.0` and `LGPL` are asked of the person with their effect, not listed. A policy, not legal advice.
- Q-1596-2: the local scheduled scan (item 4). Reading: not built until the owner says yes.
- Q-1596-3: does a lock record licences? Reading: `package-lock.json` entries may carry `license` `(verify: per npm
  version)`; `requirements.lock` carries none, so the record's `Parts:` gives it, else `unknown` and red.
- Q-1596-4: new `[[gates]]` rows in `default.toml`? Reading: no; the runner runs the steps as it runs `layers`, because a
  new row changes SPEC-0072 rule 2's and SPEC-0048 rule 21's fixed gate lists, which this amendment does not reach.
