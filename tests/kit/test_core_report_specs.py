"""The small weekly-report specs are sections of SPEC-0011 (brief #385, ADR-0244, REQ-039).

SPEC-0014, 0015, 0016, 0017, 0019, 0022, 0024 and 0026 each added one detail to the weekly product
report of SPEC-0011. Their 72 rules move into SPEC-0011, one section per spec in the order the specs
were approved, the text unchanged after the number (answers 1 and 3); each old file keeps its
number and its history and holds one pointer line per old rule, `N. Now SPEC-0011 rule M.`
(answer 2); the change is one spec amendment that `check_specs.py` accepts (answer 5). The text
before the change is pinned by the SHA-256 of each rule, so the test needs no history; where the
history holds the base commit, the digests are read back from it as well. Files and git only: no
network, no model.
"""

from __future__ import annotations

import hashlib
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "docs" / "specs"
CORE = "docs/specs/0011-inbox-and-report.md"
AMENDMENT = "docs/runs/proposed-spec-amendments-108.md"
# The default branch before the change (brief #385 was built on it).
BASE = "ebc556fe063b1ece17cb3e4adb4a70e44b2672ff"
CORE_RULES = 23  # SPEC-0011's own rules keep their numbers 1 to 23

NUMBERED = re.compile(r"^(\d+)\. ")
POINTER = re.compile(r"^(\d+)\. Now SPEC-0011 rule (\d+)\.$")

