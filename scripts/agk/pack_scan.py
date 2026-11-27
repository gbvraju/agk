# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The adoption scans of a pack (SPEC-0077 rule 6; REQ-084 AC3; brief #2034, ADR-0841).
Installed: `kit/manifest.json` lists it in `verbatim`.

`scan(root, folder)` runs on a staged pack, before `packs.add` writes anything, beside
`check_packs.problems` (which already runs `guard.scan_text` on every listed file): the outbound
guard (`steward_outbound.check`: the neutrality lists, `guard.scan_text` with the `[guard]
patterns`, the project's hosts) and the instruction scan on every text file; the licence against
`gates/licences.allowed_list` (the project's `config/licences.toml`, else the kit's list); the size
limits; the content rule (no hook, agent file, workflow, settings file, `.mcp.json`, script outside
a `skills/<name>/` folder, binary file outside a skill's `assets/`, or file outside the kinds'
folders); and `admitted`: the tier against `[packs] trust` and the `kit` range against the running
kit's version, which `packs.verify` runs on each locked pack too. Each line is
`rule 6: config/packs/<id>: ...` naming the key, setting or path class, never a value or a line's
text. `instructions(text)` gives the line numbers of the lines that ask an agent to approve, merge,
push, skip or disable a check, reveal a secret, change its role or task, or ignore the rules
(session rule 38). Every line is scanned, a quoted example too (`Q-PD-1`); there is no allow list.
It holds no detector of its own: secrets and tokens are the kit's scanners'. Reads files only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_packs
import kit_root
import steward_outbound

# ADR-0841 (`Q-PD-2`): today's largest kit knowledge file is 7,000 bytes (a domain pack) and its
# largest skill 14,653 bytes; all playbooks and domain packs together are 55,999 bytes.
FILE_LIMIT = 64 * 1024  # bytes per file: over four times the largest skill
PACK_LIMIT = 512 * 1024  # bytes per pack: over nine times today's playbooks and domain packs
SCRIPTS = (
    ".py",
    ".sh",
    ".bash",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".rb",
    ".pl",
    ".ps1",
    ".bat",
    ".cmd",
)
RANK = {tier: n for n, tier in enumerate(check_packs.TIERS)}  # official 0 > curated 1 > community 2
RANGE = re.compile(r"^>=(\d+)\.(\d+)\.(\d+),<(\d+)\.(\d+)\.(\d+)$")
EXACT = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# Answer 1: where a line asks (its start, after a sentence, `please`, or `you/agents must ...`).
_LEAD = (
    r"(?:^|[.!?;:]\s+|\bplease\s+|\b(?:you|agents?|the\s+(?:agent|model|assistant|session|"
    r"builder|conductor|steward|reviewer))\s+(?:must|should|shall|will|can|need\s+to|have\s+to|"
    r"are\s+to)\s+(?:now\s+)?)"
)
_OBJ = r"(?:(?:this|the|that|these|those|your|my|our|its|it|all|any|every|each|a|an)\s+)*"
ASKS = {
    "approve": rf"approve\s+{_OBJ}(?:pull\s+requests?|prs?|changes?|it|reviews?|briefs?|specs?|"
    r"adrs?|packs?|merges?|commits?)\b",
    "merge": rf"merge\s+{_OBJ}(?:pull\s+requests?|prs?|branch(?:es)?|changes?|it|commits?)\b",
    "push": rf"(?:force[- ]?)?push\s+{_OBJ}(?:branch(?:es)?|changes?|commits?|code|it|tags?)\b",
    "skip": rf"skip\s+{_OBJ}(?:checks?|tests?|reviews?|scans?|scanners?|gates?|hooks?|ci)\b",
    "disable": rf"(?:disable|bypass|turn\s+off|silence)\s+{_OBJ}(?:secret\s+)?(?:checks?|tests?|"
    r"scans?|scanners?|gates?|hooks?|ci|guards?)\b",
    "reveal": rf"(?:reveal|print|show|share|send|post|leak|output|echo|paste)\s+{_OBJ}"
    r"(?:secret\s+)?(?:secrets?|tokens?|api\s+keys?|passwords?|credentials?|private\s+keys?)\b",
    "task": rf"(?:change|abandon|drop|replace)\s+{_OBJ}(?:task|brief|instructions|goal)\b",
}
ANYWHERE = {
    "ignore": rf"\b(?:ignore|disregard|forget|override)\s+{_OBJ}(?:(?:previous|prior|above|"
    r"earlier|other)\s+)?(?:rules?|instructions?|guidelines?|constitution|principles?|prompts?)\b",
    "role": r"\b(?:act\s+as|pretend\s+to\s+be|take\s+(?:on\s+)?the\s+role\s+of|"
    r"switch\s+(?:your\s+)?roles?|you\s+are\s+now|from\s+now\s+on)\b",
}
_ASKED = re.compile(_LEAD + "(?:" + "|".join(ASKS.values()) + ")", re.IGNORECASE)
_ANY = re.compile("|".join(ANYWHERE.values()), re.IGNORECASE)
_MARKS = re.compile(r"^[\s>*+\-#`'\"\d.)]*")


def instructions(text: str) -> list[int]:
    """Rule 6: the 1-based numbers of the lines that ask an agent to act (session rule 38)."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        body = _MARKS.sub("", line)
        if _ASKED.search(body) or _ANY.search(body):
            out.append(n)
    return out


def holds(spec: object, version: str) -> bool | None:
    """Whether the `kit` range `>=x.y.z,<a.b.c` holds VERSION; None when either does not parse."""
    found = RANGE.match(spec) if isinstance(spec, str) else None
    have = EXACT.match(version or "")
    if found is None or have is None:
        return None
    nums = tuple(map(int, found.groups()))
    return nums[:3] <= tuple(map(int, have.groups())) < nums[3:]


def kit_version(root: Path) -> str | None:
    """The running kit's version: the plugin's in the clean layout (SPEC-0071 rule 6), else
    `agk.toml` `version`, else the plugin manifest beside this script; None when none is read."""
    try:
        if kit_root.layout(Path(root)) == "plugin":
            return kit_root.plugin_version(kit_root.plugin_root(Path(root)))
    except kit_root.Refused:
        return None
    value = kit_root._toml(Path(root)).get("version")
    if isinstance(value, str) and value:
        return value
    return kit_root.plugin_version(Path(__file__).resolve().parents[2])


def admitted(root: Path, data: dict, pack: str, trust: str) -> list[str]:
    """Rule 6: the tier against TRUST and the `kit` range against the running kit's version."""
    out = []
    tier = data.get("tier")
    if RANK.get(tier if isinstance(tier, str) else "", len(RANK)) > RANK[trust]:
        out.append(f"rule 6: {pack}: the pack's tier is below the trust (setting: packs.trust)")
    if not holds(data.get("kit"), kit_version(root) or ""):
        out.append(f"rule 6: {pack}: the kit range does not hold the running kit (key: kit)")
    return out


def path_class(rel: str) -> str:
    """A file's path class inside a pack: its first folder, or the manifest's name."""
    parts = rel.split("/")
    return f"{parts[0]}/" if len(parts) > 1 else (rel if rel == check_packs.MANIFEST else "./")


def content(rel: str, executable: bool) -> str | None:
    """Rule 6 (`Q-S0077-2`): the first kind of file a pack may not hold that REL is, else None."""
    parts = rel.split("/")
    name = parts[-1]
    if rel == check_packs.MANIFEST:
        return None
    if "hooks" in parts[:-1] or name == "hooks.json":
        return "a hook"
    if "agents" in parts[:-1] or ".claude" in parts:
        return "an agent file"
    if ".github" in parts or "workflows" in parts:
        return "a workflow"
    if name == ".mcp.json" or re.match(r"^settings(?:\.local)?\.json$", name):
        return "a settings file"
    in_skill = parts[0] == "skills" and len(parts) >= 3
    if (Path(name).suffix in SCRIPTS or executable) and not in_skill:
        return "a script outside a skill's folder"
    if len(parts) < 2 or parts[0] not in check_packs.KINDS:
        return "a file outside the kinds' folders"
    return None


def _licence(root: Path, data: dict, pack: str) -> list[str]:
    from gates import licences

    allowed = licences.allowed_list(Path(root))
    if allowed is None:
        return [
            f"rule 6: {pack}: the licence list is not of its form (setting: {licences.SETTING})"
        ]
    licence = data.get("licence")
    if not isinstance(licence, str) or not licences.passes(licence, allowed):
        return [f"rule 6: {pack}: the licence is not on the allowed list (key: licence)"]
    return []


def scan(root: Path, folder: Path) -> list[str]:
    """Rule 6: every adoption problem of the staged pack at FOLDER, for the project at ROOT."""
    import config

    root, folder = Path(root), Path(folder)
    data = check_packs.load(folder / check_packs.MANIFEST) or {}
    pid = data.get("id")
    ok_id = isinstance(pid, str) and check_packs.SLUG.match(pid) and pid != check_packs.CORE
    pack = f"{check_packs.FOLDER}/{pid}" if ok_id else f"{check_packs.FOLDER}/"
    try:
        trust = config.packs_settings(root)["trust"]
    except config.PacksSettingError as exc:
        return [f"rule 12: {exc}"]
    found = steward_outbound.remotes(root)
    out: list[str] = []
    total = 0
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        rel = path.relative_to(folder).as_posix()
        cls = path_class(rel)
        size = path.stat().st_size
        total += size
        kind = content(rel, bool(path.stat().st_mode & 0o111))
        if kind:
            out.append(f"rule 6: {pack}: {cls}: {kind} (key: files)")
        if size > FILE_LIMIT:
            out.append(f"rule 6: {pack}: {cls}: a file over the size limit (key: files)")
            continue
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            parts = rel.split("/")
            if not (parts[0] == "skills" and len(parts) >= 4 and parts[2] == "assets"):
                out.append(
                    f"rule 6: {pack}: {cls}: a binary file outside a skill's assets (key: files)"
                )
            continue
        out += [
            f"rule 6: {pack}: an instruction-shaped line (session rule 38) at {cls} line {n}"
            " (key: files)"
            for n in instructions(text)
        ]
        hits = steward_outbound.check(text, root, found) if found is not None else None
        hits = steward_outbound.check(text, root) if hits is None else hits
        out += [f"rule 6: {pack}: {cls}: {line}" for line in hits]
    if total > PACK_LIMIT:
        out.append(f"rule 6: {pack}: the pack is over the size limit (key: files)")
    out += _licence(root, data, pack) + admitted(root, data, pack, trust)
    return list(dict.fromkeys(out))
