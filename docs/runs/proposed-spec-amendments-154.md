# Proposed spec amendments 154 (SPEC-0057; REQ-064)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). SPEC-0057 rule 8 names
this route and brief #879 builds it; it changes `docs/specs/0057-the-kit-proposes-a-repository-s-work-type-and-stack-and-a-person-confirms.md` once the owner's `Approve:` line approves it, and no Approved spec is edited in this pull request.

1. **SPEC-0057 rule 8, the words on the one list.** "When it lands, the manifest list of its rule 10 and the table of rule 5
   are one list: build (d) makes it so, by the survey reading the table or by an amendment the build proposes." becomes "When
   it lands, the survey reads the manifest list of its rule 10 from the table of rule 5, and the two are one list, except for
   the manifests the survey holds and the table has no stack for (`composer.json`, `*.csproj`, `Gemfile`; SPEC-0041 rule 10
   names only `*.csproj`, among its examples), which stay in the survey and give `detect` no proposal."
2. **SPEC-0057 rule 3, the `tests:` line.** "`tests: <folder> patterns <pattern> (from <source>)`" becomes
   "`tests: "<folder>" language <language> files <n> (from <source>)`", since rule 8 moves the source to a detector that
   returns files and languages, not patterns.