# The eight specs in the order they were approved (ADR-0050, 0051, 0057, 0058, 0063, 0070, 0078,
# then SPEC-0026), each with the SHA-256 of the text of each of its rules after `N. `, before the
# move.
MOVED: dict[str, list[str]] = {
    "0014": [
        "ce4bc2b2c0e449649669d0d1a9a42aa49cba3850ddc6fff4a29186fe6b16a1fc",
        "8be9ce7972c4e38fd684a451013aa37469a2b276f5219b41f3ac922e795a9b5b",
        "7756d4d96414cfb853964e1f9515f19374f6fc4dc8531e6a96c2939cebecb595",
        "9d924641f06a7eaa1c01b4e0ce3f032bacf81948b8d0a728d782b880e3f2aa86",
        "0b0effa28697a9f8934a20273e140889fec0daa2cf9f1916ca13e310ad321a67",
    ],
    "0015": [
        "babdfd9b5c31a273fdef5d7ef1bdf8cc5faa624f10d9ca31f299a3cfce6cffc3",
        "fed80608afac159a8a291fac8108223ed261ec3c3773bb8d967e65e1e72bce0a",
        "8d9d3531e7cdeacfef30f69d467f22e8265839e5f275823e4beafa45036c55ff",
        "4d576b8c038823948a57c9d50e1ce425303f189d5fe454106cefdea18ecc867b",
        "218d696052a02ba5d7c7340b59b4714bc5e93df8c648389dfdcffe809b9cf43e",
        "2eae7b1892f4dc51ebc1735f395069965001638b7e5c2977a8e474f585d7bde7",
        "7488ed3f4ea22e6e3285d299dd253757e5955f7b3db765113782a1614725b1ff",
        "0a3fdc430c6ba583a5c423e5517793b347089bb63d3c32b6891b18d6b39ac8b4",
    ],
    "0016": [
        "d7d685a4198566da48a336e93a58b2781760bb84f2c89db3691f92934eb32a69",
        "62caf9367d1b4dd3a601290fc7bf860eec261734085e48cab37cc2c6c96c02ef",
        "e5679ed44f2347dfc01257863cb3f781fd37e98a0d689d124530f6f775ab63f2",
        "00f1aeb8bba842f2d2d221550aa855714495ce86fef82cfc4de23c78cf5446fc",
        "b38335f22fea12f2c47c03d59256441254cd88d287ab54821a5d80b85990303f",
        "4a0ed3f43cbc3b9e00ab322d75e05a51bd2a87d71d20731b0720f84f105d4405",
        "62550afd34448ee023e39174c39b349a1b0c6a973f7423e6ba9492f1ab68d137",
        "a9b9b06da60e5487c4b5c4437a98a320ca61a51eb1c6aed27b78b528fd5a687e",
        "d53ac5f44acbc2e0fd73979d1c338bae52e6809d4e20c6567e1eddf1510a1742",
        "0609198fd7d10c2045163ae7b16551db2e5ce54b4e52d2b1ea5e07581c13c0ce",
    ],
    "0017": [
        "2a10ec6626d028a039194b21d2872eda6bafa31e49110d9d0464306f96593caf",
        "b0cd6cf0ffb8c7e5603ca922ded5bfa5cfe3619853baa5b797180737e1550c0e",
        "67b5649b2894e683bac1ae60f6bb9a00efd454db22d2e3a1568df5e8777b6f9b",
        "c2c2b1a7aeb36a353b3d364830100aaf8703fd34bea5f70318fb42a8a92c717e",
        "6918c14696303318bddc7fb33894ad29c16bd77bd49e86eb0e74e8e985c6679f",
        "13a29f18bea48cee670ddd6cd40c3594933b5ce0f2daa50212e46f826058fead",
        "c8c8692becfa3af45a8254fb56f397bb80389bd6ded80578ba780a097c363ccb",
        "4686250e03e7b525fd48f260266e3bd7252d8a2d162d7101e1437c6286fb82f0",
        "1bd988a589e3c48fbd50a707cdff5dc022bea385c70fd9c54cd6d3b50587b618",
    ],
    "0019": [
        "526d755a3b6f24764caba9ee2e71750dd00a440a3a4ef7c53a3617640846082a",
        "9e40d081f02346080aef4270ee697873a2c50806784ed254d8c7357282d276ab",
        "cd3d5c87cb858a10bcc61c3fff699b52fdc34ec7221ec4a0a2f48a88fbc45d94",
        "a55e214c6e6612b11124ebc32f8a8cb45c812ccc9c0cf9ef0b89c6cfd50e99d2",
        "7926e6acb4fd9f05f32d14a4183897a74a49632e7c3c6989a33f586b61bdb7b2",
        "bc54a1015e302993e8f98ce3fc0e20e4483985a84be6dcc7e69253f7ff278e30",
        "29701541d0d7bbe0c3f470197c9db1ba7df41ec6f7a974a1f29c5fe793e02e33",
        "abdc6041ea5ac655afe949b0256b0dd7b6d0ed9408fb25c078e65982ee178cfc",
        "f68de188d3db541cdc86c1dfda6b34536c17ab79145bf37928fbbc5d6f86a16c",
        "9caaf98b63f7a95661b5141a9762bc556699fead692a8cde729f02aeeede3ce1",
    ],
    "0022": [
        "f3c4602b17dfc31cb5ac8fc4e22630102ffd1df522dde18ca157f9daea4859bd",
        "5106b7c29ec2217b91f258293cd6738bed6172d9be7ca723d324d4897dfa00c4",
        "a7d3bf88d3928334fe324d627797c6930ad1a40dfc702cc6173420d4f4ae6acf",
        "1a6ea752a7d29401ca89a53424fdfa876d57df57514a95e80d0942d7420c4a09",
        "431b54e3d94d7071a470d40e98dbf44e4bd939f40a0670b0f5e993a23fce28ac",
        "3cac89d504ebf8d40d036bae97479aacde7ab194304b86d3c540a6e4a50189e8",
        "ecf651a99b95dde623b8a0568933d614f5333653a9c5fb7beaae37ae1306d1f2",
        "33bd1f25f965793999e6e4eff7e7295517ec98e1c59c20d470627b581fd0a844",
        "e76158b98e19d851a2b7e67a02c42db9d946b2f1fc1eab5c694f0fbdf7b344bd",
        "3b19ce3734ccb23cf7caa7132f98ed946d59edb087a90b0ceceb772cfb1c37f1",
        "49102e4a6d4c67e49983e9ff966b77fdd27eb44ee41dccdc11bbcafe796aeb42",
        "03d4dcddb7e089ed3f3f97020ca176fa68e92405778da68421073b1045c6b65c",
    ],
    "0024": [
        "9ee6d9140dfb3b2a55ad8a2c4a60953a7da1a67e4affc53fb04dbdb99e7d8f50",
        "2bea3f8d5d4183edc50d54cc579e2c0050e8235f7e617ed09771bf6be1602643",
        "cc27244e8de818b6e516969aec135a20164e03a40d7d2245c780685f31a144ad",
        "0a43cc84f64e4fcf4b6a23910d4bba83d68c253401706e0759c0482915b876ad",
        "4402f443f0f36bb86eb1a138e87cb442eee4ef5cc038f6fe51e6418e51f520b7",
        "28097b22bc4cbc0cd49ff8d736a6473bd114ad2268362663f6872ffe8b1e8cb6",
        "dbcaa4cf2e2764455b33412f85a11d0c1cfcad6194b4c0baa5df8c3fec873cb8",
        "e3e3b1842b3d8c9567123dfb6ccf6c201ede32ad4c4f448f70cca0700b98902f",
    ],
    "0026": [
        "552cddf26a9d06624833da0f83b27cb500ea3024cf12a3c402964eee13e3ea5a",
        "86c975a91b4f3a9016d9df0863a4d196d583e7038c996a1ac99d064780cb5e88",
        "d1d5f25b5882b1a6da1e28ab441e8725a896d15209d9014d184a4c126d26044b",
        "ef1083872d2a2d5fbb1b5d6e541f9a48595e26f71eb50ada4b68e3e55a9d4f76",
        "52b60b9626417452ac3615c5fc4595674199eb09129bd8ed895326f54e8794a4",
        "b7854985abef0ba2a3ee554bf62b6d17bac34a58fd7240737178f5dcf2129f27",
        "d84b90d7ee2261275710b01448effb4391c7ab1512fc5fc1bf1e57fb0064710a",
        "d7de9a2b31bff4abf9ff65d9a4ed224eb9c20a5b59091d3938cb30f01e941dc9",
        "260c1c0b3d1b8bb27e5e6ce35071ca0950678a3e5124c7595dcaedbdb491d48f",
        "1d8d5d214881e0bc7d9c8a37d025f004e61ece710bce9e19b01d58840032adf5",
    ],
}


