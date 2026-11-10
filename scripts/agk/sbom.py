"""The bill of materials of a commit, its offline check and its findings (SPEC-0054 rules 2-4, 7).

    python3 scripts/agk/sbom.py make [--ref REF] --out FILE
    python3 scripts/agk/sbom.py check FILE [--ref REF]
    python3 scripts/agk/sbom.py findings RESULT --bom FILE

`make` writes one CycloneDX JSON document of the components the repository's files declare at the
commit (default `HEAD`), read with local `git` only: the same commit gives the same bytes. `check`
compares a bill with its commit and prints `ok bom`, or one `FAIL bom: <class> <reason>` line per
problem, naming the class and the rule and never a name, a version or a value. It posts nothing,
opens no socket and starts no program other than `git`; no governance step runs it. `findings`
reads a scanner's saved JSON result and the bill, and starts nothing: it prints the counts by
severity, each finding's advisory ids with its component's class, name and pin, and every
component the result does not name as `unknown`. Nothing else of the result is kept, and a result
it cannot read is the one line `unknown: the scan result cannot be read` and exit 1.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from ci_tools import LINE as CI_TOOL_LINE
from ci_tools import PIN_FILE
from common import CheckError, git, repo_root

NAME = "bom"
USAGE = (
    "usage: sbom.py make [--ref REF] --out FILE | sbom.py check FILE [--ref REF]"
    " | sbom.py findings RESULT --bom FILE"
)
SPEC_VERSION = "1.6"  # ruled in Q-S0054-1; the newest version when this was built is 1.7 (Q-787-2)
PYPROJECT, AGK_TOML, MANIFEST, WORKFLOWS = (
    "pyproject.toml",
    "agk.toml",
    "kit/manifest.json",
    ".github/workflows/",
)
TYPES = {
    "python": "library",
    "ci-tool": "library",
    "scanner": "application",
    "action": "application",
    "kit-file": "file",
}
REQUIREMENT = re.compile(r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(\[[^\]]*\])?\s*(.*)")
EXACT = re.compile(r"==\s*([0-9A-Za-z][0-9A-Za-z.+!_-]*)")
SPECIFIERS = re.compile(r"(?:(?:===|==|~=|!=|<=|>=|<|>)\s*[^\s,]+\s*,?\s*)+")
USES = re.compile(r"""^\s*(?:-\s+)?uses:\s*["']?([^\s"'#]+)["']?[ \t]*(?:#[ \t]*(\S+))?""", re.M)
SCANNER_PIN = re.compile(r"""^\s*([A-Z][A-Z0-9_]*)_(VERSION|SHA256):\s*["']?([^\s"'#]+)""", re.M)
FULL_SHA = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
TOP_FIELDS = {"bomFormat", "specVersion", "version", "serialNumber", "metadata", "components"}
FIELDS = {"type", "bom-ref", "name", "version", "purl", "hashes", "properties"}
REQUIRED = {"type", "bom-ref", "name", "properties"}
SEVERITIES = ("critical", "high", "medium", "low", "unknown")
SCORES = (("critical", 9.0), ("high", 7.0), ("medium", 4.0), ("low", 0.0))
LABELS = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MODERATE": "medium",
    "MEDIUM": "medium",
    "LOW": "low",
}
ADVISORY_ID = re.compile(r"[A-Za-z][A-Za-z0-9]*-[A-Za-z0-9][A-Za-z0-9._:-]*")
SCORE = re.compile(r"[0-9]{1,2}(?:\.[0-9]+)?")
RESULT_UNREADABLE = "unknown: the scan result cannot be read"
BILL_UNREADABLE = "unknown: the bill cannot be read"
NOT_OF_FORM = (AttributeError, KeyError, OSError, RecursionError, TypeError, ValueError)


def show(root: Path, commit: str, path: str) -> bytes | None:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True
    )
    return proc.stdout if proc.returncode == 0 else None


def not_parsed(label: str) -> CheckError:
    return CheckError(f"{label} cannot be parsed at the commit (rule 2)")


def read_text(root: Path, commit: str, path: str, label: str | None = None) -> str:
    data = show(root, commit, path)
    if data is None:
        raise CheckError(f"{label or path} cannot be read at the commit (rule 2)")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise not_parsed(label or path) from None


def read_toml(root: Path, commit: str, path: str) -> dict:
    try:
        return tomllib.loads(read_text(root, commit, path))
    except tomllib.TOMLDecodeError:
        raise not_parsed(path) from None


