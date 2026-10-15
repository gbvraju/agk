"""Validate a reviewer report against its review context (SPEC-0003 rules 8-10 and 17).

Standard library only; no network. Exits 0 only when the verdict, the truncation statement and
every finding hold.
Messages name the finding number and the field, never content (principle 8).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

from common import CheckError, run

NAME = "review-report"
USAGE = "usage: check_review_report.py --context FILE --report FILE"
VERDICTS = ("cleared", "fix list", "rejected")
TOKENS = ("PR body", "context problems")
FIELDS = ("Where", "Rule", "Wrong", "Fix")
MAX_FIELD = 400
FIELD_LINE = re.compile(r"^\s*(Where|Rule|Wrong|Fix):\s*(.*)$")
FINDING_START = re.compile(r"^(\d+)\.(?:\s+(.*))?$")
HUNK_HEAD = re.compile(r"^### (.+):H(\d+) \(old \d+,\d+ new \d+,\d+\)$")
FOOTER = re.compile(
    r"<!--\s*agk-review:\s*verdict=(.*?)\s+findings=(\d+)\s+truncated=(true|false)\s*-->"
)
CITE_SPEC = re.compile(r"SPEC-(\d{4}) rule (\d+)")
CITE_ADR = re.compile(r"ADR-(\d{4}) decision (\d+)")
CITE_PRINCIPLE = re.compile(r"principle (\d+)")
CITE_REQ = re.compile(r"REQ-(\d{3}) AC(\d+)")


class Context:
    """What the validator needs from a review context: hunks, texts and the truncation flag."""

    def __init__(self, text: str) -> None:
        self.truncated = False
        self.hunks: set[str] = set()
        self.docs: dict[str, list[str]] = {}
        self.requirements: dict[str, list[str]] = {}
        self.principles: list[str] = []
        section = item = None
        fence: str | None = None
        for line in text.splitlines():
            if fence is not None:
                if line.strip() == fence:
                    fence = None
                elif section == "Referenced specs and ADRs" and item:
                    self.docs[item].append(line)
                elif section == "Requirements" and item:
                    self.requirements[item].append(line)
                elif section == "Principles":
                    self.principles.append(line)
                continue
            if line.startswith("~~~~"):
                fence = line.rstrip("abcdefghijklmnopqrstuvwxyz").strip()
            elif line.startswith("## "):
                section, item = line[3:], None
            elif line.startswith("### "):
                item = line[4:].strip()
                head = HUNK_HEAD.match(line)
                if section == "Diff" and head:
                    self.hunks.add(f"{head.group(1)}:H{head.group(2)}")
                elif section == "Referenced specs and ADRs":
                    self.docs[item] = []
                elif section == "Requirements":
                    self.requirements[item] = []
            elif line.startswith("Truncated:") and section is None:
                self.truncated = line.split(":", 1)[1].strip() == "yes"

    def numbered(self, lines: list[str], number: str) -> bool:
        return any(re.match(rf"^\s*{number}\.\s", ln) for ln in lines)

    def cites(self, rule: str) -> bool:
        spec = CITE_SPEC.fullmatch(rule) or CITE_ADR.fullmatch(rule)
        if spec:
            folder = "docs/specs/" if rule.startswith("SPEC") else "docs/adr/"
            prefix = f"{folder}{spec.group(1)}-"
            return any(
                path.startswith(prefix) and self.numbered(lines, spec.group(2))
                for path, lines in self.docs.items()
            )
        principle = CITE_PRINCIPLE.fullmatch(rule)
        if principle:
            return self.numbered(self.principles, principle.group(1))
        req = CITE_REQ.fullmatch(rule)
        if req:
            lines = self.requirements.get(f"REQ-{req.group(1)}", [])
            return any(re.search(rf"\bAC{req.group(2)}\b", ln) for ln in lines)
        return False


@dataclass
class Finding:
    number: int
    fields: dict[str, str] = field(default_factory=dict)
    extra: list[str] = field(default_factory=list)


def parse_report(text: str) -> dict:
    verdicts: list[str] = []
    truncated: list[str] = []
    footers: list[tuple[str, ...]] = []
    findings: list[Finding] = []
    last = "number"
    for line in text.splitlines():
        footer = FOOTER.search(line)
        start = FINDING_START.match(line)
        labelled = FIELD_LINE.match(line)
        if footer:
            footers.append(footer.groups())
        elif line.startswith("Verdict:"):
            verdicts.append(line.split(":", 1)[1].strip())
        elif line.startswith("Context truncated:"):
            truncated.append(line.split(":", 1)[1].strip())
        elif start:
            findings.append(Finding(int(start.group(1))))
            last = "number"
            first = FIELD_LINE.match(start.group(2) or "")
            if first:
                findings[-1].fields[first.group(1)] = first.group(2).strip()
                last = first.group(1)
            elif (start.group(2) or "").strip():
                findings[-1].extra.append(last)
        elif findings and labelled:
            findings[-1].fields[labelled.group(1)] = labelled.group(2).strip()
            last = labelled.group(1)
        elif findings and line.strip():
            findings[-1].extra.append(last)
    return {"verdicts": verdicts, "truncated": truncated, "footers": footers, "findings": findings}


def validate(context: Context, report: dict) -> list[str]:
    problems: list[str] = []
    findings = report["findings"]
    verdicts = report["verdicts"]
    verdict = verdicts[0] if len(verdicts) == 1 else None
    if len(verdicts) != 1:
        problems.append("verdict: exactly one 'Verdict:' line is required")
    elif verdict not in VERDICTS:
        problems.append("verdict: the 'Verdict:' value must be cleared, fix list or rejected")
    if verdict == "cleared" and findings:
        problems.append("verdict: cleared requires no findings")
    if verdict in ("fix list", "rejected") and not findings:
        problems.append(f"verdict: {verdict} requires at least one finding")

    if len(report["truncated"]) != 1 or report["truncated"][0] not in ("yes", "no"):
        problems.append(
            "truncated: exactly one 'Context truncated:' line with yes or no is required"
        )
    elif (report["truncated"][0] == "yes") != context.truncated:
        problems.append("truncated: the 'Context truncated:' line does not match the context")

    for position, finding in enumerate(findings, 1):
        label = f"finding {position}"
        if finding.number != position:
            problems.append(f"{label} field number: expected {position}")
        fields = finding.fields
        for name in FIELDS:
            if name not in fields:
                problems.append(f"{label} field {name}: missing")
            elif not fields[name]:
                problems.append(f"{label} field {name}: empty")
            elif len(fields[name]) > MAX_FIELD or "```" in fields[name] or "~~~" in fields[name]:
                problems.append(
                    f"{label} field {name}: must be one short sentence without a code block"
                )
        for name in sorted(set(finding.extra)):
            problems.append(f"{label} field {name}: must stay on one line")
        where = fields.get("Where")
        if where and where not in TOKENS and where not in context.hunks:
            problems.append(f"{label} field Where: not a hunk of the context or a fixed token")
        rule = fields.get("Rule")
        if rule and not context.cites(rule):
            problems.append(f"{label} field Rule: does not resolve to a rule in the context")

    flag = "true" if context.truncated else "false"
    footer = f"verdict={verdict} findings={len(findings)} truncated={flag}"
    if len(report["footers"]) > 1 or (
        report["footers"]
        and f"verdict={report['footers'][0][0]} findings={report['footers'][0][1]} "
        f"truncated={report['footers'][0][2]}"
        != footer
    ):
        problems.append("footer: the 'agk-review' footer does not match the report")
    return problems


def read(path: str, what: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError(f"cannot read the {what} file") from exc


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    values: dict[str, str] = {}
    i = 0
    while i + 1 < len(args) and args[i] in ("--context", "--report"):
        values[args[i]] = args[i + 1]
        i += 2
    if i != len(args) or set(values) != {"--context", "--report"}:
        print(USAGE, file=sys.stderr)
        return 2
    context = Context(read(values["--context"], "context"))
    report = parse_report(read(values["--report"], "report"))
    problems = validate(context, report)
    for problem in problems:
        print(f"FAIL {NAME}: {problem}")
    if problems:
        return 1
    flag = "true" if context.truncated else "false"
    print(f"ok {NAME}")
    verdict, count = report["verdicts"][0], len(report["findings"])
    print(f"<!-- agk-review: verdict={verdict} findings={count} truncated={flag} -->")
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
