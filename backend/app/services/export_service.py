"""Export service generating JSON, Markdown, and SARIF 2.1.0 security audit reports."""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List


class ExportService:
    """Formats and exports API fuzz findings into standard formats."""

    @staticmethod
    def export_json(job: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Export findings as comprehensive structured JSON document."""
        report = {
            "schema_version": "1.0.0",
            "generator": "api-fuzzer-alan-vo",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "job": {
                "id": job["id"],
                "target_base_url": job["target_base_url"],
                "status": job["status"],
                "total_cases": job["total_cases"],
                "passed_cases": job["passed_cases"],
                "findings_count": job["findings_count"],
            },
            "findings": [
                {
                    "id": r["id"],
                    "test_name": r.get("test_name", ""),
                    "endpoint": r.get("endpoint", ""),
                    "method": r.get("method", "GET"),
                    "dimension": r.get("dimension", ""),
                    "severity": r["severity"],
                    "status_code": r.get("status_code"),
                    "latency_ms": r.get("latency_ms"),
                    "reasoning": r.get("reasoning", ""),
                    "reproduction_curl": r.get("reproduction_curl", ""),
                    "advisory_notes": r.get("advisory_notes"),
                }
                for r in results
                if r["severity"] != "pass"
            ],
        }
        return json.dumps(report, indent=2)

    @staticmethod
    def export_markdown(job: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Export findings as human-readable GitHub-flavored Markdown report."""
        findings = [r for r in results if r["severity"] != "pass"]
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"# API Fuzz Security Audit Report",
            f"",
            f"**Target URL:** `{job['target_base_url']}`  ",
            f"**Job ID:** `{job['id']}`  ",
            f"**Date:** {now_str}  ",
            f"**Summary:** {len(findings)} finding(s) discovered across {job['total_cases']} executed cases.",
            f"",
            f"## Severity Summary",
            f"",
            f"| Severity | Count |",
            f"|---|---|",
            f"| Critical | {sum(1 for f in findings if f['severity'] == 'critical')} |",
            f"| Moderate | {sum(1 for f in findings if f['severity'] == 'moderate')} |",
            f"| Minor | {sum(1 for f in findings if f['severity'] == 'minor')} |",
            f"",
            f"## Detailed Findings",
            f"",
        ]

        if not findings:
            lines.append("No security vulnerabilities or deviations detected. All test cases passed.")
            return "\n".join(lines)

        for i, f in enumerate(findings, 1):
            sev_badge = f"**[{f['severity'].upper()}]**"
            lines.extend([
                f"### {i}. {sev_badge} {f.get('test_name', 'Fuzz Finding')}",
                f"",
                f"- **Endpoint:** `{f.get('method', 'GET')} {f.get('endpoint', '/')}`",
                f"- **Attack Dimension:** `{f.get('dimension', 'unknown')}`",
                f"- **HTTP Status:** `{f.get('status_code') or 'ERR'}`",
                f"- **Latency:** `{f.get('latency_ms', 0):.1f}ms`",
                f"- **Evaluation:** {f.get('reasoning', '')}",
                f"",
            ])
            if f.get("advisory_notes"):
                lines.extend([
                    f"> **Advisory Note:** {f['advisory_notes']}",
                    f"",
                ])
            lines.extend([
                f"**Reproduction Command:**",
                f"```bash",
                f"{f.get('reproduction_curl', 'curl')}",
                f"```",
                f"",
            ])

        return "\n".join(lines)

    @staticmethod
    def export_sarif(job: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Export findings in standard SARIF 2.1.0 format for GitHub Security integration."""
        findings = [r for r in results if r["severity"] != "pass"]

        sarif_level_map = {
            "critical": "error",
            "moderate": "warning",
            "minor": "note"
        }

        rules = []
        rule_ids = set()
        sarif_results = []

        for f in findings:
            dim = f.get("dimension", "api_security_rule")
            rule_id = f"API-FUZZ-{dim.upper().replace('_', '-')}"
            if rule_id not in rule_ids:
                rule_ids.add(rule_id)
                rules.append({
                    "id": rule_id,
                    "name": dim,
                    "shortDescription": {"text": f"API security vulnerability in {dim}"},
                    "defaultConfiguration": {"level": sarif_level_map.get(f["severity"], "warning")},
                })

            sarif_results.append({
                "ruleId": rule_id,
                "level": sarif_level_map.get(f["severity"], "warning"),
                "message": {
                    "text": f"[{f['severity'].upper()}] {f.get('test_name')}: {f.get('reasoning')}"
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.get("endpoint", "/")},
                        "region": {"startLine": 1}
                    }
                }]
            })

        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "api-fuzzer-alan-vo",
                        "version": "1.0.0",
                        "rules": rules
                    }
                },
                "results": sarif_results
            }]
        }
        return json.dumps(sarif, indent=2)