def entry(
    kind: str,
    name: str,
    version: str | None = None,
    pin: str | None = None,
    purl: str | None = None,
    digest: str | None = None,
) -> dict:
    """One component; a component with no version is unpinned, except a file, which has none."""
    label = pin or version
    item: dict = {
        "bom-ref": f"{kind}:{name}" + (f"@{label}" if label else ""),
        "name": name,
        "type": TYPES[kind],
    }
    properties = [{"name": "agk:class", "value": kind}]
    if version:
        item["version"] = version
    elif kind != "kit-file":
        properties.append({"name": "agk:pin", "value": "unpinned"})
    if purl:
        item["purl"] = purl
    if digest:
        item["hashes"] = [{"alg": "SHA-256", "content": digest}]
    item["properties"] = properties
    return item


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement(text: object) -> dict:
    """The `python` component of one requirement; a version only for one exact `==` pin."""
    found = REQUIREMENT.fullmatch(text) if isinstance(text, str) else None
    if found is None:
        raise not_parsed(PYPROJECT)
    name = canonical(found.group(1))
    spec = found.group(3).split(";", 1)[0].strip().strip("()").strip()
    if not spec or spec.startswith("@"):
        return entry("python", name)
    if exact := EXACT.fullmatch(spec):
        return entry("python", name, exact.group(1), purl=f"pkg:pypi/{name}@{exact.group(1)}")
    if SPECIFIERS.fullmatch(spec) is None:
        raise not_parsed(PYPROJECT)
    return entry("python", name)


def python_components(data: dict) -> list[dict]:
    try:
        project = data["project"]
        groups = [
            project.get("dependencies", []),
            *project.get("optional-dependencies", {}).values(),
            *data.get("dependency-groups", {}).values(),
            data.get("build-system", {}).get("requires", []),
        ]
        if not all(isinstance(group, list) for group in groups):
            raise TypeError
        items = [i for g in groups for i in g if not (isinstance(i, dict) and "include-group" in i)]
    except (AttributeError, KeyError, TypeError):
        raise not_parsed(PYPROJECT) from None
    return [requirement(item) for item in items]


def ci_tool_components(text: str) -> list[dict]:
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if (pin := CI_TOOL_LINE.fullmatch(line)) is None:
            raise not_parsed(PIN_FILE)
        name = canonical(pin.group(1))
        items.append(entry("ci-tool", name, pin.group(2), purl=f"pkg:pypi/{name}@{pin.group(2)}"))
    return items


def action_component(target: str, tag: str | None) -> dict:
    """A `uses:` pinned by a full SHA keeps its release tag as version and the SHA in its URL."""
    path, _, sha = target.rpartition("@")
    if path.count("/") >= 1 and FULL_SHA.fullmatch(sha) and not path.startswith((".", "docker:")):
        owner, repo = path.split("/")[:2]
        pin = f"{sha}:{tag}" if tag else sha
        return entry("action", path, tag or sha, pin, f"pkg:github/{owner}/{repo}@{sha}")
    return entry("action", re.sub(r"[:@][^/]*$", "", target))


def scanner_components(text: str) -> list[dict]:
    """Each `<NAME>_VERSION` with its `<NAME>_SHA256`, either first: pinned by version and digest.

    A digest no version follows takes the version last stated, so one version with two digests
    gives two components that `build` refuses, and neither digest is dropped.
    """
    version: dict[str, str] = {}
    unpaired: set[str] = set()
    digests: dict[str, list[str]] = {}
    items = []

    def pair(name: str, digest: str) -> None:
        tool = name.lower().replace("_", "-")
        items.append(entry("scanner", tool, version[name], digest=digest))

    for name, field, value in SCANNER_PIN.findall(text):
        if field == "VERSION":
            version[name] = value
            waiting = digests.pop(name, [])
            for digest in waiting:
                pair(name, digest)
            if not waiting:
                unpaired.add(name)
        elif SHA256.fullmatch(value):
            if name in unpaired:
                unpaired.remove(name)
                pair(name, value)
            else:
                digests.setdefault(name, []).append(value)
    for name, waiting in digests.items():
        for digest in waiting if name in version else []:
            pair(name, digest)
    return items


def workflow_components(root: Path, commit: str) -> list[dict]:
    items = []
    for path in git(root, "ls-tree", "--name-only", commit, WORKFLOWS).splitlines():
        if path.endswith(".yml"):
            text = read_text(root, commit, path, WORKFLOWS)
            items += [action_component(*found) for found in USES.findall(text)]
            items += scanner_components(text)
    return items


