# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The parts record's draft (SPEC-0076 rules 3, 4, 6, 7 and 11; REQ-083; brief #2070, ADR-0860).
Installed: `kit/manifest.json` lists it in `verbatim`.

    python3 parts_record.py draft --proposal FILE [--root DIR] [--today YYYY-MM-DD]

Reads the steward's TOML proposal (outside `docs/`), whose health values were read on the person's
recorded `Setup: web-research: yes`, and writes `docs/parts.md` once from `kit/templates/parts.md`:
one `## <runtime>` section per runtime of the Accepted stack record, one row per need, the first
candidate that meets the floor kept (the licence list, `[parts]` `max_age_months` and
`advisories`, neither deprecated nor archived). It records `Setup: parts: drafted ...` in the
steward's memory and prints `question: <sentence>` for each of rule 7's four kinds, each passing
`steward_owner.question_problem`. A refusal is exit 1, names the rule and the key or setting, never
a value, and writes nothing. `rows(text)` reads the record's rows by section. Files only: no
network; the memory entry goes through `steward.record`. Exit 0 drafted, 1 refused, 2 usage.
"""

from __future__ import annotations

import datetime
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import repo_root, utf8_output  # noqa: E402

RECORD = "docs/parts.md"
TEMPLATE = Path(__file__).resolve().parents[2] / "kit" / "templates" / "parts.md"  # the kit's own
COLUMNS = (
    "Need",
    "Part",
    "Version",
    "Kind",
    "Why",
    "Alternatives considered",
    "Licence",
    "Health (date)",
    "For the business",
)
NEED_KEYS = {
    "need": True,
    "cites": True,
    "business": True,
    "runtime": False,
    "decision": False,
    "part": False,
    "candidates": False,
}
CAND_KEYS = {
    k: True
    for k in (
        "name",
        "kind",
        "version",
        "released",
        "licence",
        "advisories",
        "last_release",
        "status",
        "adoption",
        "source",
        "read",
    )
}
CAND_KEYS.update(scorecard=False, commercial=False, service=False)
WORDS = {
    "kind": ("runtime", "dev"),
    "status": ("maintained", "deprecated", "archived"),
    "advisories": ("none", "low", "moderate", "high", "critical"),
    "service": ("none", "paid", "data-out"),
}
STOPS = {
    "critical-high": {"high", "critical"},
    "critical": {"critical"},
    "any": {"low", "moderate", "high", "critical"},
}
DATES = ("released", "last_release", "read")
URL = re.compile(r"^https?://\S+$")
CITE = re.compile(r"^REQ-\d+$")
RESEARCH_YES = "Setup: web-research: yes because"
USAGE = "usage: parts_record.py draft --proposal FILE [--root DIR] [--today YYYY-MM-DD]"
QUESTIONS = {
    "commercial": "The part {name} (for: {text}) has a paid or commercial licence; do you accept "
    "its cost and terms? I recommend no, unless it is already in your budget.",
    "licence": "The part {name} (for: {text}) uses a licence your project does not allow yet; "
    "should we allow that licence? I recommend no, so we use an allowed part instead.",
    "paid": "The part {name} (for: {text}) relies on an outside service that costs money; is "
    "that cost acceptable? I recommend yes, if the price fits your budget.",
    "data-out": "The part {name} (for: {text}) sends data to a service outside the product; is "
    "that acceptable? I recommend yes, only if your customers' data may leave the product.",
    "none": "No healthy, allowed part was found for this need: {text}. May we write this small "
    "piece ourselves? I recommend yes, keeping it small.",
}


class Refused(Exception):
    """A refusal line, naming the rule and the key or setting, never a value."""


def refuse(rule: int, what: str, key: str) -> Refused:
    return Refused(f"refused: SPEC-0076 rule {rule}: {what} (key: {key}); nothing is written")


def question(kind: str, name: str, text: str) -> str:
    return QUESTIONS[kind].format(name=name, text=text.rstrip("."))


def rows(text: str) -> dict[str, list[dict[str, str]]]:
    """The record's rows by `## <runtime>` section, each a dict keyed by `COLUMNS`."""
    out: dict[str, list[dict[str, str]]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = out.setdefault(line[3:].strip(), [])
        elif current is not None and line.startswith("|") and not line.startswith("|---"):
            cells = tuple(c.strip() for c in line.strip().strip("|").split("|"))
            if cells != COLUMNS and len(cells) == len(COLUMNS):
                current.append(dict(zip(COLUMNS, cells, strict=True)))
    return out


def _load(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}


def _months(old: datetime.date, today: datetime.date) -> int:
    return (today.year - old.year) * 12 + today.month - old.month - (today.day < old.day)


def _checked(row: dict, keys: dict, today: datetime.date) -> dict:
    for key in sorted(set(row) - set(keys)):
        raise refuse(7, "a key is unknown", key)
    for key, needed in keys.items():
        value = row.get(key)
        if value is None:
            if needed:
                raise refuse(7, "a key is missing", key)
            continue
        if key == "commercial":
            wrong = type(value) is not bool
        elif key == "candidates":
            wrong = not isinstance(value, list) or not all(isinstance(c, dict) for c in value)
        elif key == "scorecard":
            wrong = isinstance(value, bool) or not isinstance(value, (str, int, float))
        else:
            wrong = not isinstance(value, str) or not value.strip()
        if wrong or (key in WORDS and value not in WORDS[key]):
            raise refuse(7, "a value is out of form", key)
        if key in DATES:
            try:
                day = datetime.date.fromisoformat(value)
            except ValueError:
                raise refuse(6, "a date is out of form", key) from None
            if day > today:
                raise refuse(6, "a date is after today", key)
    if "source" in keys and not URL.match(row["source"]):
        raise refuse(6, "a health value has no public source", "source")
    return row


def _stack(root: Path) -> list[tuple[str, str]]:
    """(runtime, its licence) of the Accepted record's chosen option: `pins.STACKS` names, else
    the first part, which the stack skill names first."""
    from gates import pins

    texts = pins.records(root)
    if texts is None:
        raise Refused(
            "refused: SPEC-0076 rule 3: no work type is declared"
            " (setting: delivery.work_type); nothing is written"
        )
    parts = pins.chosen_parts(texts)
    if not parts:
        raise Refused(
            "refused: SPEC-0076 rule 3: no Accepted stack record with a chosen option"
            " (path class: docs/adr/); nothing is written"
        )
    found = [(p[0], p[2]) for p in parts if p[0] in pins.STACKS]
    return found or [(parts[0][0], parts[0][2])]


def _catalogue(root: Path) -> tuple[dict[str, str], dict[str, list[dict]]]:
    """(need id -> its plain text, stack folder -> rows), the project's rows first."""
    import packs
    from gates import pins

    order = {packs.PROJECT: 0, packs.CORE: 1}
    try:
        files = sorted(packs.files(root, "parts"), key=lambda f: order.get(f[0], 2))
    except Exception:  # noqa: BLE001 - packs.Refused or kit_root.Refused, each a setting
        raise Refused(
            "refused: SPEC-0076 rule 5: the catalogue cannot be read"
            " (setting: packs); nothing is written"
        ) from None
    needs: dict[str, str] = {}
    stacks: dict[str, list[dict]] = {}
    folders = {row[0] for row in pins.STACKS.values()}
    for _, path in files:
        data = _load(path)
        if path.name == "needs.toml":
            needs.update({n.get("id"): n.get("text", "") for n in data.get("needs", [])})
        elif path.stem in folders:
            stacks.setdefault(path.stem, []).extend(data.get("parts", []))
    return needs, stacks


def _health(c: dict) -> str:
    card = f"scorecard {c['scorecard']}" if "scorecard" in c else "scorecard: not published"
    return (
        f"{c['status']}; advisories {c['advisories']}; last release {c['last_release']}; "
        f"{c['adoption']}; {card} (read {c['read']}, {c['source']})"
    )


def _keep(c: dict, floor: tuple, asks: list[tuple[str, str]], today: datetime.date) -> bool:
    from gates import licences

    allowed, months, stops = floor
    paid = c["licence"].startswith("LicenseRef-") or c.get("commercial") is True
    if not licences.passes(c["licence"], allowed):
        asks.append(("commercial" if paid else "licence", c["name"]))
        return False
    last = datetime.date.fromisoformat(c["last_release"])
    if _months(last, today) > months or c["advisories"] in stops or c["status"] != "maintained":
        return False
    asks += [("commercial", c["name"])] * paid
    asks += [(c.get("service", "none"), c["name"])] * (c.get("service", "none") != "none")
    return True


def _row(need: dict, part: dict | None, rt: tuple[str, str], rows: list[dict] | None) -> list[str]:
    cite = need["cites"]
    if part is None:
        return [
            need["need"],
            "stdlib",
            "none",
            "runtime",
            f"{cite}; the runtime's own library",
            "none",
            rt[1] or "none",
            "none (stdlib)",
            need["business"],
        ]
    mine = [r for r in rows or [] if r.get("need") == need["need"]]
    hit = next((r for r in mine if r.get("name") == part["name"]), None)
    why = (
        f"catalogue: none; {cite}"
        if rows is None
        else f"{cite}; {hit['when']}"
        if hit
        else f"{cite}; not in the catalogue"
    )
    others = (
        "; ".join(
            f"{r['name']}: {r.get('trade_offs', '')}" for r in mine if r.get("name") != part["name"]
        )
        or "none"
    )
    return [
        need["need"],
        part["name"],
        part["version"],
        part["kind"],
        why,
        others,
        part["licence"],
        _health(part),
        need["business"],
    ]


def build(root: Path, proposal: Path, today: str) -> tuple[str, int, list[str]]:
    """(the record's text, the number of needs, the questions); raises `Refused`."""
    import steward
    from gates import licences, pins

    import config

    try:
        day = datetime.date.fromisoformat(today)
    except ValueError:
        raise refuse(6, "today is out of form", "today") from None
    try:
        settings = config.parts_settings(root)
    except config.PartsSettingError as error:
        raise Refused(f"refused: {error}; nothing is written") from None
    runtimes = _stack(root)
    if (root / RECORD).exists():
        raise Refused(
            f"refused: SPEC-0076 rule 7: {RECORD} exists; it is edited by hand, never "
            "rewritten (path class: docs/); nothing is written"
        )
    if proposal.resolve().is_relative_to((root / "docs").resolve()):
        raise Refused(
            "refused: SPEC-0076 rule 7: the proposal is under docs/ (path class: docs/);"
            " nothing is written"
        )
    try:
        data = tomllib.loads(proposal.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise Refused(
            "refused: SPEC-0076 rule 7: the proposal is not TOML (path class: the "
            "proposal); nothing is written"
        ) from None
    needs = [_checked(n, NEED_KEYS, day) for n in data.get("needs", [])]
    if any(n.get("candidates") for n in needs) and not any(
        str(e.get("body", "")).startswith(RESEARCH_YES) for e in steward.memory_entries(root)
    ):
        raise refuse(6, "a health value needs the person's recorded research yes", "web-research")
    allowed = licences.allowed_list(root)
    if allowed is None:
        raise Refused(
            f"refused: SPEC-0076 rule 6: the licence list is out of form (setting: "
            f"{licences.SETTING}); nothing is written"
        )
    floor = (allowed, settings["max_age_months"], STOPS[settings["advisories"]])
    texts, catalogues = _catalogue(root)
    names = [r[0] for r in runtimes]
    reqs = set(re.findall(r"\bREQ-\d+\b", _text(root / "docs/requirements.md")))
    sections: dict[str, list[str]] = {n: [] for n in names}
    seen: set[tuple[str, str]] = set()
    asks: list[str] = []
    for need in needs:
        if need["need"] not in texts:
            raise refuse(4, "the need is not in the needs catalogue", "need")
        if need["cites"] != "engineering" and not (
            CITE.match(need["cites"]) and need["cites"] in reqs
        ):
            raise refuse(4, "a need cites neither a requirement nor engineering", "cites")
        rt = need.get("runtime") or (names[0] if len(names) == 1 else None)
        if rt not in names:
            raise refuse(7, "the need names no runtime of the stack", "runtime")
        if (rt, need["need"]) in seen and "decision" not in need:
            raise refuse(7, "a second part for one need has no decision", "decision")
        if need.get("part", "stdlib") != "stdlib" or ("part" in need) == bool(
            need.get("candidates")
        ):
            raise refuse(4, "a need takes `stdlib` or its candidates", "candidates")
        cands = [_checked(c, CAND_KEYS, day) for c in need.get("candidates", [])]
        found: list[tuple[str, str]] = []
        kept = next((c for c in cands if _keep(c, floor, found, day)), None)
        asks += [question(k, n, texts[need["need"]]) for k, n in found]
        if cands and kept is None:
            asks.append(question("none", "", texts[need["need"]]))
            continue
        seen.add((rt, need["need"]))
        folder = pins.STACKS[rt][0] if rt in pins.STACKS else None
        cells = _row(need, kept, (rt, dict(runtimes)[rt]), catalogues.get(folder or ""))
        sections[rt].append(
            "| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |"
        )
        if "decision" in need:
            sections[rt].append(f"Decision: {need['need']}: {need['decision']}")
    return _render(sections, asks), len(needs), asks


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _render(sections: dict[str, list[str]], asks: list[str]) -> str:
    template = _text(TEMPLATE)
    if "\n## " not in template:
        raise Refused(
            "refused: SPEC-0076 rule 7: the template is missing (path class: kit/templates/);"
            " nothing is written"
        )
    out = [template.split("\n## ", 1)[0].rstrip("\n"), ""]
    head = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for name, lines in sections.items():
        table = [ln for ln in lines if ln.startswith("|")]
        notes = [ln for ln in lines if not ln.startswith("|")]
        out += [f"## {name}", "", *head, *table, "", *([*notes, ""] if notes else [])]
    out += ["Questions for the person:", "", *(f"- {q}" for q in asks), *([""] if asks else [])]
    return "\n".join([*out, "Confirmed by: none yet", ""])


def draft(root: Path, proposal: Path, today: str, gh) -> tuple[int, list[str]]:
    """Write the record once and record the draft; (exit code, lines to print)."""
    import steward

    try:
        text, count, asks = build(root, proposal, today)
    except Refused as error:
        return 1, [str(error)]
    path = root / RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:  # never over an existing file
        handle.write(text)
    code, said = steward.record(
        root,
        "Setup",
        f"parts: drafted {count} needs, {len(asks)} "
        f"questions because the steward drafted {RECORD} on {today}",
        gh,
    )
    return code, [f"wrote {RECORD} ({count} needs)", *said, *(f"question: {q}" for q in asks)]


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    pairs = [(args[n], args[n + 1]) for n in range(1, len(args) - 1, 2)]
    opts = dict(pairs)
    flags = {"--proposal", "--root", "--today"}
    if args[:1] != ["draft"] or len(args) % 2 == 0 or "--proposal" not in opts or set(opts) - flags:
        print(USAGE, file=sys.stderr)
        return 2
    import steward

    root = Path(opts["--root"]) if "--root" in opts else repo_root()
    today = opts.get("--today") or datetime.datetime.now(datetime.UTC).date().isoformat()
    code, lines = draft(root, Path(opts["--proposal"]), today, steward.gh_api)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
