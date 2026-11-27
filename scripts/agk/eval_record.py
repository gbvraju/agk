# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The eval record and its acceptance (SPEC-0077 rules 10 and 16; REQ-084; brief #2043 build (h),
ADR-0847). Kit-only: `kit/manifest.json` lists it nowhere.

    python3 scripts/agk/eval_record.py write --runs DIR [--date YYYY-MM-DD]
    python3 scripts/agk/eval_record.py accept <date> --said FILE --at <UTC time> [--by LOGIN]

`write` reads build (g)'s run records `DIR/<product>/run-<n>.json` and writes
`docs/runs/evals/<date>.md` (`- Status: proposed`), with each median compared with the last
accepted record's beyond `tolerance` of `evals/rubric.toml`; it never overwrites. `accept` sets
`- Status: accepted` and one `- Accepted:` line only on the person's plain yes
(`steward_owner.yes_of`, in team mode a `spec_approvers` login), recording one `Setup` entry; any
other reply changes no file. `accepted` is the one reader that `check_release`, `check_packs` and
`scorecard` use. Files and git only: no network, no model. Refusals name the path class or the
setting, never a value.
"""

from __future__ import annotations

import hashlib
import re
import statistics
import subprocess  # nosec B404 - git with fixed argument lists, no shell
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

LAYERS: tuple[str, ...] = ()
RUNS = 3
try:
    from eval_run import LAYERS, RUNS
except ImportError:  # outside the kit: `main` refuses before any use
    pass

KIT = Path(__file__).resolve().parents[2]
FOLDER = "docs/runs/evals"
RUBRIC = "evals/rubric.toml"
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
AT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z")
FIELD = re.compile(
    r"- (Status|Accepted|Kit|Rubric|Tolerance|Cost per accepted feature|Compared with"
    r"|Regressions):(?: (.*))?$"
)
HEADER = "| product | layer | run 1 | run 2 | run 3 | median |"
TOLERANCE = "refused: evals/rubric.toml (setting: tolerance)"
EXISTS = f"refused: a record exists for the date (path class: {FOLDER}/)"
NO_RECORD = f"refused: no record in its form for the date (path class: {FOLDER}/)"
BAD_RUNS = "refused: a run record is out of form (path class: the run folder)"
ONE_KIT = "refused: the runs are not of one kit (path class: the run folder)"
GUARDED = f"refused: a line the data guard flags (path class: {FOLDER}/)"
ALREADY = "refused: the record is already accepted (SPEC-0077 rule 10)"
REGRESSED = "refused: a record with a regression is never accepted (SPEC-0077 rule 10)"
OTHER_RUBRIC = "refused: the record was scored on another rubric (path class: evals/)"


def _git(root: Path, *args: str) -> str | None:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, check=False
    )
    return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else None


def review_mode(root: Path) -> str:
    from common import review_mode as mode

    return mode(root)


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def tolerance(root: Path) -> float | None:
    """Rule 10's `tolerance`: a number from 0 to 6, never a `bool`; None when it is not."""
    try:
        value = tomllib.loads((Path(root) / RUBRIC).read_text("utf-8")).get("tolerance")
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return float(value) if 0 <= value <= 6 else None


def rubric_digest(root: Path) -> str:
    try:
        return hashlib.sha256((Path(root) / RUBRIC).read_bytes()).hexdigest()
    except OSError:
        return ""


def applies(root: Path, ref: str | None = None) -> bool:
    """Whether the tree (the checkout, or REF) holds `evals/rubric.toml`: the kit."""
    if ref is None:
        return (Path(root) / RUBRIC).is_file()
    return _git(Path(root), "cat-file", "-e", f"{ref}:{RUBRIC}") is not None


def _show(value: Any) -> str:
    return f"{value:g}" if _num(value) else str(value).replace("|", "/").replace("\n", " ")


def compare(new: dict, last: dict | None, tol: float) -> list[str]:
    """Rule 10: a regression is a median below the last accepted one by more than TOL (higher is
    better), or a product or layer of the last record missing from the new; none with no last."""
    out = []
    for product, layers in (last or {}).items():
        for layer, was in layers.items():
            now = new.get(product, {}).get(layer, "missing")
            if now == "missing":
                out.append(f"{product} {layer} missing")
            elif now is not None and was is not None and now < was - tol:
                out.append(f"{product} {layer} {now:g} (was {was:g}, tolerance {tol:g})")
    return out


