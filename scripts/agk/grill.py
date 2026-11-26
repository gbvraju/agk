# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The grill's questions, answers and readiness (SPEC-0073 rules 2 to 6 and 11; REQ-080; briefs
#1933 and #1934, ADR-0801 and ADR-0802).

Usage: python3 scripts/agk/grill.py questions [--depth light|standard|deep] [--playbook KIND]
           [--answers FILE] [--root DIR]
       python3 scripts/agk/grill.py record --answers FILE --id ID (--stated WORDS-FILE |
           --assumption WORDS-FILE --test TEXT | --open | --risk-accepted) [--accepted WHERE]
           [--source TEXT] [--replace] [--playbook KIND] [--root DIR]
       python3 scripts/agk/grill.py record --answers FILE --id ID --risk TEXT --sign TEXT
           --owner WHO [--playbook KIND] [--root DIR]
       python3 scripts/agk/grill.py ready --answers FILE [--depth D] [--playbook KIND] [--root DIR]

Prints the grill items to ask, in order: the items of `config/playbooks/default.toml` at or below
the depth, then the work type's own items (KIND, else the declared `[delivery] work_type`, else
none), then `success` among the critical items. Each item is one line `<id> (critical|-) <text>`
followed by `Recommended: <steward fills>`, the placeholder the grill skill fills. The last line is
`budget: <n>`, the depth's question budget. The composed domain packs' items follow the work
type's (SPEC-0074 rule 6; brief #1937, ADR-0806): a regulated pack's critical items at every depth,
its others at `standard` and `deep`; once the answers file holds the budget's number of asked
items, only those critical items are printed, then the line `PAST_BUDGET`. An id the answers
file holds (its `answers` list, and its `grill` list) is never printed. Without `--depth` the
depth is `[quality] grill`. Reads files only: no network, no model. Exit 0 ok, 1 refused, 2 usage.

`record` appends one row to the answers file's `grill` list, the claim quoted as given, and never
writes `answers`: `stated`, `assumption` (with its test), `open`, or a `Risk accepted:` row. It
refuses an id that is not a grill item of the composed playbook, an assumption with no test, a
second row for one id without `--replace` and the person's words (the earlier row stays), and an
answer the data guard flags. A plain yes (`--accepted`) and `--risk-accepted` are refused in team
mode, naming `review_mode`. `record --risk --sign --owner` appends one pre-mortem risk `{id, risk,
sign, owner}` to the answers file's `risks` list instead (brief #1938, ADR-0803), each value one
non-empty line the data guard passes. `ready` prints the readiness line of rule 7 and exits 1
while a critical item is open with no accepted risk.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import playbook_format  # noqa: E402
from common import CheckError, review_mode, run, utf8_output  # noqa: E402

from config import quality_settings  # noqa: E402

NAME = "grill"
USAGE = __doc__.split("\n\n", 2)[1]
FLAGS = ("--depth", "--playbook", "--answers", "--root")
RECORD_FLAGS = (
    *("--answers", "--id", "--stated", "--assumption", "--test", "--accepted", "--source"),
    *("--playbook", "--root", "--risk", "--sign", "--owner"),
)
RISK_FLAGS = ("--risk", "--sign", "--owner")  # brief #1938: one pre-mortem risk, all three
SWITCHES = ("--open", "--risk-accepted", "--replace")
KINDS = ("--stated", "--assumption", "--open", "--risk-accepted", "--risk")
READY_FLAGS = ("--answers", "--depth", "--playbook", "--root")
BUDGET = {"light": 5, "standard": 12, "deep": 20}  # SPEC-0073 rule 11
RECOMMENDED = "Recommended: <steward fills>"
SUCCESS = "success"  # SPEC-0073 rule 3: a discovery id, the fifth critical item
WORK_TYPE = "(setting: work-type)"
PAST_BUDGET = "A few more questions are needed for the rules of this business."  # SPEC-0074 rule 6


def _checked(path: Path, root: Path) -> Path:
    if not path.is_file():
        raise CheckError(
            f"rule 3: the work type has no playbook under {playbook_format.FOLDER}/ {WORK_TYPE}"
        )
    if playbook_format.problems(path, root):
        raise CheckError(f"rule 3: the playbook fails check_playbooks.py {WORK_TYPE}")
    return path


