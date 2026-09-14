from pathlib import Path

from pdf_remediation.infrastructure.artifacts import FileSystemArtifactStore


def test_filesystem_store_preserves_extension(tmp_path: Path) -> None:
    store = FileSystemArtifactStore(tmp_path)
    uri = store.put("a/b/final_pdf.pdf", b"%PDF-1.7\n", "application/pdf")
    assert uri.endswith("final_pdf.pdf")
    assert Path(uri.removeprefix("file://")).read_bytes().startswith(b"%PDF-")