def _product(name: str, recs: list) -> tuple[list[str], dict, str | None, list]:
    """(table rows, layer medians, the incomplete line, complete runs) of one product."""
    complete = [r for r in recs if r and r["status"] == "complete"]

    def cell(rec: dict | None, value: Any) -> str:
        if rec is None:
            return "missing"
        return f"incomplete ({rec['stage']})" if rec["status"] != "complete" else _show(value)

    keys: list[tuple[str, str]] = [("review", layer) for layer in LAYERS]
    for part in ("objective", "process", "cost"):
        for rec in complete:
            keys += [(part, k) for k in rec[part] if (part, k) not in keys]
    rows, medians = [], {}
    for part, key in keys:
        values = [r[part].get(key) for r in complete]
        mid = statistics.median(values) if values and all(map(_num, values)) else None
        if part == "review":
            medians[key] = mid
        label = key if part == "review" else f"{part}.{key}"
        cells = [cell(r, r[part].get(key) if r else None) for r in recs]
        rows.append(
            f"| {name} | {label} | {' | '.join(cells)} | {_show(mid) if mid is not None else '-'} |"
        )
    short = None
    if len(complete) < RUNS:
        stage = next((r["stage"] for r in recs if r and r["status"] != "complete"), "missing")
        short = f"{name} incomplete {stage}"
    return rows, medians, short, complete


def _runs(folder: Path) -> dict[str, list]:
    import json

    out = {}
    for product in sorted(p for p in folder.iterdir() if p.is_dir()):
        recs = []
        for n in range(1, RUNS + 1):
            path = product / f"run-{n}.json"
            recs.append(json.loads(path.read_text("utf-8")) if path.is_file() else None)
        out[product.name] = recs
    return out


def write(root: Path, runs: Path, day: str) -> tuple[int, list[str]]:
    """Answer 1: the record of the runs under RUNS for DAY, compared with the last accepted."""
    import eval_run
    from guard import scan_text

    from config import guard_patterns

    root = Path(root)
    tol = tolerance(root)
    if tol is None:
        return 1, [TOLERANCE]
    path = root / FOLDER / f"{day}.md"
    if path.exists():
        return 1, [EXISTS]
    fails = eval_run.median(Path(runs))[0] if Path(runs).is_dir() else [BAD_RUNS]
    products = _runs(Path(runs)) if not fails else {}
    if fails or not products:
        return 1, list(dict.fromkeys([*fails, BAD_RUNS]))
    kits = {(r["kit"]["version"], r["kit"]["sha"]) for recs in products.values() for r in recs if r}
    if len(kits) != 1:
        return 1, [ONE_KIT]
    table, medians, regressions, costs = (
        [HEADER, "| --- | --- | --- | --- | --- | --- |"],
        {},
        [],
        [],
    )
    for name, recs in products.items():
        rows, medians[name], short, complete = _product(name, recs)
        table += rows
        regressions += [short] if short else []
        costs += [eval_run.per_feature(r) for r in complete]
    known = [c for c in costs if c is not None]
    cost = (
        f"{statistics.median(known):.2f} usd" if known and len(known) == len(costs) else "unknown"
    )
    last = accepted(root)
    regressions += compare(medians, last[1]["medians"] if last else None, tol)
    ((version, sha),) = kits
    lines = [
        f"# Eval record {day}",
        "",
        "- Status: proposed",
        f"- Kit: {version} at {sha}",
        f"- Rubric: {rubric_digest(root)}",
        f"- Tolerance: {tol:g}",
        f"- Cost per accepted feature: {cost}",
        f"- Compared with: {last[0] if last else 'none (first record)'}",
        "- Regressions:" + ("" if regressions else " none"),
        *(f"- {r}" for r in regressions),
        "",
        *table,
    ]
    patterns = guard_patterns(root)
    if any(scan_text(line, patterns) for line in lines):
        return 1, [GUARDED]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0, [f"wrote {FOLDER}/{day}.md ({len(regressions)} regressions)"]