def _work_type(root: Path, kind: str | None) -> Path | None:
    """The work type's playbook: KIND, else the declared one, else None."""
    if kind is None:
        kind, found = playbook_format.declaration(root)
        if found:
            raise CheckError(found[0])
        if kind is None:
            return None
    elif kind not in playbook_format.WORK_TYPES:
        raise CheckError(f"rule 3: the work type is not one of the work types {WORK_TYPE}")
    return _checked(playbook_format.path(root, kind), root)


def answered(path: str | None) -> set[str]:
    """The ids the answers file holds; refused naming `--answers`, never read as empty."""
    if path is None:
        return set()
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise CheckError("rule 2: the answers file cannot be read (setting: --answers)") from None
    lists = [data.get(k, []) for k in ("answers", "grill")] if isinstance(data, dict) else [None]
    rows = [r for found in lists if isinstance(found, list) for r in found]
    kept = lists[-1] if isinstance(lists[-1], list) else []
    bad_id = any(isinstance(r, dict) and not isinstance(r.get("id"), str) for r in kept)
    if any(not isinstance(f, list) for f in lists) or any(not isinstance(r, dict) for r in rows):
        bad_id = True
    if bad_id:
        raise CheckError("rule 2: the answers file is not an object of lists (setting: --answers)")
    return {r["id"] for r in rows if isinstance(r.get("id"), str)}


def pack_items(root: Path) -> tuple[list[tuple[str, str, str, bool]], set[str]]:
    """SPEC-0074 rule 6 (brief #1937, ADR-0806): the grill items of the packs of `[domain] packs`
    in their composed order, and the ids asked past the budget. A regulated pack (a `critical`
    `[[regulations]]` entry) asks its critical items at `light` and its others at `standard` at
    the least; any other pack's items keep their depth."""
    import check_domains  # here: a project without packs reads no pack

    regulated = set()
    for name in check_domains.order(root, check_domains._listed(root)):
        path = check_domains.pack_path(root, name)
        rows = (check_domains.load(path) or {}).get("regulations") if path else None
        if any(isinstance(r, dict) and r.get("critical") is True for r in rows or []):
            regulated.add(name)
    depths = playbook_format.GRILL_DEPTHS
    items, always = [], set()
    for entry in check_domains.items(root)["discovery"]:
        if entry.get("depth") not in depths or not isinstance(entry.get("critical"), bool):
            continue
        depth, critical = entry["depth"], entry["critical"]
        if entry["pack"] in regulated:
            depth = depths[0] if critical else max(depth, depths[1], key=depths.index)
            if critical:
                always.add(entry["id"])
        items.append((entry["id"], entry["text"], depth, critical))
    return items, always


def composed(root: Path, kind: str | None) -> list[tuple[str, str, str, bool]]:
    """The grill items of the composed playbook, in order, then the packs' (brief #1937),
    `success` last; an id held earlier keeps its first place."""
    base = playbook_format.default_playbook(root)
    if base is None:
        raise CheckError(f"rule 3: there is no default playbook under {playbook_format.FOLDER}/")
    _checked(base, root)
    own = _work_type(root, kind)
    items = [*playbook_format.grill_items(base), *(playbook_format.grill_items(own) if own else [])]
    held = {item[0] for item in items} | {SUCCESS}
    items += [item for item in pack_items(root)[0] if item[0] not in held]
    texts = dict(playbook_format.discovery(base))
    return [*items, (SUCCESS, texts[SUCCESS], playbook_format.GRILL_DEPTHS[0], True)]


def grill_ids(root: Path) -> set[str]:
    """Every grill id of the composed playbook, `success` among them; none without a playbook."""
    try:
        return {item[0] for item in composed(root, None)}
    except CheckError:
        return set()


