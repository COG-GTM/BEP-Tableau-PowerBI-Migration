#!/usr/bin/env python3
"""
CLI runner for BEP Tableau-to-Power BI conversion validation.

Runs all pytest tests programmatically, captures results, and generates:
  - validation/reports/conversion_validation_report.md
  - validation/reports/validation_summary.json

Returns exit code 0 if all pass, 1 if any fail.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import pytest

from validate_conversion import ValidationReport, run_all_validations

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")
MD_REPORT = os.path.join(REPORTS_DIR, "conversion_validation_report.md")
JSON_REPORT = os.path.join(REPORTS_DIR, "validation_summary.json")


# ---------------------------------------------------------------------------
# Pytest runner
# ---------------------------------------------------------------------------

class PytestResultCollector:
    """Collect pytest results for reporting."""

    def __init__(self) -> None:
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.errors: List[str] = []
        self.skipped: List[str] = []
        self.failure_details: Dict[str, str] = {}

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.failed) + len(self.errors) + len(self.skipped)


def run_pytest_tests() -> PytestResultCollector:
    """Run all pytest tests and collect results."""
    collector = PytestResultCollector()

    class ResultPlugin:
        """pytest plugin to capture test results."""

        def pytest_runtest_logreport(self, report: Any) -> None:
            if report.when == "call":
                if report.passed:
                    collector.passed.append(report.nodeid)
                elif report.failed:
                    collector.failed.append(report.nodeid)
                    collector.failure_details[report.nodeid] = str(
                        report.longrepr
                    )
            elif report.when == "setup" and report.failed:
                collector.errors.append(report.nodeid)
                collector.failure_details[report.nodeid] = str(report.longrepr)
            if report.skipped:
                collector.skipped.append(report.nodeid)

    # Run pytest with verbose output
    exit_code = pytest.main(
        [
            SCRIPT_DIR,
            "-v",
            "--tb=short",
            "-q",
        ],
        plugins=[ResultPlugin()],
    )

    return collector


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------

def _categorize_test(test_name: str) -> str:
    """Determine which dashboard a test belongs to."""
    if "sales" in test_name.lower():
        return "Sales Dashboard"
    if "hr" in test_name.lower():
        return "HR Dashboard"
    if "ciso" in test_name.lower() or "vuln" in test_name.lower():
        return "CISO Cybersecurity Dashboard"
    if "it_project" in test_name.lower() or "jira" in test_name.lower():
        return "IT Project Management Dashboard"
    return "Other"


def _classify_conversion_type(test_name: str) -> str:
    """Determine conversion type from test name."""
    name = test_name.lower()
    if "lod" in name or "per_customer" in name or "risk_score" in name:
        return "LOD Expression"
    if "window" in name or "running" in name or "moving" in name or "highlight" in name:
        return "Table Calculation"
    if "kpi" in name or "avg" in name:
        return "Table Calculation"
    if "min_max" in name:
        return "Table Calculation"
    if "pct" in name or "rate" in name:
        return "Simple IF / Aggregation"
    return "Simple IF / Aggregation"


def generate_md_report(
    pytest_results: PytestResultCollector,
    validation_report: ValidationReport,
) -> str:
    """Generate a Markdown report suitable for BEP stakeholders."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    total_tests = pytest_results.total
    passed_tests = len(pytest_results.passed)
    failed_tests = len(pytest_results.failed)
    error_tests = len(pytest_results.errors)

    pass_rate = (passed_tests / total_tests * 100) if total_tests else 0

    lines: List[str] = []
    lines.append("# BEP Tableau-to-Power BI Conversion Validation Report")
    lines.append("")
    lines.append(f"> Generated: {now}")
    lines.append("> Framework: Python pytest + pandas validation engine")
    lines.append("> Methodology: Dual implementation (Tableau logic + DAX logic) comparison")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    if pass_rate == 100:
        lines.append(
            "All conversion validations **PASSED**. The DAX measures produce identical "
            "results to the original Tableau calculated fields when run against the same "
            "production datasets. The conversion is verified and ready for IV&V review."
        )
    elif pass_rate >= 90:
        lines.append(
            f"Conversion validation achieved **{pass_rate:.1f}%** pass rate. "
            f"{failed_tests} measure(s) require review. See details below."
        )
    else:
        lines.append(
            f"Conversion validation achieved **{pass_rate:.1f}%** pass rate. "
            f"{failed_tests} measure(s) failed verification. Remediation required."
        )
    lines.append("")

    # Overall Stats
    lines.append("## Overall Results")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Tests | {total_tests} |")
    lines.append(f"| Passed | {passed_tests} |")
    lines.append(f"| Failed | {failed_tests} |")
    lines.append(f"| Errors | {error_tests} |")
    lines.append(f"| **Pass Rate** | **{pass_rate:.1f}%** |")
    lines.append("")

    # Results by Dashboard
    lines.append("## Results by Dashboard")
    lines.append("")
    dashboard_groups: Dict[str, List[str]] = {}
    all_tests = pytest_results.passed + pytest_results.failed + pytest_results.errors
    for test in all_tests:
        dash = _categorize_test(test)
        dashboard_groups.setdefault(dash, []).append(test)

    for dash, tests in sorted(dashboard_groups.items()):
        d_passed = sum(1 for t in tests if t in pytest_results.passed)
        d_total = len(tests)
        d_pct = (d_passed / d_total * 100) if d_total else 0
        status_icon = "PASS" if d_passed == d_total else "PARTIAL"
        lines.append(f"### {dash} — {status_icon} ({d_passed}/{d_total})")
        lines.append("")
        lines.append("| Test | Status |")
        lines.append("|------|--------|")
        for t in sorted(tests):
            short_name = t.split("::")[-1] if "::" in t else t
            if t in pytest_results.passed:
                lines.append(f"| {short_name} | PASS |")
            elif t in pytest_results.failed:
                lines.append(f"| {short_name} | **FAIL** |")
            else:
                lines.append(f"| {short_name} | ERROR |")
        lines.append("")

    # Results by Conversion Type
    lines.append("## Results by Conversion Type")
    lines.append("")
    type_groups: Dict[str, Dict[str, int]] = {}
    for test in all_tests:
        ctype = _classify_conversion_type(test)
        if ctype not in type_groups:
            type_groups[ctype] = {"passed": 0, "failed": 0, "total": 0}
        type_groups[ctype]["total"] += 1
        if test in pytest_results.passed:
            type_groups[ctype]["passed"] += 1
        else:
            type_groups[ctype]["failed"] += 1

    lines.append("| Conversion Type | Passed | Failed | Total | Rate |")
    lines.append("|----------------|--------|--------|-------|------|")
    for ctype, counts in sorted(type_groups.items()):
        rate = (counts["passed"] / counts["total"] * 100) if counts["total"] else 0
        lines.append(
            f"| {ctype} | {counts['passed']} | {counts['failed']} | "
            f"{counts['total']} | {rate:.0f}% |"
        )
    lines.append("")

    # Standalone Validation Engine Results
    lines.append("## Standalone Validation Engine Results")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Measures Validated | {validation_report.total} |")
    lines.append(f"| PASS | {validation_report.pass_count} |")
    lines.append(f"| WARN | {validation_report.warn_count} |")
    lines.append(f"| FAIL | {validation_report.fail_count} |")
    lines.append(
        f"| **Pass Rate** | **{validation_report.pass_rate:.1%}** |"
    )
    lines.append("")

    # Failure Details
    if pytest_results.failed or pytest_results.errors:
        lines.append("## Failure Details")
        lines.append("")
        for test_id, detail in pytest_results.failure_details.items():
            short = test_id.split("::")[-1] if "::" in test_id else test_id
            lines.append(f"### {short}")
            lines.append("")
            lines.append("```")
            # Truncate very long failures
            detail_lines = str(detail).split("\n")
            for line in detail_lines[:30]:
                lines.append(line)
            if len(detail_lines) > 30:
                lines.append(f"... ({len(detail_lines) - 30} more lines)")
            lines.append("```")
            lines.append("")

    # Validation Engine Details
    warns_and_fails = [
        r for r in validation_report.results if r.status in ("WARN", "FAIL")
    ]
    if warns_and_fails:
        lines.append("## Validation Engine Warnings/Failures")
        lines.append("")
        for r in warns_and_fails:
            lines.append(f"### [{r.status}] {r.dashboard} — {r.measure_name}")
            lines.append("")
            lines.append(f"- **Tableau Formula**: `{r.tableau_formula}`")
            lines.append(f"- **DAX Formula**: `{r.dax_formula}`")
            lines.append(f"- **Tableau Value**: {r.tableau_value}")
            lines.append(f"- **DAX Value**: {r.dax_value}")
            if r.note:
                lines.append(f"- **Note**: {r.note}")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        "*This report was auto-generated by the BEP validation framework. "
        "For questions, contact the BEP MES Migration Team.*"
    )

    return "\n".join(lines)


