# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The evaluation set's checks (SPEC-0077 rules 9 and 10; REQ-084; brief #2042 build (a), ADR-0846).
Kit-only: `kit/manifest.json` lists it nowhere, and it runs only in the kit's own repository.

    python3 scripts/agk/eval_run.py check [--root DIR]
    python3 scripts/agk/eval_run.py median DIR

`check` reads `evals/rubric.toml` and each `evals/<id>/product.toml` and prints one line per
problem, `FAIL evals: <file class>: <rule>: <what> (setting: <key>)`, never a value, exit 1, else
`ok evals: <n> products, <m> layers`. `median DIR` checks each run record
`DIR/<product>/run-<n>.json` (n 1 to 3) and prints, per product, the median of each layer over
three complete runs and the cost per accepted feature, or
`<product> incomplete (<k> of 3 runs complete)`, never 0 (`Q-PG-3`).
Files only: no network, no model, no GitHub call. Build (b) adds `run`.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

KIT = Path(__file__).resolve().parents[2]
RUNS = 3  # rule 9: three runs on `strongest`; never a rubric key
TIER = "strongest"
LAYERS = (  # rule 9's eight layers, in order
    "problem",
    "scope",
    "domain-rules",
    "architecture",
    "threats",
    "data",
    "usability",
    "code",
)
NUM, INT, STR, STRS, TABLE, ROWS = "number", "int", "str", "strs", "table", "rows"
PRODUCT = {
    "format": INT,
    "id": STR,
    "title": STR,
    "source": STR,
    "work_type": STR,
    "domain": STR,
    "idea": STR,
    "problem": STR,
    "users": STRS,
    "non_goals": STRS,
    "acceptance": ROWS,
    "answers": TABLE,
}
RUBRIC = {"format": INT, "scale": INT, "tolerance": NUM, "layer": ROWS}
RECORD = {
    "product": STR,
    "run": INT,
    "kit": TABLE,
    "tier": STR,
    "models": STRS,
    "status": STR,
    "objective": TABLE,
    "process": TABLE,
    "cost": TABLE,
    "review": TABLE,
    "accepted": STRS,
}
COST = ("input", "cache_write", "cache_read", "output", "other", "total")
WORDS = ("unknown", "not-run")  # a figure not read, never 0
STAGES_MORE = ("review", "tier", "unknown")
AC = re.compile(r"^AC[1-9][0-9]*$")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
SPEC_RULE = re.compile(r"^SPEC-\d{4} rule \d+$")
HOST = re.compile(r"https?://([^/\s\"'<>]+)")
ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]+)")


class Usage(Exception):
    """A refused option or place: exit 2, naming the option or the path class."""


def _is(value: Any, kind: str) -> bool:
    if kind == INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == NUM:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == STR:
        return isinstance(value, str) and bool(value.strip())
    if kind == STRS:
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if kind == TABLE:
        return isinstance(value, dict)
    return isinstance(value, list) and all(isinstance(v, dict) for v in value)


def _as(value: Any, kind: str, default: Any) -> Any:
    return value if _is(value, kind) else default


def keys(data: dict, form: dict[str, str], rule: str, optional: tuple[str, ...] = ()) -> list:
    """(rule, what, key) for each missing, unknown or wrongly typed key."""
    out = [(rule, "an unknown key", k) for k in data if k not in form and k not in optional]
    for key, kind in form.items():
        if key not in data:
            out.append((rule, "a missing key", key))
        elif not _is(data[key], kind):
            out.append((rule, "a value of the wrong type", key))
    return out


def texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for v in value.values() for t in texts(v)]
    if isinstance(value, list):
        return [t for v in value for t in texts(v)]
    return []


def product_problems(data: dict, folder: str) -> list:
    rule = "rule 9"
    out = keys(data, PRODUCT, rule)
    if data.get("format") != 1 and _is(data.get("format"), INT):
        out.append((rule, "an unknown format", "format"))
    if _is(data.get("id"), STR) and data["id"] != folder:
        out.append((rule, "an id that is not its folder's name", "id"))
    stems = {p.stem for p in (KIT / "config" / "playbooks").glob("*.toml")}  # the kit's own
    if _is(data.get("work_type"), STR) and data["work_type"] not in stems:
        out.append((rule, "a value outside its list", "work_type"))
    if _is(data.get("domain"), STR) and data["domain"] not in ("none", *shipped_domains()):
        out.append((rule, "a value outside its list", "domain"))
    if _is(data.get("source"), STR) and not DATE.search(data["source"]):
        out.append((rule, "a source with no read date", "source"))
    rows: list = _as(data.get("acceptance"), ROWS, [])
    if rows and not 3 <= len(rows) <= 12:
        out.append((rule, "not 3 to 12 acceptance criteria", "acceptance"))
    ids = [r.get("id") for r in rows]
    for row in rows:
        out += [
            (rule, w, f"acceptance.{k}") for _, w, k in keys(row, {"id": STR, "text": STR}, rule)
        ]
    if any(not (isinstance(i, str) and AC.match(i)) for i in ids):
        out.append((rule, "an acceptance id not of the form AC<n>", "acceptance.id"))
    if len(ids) != len(set(map(str, ids))):
        out.append((rule, "a repeated acceptance id", "acceptance.id"))
    if _is(data.get("answers"), TABLE) and not _is(list(data["answers"].values()), STRS):
        out.append((rule, "a value of the wrong type", "answers"))
    for text in texts(data):
        if any(not _ours(h, "example.com") for h in HOST.findall(text)):
            out.append((rule, "a host other than example.com", "host"))
        if any(not _ours(a, "invalid") for a in ADDRESS.findall(text)):
            out.append((rule, "an address outside .invalid", "address"))
    return list(dict.fromkeys(out))


