# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The project domain model, `docs/domain/` (SPEC-0074 rules 7 and 9; REQ-081 AC4; brief #1954,
ADR-0810). Installed: `kit/manifest.json` lists it in `verbatim`.

    python3 scripts/agk/domain_model.py [--root DIR] init --area A
    python3 scripts/agk/domain_model.py [--root DIR] rule --area A --text T --source S --where W
        --owner O [--inferred]
    python3 scripts/agk/domain_model.py [--root DIR] classify --item I --class C
    python3 scripts/agk/domain_model.py [--root DIR] entity --name N --meaning M
        [--relates E:one-many:R]
    python3 scripts/agk/domain_model.py [--root DIR] regulation --id P.R --scope in|out --reason R
    python3 scripts/agk/domain_model.py [--root DIR] confirm --id BR-<n>

The one place that holds the four forms, imported by `check_domains.py`, the steward's harvest and
the data model's reader. `entities.md`: a `## <Entity>` section per entity, its meaning, then
`- relates to <Entity>: <one|many> to <one|many>, <reason>` lines. `rules-<area>.md`: lines
`- BR-<n>: <rule>; source: <customer material|interview|code>, <where>; owner: <who>;
<confirmed|inferred>`, read from the right, at most 200 per file, `BR-<n>` unique across the
folder. `data.md`: `- <item>: <personal|health|payment|confidential|public>`. `regulations.md`:
`- <pack>.<regulation>: <in scope|out of scope>, <reason>`, a regulation of a pack in `[domain]
packs`. `findings` gives one line per problem, `rule 7: docs/domain/<file>: <what> (id: <id>)`,
never a rule's text or a value, only where `docs/domain/` exists. The commands write only under
`docs/domain/` and never commit; the steward or the architect runs them in planning, never a
builder. Each value is scanned by the data guard first; a match refuses naming the class. Files
only: no network, no model.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import utf8_output  # noqa: E402
from guard import scan_text  # noqa: E402

