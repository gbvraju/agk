"""A command reuses one GitHub connection for its reads, and the guarded merge reads through the
shared cached reader.

Brief #1336, ADR-0566; REQ-050. `[flow] github_transport` is `"gh"` (the default, one `gh api`
process a call) or `"direct"`: the plain GETs of one process go over one kept-alive HTTPS
connection, answered to `session.gh()` in the form `gh api -i` prints, so the ETag cache, 304s,
paging, counting and limit waits are the same code. The token is read once, kept in memory and
sent only in the `Authorization` header to the API host; any failure that is not GitHub's own
answer turns the process back to `gh api`, with one line. `merge_cleared.py`'s GETs go through
`session.gh` and reach GitHub through its `gh_api`. A fake connection, a recorded double of `gh`
and a fake clock: no network, no real sleep, invented data only."""

from __future__ import annotations

import http.client
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import tracemalloc
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import merge_cleared  # noqa: E402
import session  # noqa: E402
from test_github_read_budget import COMMANDS, World, said  # noqa: E402
from test_merge_cleared_verdict import ON, cleared, merge_cleared_run, toml  # noqa: E402
from test_session import REPO, SCRIPTS, clean_env  # noqa: E402
from test_session_plan_reads import Double  # noqa: E402

PLANTED = "-".join(("planted", "example", "value"))  # invented, built from parts
EP = "repos/acme/widgets/issues/7"
BODY = {"number": 7, "title": "example"}
MERGE_READS = 9  # measured (brief #1336 answer 4), plus the permission read (brief #1709)


class Answer:
    def __init__(self, status: int, headers: dict[str, str], body: bytes, reason: str = "") -> None:
        self.status, self.reason, self.body = status, reason, body
        self.headers = list(headers.items())

    def getheader(self, name: str, default=None):
        return next((v for k, v in self.headers if k.lower() == name.lower()), default)

    def getheaders(self):
        return self.headers

    def read(self) -> bytes:
        return self.body


def ok(body=None, etag: str | None = '"e1"') -> Answer:
    text = json.dumps(BODY if body is None else body).encode()
    headers = {"Content-Type": "application/json", **({"ETag": etag} if etag else {})}
    return Answer(200, headers, text, "OK")


class Server:
    """The answers the fake connections give, in order (an exception is raised), and what each
    request carried."""

    def __init__(self, *answers) -> None:
        self.answers = list(answers)
        self.asked: list[tuple[str, str, dict]] = []
        self.opened: list[str] = []

    def connect(self, host: str):
        self.opened.append(host)
        server = self

        class Conn:
            def request(self, method, path, headers=None):
                server.asked.append((method, path, dict(headers or {})))
                found = server.answers.pop(0) if server.answers else ok()
                if isinstance(found, BaseException):
                    raise found
                self.found = found

            def getresponse(self):
                return self.found

            def close(self):
                pass

        return Conn()


class GhDouble:
    def __init__(self, out: str = json.dumps(BODY), code: int = 0, err: str = "") -> None:
        self.calls: list[list[str]] = []
        self.out, self.code, self.err = out, code, err

    def __call__(self, args, **_kw):
        self.calls.append(list(args))
        return subprocess.CompletedProcess(args, self.code, self.out, self.err)


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def direct(monkeypatch, tmp_path):
    """The direct transport on, with a fake server, a fake clock and a cache in TMP_PATH."""
    server, clock, gh = Server(), Clock(), GhDouble()
    fresh = session.Direct()
    monkeypatch.setattr(session, "DIRECT", fresh)
    monkeypatch.setattr(fresh, "connect", server.connect)
    monkeypatch.setattr(fresh, "read_token", lambda host: PLANTED)
    monkeypatch.setattr(session, "transport_setting", lambda start=None: "direct")
    monkeypatch.setattr(session, "time", SimpleNamespace(
        time=clock.time, monotonic=clock.monotonic, sleep=clock.sleep))  # fmt: skip
    monkeypatch.setattr(session.subprocess, "run", gh)
    monkeypatch.setenv(session.CACHE_ENV, str(tmp_path / "cache"))
    for name in session.PROXY_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("GH_HOST", raising=False)
    monkeypatch.setattr(session, "CACHE", session.ReadCache())
    monkeypatch.setattr(session, "MEMO", None)
    monkeypatch.setattr(session, "RUN", None)
    monkeypatch.setattr(session, "WRITES", 0)
    monkeypatch.setattr(session, "LAST_WRITE", None)  # a fake-clock write time never leaks out
    return SimpleNamespace(
        server=server, clock=clock, gh=gh, transport=fresh, cache=tmp_path / "cache"
    )