def _ours(host: str, suffix: str) -> bool:
    host = host.lower().split(":")[0].rstrip(".,;)")
    return host == suffix or host.endswith("." + suffix)


def shipped_domains() -> tuple[str, ...]:
    import check_domains

    return tuple(check_domains.SHIPPED)


def rubric_problems(data: dict) -> list:
    out = keys(data, RUBRIC, "rule 9")
    tol: Any = data.get("tolerance")
    if "tolerance" in data:
        out = [(r, w, k) for r, w, k in out if k != "tolerance"]
        if not _is(tol, NUM):
            out.append(("rule 10", "a value of the wrong type", "rubric.tolerance"))
        elif not 0 <= tol <= 6:
            out.append(("rule 10", "a value outside 0 to 6", "rubric.tolerance"))
    if data.get("format") != 1 and _is(data.get("format"), INT):
        out.append(("rule 9", "an unknown format", "format"))
    if data.get("scale") != 6 and _is(data.get("scale"), INT):
        out.append(("rule 9", "a scale other than 0 to 6", "scale"))
    layers: list = _as(data.get("layer"), ROWS, [])
    if tuple(layer.get("name") for layer in layers) != LAYERS:
        out.append(("rule 9", "a layer missing or out of order", "layer.name"))
    for layer in layers:
        found = keys(layer, {"name": STR, "criteria": ROWS}, "rule 9")
        out += [(r, w, f"layer.{k}") for r, w, k in found]
        for crit in layer.get("criteria") or [] if _is(layer.get("criteria"), ROWS) else []:
            form = {"text": STR, "source": STR}
            out += [
                (r, "a criterion with no source" if k == "source" else w, f"criteria.{k}")
                for r, w, k in keys(crit, form, "rule 9", ("accessed",))
            ]
            src = crit.get("source")
            if _is(src, STR) and not SPEC_RULE.match(src):
                dated = isinstance(crit.get("accessed"), str) and DATE.fullmatch(crit["accessed"])
                if not (src.startswith("https://") and dated):
                    out.append(
                        (
                            "rule 9",
                            "a source neither a spec rule nor a dated URL",
                            "criteria.source",
                        )
                    )
    return list(dict.fromkeys(out))


def read_toml(path: Path) -> dict | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None


