from __future__ import annotations

import json
from collections import Counter
from typing import Any

from pdf_remediation.ir import ValidationResult


class PassThroughFinalizer:
    def finalize(self, candidate: bytes, validation: ValidationResult) -> bytes:
        return candidate


def _issue_counts(validation: ValidationResult | None) -> Counter[str]:
    if validation is None:
        return Counter()
    return Counter(issue.code for issue in validation.issues)


class AccessibilityReportGenerator:
    def generate(self, validation: ValidationResult, context: dict[str, Any]) -> bytes:
        preflight = context.get("preflight_validation")
        if not isinstance(preflight, ValidationResult):
            preflight = None

        before = _issue_counts(preflight)
        after = _issue_counts(validation)

        fixed: dict[str, int] = {}
        remaining: dict[str, int] = {}
        introduced: dict[str, int] = {}

        for code in sorted(set(before) | set(after)):
            fixed_count = max(before[code] - after[code], 0)
            remaining_count = min(before[code], after[code])
            introduced_count = max(after[code] - before[code], 0)
            if fixed_count:
                fixed[code] = fixed_count
            if remaining_count:
                remaining[code] = remaining_count
            if introduced_count:
                introduced[code] = introduced_count

        normalization_report: dict[str, Any] | None = None
        raw_normalization = context.get("normalization_report")
        if isinstance(raw_normalization, bytes):
            try:
                normalization_report = json.loads(raw_normalization.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                normalization_report = {"parse_error": True}

        payload = {
            "job_id": context.get("job_id"),
            "run_id": context.get("run_id"),
            "validator": validation.validator,
            "preflight": {
                "valid": preflight.valid if preflight else None,
                "issue_count": len(preflight.issues) if preflight else None,
                "issues": [
                    issue.model_dump(mode="json")
                    for issue in (preflight.issues if preflight else [])
                ],
            },
            "postflight": {
                "valid": validation.valid,
                "issue_count": len(validation.issues),
                "issues": [
                    issue.model_dump(mode="json")
                    for issue in validation.issues
                ],
                "metadata": validation.metadata,
            },
            "comparison": {
                "fixed_issue_counts": fixed,
                "remaining_issue_counts": remaining,
                "introduced_issue_counts": introduced,
            },
            "font_normalization": normalization_report,
            "final_pdf_emitted": validation.valid,
            "note": (
                "Machine validation is not a substitute for human accessibility review. "
                "final_pdf.pdf is emitted only when postflight veraPDF validation passes."
            ),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
