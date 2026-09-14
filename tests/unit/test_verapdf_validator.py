from __future__ import annotations

from pdf_remediation.adapters.verapdf import VeraPDFValidator


def test_verapdf_missing_executable_is_explicit(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    result = VeraPDFValidator(executable="not-there").validate(b"%PDF-1.7\n")
    assert result.valid is False
    assert result.issues[0].code == "VERAPDF_NOT_INSTALLED"
    assert result.metadata["executed"] is False