def no_token_anywhere(capsys, *folders: Path) -> None:
    out = capsys.readouterr()
    assert PLANTED not in out.out + out.err
    for folder in folders:
        for item in folder.rglob("*") if folder.exists() else []:
            assert PLANTED.encode() not in item.read_bytes(), item


# --- answers 1 and 7: the setting and its default ---------------------------------------------


def test_the_default_is_gh_and_needs_no_line(tmp_path):
    """REQ-050"""
    (tmp_path / "agk.toml").write_text("[flow]\nmax_builders = 2\n", encoding="utf-8")
    assert session.TRANSPORT_DEFAULT == "gh"
    assert session.transport_setting(tmp_path) == "gh"
    (tmp_path / "agk.toml").write_text('[flow]\ngithub_transport = "direct"\n', encoding="utf-8")
    (tmp_path / "sub").mkdir()
    assert session.transport_setting(tmp_path / "sub") == "direct"  # the nearest agk.toml above


def test_any_other_value_reads_as_gh_naming_the_setting_never_the_value(tmp_path, capsys):
    """REQ-050"""
    (tmp_path / "agk.toml").write_text('[flow]\ngithub_transport = "fast-x"\n', encoding="utf-8")
    assert session.transport_setting(tmp_path) == "gh"
    err = capsys.readouterr().err
    assert (
        "github_transport of the [flow] table must be gh or direct" in err and "fast-x" not in err
    )


def test_with_gh_every_call_is_a_gh_process_as_before(monkeypatch, tmp_path):
    """REQ-050"""
    gh = GhDouble()
    monkeypatch.setattr(session, "DIRECT", session.Direct())
    monkeypatch.setattr(session, "transport_setting", lambda start=None: "gh")
    monkeypatch.setattr(session.DIRECT, "connect", lambda host: pytest.fail("no connection"))
    monkeypatch.setattr(session.subprocess, "run", gh)
    monkeypatch.setattr(session.CACHE, "place", None)
    monkeypatch.setattr(session, "MEMO", None)
    assert session.gh(EP) == BODY and session.gh(EP) == BODY
    assert [c[:2] for c in gh.calls] == [["gh", "api"]] * 2


# --- answer 1: one connection, the same answers ------------------------------------------------


def test_the_reads_of_one_process_share_one_connection_and_the_etag_cache(direct, capsys):
    """REQ-050"""
    direct.server.answers = [ok(), Answer(304, {"ETag": '"e1"'}, b""), ok({"n": 2}, etag=None)]
    before = session.CACHED
    assert session.gh(EP) == BODY
    assert session.gh(EP) == BODY  # a 304: the cached body
    assert session.gh(f"{EP}/comments?per_page=100&page=1") == {"n": 2}
    assert direct.server.opened == ["api.github.com"] and direct.transport.opened == 1
    assert session.CACHED - before == 1
    assert direct.server.asked[1][2]["If-None-Match"] == '"e1"'
    assert all(h["Authorization"] == f"Bearer {PLANTED}" for _, _, h in direct.server.asked)
    assert direct.server.asked[0][1] == f"/{EP}"
    assert direct.gh.calls == []  # no `gh api`, and the token was read once by the fake
    no_token_anywhere(capsys, direct.cache)


def test_writes_and_reads_with_extra_arguments_stay_with_gh(direct):
    """REQ-050"""
    session.gh(f"{EP}/comments", "-f", "body=example", method="POST")
    session.gh(EP, "-H", "Accept: application/vnd.github.raw")
    assert direct.server.asked == []
    assert len(direct.gh.calls) == 2


def test_a_github_answer_is_handed_on_as_gh_reports_it(direct):
    """REQ-050"""
    direct.server.answers = [Answer(404, {}, b'{"message": "Not Found"}', "Not Found")]
    assert session.gh(EP) is None
    assert "Not Found (HTTP 404)" in session.LAST_ERROR
    assert direct.transport.mode == "direct" and direct.gh.calls == []


# --- answer 2: the credential, and the fall back ------------------------------------------------