FOLDER = "docs/domain"
RULE = "rule 7"
ENTITIES, DATA, REGULATIONS = "entities.md", "data.md", "regulations.md"
TEMPLATES = Path(__file__).resolve().parents[2] / "kit" / "templates"
AREA = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RULES_FILE = re.compile(r"^rules-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
RULE_ID = re.compile(r"^BR-[1-9]\d*$")
RULE_LINE = re.compile(r"^- (BR-[^:\s]*):\s*(.*)$")
RELATION = re.compile(r"^- relates to ([^:]+):\s*(.*)$")
CARDINALITY = re.compile(r"^(one|many) to (one|many), \S")
ITEM_LINE = re.compile(r"^- (.+): ([^:]*)$")
REG_LINE = re.compile(r"^- ([^\s:]+\.[^\s:]+):\s*(.*)$")
SOURCES = ("customer material", "interview", "code")
STATUSES = ("confirmed", "inferred")
CLASSES = ("personal", "health", "payment", "confidential", "public")
SCOPES = ("in scope", "out of scope")
SCOPE_WORDS = {"in": "in scope", "out": "out of scope"}
MAX_RULES = 200


@dataclass
class Rule:
    id: str
    text: str
    source: str
    where: str
    owner: str
    status: str
    file: str
    line: int


class Refused(Exception):
    """A command is refused, naming the setting or the class, never a value."""


def folder(root: Path) -> Path:
    return Path(root) / FOLDER


def read(path: Path) -> str | None:
    """The file's text (a BOM read as UTF-8), or None when it cannot be read."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def rule_files(root: Path) -> list[Path]:
    where = folder(root)
    return sorted(where.glob("rules*.md")) if where.is_dir() else []


def parse_rule(rest: str) -> tuple[dict, str | None]:
    """The rule's parts, read from the right, and the first problem, or None."""
    parts = [p.strip() for p in rest.split(";")]
    found = {"text": "", "source": "", "where": "", "owner": "", "status": ""}
    if not parts or parts[-1] not in STATUSES:
        return found, "the rule has no status confirmed or inferred"
    found["status"] = parts.pop()
    if not parts or not parts[-1].startswith("owner:") or not parts[-1][6:].strip():
        return found, "the rule has no owner"
    found["owner"] = parts.pop()[6:].strip()
    if not parts or not parts[-1].startswith("source:"):
        return found, "the rule has no source"
    kind, _, where = parts.pop()[7:].strip().partition(",")
    found |= {"source": kind.strip(), "where": where.strip(), "text": "; ".join(parts).strip()}
    if found["source"] not in SOURCES:
        return found, "the source kind is not customer material, interview or code"
    if not found["where"]:
        return found, "the source names no place"
    return found, None if found["text"] else "the rule has no text"


def _patterns(root: Path) -> list:
    import config

    try:
        return config.guard_patterns(Path(root))
    except config.CheckError:
        return []


def _guarded(text: str, patterns: list) -> dict[int, str]:
    return {hit.line: hit.kind for hit in scan_text(text, patterns)}


def _items(text: str, skip: dict[int, str]):
    for number, line in enumerate(text.splitlines(), 1):
        if number not in skip and line.startswith("- "):
            yield number, line.rstrip()


def rules(root: Path) -> list[Rule]:
    """Every well-formed rule of the folder, in file and line order."""
    out = []
    for path in rule_files(root):
        for number, line in _items(read(path) or "", {}):
            found = RULE_LINE.match(line)
            if found and RULE_ID.match(found[1]):
                parts, problem = parse_rule(found[2])
                if problem is None:
                    out.append(Rule(found[1], **parts, file=path.name, line=number))
    return out


def data_items(text: str) -> list[tuple[str, str]]:
    return [(m[1].strip(), m[2].strip()) for _, x in _items(text, {}) if (m := ITEM_LINE.match(x))]


def pack_regulations(root: Path) -> set[str] | None:
    """`<pack>.<regulation>` of each pack in `[domain] packs`, or None when the table is refused."""
    import check_domains

    import config

    try:
        packs = config.domain_settings(Path(root))["packs"]
    except config.CheckError:
        return None
    out = set()
    for name in packs:
        path = check_domains.pack_path(Path(root), name)
        regs = (check_domains.load(path) or {}).get("regulations", []) if path else []
        out |= {f"{name}.{r['id']}" for r in regs if isinstance(r, dict) and "id" in r}
    return out


def _check_rules(paths: list[Path], texts: dict, patterns: list) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    seen: dict[str, str] = {}
    for path in paths:
        name, text = path.name, texts[path.name]
        if not RULES_FILE.match(name):
            out.append((name, "a rules file is not rules-<area>.md", "file"))
            continue
        count = 0
        for number, line in _items(text, _guarded(text, patterns)):
            found = RULE_LINE.match(line)
            if not found:
                out.append((name, "a line is not a rule", f"line {number}"))
                continue
            rid = found[1]
            count += 1
            if not RULE_ID.match(rid):
                out.append((name, "the rule id is not BR-<n>", rid))
            elif rid in seen:
                also = "twice in the file" if seen[rid] == name else f"also in {FOLDER}/{seen[rid]}"
                out.append((name, f"the rule id is used {also}", rid))
            seen.setdefault(rid, name)
            problem = parse_rule(found[2])[1]
            if problem:
                out.append((name, problem, rid))
            if count == MAX_RULES + 1:
                out.append((name, f"the file holds over {MAX_RULES} rules", rid))
    return out


def _check_entities(text: str, patterns: list) -> list[tuple[str, str, str]]:
    out, names, relations, current = [], set(), [], None
    skip = _guarded(text, patterns)
    for number, line in enumerate(text.splitlines(), 1):
        if number in skip:
            continue
        if line.startswith("## "):
            current = line[3:].strip()
            if current in names:
                out.append((ENTITIES, "an entity is named twice", current))
            names.add(current)
        elif line.startswith("- "):
            found = RELATION.match(line.rstrip())
            ident = current or f"line {number}"
            if not found:
                out.append((ENTITIES, "a line is not a relation", ident))
            elif not CARDINALITY.match(found[2]):
                out.append((ENTITIES, "a relation is not <one|many> to <one|many>", ident))
            else:
                relations.append((found[1].strip(), ident))
    out += [(ENTITIES, "a relation names no entity", i) for e, i in relations if e not in names]
    return out


def _check_data(text: str, patterns: list) -> list[tuple[str, str, str]]:
    out, seen = [], set()
    for number, line in _items(text, _guarded(text, patterns)):
        found = ITEM_LINE.match(line)
        if not found:
            out.append((DATA, "a line is not <item>: <class>", f"line {number}"))
            continue
        item, kind = found[1].strip(), found[2].strip()
        if kind not in CLASSES:
            out.append((DATA, "the class is not one of the five classes", item))
        if item in seen:
            out.append((DATA, "a data item is named twice", item))
        seen.add(item)
    return out


def _check_regulations(text: str, patterns: list, known: set | None) -> list:
    out, seen = [], set()
    for number, line in _items(text, _guarded(text, patterns)):
        found = REG_LINE.match(line)
        if not found:
            out.append(
                (REGULATIONS, "a line is not <pack>.<regulation>: <decision>", f"line {number}")
            )
            continue
        rid, (scope, _, reason) = found[1], found[2].partition(",")
        if scope.strip() not in SCOPES or not reason.strip():
            out.append(
                (REGULATIONS, "the decision is not in scope or out of scope with a reason", rid)
            )
        if known is not None and rid not in known:
            out.append((REGULATIONS, "the regulation is of no pack in [domain] packs", rid))
        if rid in seen:
            out.append((REGULATIONS, "a regulation is named twice", rid))
        seen.add(rid)
    return out


def findings(root: Path) -> list[str]:
    """Rule 7: the problems of `docs/domain/`, each naming the rule, the file and the id."""
    where = folder(root)
    if not where.is_dir():
        return []
    patterns = _patterns(root)
    found: list[tuple[str, str, str]] = []
    names = [ENTITIES] + [p.name for p in rule_files(root)] + [DATA, REGULATIONS]
    texts: dict[str, str] = {}
    for name in names:
        path = where / name
        text = read(path) if path.is_file() else ""
        if text is None:
            found.append((name, "the file cannot be read", "file"))
        texts[name] = text or ""
        for line, kind in sorted(_guarded(texts[name], patterns).items()):
            found.append(
                (name, f"line {line} holds what the data guard flags {kind}", f"line {line}")
            )
    found += _check_entities(texts[ENTITIES], patterns)
    found += _check_rules(rule_files(root), texts, patterns)
    found += _check_data(texts[DATA], patterns)
    found += _check_regulations(texts[REGULATIONS], patterns, pack_regulations(root))
    return list(dict.fromkeys(f"{RULE}: {FOLDER}/{f}: {what} (id: {i})" for f, what, i in found))


# --- the writer (answer 2) --------------------------------------------------------------------


def _scan(root: Path, *values: str) -> None:
    for value in values:
        if "\n" in value or "\r" in value:
            raise Refused("a value holds a line break (setting: the command's options)")
        hits = scan_text(value, _patterns(root))
        if hits:
            kinds = ", ".join(sorted({h.kind for h in hits}))
            raise Refused(
                f"a value holds what the data guard flags ({kinds}) (setting: [guard] patterns)"
            )


def _append(root: Path, name: str, template: str, text: str) -> None:
    path = folder(root) / name
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text((TEMPLATES / template).read_text(encoding="utf-8"), encoding="utf-8")
    old = read(path)
    if old is None:
        raise Refused(f"{FOLDER}/{name} cannot be read (path class: {FOLDER}/)")
    path.write_text(old + ("" if old.endswith("\n") or not old else "\n") + text, encoding="utf-8")


def cmd_init(root: Path, area: str) -> str:
    where = folder(root)
    if where.is_dir() and any(where.glob("*.md")):
        raise Refused(f"the domain model exists (path class: {FOLDER}/)")
    targets = {
        ENTITIES: "domain-entities.md",
        f"rules-{area}.md": "domain-rules.md",
        DATA: "domain-data.md",
        REGULATIONS: "domain-regulations.md",
    }
    where.mkdir(parents=True, exist_ok=True)
    for name, template in targets.items():
        (where / name).write_text(
            (TEMPLATES / template).read_text(encoding="utf-8"), encoding="utf-8"
        )
    return f"wrote {len(targets)} files under {FOLDER}/"


def cmd_rule(root: Path, opts: argparse.Namespace) -> str:
    _scan(root, opts.text, opts.where, opts.owner)
    if opts.source not in SOURCES:
        raise Refused(
            "the source kind is not customer material, interview or code (setting: --source)"
        )
    if ";" in opts.where + opts.owner or not (
        opts.text.strip() and opts.where.strip() and opts.owner.strip()
    ):
        raise Refused(
            "a rule needs text, a place and an owner without ; (setting: --where, --owner)"
        )
    name = f"rules-{opts.area}.md"
    held = [
        r
        for p in rule_files(root)
        for _, x in _items(read(p) or "", {})
        if (r := RULE_LINE.match(x))
    ]
    numbers = [int(m[1][3:]) for m in held if RULE_ID.match(m[1])]
    path = folder(root) / name
    if path.is_file() and sum(1 for _ in _items(read(path) or "", {})) >= MAX_RULES:
        raise Refused(f"{FOLDER}/{name} holds {MAX_RULES} rules: split by area (setting: --area)")
    rid = f"BR-{max(numbers, default=0) + 1}"
    status = "inferred" if opts.inferred else "confirmed"
    source = f"source: {opts.source}, {opts.where.strip()}"
    line = f"- {rid}: {opts.text.strip()}; {source}; owner: {opts.owner.strip()}; {status}\n"
    _append(root, name, "domain-rules.md", line)
    return f"wrote {rid} to {FOLDER}/{name}"


def cmd_classify(root: Path, item: str, kind: str) -> str:
    _scan(root, item)
    if kind not in CLASSES:
        raise Refused("the class is not one of the five classes (setting: --class)")
    if item.strip() in {i for i, _ in data_items(read(folder(root) / DATA) or "")}:
        raise Refused("the data item is named already (setting: --item)")
    _append(root, DATA, "domain-data.md", f"- {item.strip()}: {kind}\n")
    return f"classified one data item in {FOLDER}/{DATA}"


def cmd_entity(root: Path, name: str, meaning: str, relates: list[str]) -> str:
    _scan(root, name, meaning, *relates)
    text = read(folder(root) / ENTITIES) or ""
    names = {line[3:].strip() for line in text.splitlines() if line.startswith("## ")}
    if not name.strip() or name.strip() in names:
        raise Refused("the entity is named already (setting: --name)")
    lines = []
    for spec in relates:
        other, cards, reason = (spec.split(":", 2) + ["", ""])[:3]
        left, _, right = cards.partition("-")
        relation = f"- relates to {other.strip()}: {left} to {right}, {reason.strip()}"
        if other.strip() not in names | {name.strip()} or not CARDINALITY.match(
            relation.split(": ", 1)[1]
        ):
            raise Refused("a relation names no entity or no <one|many> pair (setting: --relates)")
        lines.append(relation + "\n")
    block = f"\n## {name.strip()}\n\n{meaning.strip()}\n" + ("\n" + "".join(lines) if lines else "")
    _append(root, ENTITIES, "domain-entities.md", block)
    return f"wrote one entity to {FOLDER}/{ENTITIES}"


def cmd_regulation(root: Path, rid: str, scope: str, reason: str) -> str:
    _scan(root, rid, reason)
    known = pack_regulations(root)
    if known is None or rid not in known:
        raise Refused("the regulation is of no pack in [domain] packs (setting: domain.packs)")
    text = read(folder(root) / REGULATIONS) or ""
    if any(m and m[1] == rid for _, x in _items(text, {}) for m in [REG_LINE.match(x)]):
        raise Refused("the regulation is named already (setting: --id)")
    if not reason.strip():
        raise Refused("a decision needs a reason (setting: --reason)")
    _append(
        root,
        REGULATIONS,
        "domain-regulations.md",
        f"- {rid}: {SCOPE_WORDS[scope]}, {reason.strip()}\n",
    )
    return f"recorded one regulation in {FOLDER}/{REGULATIONS}"


def cmd_confirm(root: Path, rid: str) -> str:
    """Rule 9: after the person's recorded yes, only the status word changes."""
    for rule in rules(root):
        if rule.id == rid and rule.status == "inferred":
            path = folder(root) / rule.file
            lines = (read(path) or "").splitlines(keepends=True)
            at = rule.line - 1
            end = lines[at][len(lines[at].rstrip("\r\n")) :]
            lines[at] = lines[at].rstrip("\r\n")[: -len("inferred")] + "confirmed" + end
            path.write_text("".join(lines), encoding="utf-8")
            return f"confirmed {rid} in {FOLDER}/{rule.file}"
    raise Refused("no inferred rule has that id (setting: --id)")


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="domain_model.py", description=__doc__.split("\n\n")[0])
    top.add_argument("--root", default=".")
    sub = top.add_subparsers(dest="command", required=True)
    sub.add_parser("init").add_argument("--area", required=True)
    rule = sub.add_parser("rule")
    for key in ("--area", "--text", "--source", "--where", "--owner"):
        rule.add_argument(key, required=True)
    rule.add_argument("--inferred", action="store_true")
    classify = sub.add_parser("classify")
    classify.add_argument("--item", required=True)
    classify.add_argument("--class", dest="kind", required=True)
    entity = sub.add_parser("entity")
    entity.add_argument("--name", required=True)
    entity.add_argument("--meaning", required=True)
    entity.add_argument("--relates", action="append", default=[])
    reg = sub.add_parser("regulation")
    reg.add_argument("--id", required=True)
    reg.add_argument("--scope", choices=("in", "out"), required=True)
    reg.add_argument("--reason", required=True)
    sub.add_parser("confirm").add_argument("--id", required=True)
    return top


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    opts = parser().parse_args(argv)
    root = Path(opts.root)
    if getattr(opts, "area", None) is not None and not AREA.match(opts.area):
        print("refused: the area is not a lower-case slug (setting: --area)")
        return 1
    commands = {
        "init": lambda: cmd_init(root, opts.area),
        "rule": lambda: cmd_rule(root, opts),
        "classify": lambda: cmd_classify(root, opts.item, opts.kind),
        "entity": lambda: cmd_entity(root, opts.name, opts.meaning, opts.relates),
        "regulation": lambda: cmd_regulation(root, opts.id, opts.scope, opts.reason),
        "confirm": lambda: cmd_confirm(root, opts.id),
    }
    try:
        print(f"ok domain-model: {commands[opts.command]()}")
    except Refused as exc:
        print(f"refused: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
