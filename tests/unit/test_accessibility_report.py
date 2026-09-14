import json

from pdf_remediation.adapters.finalization import AccessibilityReportGenerator
from pdf_remediation.ir import ValidationIssue, ValidationResult


def test_report_compares_preflight_and_postflight() -> None:
    pre = ValidationResult(
        valid=False,
        validator="veraPDF",
        issues=[
            ValidationIssue(code="TAG", message="tag"),
            ValidationIssue(code="FONT", message="font 1"),
            ValidationIssue(code="FONT", message="font 2"),
        ],
    )
    post = ValidationResult(
        valid=False,
        validator="veraPDF",
        issues=[ValidationIssue(code="FONT", message="font remains")],
    )

    raw = AccessibilityReportGenerator().generate(
        post,
        {
            "job_id": "job",
            "run_id": "run",
            "preflight_validation": pre,
            "normalization_report": b'{"changed": true}',
        },
    )
    report = json.loads(raw)
    assert report["comparison"]["fixed_issue_counts"] == {"FONT": 1, "TAG": 1}
    assert report["comparison"]["remaining_issue_counts"] == {"FONT": 1}
    assert report["comparison"]["introduced_issue_counts"] == {}
    assert report["final_pdf_emitted"] is False