def scanned(path: Path) -> bool:
    from guard import scan_text

    try:
        return bool(scan_text(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError):
        return False


def check(root: Path) -> tuple[list[str], str]:
    """The FAIL lines of `root/evals`, and the ok line."""
    evals = root / "evals"
    lines: list[str] = []

    def add(cls: str, found: list) -> None:
        lines.extend(f"FAIL evals: {cls}: {r}: {w} (setting: {k})" for r, w, k in found)

    def read(path: Path, cls: str) -> dict | None:
        data = read_toml(path)
        if data is None:
            add(cls, [("rule 9", "not TOML", "file")])
        if scanned(path):
            add(cls, [("rule 9", "a line the secret scan flags", "file")])
        return data

    rubric = read(evals / "rubric.toml", "rubric")
    if rubric is not None:
        add("rubric", rubric_problems(rubric))
    folders = sorted(p for p in evals.iterdir() if p.is_dir())
    for folder in folders:
        cls = f"product file {folder.name}"
        data = read(folder / "product.toml", cls)
        if data is not None:
            add(cls, product_problems(data, folder.name))
    if not folders:
        add("product file", [("rule 9", "no product", "evals")])
    layers = len(rubric.get("layer") or []) if isinstance(rubric, dict) else 0
    return lines, f"ok evals: {len(folders)} products, {layers} layers"


def record_problems(data: dict, product: str, n: int) -> list:
    rule = "rule 9"
    out = keys(data, RECORD, rule, ("stage",))
    if data.get("product") != product and _is(data.get("product"), STR):
        out.append((rule, "a product that is not its folder's name", "product"))
    if data.get("run") != n and _is(data.get("run"), INT):
        out.append((rule, "a run that is not its file's number", "run"))
    if _is(data.get("kit"), TABLE):
        out += [
            (r, w, f"kit.{k}") for r, w, k in keys(data["kit"], {"version": STR, "sha": STR}, rule)
        ]
    if _is(data.get("tier"), STR) and data["tier"] != TIER:
        out.append((rule, "a value outside its list", "tier"))
    status = data.get("status")
    if _is(status, STR) and status not in ("complete", "incomplete"):
        out.append((rule, "a value outside its list", "status"))
    if status == "incomplete" and "stage" not in data:
        out.append((rule, "a missing key", "stage"))
    if status == "complete" and "stage" in data:
        out.append((rule, "a stage on a complete run", "stage"))
    if status == "incomplete" and "stage" in data and data["stage"] not in stages():
        out.append((rule, "a value outside its list", "stage"))
    for part in ("objective", "process"):
        for key, value in (data.get(part) or {}).items() if _is(data.get(part), TABLE) else []:
            if not (_is(value, NUM) or _is(value, STR)):
                out.append((rule, "a value of the wrong type", f"{part}.{key}"))
    cost: dict = _as(data.get("cost"), TABLE, {})
    for key in (*COST, "usd") if cost or "cost" not in data else ():
        value = cost.get(key)
        if key not in cost:
            out.append((rule, "a missing key", f"cost.{key}"))
        elif not (
            _is(value, INT if key != "usd" else NUM) or value in WORDS or _priced(key, value)
        ):
            out.append((rule, "a value of the wrong type", f"cost.{key}"))
    out += [(rule, "an unknown key", f"cost.{k}") for k in cost if k not in (*COST, "usd")]
    review: dict = _as(data.get("review"), TABLE, {})
    if any(k not in LAYERS for k in review):
        out.append((rule, "an unknown layer", "review"))
    if any(not (_is(v, INT) and 0 <= v <= 6) for v in review.values()):
        out.append((rule, "a score outside 0 to 6", "review"))
    if status == "complete" and set(review) != set(LAYERS):
        out.append((rule, "a layer not scored", "review"))
    accepted: list = _as(data.get("accepted"), STRS, [])
    if any(not AC.match(a) for a in accepted):
        out.append((rule, "an acceptance id not of the form AC<n>", "accepted"))
    if len(accepted) != len(set(accepted)):
        out.append((rule, "a repeated acceptance id", "accepted"))
    return list(dict.fromkeys(out))


def _priced(key: str, value: Any) -> bool:
    return key == "usd" and isinstance(value, str) and value.startswith("not priced (setting: ")


def stages() -> tuple[str, ...]:
    import steward_evidence

    return (*steward_evidence.STAGES, *STAGES_MORE)


def per_feature(rec: dict) -> float | None:
    usd, accepted = rec["cost"]["usd"], rec["accepted"]
    if not _is(usd, NUM) or not accepted:
        return None
    return usd / len(accepted)


def median(folder: Path) -> tuple[list[str], list[str]]:
    """(FAIL lines, report lines) of a saved run tree."""
    fails: list[str] = []
    report: list[str] = []
    for product in sorted(p for p in folder.iterdir() if p.is_dir()):
        complete = []
        for n in range(1, RUNS + 1):
            path = product / f"run-{n}.json"
            if not path.is_file():
                continue
            cls = f"run record {product.name} run-{n}"
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                fails.append(f"FAIL evals: {cls}: rule 9: not JSON (setting: file)")
                continue
            found = (
                record_problems(rec, product.name, n)
                if isinstance(rec, dict)
                else [("rule 9", "not a JSON object", "file")]
            )
            fails += [f"FAIL evals: {cls}: {r}: {w} (setting: {k})" for r, w, k in found]
            if not found and rec["status"] == "complete":
                complete.append(rec)
        if len(complete) < RUNS:
            report.append(f"{product.name} incomplete ({len(complete)} of {RUNS} runs complete)")
            continue
        for layer in LAYERS:
            value = statistics.median(rec["review"][layer] for rec in complete)
            report.append(f"{product.name} {layer} {value:g}")
        costs = [per_feature(rec) for rec in complete]
        known = [c for c in costs if c is not None]
        money = f"{statistics.median(known):.2f} usd" if len(known) == len(costs) else "unknown"
        report.append(f"{product.name} cost per accepted feature {money}")
    return fails, report


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if not ((KIT / "kit" / "manifest.json").is_file() and (KIT / "evals").is_dir()):
            raise Usage("eval_run.py runs only in the kit's own repository (path class: evals/)")
        if args[:1] == ["check"] and args[1:] in ([], *(["--root", a] for a in args[2:3])):
            root = Path(args[2]) if len(args) == 3 else KIT
            if not (root / "evals").is_dir():
                raise Usage("no evals/ under the root (option: --root)")
            fails, ok = check(root)
        elif args[:1] == ["median"] and len(args) == 2:
            if not Path(args[1]).is_dir():
                raise Usage("the run folder is not a folder (option: DIR)")
            fails, report = median(Path(args[1]))
            ok = "\n".join(report)
        else:
            raise Usage("usage: eval_run.py check [--root DIR] | median DIR")
    except Usage as exc:
        print(f"eval_run: {exc}", file=sys.stderr)
        return 2
    print("\n".join(fails) if fails else ok)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