def questions(root: Path, depth: str | None, kind: str | None, answers: str | None) -> list[str]:
    """The lines `questions` prints, the budget line last."""
    depth = depth or quality_settings(root)["grill"]
    rank = playbook_format.GRILL_DEPTHS.index(depth)
    done = answered(answers)
    kept = _load(answers).get("grill", []) if answers else []
    spent = len({r.get("id") for r in kept if "status" in r}) >= BUDGET[depth]
    always = pack_items(root)[1] if spent else set()
    lines = []
    for item_id, text, item_depth, critical in composed(root, kind):
        if item_id in done or playbook_format.GRILL_DEPTHS.index(item_depth) > rank:
            continue
        if spent and item_id not in always:  # rule 6: past the budget, the rules' items only
            continue
        lines += [f"{item_id} {'(critical)' if critical else '-'} {text}", RECOMMENDED]
    if lines and spent:
        lines.append(PAST_BUDGET)
    return [*lines, f"budget: {BUDGET[depth]}"]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: str) -> dict:
    answered(path)  # the same refusals as `questions`, never read as empty
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _guarded(text: str, what: str) -> str:
    """Rule 14: the data guard on every value written; refused by class, never the value."""
    from guard import scan_text

    found = scan_text(text)
    if found:
        kinds = ", ".join(sorted({f.kind for f in found}))
        raise CheckError(f"rule 14: the data guard finds {kinds} in {what}; ask for general words")
    return text


def _words(path: str) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
    except (OSError, UnicodeDecodeError):
        raise CheckError("rule 5: the answer cannot be read (setting: the words file)") from None
    if not text.strip():
        raise CheckError("rule 5: the answer is empty (setting: the words file)")
    return _guarded(text, "the answer")


def record(root: Path, opts: dict[str, str], switches: set[str]) -> dict[str, str | bool]:
    """The one row `record` appends (rule 5); refusals name the setting, never the words."""
    item = opts["--id"]
    if item not in {i[0] for i in composed(root, opts.get("--playbook"))}:
        raise CheckError(
            "rule 5: the id is not a grill item of the composed playbook (setting: --id)"
        )
    team = review_mode(root) == "team"
    if team and ("--accepted" in opts or "--risk-accepted" in switches):
        raise CheckError("rule 12: a plain yes never holds in team mode (setting: review_mode)")
    data = _load(opts["--answers"])
    kept = data.get("grill", [])
    if "--accepted" in opts and ("--open" in switches or "--risk-accepted" in switches):
        raise CheckError(
            "rule 5: a plain yes is recorded with words, never with --open or --risk-accepted"
            " (setting: --accepted)"
        )
    for flag in ("--test", "--source", "--accepted"):
        if flag in opts:
            _guarded(opts[flag], f"the value of {flag}")
    if "--risk-accepted" in switches:
        return {"id": item, "risk": f"Risk accepted: {item} ({_now()})"}
    if "--assumption" in opts and not opts.get("--test", "").strip():
        raise CheckError("rule 5: an assumption carries its test (setting: --test)")
    earlier = any(r.get("id") == item and "status" in r for r in kept)
    has_words = "--stated" in opts or "--assumption" in opts
    if earlier and ("--replace" not in switches or not has_words):
        raise CheckError(
            "rule 5: the id is recorded; a revision needs the person's words (setting: --replace)"
        )
    row: dict[str, str | bool]
    if "--stated" in opts:
        row = {"id": item, "claim": _words(opts["--stated"]), "status": "stated"}
    elif "--assumption" in opts:
        row = {"id": item, "claim": _words(opts["--assumption"]), "status": "assumption"}
        row["test"] = opts["--test"]
    else:
        row = {"id": item, "claim": "", "status": "open"}
    if "--source" in opts:
        row["source"] = opts["--source"]
    if "--accepted" in opts:
        row["accepted"] = f"accepted recommendation ({opts['--accepted']}, {_now()})"
    if earlier:
        row["revised"] = True
    return row


def risk_row(root: Path, opts: dict[str, str]) -> dict[str, str]:
    """Rule 7's `R-<n>` source: one pre-mortem risk, its first sign and its owner, one line each."""
    if opts["--id"] not in {i[0] for i in composed(root, opts.get("--playbook"))}:
        raise CheckError(
            "rule 5: the id is not a grill item of the composed playbook (setting: --id)"
        )
    _load(opts["--answers"])
    row = {"id": opts["--id"]}
    for flag in RISK_FLAGS:
        value = opts[flag]
        if not value.strip() or "\n" in value or "\r" in value:
            raise CheckError(f"rule 7: a risk is one line of words (setting: {flag})")
        row[flag[2:]] = _guarded(value.strip(), f"the value of {flag}")
    return row


