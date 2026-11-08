"""Group exported GitHub image alerts without dismissing any findings."""

import argparse
import json
from pathlib import Path
import re


SEVERITIES = ("critical", "high", "medium", "low", "unknown")
ADVISORY = re.compile(r"^(CVE-\d{4}-\d+|GO-\d{4}-\d+|GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})(?:-|$)")


def parse_alert(alert: dict) -> dict:
    message = alert["message"]
    match = ADVISORY.match(alert["rule_id"])
    advisory = match.group(1) if match else alert["rule_id"]
    if alert["tool"] == "Trivy":
        fields = dict(re.findall(r"^([^:\n]+):[ \t]*(.*)$", message, re.MULTILINE))
        package = fields["Package"]
        version = fields["Installed Version"]
        fixed = fields.get("Fixed Version", "").strip()
        severity = fields.get("Severity", "unknown").lower()
        fix_known = "Fixed Version" in fields
    elif alert["tool"] == "Grype":
        match = re.search(
            r"^A (\w+) vulnerability in [^:]+ package: (.+?), version (.+?) was found in image ",
            message,
        )
        if match is None:
            raise ValueError(f"Unrecognized Grype message for alert {alert['number']}")
        severity, package, version = match.groups()
        fixed = ""
        fix_known = False
        for line in (alert.get("help") or "").splitlines():
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(cells) == 8 and cells[1:3] == [package, version]:
                fixed = cells[3]
                fix_known = True
                break
    else:
        raise ValueError(f"Unsupported scanner {alert['tool']} for alert {alert['number']}")
    severity = alert.get("severity") or severity
    if severity not in SEVERITIES:
        severity = "unknown"
    return {
        "advisory": advisory,
        "package": package,
        "version": version,
        "severity": severity,
        "fixed_version": fixed or None,
        "fix_metadata_present": fix_known,
        "number": alert["number"],
        "tool": alert["tool"],
        "category": alert["category"],
        "ref": alert["ref"],
        "path": alert["path"],
        "commit": alert["commit"],
        "url": alert["url"],
    }


def summarize(alerts: list[dict]) -> dict:
    groups: dict[tuple[str, str], list[dict]] = {}
    numbers: set[int] = set()
    for alert in alerts:
        item = parse_alert(alert)
        if item["number"] in numbers:
            raise ValueError(f"Duplicate exported alert number {item['number']}")
        numbers.add(item["number"])
        groups.setdefault((item["advisory"], item["package"]), []).append(item)
    findings = []
    for (advisory, package), occurrences in groups.items():
        fixes = sorted({item["fixed_version"] for item in occurrences if item["fixed_version"]})
        status = (
            "scanner_reported_fix" if fixes else
            "fix_metadata_missing" if any(not item["fix_metadata_present"] for item in occurrences)
            else "no_fix_reported"
        )
        findings.append({
            "advisory": advisory,
            "package": package,
            "severity": min(
                (item["severity"] for item in occurrences), key=SEVERITIES.index,
            ),
            "status": status,
            "reported_fixed_versions": fixes,
            "alert_count": len(occurrences),
            "occurrences": sorted(occurrences, key=lambda item: item["number"]),
        })
    findings.sort(key=lambda item: (
        SEVERITIES.index(item["severity"]), item["advisory"], item["package"],
    ))
    return {
        "alert_count": len(numbers),
        "advisory_package_count": len(findings),
        "status_counts": {
            status: sum(item["status"] == status for item in findings)
            for status in ("scanner_reported_fix", "no_fix_reported", "fix_metadata_missing")
        },
        "limitations": [
            "Reported fixed versions require vendor availability, rebuild and fresh scan verification.",
            "No fix reported is not proof that no upstream patch exists.",
            "Different advisory identifiers are not merged without verified alias evidence.",
            "Every scanner, image, architecture, path and source commit is retained in occurrences.",
            "GitHub alerts may refer to historical images; this is not a current deployment scan.",
        ],
        "findings": findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alerts", type=Path, help="JSONL alert export documented in SECURITY_BASELINE")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        alerts = [json.loads(line) for line in args.alerts.read_text().splitlines() if line.strip()]
        result = summarize(alerts)
    except (KeyError, TypeError, ValueError) as error:
        parser.error(f"Invalid alert export: {error}")
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "findings"}, indent=2))


if __name__ == "__main__":
    main()
