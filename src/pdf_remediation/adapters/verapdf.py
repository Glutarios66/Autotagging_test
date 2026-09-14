from __future__ import annotations

import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from pdf_remediation.ir import SemanticDocumentIR, ValidationIssue, ValidationResult


class VeraPDFValidator:
    def __init__(self, executable: str = "verapdf", flavour: str = "ua1") -> None:
        self.executable = executable
        self.flavour = flavour

    def validate(
        self,
        content: bytes,
        semantics: SemanticDocumentIR | None = None,
    ) -> ValidationResult:
        executable = shutil.which(self.executable)
        if executable is None:
            return ValidationResult(
                valid=False,
                validator="veraPDF",
                issues=[
                    ValidationIssue(
                        code="VERAPDF_NOT_INSTALLED",
                        severity="error",
                        message=(
                            f"veraPDF executable '{self.executable}' was not found on PATH. "
                            "Tagged PDF generation can still succeed, but PDF/UA validation was skipped."
                        ),
                    )
                ],
                metadata={"flavour": self.flavour, "executed": False},
            )

        with tempfile.TemporaryDirectory(prefix="pdf-remediation-verapdf-") as temp:
            pdf_path = Path(temp) / "candidate.pdf"
            pdf_path.write_bytes(content)
            process = subprocess.run(
                [
                    executable,
                    "--format",
                    "xml",
                    "--flavour",
                    self.flavour,
                    "--maxfailuresdisplayed",
                    "50",
                    str(pdf_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

        raw = process.stdout.strip()
        if not raw:
            return ValidationResult(
                valid=False,
                validator="veraPDF",
                issues=[
                    ValidationIssue(
                        code="VERAPDF_EXECUTION_FAILED",
                        severity="error",
                        message=(process.stderr.strip() or "veraPDF produced no report")[:2000],
                    )
                ],
                metadata={
                    "flavour": self.flavour,
                    "executed": True,
                    "return_code": process.returncode,
                },
            )

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            return ValidationResult(
                valid=False,
                validator="veraPDF",
                issues=[
                    ValidationIssue(
                        code="VERAPDF_REPORT_PARSE_ERROR",
                        severity="error",
                        message=str(exc),
                    )
                ],
                metadata={
                    "flavour": self.flavour,
                    "executed": True,
                    "return_code": process.returncode,
                    "raw_report": raw[:10000],
                },
            )

        report = root.find(".//validationReport")
        compliant = (
            report is not None
            and str(report.attrib.get("isCompliant", "")).lower() == "true"
        )
        issues: list[ValidationIssue] = []

        for rule in root.findall(".//rule[@status='failed']"):
            description = (rule.findtext("description") or "veraPDF validation rule failed").strip()
            code = "-".join(
                part
                for part in (
                    rule.attrib.get("specification"),
                    rule.attrib.get("clause"),
                    rule.attrib.get("testNumber"),
                )
                if part
            ) or "VERAPDF_RULE_FAILED"
            contexts = [
                (check.findtext("context") or "").strip()
                for check in rule.findall("check")
            ]
            contexts = [context for context in contexts if context]
            message = description
            if contexts:
                message += f" Context: {contexts[0]}"
            issues.append(
                ValidationIssue(
                    code=code[:200],
                    severity="error",
                    message=message[:4000],
                )
            )

        profile_name = report.attrib.get("profileName") if report is not None else None
        return ValidationResult(
            valid=compliant,
            validator="veraPDF",
            issues=issues,
            metadata={
                "flavour": self.flavour,
                "profile_name": profile_name,
                "executed": True,
                "return_code": process.returncode,
            },
        )
