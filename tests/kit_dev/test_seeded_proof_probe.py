"""A seeded probe for the proof check (SPEC-0010 rule 20); not to be merged.

It passes on `main` as it is, so a pull request that adds only this file must read
`not-proven (green-on-base)`.
"""


def test_the_probe_passes_without_any_change():
    assert sum([1, 2, 3]) == 6