def test_no_token_means_gh_for_the_run_with_one_line(direct, monkeypatch, capsys):
    """REQ-050"""
    monkeypatch.setattr(direct.transport, "read_token", lambda host: "")
    assert session.gh(EP) == BODY and session.gh(EP) == BODY
    assert capsys.readouterr().err.count(session.DIRECT_OFF) == 1
    assert direct.server.opened == [] and len(direct.gh.calls) == 2


def test_a_proxy_means_gh(direct, monkeypatch, capsys):
    """REQ-050"""
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:3128")
    assert session.gh(EP) == BODY
    assert direct.server.opened == [] and session.DIRECT_OFF in capsys.readouterr().err


def test_another_host_is_asked_on_its_api_path(direct, monkeypatch):
    """REQ-050"""
    monkeypatch.setenv("GH_HOST", "git.example.com")
    assert session.gh(EP) == BODY
    assert direct.server.opened == ["git.example.com"]
    assert direct.server.asked[0][1] == f"/api/v3/{EP}"


def test_a_dropped_kept_alive_connection_is_opened_once_again(direct, capsys):
    """REQ-050"""
    direct.server.answers = [ok(), http.client.RemoteDisconnected("closed"), ok()]
    assert session.gh(EP) == BODY and session.gh(f"{EP}/x") == BODY
    assert len(direct.server.opened) == 2 and direct.gh.calls == []
    assert session.DIRECT_OFF not in capsys.readouterr().err


@pytest.mark.parametrize(
    "fault",
    [
        [TimeoutError("timed out"), TimeoutError("timed out")],
        [ConnectionResetError(PLANTED), ConnectionResetError(PLANTED)],  # an error that names it
        [OSError("certificate verify failed"), OSError("certificate verify failed")],
        [
            Answer(200, {"Content-Length": "999"}, b'{"cut'),
            Answer(200, {"Content-Length": "9"}, b"{"),
        ],
        [Answer(401, {}, b'{"message": "Bad credentials"}')],
        [Answer(301, {"Location": "https://other.example.com/x"}, b"")],
    ],
    ids=["timeout", "reset", "certificate", "truncated", "401", "redirect"],
)
def test_a_fault_falls_back_to_gh_once_and_the_run_completes(direct, capsys, fault):
    """REQ-050"""
    direct.server.answers = list(fault)
    assert session.gh(EP) == BODY  # the same call, asked again with `gh api`
    assert session.gh(f"{EP}/x") == BODY
    assert capsys.readouterr().err.count(session.DIRECT_OFF) == 1
    assert all(host == "api.github.com" for host in direct.server.opened)  # never another host
    assert len(direct.gh.calls) == 2
    no_token_anywhere(capsys, direct.cache)


@pytest.mark.parametrize("code", [500, 502, 503])
def test_a_server_error_is_the_same_failed_read_as_with_gh(direct, code):
    """REQ-050"""
    direct.server.answers = [Answer(code, {}, b'{"message": "Server Error"}')]
    assert session.gh(EP) is None and f"(HTTP {code})" in session.LAST_ERROR
    assert direct.gh.calls == [] and direct.transport.mode == "direct"


def test_limits_are_waited_out_from_the_same_headers(direct, capsys):
    """REQ-050"""
    reset = str(int(direct.clock.now) + 100)
    primary = Answer(403, {"X-Ratelimit-Remaining": "0", "X-Ratelimit-Reset": reset},
                     b'{"message": "API rate limit exceeded"}')  # fmt: skip
    secondary = Answer(403, {"Retry-After": "30", "X-Ratelimit-Remaining": "4000"},
                       b'{"message": "You have exceeded a secondary rate limit"}')  # fmt: skip
    direct.server.answers = [primary, secondary, ok()]
    assert session.gh(EP) == BODY
    assert direct.clock.slept == [100.0 + session.RESET_SLACK, 30.0]
    assert direct.transport.opened == 1 and direct.gh.calls == []
    no_token_anywhere(capsys, direct.cache)


# --- answer 7 (b): stress in the double --------------------------------------------------------