def spec_path(number: str) -> Path:
    found = sorted(SPECS.glob(f"{number}-*.md"))
    assert len(found) == 1, f"SPEC-{number}: one file expected"
    return found[0]


def rules_of(text: str) -> dict[int, str]:
    """The numbered rules of the `## Rules` section: number -> the text after `N. `.

    A rule runs to the next numbered line or heading; its trailing blank lines are not part of it.
    """
    rules: dict[int, list[str]] = {}
    current: int | None = None
    inside = False
    for line in text.split("\n"):
        if line.startswith("## "):
            inside = line.strip() == "## Rules"
            current = None
            continue
        if not inside:
            continue
        if line.startswith("### "):
            current = None
            continue
        match = NUMBERED.match(line)
        if match:
            current = int(match.group(1))
            assert current not in rules, f"rule {current} appears twice"
            rules[current] = [line[match.end() :]]
        elif current is not None:
            rules[current].append(line)
    return {n: "\n".join(lines).rstrip("\n").rstrip() for n, lines in rules.items()}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def start_of(number: str) -> int:
    """The number in SPEC-0011 of the first moved rule of a spec."""
    first = CORE_RULES + 1
    for spec, digests in MOVED.items():
        if spec == number:
            return first
        first += len(digests)
    raise KeyError(number)


def core() -> dict[int, str]:
    return rules_of((ROOT / CORE).read_text(encoding="utf-8"))


def test_seventy_two_rules_move():
    """REQ-039: brief #385, the sentence (72 rules of eight specs)."""
    assert sum(len(d) for d in MOVED.values()) == 72


def test_every_rule_of_the_eight_specs_is_in_spec_0011_byte_for_byte_after_its_number():
    """REQ-039: brief #385 answers 1, 3 and 5 (text unchanged, in approval order)."""
    rules = core()
    for spec, digests in MOVED.items():
        first = start_of(spec)
        for i, expected in enumerate(digests):
            number = first + i
            assert number in rules, f"SPEC-0011 rule {number} (SPEC-{spec} rule {i + 1}) is missing"
            assert digest(rules[number]) == expected, (
                f"SPEC-0011 rule {number} differs from SPEC-{spec} rule {i + 1}"
            )


