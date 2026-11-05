"""Tests of the data guard's detectors, scan_text and the [guard] table (SPEC-0042 rules 1 and 10).

Every value is invented: example.com addresses, the published Visa test number, an Aadhaar-shaped
number that passes the Verhoeff check and belongs to no one, and key-shaped strings built here
from a fixed seed, so no secret-like constant sits in this file.
"""

from __future__ import annotations

import json
import random
import string
import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

import guard
import pytest

import config

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
RNG = random.Random(561)  # a fixed seed: the same invented values on every run


def made(alphabet: str, n: int) -> str:
    return "".join(RNG.choice(alphabet) for _ in range(n))


B64 = string.ascii_letters + string.digits
HEX = "0123456789abcdef"
CARD = "4111111111111111"  # the Visa test number the card networks publish (Luhn-valid)
AADHAAR = "2345 6789 0124"  # Verhoeff-valid, invented
PHONE = "9876543210"  # an Indian mobile shape, invented


def kinds(text: str, **kw) -> list[str]:
    return [f.kind for f in guard.scan_text(text, **kw)]


# --- rule 10: true positives --------------------------------------------------------------------


def test_ac3_each_personal_kind_is_found_with_its_position_and_never_its_text():
    """REQ-049 AC3: rule 10 (EMAIL, PHONE, CARD, AADHAAR, PAN, IP)."""
    text = (
        f"mail person@mail.example.io\nphone +44 20 7946 0958 and {PHONE}\n"
        f"card {CARD}\naadhaar {AADHAAR}\npan ABCDE1234F\n"
        "ip 10.1.2.3 and fe80::1ff:fe23:4567:890a\n"
    )
    found = guard.scan_text(text)
    assert [f.kind for f in found] == [
        "EMAIL", "PHONE", "PHONE", "CARD", "AADHAAR", "PAN", "IP", "IP",
    ]  # fmt: skip
    first = found[0]
    assert (first.line, first.column, first.length) == (1, 6, len("person@mail.example.io"))
    assert "person" not in repr(first)


def test_ac3_card_spaces_and_dashes_are_allowed_and_luhn_decides():
    """REQ-049 AC3: rule 10 CARD."""
    assert kinds("4111 1111 1111 1111") == ["CARD"]
    assert kinds("4111-1111-1111-1111") == ["CARD"]
    assert kinds("4111111111111112") == []


def test_ac3_aadhaar_verhoeff_decides_and_the_first_digit_is_two_to_nine():
    """REQ-049 AC3: rule 10 AADHAAR."""
    assert kinds("234567890124") == ["AADHAAR"]
    assert kinds("2345 6789 0125") == []
    assert kinds("1345 6789 0124") == []


def test_ac3_indian_phone_prefixes_and_international_lengths():
    """REQ-049 AC3: rule 10 PHONE."""
    assert kinds(f"+91{PHONE}") == ["PHONE"]
    assert kinds(f"0{PHONE}") == ["PHONE"]
    assert kinds("5876543210") == []  # an Indian number starts 6 to 9
    assert kinds("+1234567") == []  # 7 digits: too short for an international number