def test_five_thousand_reads_one_connection_and_flat_memory(direct, monkeypatch):
    """REQ-050"""
    monkeypatch.setattr(session.CACHE, "place", None)
    body = ok(etag=None)
    direct.server.asked = type("Dropped", (list,), {"append": lambda self, item: None})()
    monkeypatch.setattr(direct.server, "answers", type("Always", (list,), {
        "pop": lambda self, i=0: body, "__bool__": lambda self: True})())  # fmt: skip
    tracemalloc.start()
    for i in range(1000):
        session.gh(f"{EP}/{i}")
    first = tracemalloc.get_traced_memory()[0]
    for i in range(4000):
        session.gh(f"{EP}/{i}")
    last = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    assert direct.transport.opened == 1 and direct.gh.calls == []
    assert last - first < 1_000_000, (first, last)


WRITER = """
import os, sys
sys.path.insert(0, sys.argv[1])
import session
for i in range(60):
    endpoint = f"repos/acme/widgets/issues/{sys.argv[2]}{i}"
    session.CACHE.keep(endpoint, f'"e{i}"', {"i": i, "w": "x" * 500})
"""


def test_eight_processes_share_one_cache_folder_with_no_corrupt_file(tmp_path):
    """REQ-050"""
    cache = tmp_path / "cache"
    script = tmp_path / "writer.py"
    script.write_text(WRITER, encoding="utf-8")
    env = {**clean_env(), session.CACHE_ENV: str(cache)}
    procs = [
        subprocess.Popen(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(script), str(SCRIPTS), str(n)], env=env
        )
        for n in range(8)
    ]
    assert all(p.wait(timeout=120) == 0 for p in procs)
    files = list(cache.iterdir())
    assert [f.name for f in files] == ["acme__widgets.json"]  # no half-written temp file is left
    entries = json.loads(files[0].read_text(encoding="utf-8"))["entries"]
    assert entries and all(e["body"]["w"] == "x" * 500 for e in entries.values())


# --- answer 3: the guarded merge reads through the shared reader -------------------------------


def test_a_write_time_from_another_clock_never_makes_a_long_wait(monkeypatch):
    """REQ-050: the hang on a81ea3e: a write time from a fake clock far ahead of the real one."""
    slept: list[float] = []
    monkeypatch.setattr(session, "LAST_WRITE", time.monotonic() + 1_000_000.0)
    monkeypatch.setattr(session.time, "sleep", slept.append)
    session.pace("POST")
    assert slept and max(slept) <= session.WRITE_GAP


def test_the_merge_reads_are_counted_and_conditional(monkeypatch, tmp_path):
    """REQ-050"""
    monkeypatch.setattr(session, "rate_state", lambda: None)  # never a real `gh`
    seen: list[list[str]] = []
    answers = iter([
        f'HTTP/2.0 200 OK\r\nEtag: "m1"\r\n\r\n{json.dumps(BODY)}',
        'HTTP/2.0 304 Not Modified\r\nEtag: "m1"\r\n\r\n',
    ])  # fmt: skip

    def fake(args, env=None):
        seen.append(list(args))
        out = next(answers)
        return subprocess.CompletedProcess(args, 0 if " 200 " in out else 1, out, "")

    monkeypatch.setenv(session.CACHE_ENV, str(tmp_path / "cache"))
    monkeypatch.setattr(session, "CACHE", session.ReadCache())
    monkeypatch.setattr(session, "transport_setting", lambda start=None: "gh")
    monkeypatch.setattr(session, "DIRECT", session.Direct())
    monkeypatch.setattr(merge_cleared, "gh_api", fake)
    monkeypatch.setattr(session.CACHE, "unchanged", (0.0, set()))  # never used by the merge
    before = session.CALLS
    assert merge_cleared.read_json(EP, dict, "the pull request") == BODY
    assert merge_cleared.read_once(EP, dict) == BODY  # a 304 for the same request
    assert session.CALLS - before == 2 and len(seen) == 2
    assert seen[1][-2:] == ["-H", 'If-None-Match: "m1"']
    assert session.RUN is None and session.CACHE.unchanged == (0.0, set())


def test_one_cleared_merge_holds_its_read_budget(tmp_path):
    """REQ-050"""
    proc, made = merge_cleared_run(tmp_path, toml(ON), [cleared()])
    assert proc.returncode == 0
    reads = [c for c in made if c[2] == "GET"]
    assert len(reads) <= MERGE_READS, reads
    assert all(c[-1] == "-i" for c in reads)  # each read through the shared reader


# --- answer 4: the same output with each transport on the 650-brief fixture --------------------