def installed_files(manifest: dict) -> set[str]:
    """What the installers write, as `kit_hashes.py` lists it: template sources by own path."""
    adopt = manifest.get("adopt") or {}
    sources = adopt.get("block_sources") or {}
    blocks = set(adopt.get("blocks") or {}) - set(manifest.get("rendered") or [])
    return {
        *manifest.get("verbatim", []),
        *manifest.get("experimental", []),
        *manifest.get("templates", {}).values(),
        *(adopt.get("templates") or {}).values(),
        *(sources.get(path, path) for path in blocks),
    }


def kit_file_components(root: Path, commit: str) -> list[dict]:
    if show(root, commit, MANIFEST) is None:
        return []
    try:
        paths = sorted(installed_files(json.loads(read_text(root, commit, MANIFEST))))
    except (AttributeError, TypeError, ValueError):
        raise not_parsed(MANIFEST) from None
    items = []
    for path in paths:
        data = show(root, commit, path)
        if data is None:
            raise CheckError("kit-file cannot be read at the commit (rule 2)")
        items.append(entry("kit-file", path, digest=hashlib.sha256(data).hexdigest()))
    return items


def resolve(root: Path, ref: str) -> str:
    commit = git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}", check=False).strip()
    if not commit:
        raise CheckError("--ref does not resolve to a commit")
    return commit


def build(root: Path, commit: str) -> dict:
    pyproject = read_toml(root, commit, PYPROJECT)
    version = read_toml(root, commit, AGK_TOML).get("version")
    project = pyproject.get("project")
    name = project.get("name") if isinstance(project, dict) else None
    if not isinstance(version, str):
        raise not_parsed(AGK_TOML)
    if not isinstance(name, str):
        raise not_parsed(PYPROJECT)
    found = [
        *python_components(pyproject),
        *ci_tool_components(read_text(root, commit, PIN_FILE)),
        *workflow_components(root, commit),
        *kit_file_components(root, commit),
    ]
    unique: dict[str, dict] = {}
    for item in found:
        if unique.setdefault(item["bom-ref"], item) != item:
            raise not_parsed(WORKFLOWS)
    moment = datetime.fromtimestamp(int(git(root, "show", "-s", "--format=%ct", commit)), UTC)
    return {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        "version": 1,
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, commit)}",
        "metadata": {
            "timestamp": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "component": {"type": "application", "name": name, "version": version},
        },
        "components": [unique[ref] for ref in sorted(unique)],
    }


def property_of(item: dict, name: str) -> object:
    properties = item.get("properties")
    for found in properties if isinstance(properties, list) else []:
        if isinstance(found, dict) and found.get("name") == name:
            return found.get("value")
    return None


def well_formed(item: dict) -> bool:
    hashes, properties = item.get("hashes", []), item.get("properties")
    return (
        REQUIRED <= set(item) <= FIELDS
        and all(isinstance(item.get(k, ""), str) for k in FIELDS - {"hashes", "properties"})
        and isinstance(hashes, list)
        and all(isinstance(h, dict) and set(h) == {"alg", "content"} for h in hashes)
        and isinstance(properties, list)
        and all(isinstance(p, dict) and set(p) == {"name", "value"} for p in properties)
        and all(p["name"] in ("agk:class", "agk:pin") for p in properties)
    )


def kind_of(item: object) -> str | None:
    kind = property_of(item, "agk:class") if isinstance(item, dict) else None
    return kind if isinstance(kind, str) and kind in TYPES else None


def take_twin(pool: list[dict], kind: str | None, item: object) -> bool:
    """Remove the first component of POOL with ITEM's class and name; whether there was one."""
    name = item.get("name") if isinstance(item, dict) else None
    for candidate in pool:
        if kind_of(candidate) == kind and candidate["name"] == name:
            pool.remove(candidate)
            return True
    return False


def component_problems(items: list, wanted: list[dict]) -> list[tuple[str, str]]:
    """(class, reason) of each component that is not the commit's, one per component."""
    expected, problems, leftover = list(wanted), [], []
    for item in items:
        kind = kind_of(item)
        if kind is None or not well_formed(item):
            problems.append((kind or "document", "component field not of rule 3's form (rule 4)"))
            take_twin(expected, kind, item)
        elif item in expected:
            expected.remove(item)
        else:
            leftover.append(item)
    for item in leftover:
        kind = str(kind_of(item))
        twin = take_twin(expected, kind, item)
        if property_of(item, "agk:pin") == "unpinned" and "version" in item:
            problems.append((kind, "unpinned component listed with a version (rule 4)"))
        elif twin:
            problems.append((kind, "pin, SHA or digest other than the commit's (rule 4)"))
        else:
            problems.append((kind, "component listed that the commit does not declare (rule 4)"))
    absent = "declared at the commit and not listed (rule 4)"
    problems += [(str(kind_of(item)), absent) for item in expected]
    return sorted(problems)