def append(path: str, row: dict, key: str = "grill") -> None:
    data = _load(path)
    if not isinstance(data.get(key, []), list):
        raise CheckError("rule 2: the answers file is not an object of lists (setting: --answers)")
    data[key] = [*data.get(key, []), row]
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def readiness(root: Path, path: str, depth: str | None, kind: str | None) -> tuple[str, bool]:
    """Rule 7's readiness line, and whether every critical item is settled (rule 6)."""
    depth = depth or quality_settings(root)["grill"]
    data = _load(path)
    kept = data.get("grill", [])
    risks = [r["id"] for r in kept if "risk" in r and isinstance(r.get("id"), str)]
    last = {r.get("id"): r for r in kept if "status" in r}
    for row in data.get("answers", []):
        if row.get("id") == SUCCESS and SUCCESS not in last:
            given = isinstance(row.get("answer"), str) and row.get("open") is not True
            last[SUCCESS] = {"status": "stated" if given else "open"}

    def settled(item: str) -> bool:
        row = last.get(item, {})
        status, test = row.get("status"), str(row.get("test", "")).strip()
        return status == "stated" or (status == "assumption" and bool(test)) or item in risks

    critical = [i[0] for i in composed(root, kind) if i[3]]
    done = sum(1 for i in critical if settled(i))
    accepted = sum(1 for r in kept if "accepted" in r)
    asked = len({r.get("id") for r in kept if "status" in r})
    shown = ", ".join(dict.fromkeys(risks)) or "none"
    line = (
        f"critical {done}/{len(critical)}; risk accepted: {shown}; "
        f"questions {asked}/{BUDGET[depth]}; accepted recommendations {accepted}"
    )
    return line, done == len(critical)


def parse(args: list[str], flags: tuple[str, ...], switches: tuple[str, ...]):
    """The flags with values and the switches given; None on a usage error."""
    opts, seen, n = {}, set(), 0
    while n < len(args):
        if args[n] in switches:
            seen.add(args[n])
            n += 1
        elif args[n] in flags and n + 1 < len(args) and args[n] not in opts:
            opts[args[n]] = args[n + 1]
            n += 2
        else:
            return None
    return opts, seen


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else None
    found = None
    if command == "questions":
        found = parse(args[1:], FLAGS, ())
    elif command == "record":
        found = parse(args[1:], RECORD_FLAGS, SWITCHES)
        if found is not None:
            opts, seen = found
            kinds = [k for k in KINDS if k in opts or k in seen]
            given = [f for f in RISK_FLAGS if f in opts]
            if "--answers" not in opts or "--id" not in opts or len(kinds) != 1:
                found = None
            elif given and len(given) != len(RISK_FLAGS):
                found = None
            elif given and ({"--test", "--source", "--accepted"} & set(opts) or seen):
                found = None
    elif command == "ready":
        found = parse(args[1:], READY_FLAGS, ())
        if found is not None and "--answers" not in found[0]:
            found = None
    depth = found[0].get("--depth") if found else None
    if found is None or (depth is not None and depth not in BUDGET):
        print(USAGE, file=sys.stderr)
        return 2
    opts, seen = found
    root = Path(opts.get("--root", "."))

    def body() -> int:
        if command == "record" and "--risk" in opts:
            append(opts["--answers"], risk_row(root, opts), "risks")
            print(f"recorded: {opts['--id']} risk")
            return 0
        if command == "record":
            row = record(root, opts, seen)
            append(opts["--answers"], row)
            print(f"recorded: {row['id']} {row.get('status', 'risk accepted')}")
            return 0
        if command == "ready":
            line, ok = readiness(root, opts["--answers"], depth, opts.get("--playbook"))
            print(line)
            return 0 if ok else 1
        print("\n".join(questions(root, depth, opts.get("--playbook"), opts.get("--answers"))))
        return 0

    return run(NAME, body)


if __name__ == "__main__":
    sys.exit(main())