RUNNER = """
import importlib, json, os, re, shutil, subprocess, sys
from urllib.parse import unquote
sys.path.insert(0, sys.argv[1])
import session
PLANTED = PLANTED_HERE
GH = shutil.which("gh")

class Answer:
    def __init__(self, status, headers, body):
        self.status, self.reason, self.headers, self.body = status, "", headers, body
    def getheader(self, name, default=None):
        return next((v for k, v in self.headers if k.lower() == name.lower()), default)
    def getheaders(self):
        return self.headers
    def read(self):
        return self.body

class Conn:
    def request(self, method, path, headers=None):
        assert method == "GET" and headers["Authorization"] == "Bearer " + PLANTED
        with open(os.path.join(os.environ["GH_STUB_DIR"], "direct.log"), "a") as out:
            out.write(path + "\\n")
        argv = [GH, "api", "--method", "GET", unquote(path.lstrip("/")), "-i"]
        if "If-None-Match" in headers:
            argv += ["-H", "If-None-Match: " + headers["If-None-Match"]]
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        status, head, body = session.split_response(proc.stdout)
        if status is None:
            found = re.search(r"HTTP (\\d{3})", proc.stderr)
            status, body = (int(found.group(1)) if found else 200), (body or '{"message": "x"}')
        self.answer = Answer(status, list(head.items()), body.encode())
    def getresponse(self):
        return self.answer
    def close(self):
        pass

def connect(host):
    assert host == "api.github.com"
    return Conn()

session.Direct.connect = staticmethod(connect)
session.Direct.read_token = staticmethod(lambda host: PLANTED)
module = importlib.import_module(sys.argv[2])
sys.argv = [sys.argv[2] + ".py", *sys.argv[3:]]
sys.exit(module.main())
""".replace("PLANTED_HERE", repr(PLANTED))


@pytest.fixture
def served(repo, tmp_path):
    """The recorded double and its project, as test_github_read_budget's `proj` sets them."""
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write(
        "config/reviewers.yaml", "version: 1\nverdict_authors: [boss]\nspec_approvers: [owner]\n"
    )
    return repo, Double(tmp_path)


def run_with(proj, double, transport: str, script: str, *args: str):
    proj.write("agk.toml", "[flow]\nconductor_poll_seconds = 1\nmax_builders = 4\n"
               f'github_reads = "delta"\ngithub_transport = "{transport}"\n')  # fmt: skip
    runner = double.dir.parent / "runner.py"
    runner.write_text(RUNNER, encoding="utf-8")
    env = clean_env()
    env.update(
        PATH=f"{double.bin}{os.pathsep}{os.environ['PATH']}",
        GH_STUB_DIR=str(double.dir),
        AGK_READ_CACHE=str(double.cache),
    )
    for name in session.PROXY_VARS:
        env.pop(name, None)
    double.forget()
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(runner), str(SCRIPTS), script.removesuffix(".py"), *args],
        cwd=proj.root, capture_output=True, text=True, env=env, timeout=300,
    )  # fmt: skip


SWITCHED = {**COMMANDS, "plan": ("session.py", "plan")}


def timed(out: tuple[int, str]) -> tuple[int, str]:
    return out[0], re.sub(r", \d+(?:\.\d+)? s\b", ", <s>", out[1])  # the plan's seconds


@pytest.mark.parametrize("name", sorted(SWITCHED))
def test_each_switched_command_prints_the_same_with_either_transport(served, name):
    """REQ-050"""
    proj, double = served
    World().serve(double)
    script, *args = SWITCHED[name]
    outs = {}
    for transport in ("gh", "direct"):
        for item in double.cache.glob("*") if double.cache.exists() else []:
            item.unlink()  # each transport starts cold
        (double.dir / "direct.log").unlink(missing_ok=True)
        found = run_with(proj, double, transport, script, *args)
        asked = (double.dir / "direct.log").exists()
        assert asked == (transport == "direct"), found.stderr  # the transport that ran
        assert session.DIRECT_OFF not in found.stderr, found.stderr
        assert PLANTED not in found.stdout + found.stderr
        outs[transport] = (timed(said(found)), [c[:2] + c[3:] for c in double.calls()])
    assert outs["gh"] == outs["direct"]
    for item in double.cache.glob("*"):
        assert PLANTED.encode() not in item.read_bytes()
    assert not re.search(r"Traceback", outs["direct"][0][1])