def document_problems(doc: object, wanted: dict) -> list[tuple[str, str]]:
    if not isinstance(doc, dict):
        return [("document", "not JSON of rule 3's form (rule 4)")]
    problems = []
    if set(doc) != TOP_FIELDS:
        problems.append(("document", "a field other than rule 3's (rule 4)"))
    for key in sorted(TOP_FIELDS - {"components"}):
        if key in doc and doc[key] != wanted[key]:
            problems.append(("document", f"{key} other than the commit's (rule 4)"))
    items = doc.get("components")
    if not isinstance(items, list):
        return [*problems, ("document", "components not a list (rule 4)")]
    refs = [i.get("bom-ref") for i in items if isinstance(i, dict)]
    named = [ref for ref in refs if isinstance(ref, str)]
    if len(named) != len(refs) or named != sorted(set(named)):
        problems.append(("document", "components not sorted by bom-ref (rule 4)"))
    return problems + component_problems(items, wanted["components"])


def make(root: Path, ref: str, out: str) -> None:
    target = Path(out).resolve()
    if target.is_relative_to(root.resolve()):
        rel = str(target.relative_to(root.resolve()))
        ignored = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "check-ignore", "-q", "--", rel], cwd=root, capture_output=True
        )
        if ignored.returncode != 0:
            raise CheckError("--out is inside the repository and not ignored (principle 5)")
    text = json.dumps(build(root, resolve(root, ref)), indent=2, sort_keys=True) + "\n"
    try:
        target.write_bytes(text.encode("utf-8"))
    except OSError:
        raise CheckError("--out cannot be written") from None


def check(root: Path, ref: str, path: str) -> list[tuple[str, str]]:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, RecursionError, ValueError):
        return [("document", "not JSON of rule 3's form (rule 4)")]
    return document_problems(doc, build(root, resolve(root, ref)))


def need(condition: object) -> None:
    if not condition:
        raise ValueError


def advisory_ids(value: object) -> list[str]:
    """Ids as the result states them; only the form of an id can reach the printed body."""
    if not isinstance(value, list):
        raise ValueError
    need(all(isinstance(i, str) and ADVISORY_ID.fullmatch(i) for i in value))
    return list(value)


def worst(one: str, other: str) -> str:
    return min(one, other, key=SEVERITIES.index)


def score_severity(text: str) -> str | None:
    """The severity of a stated score from 0.1 to 10; anything else states none."""
    if SCORE.fullmatch(text) is None or not 0 < float(text) <= 10:
        return None
    return next(name for name, low in SCORES if float(text) >= low)


def package_findings(found: dict) -> dict[frozenset[str], str]:
    """A package's findings: each group of the scanner's, then each advisory in no group."""
    vulnerabilities, groups = found["vulnerabilities"], found.get("groups") or []
    need(isinstance(vulnerabilities, list) and isinstance(groups, list))
    aliases: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    for vulnerability in vulnerabilities:
        ident = advisory_ids([vulnerability["id"]])[0]
        aliases[ident] = advisory_ids(vulnerability.get("aliases") or [])
        specific = vulnerability.get("database_specific") or {}
        need(isinstance(specific, dict))
        labels[ident] = LABELS.get(str(specific.get("severity")).upper(), "unknown")
    findings: dict[frozenset[str], str] = {}
    grouped: set[str] = set()
    for group in groups:
        members = advisory_ids(group["ids"])
        need(members)
        score = group.get("max_severity", "")
        need(isinstance(score, str))
        stated = [labels.get(ident, "unknown") for ident in members]
        ids = {*members, *advisory_ids(group.get("aliases") or [])}
        ids.update(alias for ident in members for alias in aliases.get(ident, []))
        findings[frozenset(ids)] = score_severity(score) or min(stated, key=SEVERITIES.index)
        grouped.update(members)
    for ident in set(labels) - grouped:
        findings[frozenset({ident, *aliases[ident]})] = labels[ident]
    return findings