def generate_json_report(
    pytest_results: PytestResultCollector,
    validation_report: ValidationReport,
) -> Dict[str, Any]:
    """Generate machine-readable JSON summary."""
    now = datetime.utcnow().isoformat() + "Z"

    # Pytest results
    pytest_data = {
        "total": pytest_results.total,
        "passed": len(pytest_results.passed),
        "failed": len(pytest_results.failed),
        "errors": len(pytest_results.errors),
        "skipped": len(pytest_results.skipped),
        "pass_rate": (
            len(pytest_results.passed) / pytest_results.total
            if pytest_results.total
            else 0
        ),
        "tests": {
            "passed": pytest_results.passed,
            "failed": pytest_results.failed,
            "errors": pytest_results.errors,
        },
    }

    # Validation engine results
    engine_data = {
        "total": validation_report.total,
        "pass": validation_report.pass_count,
        "warn": validation_report.warn_count,
        "fail": validation_report.fail_count,
        "pass_rate": validation_report.pass_rate,
        "measures": [
            {
                "dashboard": r.dashboard,
                "measure": r.measure_name,
                "conversion_type": r.conversion_type,
                "status": r.status,
                "tableau_formula": r.tableau_formula,
                "dax_formula": r.dax_formula,
                "tableau_value": str(r.tableau_value),
                "dax_value": str(r.dax_value),
            }
            for r in validation_report.results
        ],
    }

    return {
        "generated_at": now,
        "framework": "BEP Tableau-to-Power BI Conversion Validation",
        "pytest_results": pytest_data,
        "validation_engine_results": engine_data,
        "overall_pass": (
            len(pytest_results.failed) == 0
            and len(pytest_results.errors) == 0
            and validation_report.fail_count == 0
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Run validation suite and generate reports."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    print("=" * 60)
    print("  BEP Conversion Validation Suite")
    print("=" * 60)

    # Step 1: Run pytest tests
    print("\n[1/4] Running pytest test suite...")
    pytest_results = run_pytest_tests()
    print(
        f"      pytest: {len(pytest_results.passed)} passed, "
        f"{len(pytest_results.failed)} failed, "
        f"{len(pytest_results.errors)} errors"
    )

    # Step 2: Run standalone validation engine
    print("\n[2/4] Running standalone validation engine...")
    validation_report = run_all_validations()
    print(
        f"      engine: {validation_report.pass_count} PASS, "
        f"{validation_report.warn_count} WARN, "
        f"{validation_report.fail_count} FAIL"
    )

    # Step 3: Generate Markdown report
    print("\n[3/4] Generating Markdown report...")
    md_content = generate_md_report(pytest_results, validation_report)
    with open(MD_REPORT, "w") as f:
        f.write(md_content)
    print(f"      Written: {MD_REPORT}")

    # Step 4: Generate JSON report
    print("\n[4/4] Generating JSON report...")
    json_data = generate_json_report(pytest_results, validation_report)
    with open(JSON_REPORT, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"      Written: {JSON_REPORT}")

    # Summary
    all_passed = (
        len(pytest_results.failed) == 0
        and len(pytest_results.errors) == 0
        and validation_report.fail_count == 0
    )

    print("\n" + "=" * 60)
    if all_passed:
        print("  RESULT: ALL VALIDATIONS PASSED")
    else:
        print("  RESULT: SOME VALIDATIONS FAILED — see reports for details")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
