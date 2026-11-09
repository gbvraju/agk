"""The survey of an existing codebase: it reads tracked files and never runs them.

    python3 survey.py [--clone DIR] [--sidecar DIR] [--today YYYY-MM-DD]

SPEC-0041 build (f), rules 10 to 12. Writes `cache/inventory.json` under the sidecar (`--sidecar`,
else the clone's registry entry). Each blob comes from git's object store, never the work tree, so
an untracked file is out of reach and no symlink can be followed. Every git call is read-only with
`--no-optional-locks` (rule 4). The read ledger is the inventory's `ledger` map, a path to the blob
the model read. Standard library only; no network. Refusals name the setting, never a value.
"""

from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import re
import subprocess  # nosec B404 - fixed read-only git argument lists only, no shell
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, personal_table  # noqa: E402

USAGE = "usage: survey.py [--clone DIR] [--sidecar DIR] [--today YYYY-MM-DD]"
INVENTORY = "cache/inventory.json"
BUDGET = "survey_budget"
BUDGET_DEFAULT = 40
BUDGET_MAX = 1000
TOO_LARGE = 1_000_000  # bytes: over this a file is listed and never read (rule 10)
BINARY_PROBE = 8000  # the prefix git itself looks in for a NUL byte
GIT_ENV = {"GIT_NO_LAZY_FETCH": "1"}  # no fetch of a missing blob

LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".java": "Java",
    ".kt": "Kotlin", ".kts": "Kotlin", ".cs": "C#", ".csproj": "C#", ".rb": "Ruby", ".rs": "Rust",
    ".php": "PHP",
}  # fmt: skip
FAMILY = {"JavaScript": "js", "TypeScript": "js", "Java": "jvm", "Kotlin": "jvm"}
INDEX_NAMES = ("__init__", "index", "mod")  # a file that stands for its folder
TAIL_MATCH = ("Go", "PHP")  # an import path longer than the tracked path: try its tails
FOLDER_PACKAGES = ("Go", "C#")  # an import that names a folder names each file in it
JVM, JS = ("Java", "Kotlin"), ("JavaScript", "TypeScript")
SIGNALS = "config/stack-signals.toml"  # the manifest names, read from the kit's own root
OUTSIDE_TABLE = ("*.csproj", "Gemfile", "composer.json")  # Q-879-1: SPEC-0041 rule 10 keeps them
MANIFESTS = {  # the language of each manifest; the names come from `manifest_names`
    "pyproject.toml": ("Python",), "requirements.txt": ("Python",), "setup.cfg": ("Python",),
    "setup.py": ("Python",), "pubspec.yaml": ("Dart",), "package.json": JS,
    "composer.json": ("PHP",), "go.mod": ("Go",), "pom.xml": JVM,
    "build.gradle": JVM, "build.gradle.kts": JVM, "Cargo.toml": ("Rust",), "*.csproj": ("C#",),
    "Gemfile": ("Ruby",),
}  # fmt: skip
WEB = ("vitest", "jest", "mocha", "ava", "jasmine", "cypress", "playwright")
FRAMEWORKS = {
    "Python": ("pytest", "nose2", "unittest"), "JavaScript": WEB, "TypeScript": WEB,
    "Java": ("junit", "testng", "spock"), "Kotlin": ("kotest", "junit", "testng"),
    "C#": ("xunit", "nunit", "mstest"), "Ruby": ("rspec", "minitest"), "PHP": ("phpunit", "pest"),
}  # fmt: skip
JSON_TEST = re.compile(r'^\s*"test(?::[\w:-]+)?"\s*:\s*"((?:[^"\\\n]|\\.)*)"', re.M)
TOML_TEST = re.compile(r'^\s*test\s*=\s*"((?:[^"\\\n]|\\.)*)"', re.M)
TEST_COMMANDS = {"package.json": JSON_TEST, "composer.json": JSON_TEST, "pyproject.toml": TOML_TEST}
JSON_ENTRY = re.compile(r'^\s*"(?:main|bin)"\s*:\s*"([^"\n]+)"', re.M)
TOML_ENTRY = re.compile(r"^\[(?:project|tool\.poetry)\.scripts\]\n((?:(?!\[).*\n?)*)", re.M)
TOML_VALUE = re.compile(r'^\s*[\w.-]+\s*=\s*"([^"\n]+)"', re.M)
ENTRY_NAMES = (
    "main.py", "__main__.py", "manage.py", "wsgi.py", "asgi.py", "main.go", "main.rs", "index.js",
    "index.ts", "server.js", "server.ts", "Program.cs", "Main.java", "Main.kt", "index.php",
    "config.ru",
)  # fmt: skip
CI_FILES = (
    ".github/workflows/*.yml", ".github/workflows/*.yaml", ".gitlab-ci.yml", "Jenkinsfile",
    ".circleci/config.yml", ".travis.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml",
)  # fmt: skip
Q = r"""['"]([^'"]+)['"]"""
LOCAL = r"""['"](\.[^'"]*)['"]"""  # a package name is no tracked file
_RE = re.compile
_JVM_LINE = [(_RE(r"^\s*import\s+(?:static\s+)?([\w.]+)"), ".", "")]
_JS_LINE = [
    (_RE(rf"\bfrom\s+{LOCAL}|^\s*import\s+{LOCAL}|\b(?:require|import)\(\s*{LOCAL}"), "", ""),
]
IMPORT_LINES = {  # language: (pattern, separator turned into `/`, prefix)
    "JavaScript": _JS_LINE, "TypeScript": _JS_LINE, "Java": _JVM_LINE, "Kotlin": _JVM_LINE,
    "Go": [(_RE(r'^\s*(?:import\s+)?(?:[\w.]+\s+)?"([^"]+)"\s*$'), "", "")],
    "C#": [(_RE(r"^\s*(?:global\s+)?using\s+(?:static\s+)?([\w.]+)\s*;"), ".", "")],
    "Ruby": [
        (_RE(rf"^\s*require_relative\s*\(?\s*{Q}"), "", "./"),
        (_RE(rf"^\s*require\s*\(?\s*{Q}"), "", ""),
    ],
    "Rust": [
        (_RE(r"^\s*(?:pub\s+)?use\s+(?:crate|super|self)::([\w:]+)"), "::", ""),
        (_RE(r"^\s*(?:pub\s+)?use\s+(?:crate|super|self)::((?:\w+::)*\w+)::"), "::", ""),
        (_RE(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;"), "", ""),
    ],
    "PHP": [
        (_RE(r"^\s*use\s+(?:function\s+|const\s+)?([\w\\]+)\s*;"), "\\", ""),
        (_RE(rf"\b(?:require|include)(?:_once)?\s*\(?\s*{Q}"), "", ""),
    ],
}  # fmt: skip
_PY_IMPORT = _RE(r"^\s*import\s+([^#]+)")
_PY_FROM = _RE(r"^\s*from\s+([\w.]*)\s+import\s+([^#(]*)")


def _names(group: str) -> list[str]:
    return [item.split()[0] for item in group.split(",") if item.strip()]


def references(language: str, line: str) -> list[str]:
    """What one import line names, as `a/b`, or `./a/b` when relative (rule 11)."""
    if language != "Python":
        return [
            prefix + "".join(found).replace(sep or "\0", "/")
            for pattern, sep, prefix in IMPORT_LINES.get(language, ())
            for found in pattern.findall(line)
        ]
    if match := _PY_IMPORT.match(line):
        return [name.replace(".", "/") for name in _names(match[1])]
    match = _PY_FROM.match(line)
    if not match:
        return []
    dots = len(match[1]) - len(match[1].lstrip("."))
    base = ("./" + "../" * (dots - 1) if dots else "") + match[1][dots:].replace(".", "/")
    sep = "" if base.endswith("/") else "/"
    return [base or "."] + [f"{base}{sep}{name}" for name in _names(match[2])]


def language_of(path: str) -> str:
    """The language of a path by its extension, or the extension itself when it is not listed."""
    ext = posixpath.splitext(path)[1]
    return LANGUAGES.get(ext, ext or "(none)")


def _test_language(path: str) -> str | None:
    """The rule 12 patterns: the language of a test file, or None."""
    folder, name = posixpath.split(path)
    parts, lang = folder.split("/"), LANGUAGES.get(posixpath.splitext(name)[1])
    web = ".test." in name or ".spec." in name or "__tests__" in parts
    jvm = name.endswith(("Test.java", "Tests.java")) or "/src/test/" in f"/{folder}/"
    hits = {
        "Python": name.startswith("test_") or name.endswith("_test.py"),
        "JavaScript": web, "TypeScript": web, "Java": jvm, "Kotlin": jvm,
        "Go": name.endswith("_test.go"),
        "C#": name.endswith(("Tests.cs", ".Tests.csproj")),
        "Ruby": name.endswith("_spec.rb") or ("test" in parts and name.endswith("_test.rb")),
        "Rust": "tests" in parts,
        "PHP": name.endswith("Test.php"),
    }  # fmt: skip
    return lang if lang and hits[lang] else None


def _framework(path: str, language: str, manifests) -> str | None:
    """The framework the nearest manifest of this language declares, as data (rule 12)."""
    for row in sorted(manifests, key=lambda m: (-len(m["folder"]), m["path"])):
        if language in row["languages"] and path.startswith(row["folder"] and row["folder"] + "/"):
            for name in FRAMEWORKS.get(language, ()):
                if re.search(rf"(?<![\w-]){name}(?![\w-])", row["text"], re.I):
                    return name
    return None


def detect_test_files(paths, manifests=()) -> list[dict]:
    """Each test file among `paths`: its path, language and, where declared, framework (rule 12)."""
    found = [(path, _test_language(path)) for path in sorted(paths)]
    return [
        {"path": p, "language": lang, "framework": _framework(p, lang, manifests)}
        for p, lang in found
        if lang
    ]


def _git(clone: Path, *args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    cmd = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(clone), *args]
    return subprocess.run(  # nosec B603 - fixed read-only argument list, no shell
        cmd, input=stdin, capture_output=True, env={**os.environ, **GIT_ENV}
    )


def _decode(raw: bytes) -> list[str]:
    return [p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p]


def tracked(clone: Path) -> dict[str, tuple[str, str]]:
    """Path to (mode, blob) from the index; during a merge the last stage of a path stands."""
    done = _git(clone, "ls-files", "--stage", "-z")
    if done.returncode != 0:
        raise CheckError("the clone cannot be read as a git repository (option: --clone)")
    entries = {}
    for line in _decode(done.stdout):
        meta, path = line.split("\t", 1)
        mode, blob, _stage = meta.split()
        entries[path] = (mode, blob)
    return entries


def blob_sizes(clone: Path, blobs: list[str]) -> dict[str, int]:
    query = "\n".join(blobs).encode() + b"\n"
    done = _git(clone, "cat-file", "--batch-check=%(objectname) %(objectsize)", stdin=query)
    rows = (line.partition(" ") for line in done.stdout.decode().splitlines())
    return {name: int(size) for name, _, size in rows if size.isdigit()}  # no size: `missing`


def read_blobs(clone: Path, blobs: list[str]):
    """Yield (blob, bytes), one request at a time so neither pipe can fill."""
    cmd = ["git", "--no-optional-locks", "-C", str(clone), "cat-file", "--batch"]
    with subprocess.Popen(  # nosec B603 - fixed read-only argument list, no shell
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={**os.environ, **GIT_ENV}
    ) as proc:
        if proc.stdin is None or proc.stdout is None:
            return
        for blob in blobs:
            proc.stdin.write(blob.encode() + b"\n")
            proc.stdin.flush()
            size = int(proc.stdout.readline().split()[2])
            yield blob, proc.stdout.read(size)
            proc.stdout.read(1)
        proc.stdin.close()


def churn(clone: Path) -> dict[str, int]:
    """The commits that touched each path; a clone with no commit has none."""
    done = _git(clone, "log", "--format=", "--name-only", "-z")
    counts: dict[str, int] = defaultdict(int)
    if done.returncode == 0:
        for path in _decode(done.stdout):
            counts[path.strip("\n")] += 1
    return counts


def _keys(path: str, language: str) -> set[str]:
    """Every name an import line could use for this file: its stem path and that path's tails."""
    stem = posixpath.splitext(path)[0]
    folder, name = posixpath.split(stem)
    stems = {stem}
    if name in INDEX_NAMES or language in FOLDER_PACKAGES:
        stems.add(folder)
    keys = set()
    for item in filter(None, stems):
        parts = item.split("/")
        keys |= {"/".join(parts[i:]) for i in range(len(parts))}
    return keys


def fan_in(refs: dict[str, list[str]], languages: dict[str, str]) -> dict[str, int]:
    """For each file, how many other tracked files have an import line that names it (rule 11)."""
    index: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path, language in languages.items():
        for key in _keys(path, language):
            index[FAMILY.get(language, language), key].add(path)
    importers: dict[str, set[str]] = defaultdict(set)
    for importer, names in refs.items():
        language = languages[importer]
        family = FAMILY.get(language, language)
        for ref in names:
            for target in _resolve(ref, importer, language, family, index):
                if target != importer:
                    importers[target].add(importer)
    return {path: len(importers[path]) for path in languages}


def _resolve(ref, importer, language, family, index) -> set[str]:
    if ref.startswith("."):
        target = posixpath.normpath(posixpath.join(posixpath.dirname(importer), ref))
        return index.get((family, target), set())
    parts = [p for p in ref.split("/") if p]
    for start in range(len(parts) if language in TAIL_MATCH else min(len(parts), 1)):
        hit = index.get((family, "/".join(parts[start:])))
        if hit:
            return hit
    return set()


def reading_list(files: dict, ledger: dict, budget: int) -> list[str]:
    """Changed files, then never-read ones; round-robin over top-level folders, best rank first."""
    changed = [p for p in files if p in ledger and ledger[p] != files[p]["blob"]]
    unread = [p for p in files if p not in ledger]
    out: list[str] = []
    for tier in (changed, unread):
        folders: dict[str, list[str]] = defaultdict(list)
        for path in sorted(tier, key=lambda p: files[p]["rank"]):
            folders[path.split("/")[0] if "/" in path else "."].append(path)
        queues = [folders[name] for name in sorted(folders)]
        while queues and len(out) < budget:
            for queue in queues:
                if len(out) < budget:
                    out.append(queue.pop(0))
            queues = [q for q in queues if q]
    return out


def survey_budget(sidecar: Path) -> int:
    setting = f"personal.{BUDGET}"
    try:
        table = personal_table(sidecar)
    except tomllib.TOMLDecodeError as exc:
        raise CheckError("the sidecar's settings cannot be read (path: agk.toml)") from exc
    if table is None:
        raise CheckError("not a sidecar: it has no personal table (setting: personal)")
    value = table.get(BUDGET, BUDGET_DEFAULT)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= BUDGET_MAX:
        raise CheckError(f"must be a whole number from 1 to {BUDGET_MAX} (setting: {setting})")
    return value


def read_ledger(sidecar: Path) -> dict[str, str]:
    """The ledger of the last inventory; none when `cache/` is gone (the spec's residual)."""
    path = sidecar / INVENTORY
    if not path.is_file():
        return {}
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))["ledger"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CheckError(f"the read ledger cannot be read (path: {INVENTORY})") from exc
    if not isinstance(ledger, dict) or not all(isinstance(v, str) for v in ledger.values()):
        raise CheckError(f"the read ledger cannot be read (path: {INVENTORY})")
    return ledger


def manifest_names() -> tuple[str, ...]:
    """SPEC-0057 rule 8: the table's manifest names, from the kit's root and never the clone's."""
    try:
        with open(Path(__file__).resolve().parents[2] / SIGNALS, "rb") as handle:
            rows = tomllib.load(handle)["stack"]
        names = {name for row in rows for name in row["manifests"]}
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise CheckError(f"the signal table cannot be read (path: {SIGNALS})") from exc
    return tuple(sorted(names | set(OUTSIDE_TABLE)))


def _manifest_row(path: str, text: str) -> dict:
    name = posixpath.basename(path)
    kind = "*.csproj" if name.endswith(".csproj") else name
    pattern = TEST_COMMANDS.get(kind)
    return {
        "path": path,
        "test_commands": pattern.findall(text) if pattern else [],
        "folder": posixpath.dirname(path),
        "languages": MANIFESTS.get(kind, ()),
        "text": text,
    }


def _entry_points(paths, manifests) -> list[dict]:
    out = [{"value": p, "source": "name"} for p in paths if posixpath.basename(p) in ENTRY_NAMES]
    for row in manifests:
        name = posixpath.basename(row["path"])
        blocks = TOML_ENTRY.findall(row["text"]) if name == "pyproject.toml" else []
        values = [v for block in blocks for v in TOML_VALUE.findall(block)]
        values += JSON_ENTRY.findall(row["text"]) if name == "package.json" else []
        out += [{"value": v, "source": row["path"]} for v in values]
    return sorted(out, key=lambda e: (e["value"], e["source"]))


def build(clone: Path, ledger: dict[str, str], budget: int, today: str | None) -> dict:
    """The inventory of rule 10, from the index and the object store alone."""
    names = manifest_names()
    entries = tracked(clone)
    skipped: dict[str, list[str]] = {"binary": [], "large": [], "submodule": [], "symlink": []}
    regular = {}
    for path, (mode, blob) in entries.items():
        if mode == "120000":
            skipped["symlink"].append(path)
        elif mode == "160000":
            skipped["submodule"].append(path)
        else:
            regular[path] = blob
    sizes = blob_sizes(clone, sorted(set(regular.values()))) if regular else {}
    small = {}
    for path, blob in regular.items():
        if sizes.get(blob, TOO_LARGE + 1) > TOO_LARGE:
            skipped["large"].append(path)
        else:
            small[path] = blob
    by_blob: dict[str, list[str]] = defaultdict(list)
    for path, blob in small.items():
        by_blob[blob].append(path)
    languages, refs, measured, manifests = {}, {}, {}, []
    for blob, data in read_blobs(clone, sorted(by_blob)):
        if b"\0" in data[:BINARY_PROBE]:
            skipped["binary"] += by_blob[blob]
            continue
        text = data.decode("utf-8", "replace")
        lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
        for path in by_blob[blob]:
            language = languages[path] = language_of(path)
            found = [references(language, line) for line in text.splitlines()]
            refs[path] = [ref for row in found for ref in row]
            measured[path] = {"blob": blob, "lines": lines, "imports": sum(map(bool, found))}
            if any(fnmatch.fnmatch(posixpath.basename(path), m) for m in names):
                manifests.append(_manifest_row(path, text))
    manifests.sort(key=lambda m: m["path"])
    fans, commits = fan_in(refs, languages), churn(clone)
    for path, row in measured.items():
        row.update(fan_in=fans[path], churn=commits.get(path, 0))
    ranked = sorted(measured, key=lambda p: (-measured[p]["fan_in"], -measured[p]["churn"], p))
    for position, path in enumerate(ranked, 1):
        measured[path]["rank"] = position
    totals: dict[str, dict[str, int]] = {}
    for path, language in languages.items():
        row = totals.setdefault(language, {"files": 0, "lines": 0})
        row["files"] += 1
        row["lines"] += measured[path]["lines"]
    read = sum(1 for p, row in measured.items() if ledger.get(p) == row["blob"])
    testable = sorted(set(measured) | set(skipped["large"]))
    return {
        "ci_files": sorted(p for p in regular if any(fnmatch.fnmatch(p, c) for c in CI_FILES)),
        "coverage": f"{read} of {len(measured)} files read",
        "date": today,
        "entry_points": _entry_points(sorted(measured), manifests),
        "files": measured,
        "languages": totals,
        "ledger": ledger,
        "manifests": [{k: m[k] for k in ("path", "test_commands")} for m in manifests],
        "reading_list": reading_list(measured, ledger, budget),
        "skipped": {k: sorted(v) for k, v in skipped.items()},
        "test_files": detect_test_files(testable, manifests),
    }


def write_private(path: Path, text: str) -> None:
    """Atomic, and on POSIX `0600` under `0700` (rule 28)."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(tmp, path)


def find_sidecar(clone: Path) -> Path:
    """The clone's sidecar from the registry; `personal_state.py` is not installed in a project."""
    try:
        import personal_state  # noqa: PLC0415 - kit and plugin only (config/kit-only.txt)
    except ImportError as exc:
        raise CheckError("the sidecar must be named here (option: --sidecar)") from exc
    home = personal_state.agk_home()
    pid = personal_state.registry(home).get(personal_state.common_dir(clone))
    if pid is None:
        raise CheckError("this clone is not attached to a sidecar (option: --sidecar)")
    return home / personal_state.PROJECTS / pid


def parse(args: list[str]) -> dict | None:
    out: dict = {"clone": ".", "sidecar": None, "today": None}
    while args:
        flag = args.pop(0)
        if flag not in ("--clone", "--sidecar", "--today") or not args:
            return None
        out[flag[2:]] = args.pop(0)
    return out


def main(argv: list[str] | None = None) -> int:
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        if options["today"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", options["today"]):
            raise CheckError("not a date of the form YYYY-MM-DD (option: --today)")
        start = Path(options["clone"])
        probe = _git(start, "rev-parse", "--show-toplevel")
        if probe.returncode != 0:
            raise CheckError("the clone cannot be read as a git repository (option: --clone)")
        clone = Path(probe.stdout.decode("utf-8", "surrogateescape").strip())
        sidecar = Path(options["sidecar"]) if options["sidecar"] else find_sidecar(clone)
        budget = survey_budget(sidecar)
        inventory = build(clone, read_ledger(sidecar), budget, options["today"])
        write_private(sidecar / INVENTORY, json.dumps(inventory, indent=1, sort_keys=True) + "\n")
    except CheckError as exc:
        print(f"refused: {exc}")
        return 1
    print(inventory["coverage"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