def test_ac3_jwt_needs_a_json_header_with_alg():
    """REQ-049 AC3: rule 10 JWT."""
    import base64

    def part(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    token = ".".join([part({"alg": "HS256"}), part({"sub": "x"}), made(B64, 30)])
    assert kinds(f"t {token} end") == ["JWT"]
    no_alg = ".".join([part({"typ": "x"}), part({"sub": "x"}), made(B64, 30)])
    assert "JWT" not in kinds(f"t {no_alg} end")


def test_ac3_bearer_and_authorization_values_are_tokens():
    """REQ-049 AC3: rule 10 TOKEN."""
    value = made(B64, 32)
    assert kinds(f"Authorization: Bearer {value}") == ["TOKEN"]
    assert kinds(f"curl -H 'Bearer {value}'") == ["TOKEN"]
    assert kinds("Bearer tokens are explained below") == []


def test_ac3_a_high_entropy_value_next_to_a_key_like_name_is_a_secret():
    """REQ-049 AC3: rule 10 SECRET (entropy next to a key-like name)."""
    value = made(B64, 32)
    for name in ("password", "client_secret", "apiKey", "AUTH_TOKEN", "db_pwd"):
        for sep in ("=", ": ", " => ", '="'):
            found = guard.scan_text(f"{name}{sep}{value}")
            assert [f.kind for f in found] == ["SECRET"], (name, sep)
            assert found[0].length == len(value)
    assert kinds(f"monkey={value}") == []  # `key` must be a whole part of the name
    assert kinds("password=aaaaaaaaaaaaaaaaaaaaaaaa") == []  # low entropy


def test_ac3_a_gitleaks_rule_finds_its_shape_without_any_gitleaks_program():
    """REQ-049 AC3: rule 10 (the gitleaks default rules copied as data)."""
    value = "ghp_" + made(B64, 36)  # the shape of the github-pat rule, built here
    assert kinds(f"push with {value} now") == ["SECRET"]


def test_ac3_the_rule_file_names_its_release_and_every_rule_compiles():
    """REQ-049 AC3: rule 10 (guard_rules.json: release, licence notice, rules)."""
    data = json.loads((SCRIPTS / "guard_rules.json").read_text(encoding="utf-8"))
    assert data["release"] == "v8.30.1"  # the release .github/workflows/governance.yml pins
    assert "MIT" in data["licence"]
    assert len(data["rules"]) > 200
    assert len(guard.compiled_rules()) == len([r for r in data["rules"] if "regex" in r])


# --- rule 10: true negatives and the exclusions -------------------------------------------------


def test_ac3_shas_digests_uuids_versions_and_example_addresses_are_not_flagged_alone():
    """REQ-049 AC3: rule 10 (not flagged on their own)."""
    alone = [
        "550e8400-e29b-41d4-a716-446655440000",
        "commit 9fceb02",
        "commit " + made(HEX, 40),
        "md5 " + made(HEX, 32),
        "sha512 " + made(HEX, 128),
        "version 3.12.1 and v2.10.0-rc1",
        "alice@example.com and bob@example.org and ci@build.example.net",
    ]
    for text in alone:
        assert kinds(text) == [], text


def test_ac3_the_same_values_are_flagged_next_to_a_key_like_name():
    """REQ-049 AC3: rule 10 (flagged next to a key-like name)."""
    for value in (
        "550e8400-e29b-41d4-a716-446655440000",
        "9fceb02",
        made(HEX, 64),
        "3.12.1",
        "alice@example.com",
    ):
        assert kinds(f"token={value}") == ["SECRET"], value


@pytest.mark.parametrize(
    "text",
    [
        "127.0.0.1", "127.0.0.53", "::1", "0.0.0.0", "192.0.2.10", "198.51.100.7",
        "203.0.113.5", "2001:db8::1",
        "comment 6614307507", "#540", "run 38890313928", "id 6634414373", "id=6634414373",
        "https://github.example.com/o/r/issues/1#issuecomment-6634414373",
        "https://github.example.com/o/r/actions/runs/38890313928",
        "noreply@example.com", "no-reply@mail.example.io",
        "4111111111111112", "ABCDE12345",
    ],
)  # fmt: skip
def test_ac3_the_exclusions_of_rule_10_are_true_negatives(text):
    """REQ-049 AC3: rule 10 (exclusions)."""
    assert kinds(text) == []


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (PHONE, "PHONE"),
        ("10.1.2.3", "IP"),
        ("person@mail.example.io", "EMAIL"),
        (f"tel:+91{PHONE}", "PHONE"),
        (f"sms:{PHONE}", "PHONE"),
        (f"https://wa.me/91{PHONE}", "PHONE"),
        (f"https://shop.example.com/pay?card={CARD}", "CARD"),
        (f"aadhaar id {AADHAAR}", "AADHAAR"),
        (f"phone id: {PHONE}", "PHONE"),
        (f"mobile id={PHONE}", "PHONE"),
        (f"PAN id {PHONE}", "PHONE"),
        (f"id +91{PHONE}", "PHONE"),
        ("id 2345-6789-0124", "AADHAAR"),
        (f"# {PHONE}", "PHONE"),
    ],
)
def test_ac3_the_edges_of_the_exclusions_are_true_positives(text, kind):
    """REQ-049 AC3: rule 10 (edges of the exclusions)."""
    assert kinds(text) == [kind]


def test_ac3_a_custom_pattern_adds_a_custom_kind():
    """REQ-049 AC3: rule 10 (each [guard] patterns entry as CUSTOM-<name>)."""
    found = kinds("ticket EMP-00417 opened", patterns=[("employee", r"EMP-\d{5}")])
    assert found == ["CUSTOM-employee"]


# --- rule 1: the [guard] table ------------------------------------------------------------------


def git(root: Path, *args: str) -> None:
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, check=True, capture_output=True
    )


