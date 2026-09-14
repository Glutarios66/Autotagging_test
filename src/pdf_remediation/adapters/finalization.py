from __future__ import annotations

import json
from typing import Any

from pdf_remediation.ir import ValidationResult


class PassThroughFinalizer:
    def finalize(self, candidate: bytes, validation: ValidationResult) -> bytes:
        # Preserve the real tagged candidate even when PDF/UA checks fail.
        # Compliance status is communicated through validation/report artifacts.
        return candidate


class AccessibilityReportGenerator:
    def generate(self, validation: ValidationResult, context: dict[str, Any]) -> bytes:
        return json.dumps(
            {
                "job_id": context.get("job_id"),
                "run_id": context.get("run_id"),
                "validator": validation.validator,
                "pdfua_machine_validation_passed": validation.valid,
                "issues": [issue.model_dump(mode="json") for issue in validation.issues],
                "metadata": validation.metadata,
                "note": (
                    "Machine validation is not a substitute for human accessibility review. "
                    "veraPDF checks machine-verifiable PDF/UA requirements."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
