"""The data guard's detectors and `scan_text` (SPEC-0042 rule 10, brief #561).

Standard library only, no network. `scan_text(text)` returns one `Finding` per secret or personal
value: its kind, line, column and length, and its offset for in-process redaction. A `Finding`
never holds the matched text, so nothing outside the process can learn a value from it.

Secrets: the gitleaks default rules copied as data into `guard_rules.json` (RE2 syntax turned into
Python's at load), a high-entropy value next to a key-like name, `JWT` and `TOKEN`. Personal data:
`EMAIL`, `PHONE`, `CARD` (Luhn), `AADHAAR` (Verhoeff), `PAN`, `IP`, and `CUSTOM-<name>` for each
`[guard] patterns` entry, with the exclusions of rule 10 so that ordinary kit text is not refused.
"""

from __future__ import annotations

import base64
import binascii
import bisect
import functools
import ipaddress
import json
import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parent / "guard_rules.json"


@dataclass(frozen=True)
class Finding:
    kind: str
    line: int
    column: int
    length: int
    start: int


# --- the gitleaks rules -------------------------------------------------------------------------


def py_regex(rx: str) -> str:
    """RE2 to Python: a `(?i)` after the start applies to the rest of its group; `\\z` is `\\Z`."""
    out: list[str] = []
    closers = [0]
    i, n, in_class = 0, len(rx), False
    while i < n:
        c = rx[i]
        if c == "\\":
            out.append(r"\Z" if rx[i : i + 2] == r"\z" else rx[i : i + 2])
            i += 2
        elif in_class:
            out.append(r"\[" if c == "[" else c)
            in_class = c != "]"
            i += 1
        elif c == "[":
            in_class = True
            j = i + 1 + (rx[i + 1 : i + 2] == "^")
            j += rx[j : j + 1] == "]"
            out.append(rx[i:j])
            i = j
        elif rx.startswith("(?i)", i) and out:
            out.append("(?i:")
            closers[-1] += 1
            i += 4
        elif c == "(":
            closers.append(0)
            out.append(c)
            i += 1
        elif c == ")":
            out.append(")" * closers.pop() + ")")
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out) + ")" * closers.pop()


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern
    keywords: tuple[str, ...]
    entropy: float
    group: int
    block: bool  # may span lines (a private key block): judged over a window, not a line


@functools.cache
def compiled_rules() -> tuple[Rule, ...]:
    data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    rules = []
    for r in data["rules"]:
        if "regex" not in r:
            continue
        rx = r["regex"]
        # A leading lazy `[\w.-]{0,50}?` only widens the match to the name before the keyword;
        # without it the secret group is the same and the search is many times faster (rule 11).
        fast = re.sub(r"^(\(\?i\))?\[\\w\.-\]\{0,50\}\?", r"\1", rx)
        rules.append(
            Rule(
                re.compile(py_regex(fast)),
                tuple(k.lower() for k in r.get("keywords", [])),
                float(r.get("entropy", 0)),
                int(r.get("secretGroup", 0)),
                "[\\s\\S" in rx or "(?s)" in rx,
            )
        )
    return tuple(rules)


def shannon(value: str) -> float:
    if not value:
        return 0.0
    counts = {c: value.count(c) for c in set(value)}
    return -sum(k / len(value) * math.log2(k / len(value)) for k in counts.values())


def secret_span(m: re.Match, group: int) -> tuple[int, int]:
    if group:
        return m.span(group)
    for g in range(1, (m.re.groups or 0) + 1):
        if m.group(g):
            return m.span(g)
    return m.span()


def line_bounds(text: str, starts: Sequence[int], pos: int) -> tuple[int, int]:
    i = bisect.bisect_right(starts, pos) - 1
    end = starts[i + 1] - 1 if i + 1 < len(starts) else len(text)
    return starts[i], end


def gitleaks(text: str, low: str, starts: Sequence[int]) -> Iterable[tuple[int, int, str]]:
    for rule in compiled_rules():
        windows: set[tuple[int, int]] = set()
        if rule.keywords:
            for kw in rule.keywords:
                pos = low.find(kw)
                while pos != -1:
                    a, b = line_bounds(text, starts, pos)
                    windows.add((a, min(len(text), a + 16384) if rule.block else b))
                    pos = low.find(kw, b + 1)
        else:
            windows.add((0, len(text)))
        for a, b in windows:
            for m in rule.pattern.finditer(text, a, b):
                s, e = secret_span(m, rule.group)
                if e > s and (not rule.entropy or shannon(text[s:e]) >= rule.entropy):
                    yield s, e, "SECRET"


# --- key-like names, JWT and bearer tokens ------------------------------------------------------