def parse(text: str) -> dict | None:
    """The record's fields and layer medians; None when it is out of answer 1's form."""
    fields: dict[str, str] = {}
    regressions: list[str] = []
    medians: dict[str, dict] = {}
    lines = text.splitlines()
    for n, line in enumerate(lines):
        found = FIELD.match(line)
        if found and found.group(1) not in fields:
            fields[found.group(1)] = (found.group(2) or "").strip()
            if found.group(1) == "Regressions" and not fields["Regressions"]:
                for more in lines[n + 1 :]:
                    if not more.startswith("- ") or FIELD.match(more):
                        break
                    regressions.append(more[2:].strip())
        cells = (
            [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("| ") else []
        )
        if len(cells) == 6 and cells[1] in LAYERS:
            if cells[5] != "-":
                try:
                    value = float(cells[5])
                except ValueError:
                    return None
                if not 0 <= value <= 6:
                    return None
            medians.setdefault(cells[0], {})[cells[1]] = None if cells[5] == "-" else value
    need = ("Status", "Kit", "Rubric", "Tolerance", "Cost per accepted feature", "Compared with")
    if any(k not in fields for k in (*need, "Regressions")) or not medians:
        return None
    if fields["Status"] not in ("proposed", "accepted") or not re.fullmatch(
        r"[0-9a-f]{64}", fields["Rubric"]
    ):
        return None
    if fields["Regressions"] not in ("", "none") or (
        fields["Regressions"] == "" and not regressions
    ):
        return None
    return {
        "status": fields["Status"],
        "accepted": fields.get("Accepted") or None,
        "rubric": fields["Rubric"],
        "cost": fields["Cost per accepted feature"],
        "regressions": regressions,
        "medians": medians,
    }


def accepted(
    root: Path, ref: str | None = None, path: str | None = None
) -> tuple[str, dict] | None:
    """Answer 4: the newest record (of the checkout, or of REF) with `- Status: accepted`, an
    `- Accepted:` line and `- Regressions: none`; with PATH, that record only."""
    root = Path(root)
    if ref is None:
        folder = root / FOLDER
        names = [p.name for p in folder.glob("*.md")] if folder.is_dir() else []
    else:
        listing = _git(root, "ls-tree", "--name-only", ref, f"{FOLDER}/") or ""
        names = [Path(x).name for x in listing.splitlines()]
    if path is not None:
        want = path if path.endswith(".md") else f"{path}.md"
        names = [n for n in names if f"{FOLDER}/{n}" == want]
    for name in sorted(
        (n for n in names if DAY.fullmatch(n[:-3]) and n.endswith(".md")), reverse=True
    ):
        rel = f"{FOLDER}/{name}"
        try:
            text = (
                (root / rel).read_text("utf-8")
                if ref is None
                else _git(root, "show", f"{ref}:{rel}")
            )
        except (OSError, UnicodeDecodeError):
            text = None
        rec = parse(text or "")
        if rec and rec["status"] == "accepted" and rec["accepted"] and not rec["regressions"]:
            return name[:-3], rec
    return None


def accept(root: Path, day: str, said: Path, at: str, by: str | None, gh) -> tuple[int, list[str]]:
    """Answer 3: the record of DAY accepted only on the person's plain yes."""
    import steward
    import steward_owner
    import steward_voice

    root = Path(root)
    path = root / FOLDER / f"{day}.md"
    text = path.read_text("utf-8") if DAY.fullmatch(day) and path.is_file() else ""
    rec = parse(text)
    if rec is None:
        return 1, [NO_RECORD]
    if rec["status"] == "accepted":
        return 1, [ALREADY]
    if rec["regressions"]:
        return 1, [REGRESSED]
    if rec["rubric"] != rubric_digest(root):
        return 1, [OTHER_RUBRIC]
    code, refusal, words = steward_owner.yes_of(root, Path(said), by)
    if refusal:
        return code, [refusal]
    if not words or not steward_voice.is_yes(words):
        return 1, [f"eval-record {day}: not accepted"]
    who = f" (by {by})" if by and review_mode(root) == "team" else ""
    line = f'the person said "{" ".join(words.split())}" at {at}{who}'
    code, out = steward.record(root, "Setup", f"eval-record {day}: accepted because {line}", gh)
    if code:
        return code, out
    path.write_text(
        text.replace("- Status: proposed", f"- Status: accepted\n- Accepted: {line}", 1), "utf-8"
    )
    return 0, [*out, f"accepted {FOLDER}/{day}.md"]


USAGE = (
    "usage: eval_record.py write --runs DIR [--date YYYY-MM-DD]"
    " | accept <date> --said FILE --at <UTC time> [--by LOGIN]"
)


def _options(args: list[str], allowed: tuple[str, ...]) -> dict[str, str]:
    from common import option_pairs

    if len(args) % 2:
        raise ValueError(USAGE)
    pairs = option_pairs(args, strict=True)
    names = [name for name, _ in pairs]
    if any(n not in allowed for n in names) or len(set(names)) != len(names):
        raise ValueError(USAGE)
    return dict(pairs)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not ((KIT / "kit" / "manifest.json").is_file() and (KIT / "evals").is_dir()):
        print(
            "eval_record: runs only in the kit's own repository (path class: evals/)",
            file=sys.stderr,
        )
        return 2
    try:
        if args[:1] == ["write"]:
            opts = _options(args[1:], ("--runs", "--date"))
            day = opts.get("--date") or datetime.now(UTC).date().isoformat()  # as `date -u`
            if "--runs" not in opts or not DAY.fullmatch(day):
                raise ValueError(f"{USAGE} (option: --runs or --date)")
            code, lines = write(KIT, Path(opts["--runs"]), day)
        elif args[:1] == ["accept"] and len(args) >= 2:
            import steward

            opts = _options(args[2:], ("--said", "--at", "--by"))
            if "--said" not in opts or not AT.fullmatch(opts.get("--at", "")):
                raise ValueError(f"{USAGE} (option: --said or --at)")
            if not Path(opts["--said"]).is_file():
                raise ValueError("the words file cannot be read (option: --said)")
            code, lines = accept(
                KIT, args[1], Path(opts["--said"]), opts["--at"], opts.get("--by"), steward.gh_api
            )
        else:
            raise ValueError(USAGE)
    except ValueError as exc:
        print(f"eval_record: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines), file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