def scanned_packages(doc: dict) -> list[tuple[str, str, dict[frozenset[str], str]]]:
    """(name, version, findings) of every package of a result; raises when not the form."""
    packages = []
    need(isinstance(doc["results"], list))
    for source in doc["results"]:
        need(isinstance(source["packages"], list))
        for found in source["packages"]:
            name, version = found["package"]["name"], found["package"]["version"]
            need(isinstance(name, str) and isinstance(version, str))
            packages.append((canonical(name), version, package_findings(found)))
    return packages


def match_keys(item: dict) -> list[tuple[str, str]]:
    """What a result calls this component; nothing for a component with no pin to compare."""
    version = item.get("version")
    if version is None:
        return []
    keys = [(canonical(item["name"]), version)]
    if kind_of(item) == "action":
        path, _, sha = item["purl"].removeprefix("pkg:github/").rpartition("@")
        keys += [(canonical(path), version), (canonical(path), sha), (canonical(item["name"]), sha)]
    return keys


def bill_components(path: str) -> list[dict]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    need(isinstance(doc, dict) and set(doc) == TOP_FIELDS)
    need((doc["bomFormat"], doc["specVersion"]) == ("CycloneDX", SPEC_VERSION))
    need(isinstance(doc["components"], list))
    need(all(kind_of(item) and well_formed(item) for item in doc["components"]))
    return doc["components"]


def component_label(item: dict) -> str:
    version = f" {item['version']}" if "version" in item else ""
    return f"{kind_of(item)} {item['name']}{version}"


def findings_body(items: list[dict], doc: dict) -> str:
    """Rule 7's body. A finding on a package the bill does not pin is a result of another bill."""
    index: dict[tuple[str, str], list[dict]] = {}
    for item in items:
        for key in set(match_keys(item)):
            index.setdefault(key, []).append(item)
    named: dict[str, dict[frozenset[str], str]] = {}
    for name, version, findings in scanned_packages(doc):
        matched = index.get((name, version), [])
        need(matched or not findings)
        for item in matched:
            slot = named.setdefault(item["bom-ref"], {})
            for ids, severity in findings.items():
                slot[ids] = worst(severity, slot.get(ids, "unknown"))
    rows = sorted(
        (SEVERITIES.index(severity), item["bom-ref"], sorted(ids), component_label(item))
        for item in items
        for ids, severity in named.get(item["bom-ref"], {}).items()
    )
    counts = {name: sum(1 for row in rows if row[0] == i) for i, name in enumerate(SEVERITIES)}
    listed = [f"- {label} {SEVERITIES[rank]}: {', '.join(ids)}" for rank, _, ids, label in rows]
    unknown = [f"- {component_label(i)}: unknown" for i in items if i["bom-ref"] not in named]
    blocks = [", ".join(f"{name} {counts[name]}" for name in SEVERITIES)]
    blocks += ["\n".join(lines) for lines in (listed, unknown) if lines]
    return "\n\n".join(blocks)


def findings(result: str, bom: str) -> tuple[int, str]:
    try:
        items = bill_components(bom)
    except NOT_OF_FORM:
        return 1, BILL_UNREADABLE
    try:
        return 0, findings_body(items, json.loads(Path(result).read_text(encoding="utf-8")))
    except NOT_OF_FORM:
        return 1, RESULT_UNREADABLE


def options(args: list[str]) -> tuple[list[str], dict[str, str]] | None:
    positional, flags = [], {}
    while args:
        arg = args.pop(0)
        if arg in ("--ref", "--out", "--bom"):
            if not args:
                return None
            flags[arg] = args.pop(0)
        elif arg.startswith("-"):
            return None
        else:
            positional.append(arg)
    return positional, flags


def main(argv: list[str] | None = None) -> int:
    parsed = options(list(sys.argv[1:] if argv is None else argv))
    words, flags = parsed if parsed else ([], {})
    if len(words) == 2 and words[0] == "findings" and set(flags) == {"--bom"}:
        code, text = findings(words[1], flags["--bom"])
        print(text)
        return code
    is_make = words == ["make"] and "--out" in flags and "--bom" not in flags
    if not is_make and not (
        len(words) == 2 and words[0] == "check" and not {"--out", "--bom"} & set(flags)
    ):
        print(USAGE)
        return 2
    ref = flags.get("--ref", "HEAD")
    try:
        root = repo_root()
        if is_make:
            make(root, ref, flags["--out"])
            return 0
        problems = check(root, ref, words[1])
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 1
    for kind, reason in problems:
        print(f"FAIL {NAME}: {kind} {reason}")
    if not problems:
        print(f"ok {NAME}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
