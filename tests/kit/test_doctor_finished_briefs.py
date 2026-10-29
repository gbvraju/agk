"""The doctor warns about finished briefs left open (brief #302 answer 3; REQ-039, ADR-0178).

`brief-finished` (warn, after `brief-label`) fails when an open brief has pull requests whose body
names it with `Brief: #n`, none of them is open, at least one merged, and the last merge is more
than a day old. It lists those briefs. It reads the open `agk-brief` issues and the latest pull
requests with GET only; a read that fails is `cannot-check`, never `ok`. No network.
"""

from __future__ import annotations

import datetime
import json

from test_doctor import FIXTURES, IDS, checks_of, doctor, prepare, run_case


def stamp(hours: float) -> str:
    when = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=hours)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def with_api(tmp_path, briefs, pulls):
    dirs = prepare("ok", tmp_path)
    (dirs["api"] / "briefs-open.json").write_text(json.dumps(briefs), encoding="utf-8")
    (dirs["api"] / "pulls-all.json").write_text(json.dumps(pulls), encoding="utf-8")
    proc = doctor("--api-dir", str(dirs["api"]), "--kit-root", str(dirs["kit"]), "--json",
                  str(dirs["root"]))  # fmt: skip
    return checks_of(proc.stdout)["brief-finished"], proc


def brief(n: int) -> dict:
    return {"number": n, "state": "open", "labels": [{"name": "agk-brief"}]}


def pull(n: int, body: str, merged: str | None, state: str = "closed") -> dict:
    return {"number": n, "state": state, "merged_at": merged, "body": body}


def test_the_check_is_a_warning_after_brief_label():
    assert IDS.index("brief-finished") == IDS.index("brief-label") + 1


def test_an_open_brief_whose_pull_requests_all_merged_long_ago_is_listed(tmp_path):
    proc, log, _ = run_case("brief-finished-open", tmp_path, "--json")
    check = checks_of(proc.stdout)["brief-finished"]
    assert (check["status"], check["severity"]) == ("fail", "warn")
    assert check["message"].endswith(" (#5)"), check["message"]
    for other in ("#6", "#7", "#8", "#9"):
        assert other not in check["message"]
    assert "Finishes:" in check["fix"]
    assert proc.returncode == 4 and not log.exists()


def test_a_merge_of_less_than_a_day_is_not_listed_yet(tmp_path):
    check, _ = with_api(tmp_path / "a", [brief(5)], [pull(10, "Brief: #5", stamp(2))])
    assert check["status"] == "ok"
    check, _ = with_api(tmp_path / "b", [brief(5)], [pull(10, "Brief: #5", stamp(25))])
    assert check["status"] == "fail" and "(#5)" in check["message"]


def test_the_latest_merge_of_a_brief_counts(tmp_path):
    pulls = [pull(10, "Brief: #5", stamp(72)), pull(11, "Brief: #5", stamp(3))]
    check, _ = with_api(tmp_path, [brief(5)], pulls)
    assert check["status"] == "ok"


def test_a_long_list_is_cut(tmp_path):
    numbers = list(range(20, 35))
    pulls = [pull(100 + n, f"Brief: #{n}", stamp(48)) for n in numbers]
    check, _ = with_api(tmp_path, [brief(n) for n in numbers], pulls)
    assert check["status"] == "fail"
    assert "#20, #21" in check["message"] and "and 5 more" in check["message"]


def test_an_unreadable_read_is_cannot_check(tmp_path):
    dirs = prepare("ok", tmp_path)
    (dirs["api"] / "pulls-all.json").unlink()
    proc = doctor("--api-dir", str(dirs["api"]), "--json", str(dirs["root"]))
    check = checks_of(proc.stdout)["brief-finished"]
    assert (check["status"], check["reason"]) == ("cannot-check", "bad-response")
    (dirs["api"] / "pulls-all.json").write_text('{"not": "a list"}', encoding="utf-8")
    proc = doctor("--api-dir", str(dirs["api"]), "--json", str(dirs["root"]))
    assert checks_of(proc.stdout)["brief-finished"]["status"] == "cannot-check"


def test_no_open_brief_is_ok(tmp_path):
    check, _ = with_api(tmp_path, [], [pull(10, "Brief: #5", stamp(48))])
    assert check["status"] == "ok"


def test_the_case_fixture_exists():
    assert (FIXTURES / "brief-finished-open" / "case.json").is_file()