def test_spec_0011_numbers_its_rules_once_and_keeps_its_own():
    """REQ-039: brief #385 answer 1 (never renumber; SPEC-0011 rules 1 to 23 keep their place)."""
    rules = core()
    assert sorted(rules) == list(range(1, CORE_RULES + 1 + 72))
    text = (ROOT / CORE).read_text(encoding="utf-8")
    assert "\n- Status: Approved\n" in text  # the pull request approves nothing (answer 4)


def test_each_moved_section_names_its_spec():
    """REQ-039: brief #385 answer 1 (a new section per spec)."""
    text = (ROOT / CORE).read_text(encoding="utf-8")
    for spec in MOVED:
        first = start_of(spec)
        heading = re.search(rf"(?m)^### From SPEC-{spec}: .*$", text)
        assert heading, f"no section for SPEC-{spec}"
        after = text[heading.end() :]
        assert re.search(rf"(?m)^{first}\. ", after), f"SPEC-{spec}: its rules follow its heading"
        assert f"SPEC-{spec} rule N is rule N + {first - 1} here" in after.split("\n### ")[0]


def test_each_old_spec_keeps_its_number_and_points_every_rule_to_one_that_exists():
    """REQ-039: brief #385 answers 2 and 5 (one pointer line per old rule; no number reused)."""
    rules = core()
    for spec, digests in MOVED.items():
        text = spec_path(spec).read_text(encoding="utf-8")
        assert text.startswith(f"# SPEC-{spec}: ")
        assert "\n- Status: Approved\n" in text
        section = text.split("\n## Rules\n", 1)[1].split("\n## ", 1)[0]
        lines = [line for line in section.split("\n") if line.strip()]
        first = start_of(spec)
        assert len(lines) == len(digests), f"SPEC-{spec}: one line per old rule"
        for i, line in enumerate(lines):
            match = POINTER.match(line)
            assert match, f"SPEC-{spec}: line {i + 1} is not a pointer"
            old, new = int(match.group(1)), int(match.group(2))
            assert old == i + 1 and new == first + i
            assert new in rules and digest(rules[new]) == digests[i]


def test_the_digests_are_those_of_the_rules_before_the_change():
    """REQ-039: brief #385 answer 5 (the rules before the change), read from the base commit."""
    known = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "cat-file", "-e", f"{BASE}^{{commit}}"], cwd=ROOT, capture_output=True
    )
    if known.returncode != 0:
        pytest.skip("the base commit is not in this history; the digests stand alone")
    for spec, digests in MOVED.items():
        rel = spec_path(spec).relative_to(ROOT).as_posix()
        old = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "show", f"{BASE}:{rel}"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout
        rules = rules_of(old)
        assert sorted(rules) == list(range(1, len(digests) + 1))
        assert [digest(rules[n]) for n in sorted(rules)] == digests, f"SPEC-{spec}"


def test_the_amendment_names_every_changed_spec():
    """REQ-039: brief #385 answers 1 and 6 (one amendment file)."""
    text = (ROOT / AMENDMENT).read_text(encoding="utf-8")
    for path in [CORE] + [spec_path(s).relative_to(ROOT).as_posix() for s in MOVED]:
        assert f"`{path}`" in text, path
    assert "ADR-0244" in text


def test_check_specs_accepts_the_change_with_the_amendment_and_refuses_it_without(repo):
    """REQ-039: brief #385 answer 5 (`check_specs` passes)."""
    paths = [CORE] + [spec_path(s).relative_to(ROOT).as_posix() for s in MOVED]
    now = {p: (ROOT / p).read_text(encoding="utf-8") for p in paths}
    repo.commit({p: text + "\nbefore\n" for p, text in now.items()}, "base")
    repo.branch()
    repo.commit(dict(now), "move")
    refused = repo.run("check_specs.py", "--base", "main")
    assert refused.returncode == 1
    repo.commit({AMENDMENT: (ROOT / AMENDMENT).read_text(encoding="utf-8")}, "amendment")
    accepted = repo.run("check_specs.py", "--base", "main")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