def project(tmp_path: Path, branch_toml: str, default_toml: str | None = None) -> Path:
    """A repository whose origin/main holds default_toml and whose checkout holds branch_toml."""
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "dev@example.com")
    git(tmp_path, "config", "user.name", "dev")
    (tmp_path / "agk.toml").write_text(default_toml or branch_toml, encoding="utf-8")
    git(tmp_path, "add", "agk.toml")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    (tmp_path / "agk.toml").write_text(branch_toml, encoding="utf-8")
    return tmp_path


FULL = """[guard]
patterns = [{ name = "employee", regex = 'EMP-\\d{5}' }]
deny_paths = ["*.bak"]
deny_commands = ["vault"]
allowed_hosts = ["db.internal.example.com"]
allow_paths = [{ path = "docs/logs/README.md", reason = "a guide, not a log" }]
"""


def test_ac1_no_guard_table_means_the_built_in_rules_alone(tmp_path):
    """REQ-049 AC1: rule 1 ([guard] absent)."""
    got = config.guard_settings(project(tmp_path, 'default_branch = "main"\n'))
    assert got == {
        "patterns": [], "deny_paths": [], "deny_commands": [], "allowed_hosts": [],
        "allow_paths": [],
    }  # fmt: skip


def test_ac1_each_additive_key_is_read_and_escapes_count_when_on_the_default_branch(tmp_path):
    """REQ-049 AC1: rule 1 (each additive key; an escape present in both counts)."""
    got = config.guard_settings(project(tmp_path, FULL))
    assert got["patterns"] == [("employee", r"EMP-\d{5}")]
    assert got["deny_paths"] == ["*.bak"] and got["deny_commands"] == ["vault"]
    assert got["allowed_hosts"] == ["db.internal.example.com"]
    assert got["allow_paths"] == [{"path": "docs/logs/README.md", "reason": "a guide, not a log"}]


def test_ac1_an_escape_only_on_the_branch_does_not_count(tmp_path):
    """REQ-049 AC1: rule 1 (a branch cannot loosen its own guard)."""
    got = config.guard_settings(project(tmp_path, FULL, default_toml="[guard]\n"))
    assert got["allow_paths"] == [] and got["allowed_hosts"] == []
    assert got["deny_commands"] == ["vault"]  # additions need no default-branch copy


def test_ac1_escapes_count_for_none_outside_a_repository(tmp_path):
    """REQ-049 AC1: rule 1 (no default branch to read: no escape counts)."""
    (tmp_path / "agk.toml").write_text(FULL, encoding="utf-8")
    got = config.guard_settings(tmp_path)
    assert got["allow_paths"] == [] and got["allowed_hosts"] == []


@pytest.mark.parametrize(
    ("table", "setting"),
    [
        ("enabled = false", "[guard] enabled"),
        ("off = true", "[guard] off"),
        ("colour = 'red'", "[guard] colour"),
        ("deny_paths = 'x'", "[guard] deny_paths"),
        ("patterns = [{ name = 'n', regex = '(' }]", "[guard] patterns"),
        ("patterns = [{ name = 'n' }]", "[guard] patterns"),
        ("allow_paths = [{ path = 'notes.md' }]", "[guard] allow_paths"),
        ("allow_paths = [{ path = 'notes.md', reason = '' }]", "[guard] allow_paths"),
        ("allow_paths = [{ path = 'logs/*.md', reason = 'r' }]", "[guard] allow_paths"),
        ("allow_paths = [{ path = '../x.md', reason = 'r' }]", "[guard] allow_paths"),
        ("allow_paths = [{ path = '/etc/x.md', reason = 'r' }]", "[guard] allow_paths"),
        ("allow_paths = [{ path = '~/x.md', reason = 'r' }]", "[guard] allow_paths"),
        ("allow_paths = [{ path = '.env', reason = 'r' }]", "[guard] allow_paths"),
        ("allow_paths = [{ path = 'keys/server.pem', reason = 'r' }]", "[guard] allow_paths"),
    ],
)
def test_ac1_a_refused_table_names_the_setting_and_never_the_value(tmp_path, table, setting):
    """REQ-049 AC1: rule 1 (refused, naming the setting, never the value)."""
    root = project(tmp_path, f"[guard]\n{table}\n")
    with pytest.raises(config.GuardSettingError) as caught:
        config.guard_settings(root)
    message = str(caught.value)
    assert f"(setting: {setting})" in message
    for value in ("red", "notes.md", "logs/*.md", "../x.md", "/etc", ".env", "server.pem"):
        assert value not in message
