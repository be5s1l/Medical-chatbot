from __future__ import annotations

import io
from pathlib import Path


class PDFService:
    def extract_text(self, *, pdf_bytes: bytes, filename: str) -> str:
        # Prefer pdfplumber if installed, fall back to PyPDF2.
        try:
            import pdfplumber  # type: ignore

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                parts: list[str] = []
                for page in pdf.pages:
                    parts.append((page.extract_text() or "").strip())
                return "\n".join([p for p in parts if p]).strip()
        except Exception:
            pass

        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts2: list[str] = []
        for page in reader.pages:
            parts2.append((page.extract_text() or "").strip())
        return "\n".join([p for p in parts2 if p]).strip()


def is_pdf(filename: str, content_type: str) -> bool:
    return (content_type or "").lower() == "application/pdf" or Path(filename or "").suffix.lower() == ".pdf"