KEY_WORDS = {"key", "secret", "token", "password", "passwd", "pwd", "auth", "credential"}
KEY_NEAR = re.compile(
    r"(?i)(?:api_key|key|secret|token|password|passwd|pwd|auth|credential)s?['\"]?[ \t]*"
    r"(?:=>|=|:)[ \t]*['\"]?([^\s'\"`,;]+)"
)
NAME_BEFORE = re.compile(r"[A-Za-z0-9_.-]*\Z")
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
HEXRUN = re.compile(r"[0-9a-fA-F]{7,128}")
B64RUN = re.compile(r"[A-Za-z0-9+/_-]{20,}={0,2}")
VERSION = re.compile(r"v?\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.-]+)?")
EXAMPLE_MAIL = re.compile(r"[^@\s]+@(?:[A-Za-z0-9-]+\.)*example\.(?:com|org|net)", re.I)


def key_like(name: str) -> bool:
    if "api_key" in name.lower():
        return True
    parts = re.split(r"[_.-]|(?<=[a-z0-9])(?=[A-Z])", name)
    return any(p.lower().rstrip("s") in KEY_WORDS or p.lower() in KEY_WORDS for p in parts if p)


def secret_value(v: str) -> bool:
    if re.fullmatch(r"[0-9a-fA-F]{20,}", v) and shannon(v) >= 3.0:
        return True
    if B64RUN.fullmatch(v) and shannon(v) >= 4.0:
        return True
    return any(p.fullmatch(v) for p in (UUID, HEXRUN, VERSION, EXAMPLE_MAIL))


def near_key(text: str) -> Iterable[tuple[int, int, str]]:
    for m in KEY_NEAR.finditer(text):
        name = NAME_BEFORE.search(text, max(0, m.start() - 80), m.start()).group(0)
        name += text[m.start() : m.end()].split("=")[0].split(":")[0].strip("'\" \t")
        if key_like(name) and secret_value(m.group(1)):
            yield m.start(1), m.end(1), "SECRET"


JWT = re.compile(r"\bey[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{2,}\.[A-Za-z0-9_-]{2,}")
TOKEN = re.compile(
    r"(?i)(?:\bBearer[ \t]+|\bAuthorization:[ \t]*(?:(?:Bearer|Basic|Token)[ \t]+)?)"
    r"([A-Za-z0-9._~+/=-]{16,})"
)


def jwt(text: str) -> Iterable[tuple[int, int, str]]:
    for m in JWT.finditer(text):
        head = m.group(0).split(".")[0]
        try:
            header = json.loads(base64.urlsafe_b64decode(head + "=" * (-len(head) % 4)))
        except (ValueError, binascii.Error):
            continue
        if isinstance(header, dict) and "alg" in header:
            yield m.start(), m.end(), "JWT"


def bearer(text: str) -> Iterable[tuple[int, int, str]]:
    for m in TOKEN.finditer(text):
        yield m.start(1), m.end(1), "TOKEN"


# --- personal data ------------------------------------------------------------------------------

EMAIL = re.compile(
    r"(?<![\w.%+-])([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})"
)
INTL = re.compile(r"(?<![\w+])\+\d(?:[ -]?\d){7,14}(?![\w])")
INDIA = re.compile(r"(?<![\w+])(?:\+?91[ -]?|0)?[6-9]\d{9}(?!\w)")
CARD = re.compile(r"(?<![\w+])\d(?:[ -]?\d){12,18}(?![\w])")
AADHAAR = re.compile(r"(?<![\w+])[2-9]\d{3}(?:[ -]?\d{4}){2}(?![\w])")
GROUPED = re.compile(r"\d{4}([ -])\d{4}\1\d{4}")
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w]|\.\d)")
IPV6 = re.compile(r"(?<![\w:.])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w:])")
URL = re.compile(r"https?://[^\s<>\"'`)\]]+", re.I)
BEFORE = re.compile(r"(?i)\b(?:comment|run|id)(?:=|[ \t]?:[ \t]?|[ \t])?\Z")
PERSONAL_ID = re.compile(
    r"(?i)\b(?:aadhaar|phone|mobile|card|pan)[ \t]?id(?:=|[ \t]?:[ \t]?|[ \t])?\Z"
)
IP_EXCLUDED = [
    ipaddress.ip_network(n)
    for n in ("127.0.0.0/8", "::1/128", "0.0.0.0/32", "::/128", "192.0.2.0/24")
    + ("198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32")
]

VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]  # fmt: skip
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]  # fmt: skip


def luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        x = int(ch) * (2 if i % 2 else 1)
        total += x - 9 if x > 9 else x
    return total % 10 == 0


def verhoeff(digits: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def url_spans(text: str) -> list[tuple[int, int]]:
    """The excluded parts of http(s) URLs: the path past its first segment, and the fragment."""
    spans = []
    for m in URL.finditer(text):
        u, base = m.group(0), m.start()
        host_end = u.find("/", u.find("//") + 2)
        frag = u.find("#")
        query = u.find("?")
        path_end = min(x for x in (query, frag, len(u)) if x != -1)
        if host_end != -1 and host_end < path_end:
            second = u.find("/", host_end + 1, path_end)
            if second != -1:
                spans.append((base + second, base + path_end))
        if frag != -1:
            spans.append((base + frag, base + len(u)))
    return spans


def masked_spans(text: str) -> list[tuple[int, int]]:
    """UUIDs and hex runs holding a letter: their digits are never a personal number."""
    spans = [m.span() for m in UUID.finditer(text)]
    spans += [m.span() for m in HEXRUN.finditer(text) if re.search("[a-fA-F]", m.group(0))]
    return spans


def inside(s: int, e: int, spans: Sequence[tuple[int, int]]) -> bool:
    return any(a <= s and e <= b for a, b in spans)


def number_excluded(text: str, s: int, e: int, urls: Sequence[tuple[int, int]]) -> bool:
    run = text[s:e]
    if run.startswith("+") or GROUPED.fullmatch(run):
        return False
    if inside(s, e, urls) or (s > 0 and text[s - 1] == "#"):
        return True
    before = text[max(0, s - 24) : s]
    return bool(BEFORE.search(before)) and not PERSONAL_ID.search(before)


def personal(text: str) -> Iterable[tuple[int, int, str]]:
    urls = url_spans(text)
    masked = masked_spans(text)

    def digits(m: re.Match) -> str:
        return re.sub(r"\D", "", m.group(0))

    for m in EMAIL.finditer(text):
        local, domain = m.group(1).lower(), m.group(2).lower()
        if local in ("noreply", "no-reply") or re.search(
            r"(?:^|\.)example\.(?:com|org|net)$", domain
        ):
            continue
        yield m.start(), m.end(), "EMAIL"
    numbers = [
        (INTL, "PHONE", lambda d: 8 <= len(d) <= 15),
        (INDIA, "PHONE", lambda d: True),
        (CARD, "CARD", lambda d: 13 <= len(d) <= 19 and luhn(d)),
        (AADHAAR, "AADHAAR", verhoeff),
    ]
    for pattern, kind, check in numbers:
        for m in pattern.finditer(text):
            s, e = m.span()
            if inside(s, e, masked) or not check(digits(m)):
                continue
            if not number_excluded(text, s, e, urls):
                yield s, e, kind
    for m in PAN.finditer(text):
        yield m.start(), m.end(), "PAN"
    for pattern in (IPV4, IPV6):
        for m in pattern.finditer(text):
            try:
                addr = ipaddress.ip_address(m.group(0))
            except ValueError:
                continue
            if not any(addr in net for net in IP_EXCLUDED if net.version == addr.version):
                yield m.start(), m.end(), "IP"


# --- scan_text ----------------------------------------------------------------------------------

RANKED = ("SECRET", "TOKEN", "JWT")  # on an overlap the later kind wins, then the longer


def rank(kind: str) -> int:
    return RANKED.index(kind) + 2 if kind in RANKED else 1


def scan_text(text: str, patterns: Sequence[tuple[str, str]] = ()) -> list[Finding]:
    """Every finding of rule 10 in `text`, in order, never overlapping; no matched text is kept."""
    low = text.lower()
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    found: list[tuple[int, int, str]] = []
    for source in (gitleaks(text, low, starts), near_key(text), jwt(text), bearer(text)):
        found.extend(source)
    found.extend(personal(text))
    for name, regex in patterns:
        found.extend((m.start(), m.end(), f"CUSTOM-{name}") for m in re.finditer(regex, text))
    chosen: list[tuple[int, int, str]] = []  # sorted by start, never overlapping
    order = sorted(set(found), key=lambda f: (-rank(f[2]), -(f[1] - f[0]), f[0]))
    for s, e, kind in order:
        i = bisect.bisect_left(chosen, (s,))
        if e <= s or (i and chosen[i - 1][1] > s) or (i < len(chosen) and chosen[i][0] < e):
            continue
        chosen.insert(i, (s, e, kind))
    result = []
    for s, e, kind in chosen:
        i = bisect.bisect_right(starts, s) - 1
        result.append(Finding(kind, i + 1, s - starts[i] + 1, e - s, s))
    return result


# --- the built-in secret file names (rule 5), for the `[guard] allow_paths` check of rule 1 ------

SECRET_NAME = re.compile(
    r"(?i)(?:\.env(?:\..*)?|.*\.(?:pem|key|p12|pfx)|id_[^.]*|.*\.tfstate(?:\..*)?|secrets\..*"
    r"|\.npmrc|\.pypirc|\.netrc|\.git-credentials)"
)


def secret_file_name(path: str) -> bool:
    """True when the last component of `path` is a built-in secret file name of rule 5."""
    name = path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return name.lower() != ".env.example" and bool(SECRET_NAME.fullmatch(name))
