from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from src.core.config import settings


class OCRService:
    """
    OCR service for lab report images.

    Tries `pytesseract` if installed/allowed; falls back to Tesseract CLI.
    """

    def __init__(self) -> None:
        self._tesseract = (getattr(settings, "tesseract_path", "") or "").strip()
        if not self._tesseract:
            raise RuntimeError("TESSERACT_PATH is not configured")

    async def extract_text(self, *, image_bytes: bytes, filename: str, mime_type: str) -> str:
        # Save upload to a temp file, then OCR.
        suffix = Path(filename or "upload").suffix or self._suffix_from_mime(mime_type)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(image_bytes)
            path = Path(tmp.name)
        try:
            text = self._try_pytesseract(path) or self._tesseract_cli(path)
            return self.clean_text(text)
        finally:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass

    def clean_text(self, text: str) -> str:
        t = (text or "").strip()
        # Normalize whitespace and remove obvious OCR artifacts.
        t = t.replace("\x0c", " ")  # form feed
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()

    def _try_pytesseract(self, path: Path) -> str | None:
        try:
            import pytesseract  # type: ignore

            pytesseract.pytesseract.tesseract_cmd = self._tesseract
            img = Image.open(path)
            return (pytesseract.image_to_string(img) or "").strip()
        except Exception:
            return None

    def _tesseract_cli(self, path: Path) -> str:
        img_path = path
        tmp_png: str | None = None
        try:
            try:
                Image.open(path).verify()
            except Exception:
                img = Image.open(path)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp_png = tmp.name
                img.convert("RGB").save(tmp_png, format="PNG")
                img_path = Path(tmp_png)

            result = subprocess.run(
                [self._tesseract, str(img_path), "stdout", "--psm", "6"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                err = (result.stderr or "").strip()
                raise RuntimeError(f"Tesseract failed (exit {result.returncode}): {err or 'Unknown error'}")
            return (result.stdout or "").strip()
        finally:
            if tmp_png:
                try:
                    Path(tmp_png).unlink(missing_ok=True)
                except Exception:
                    pass

    def _suffix_from_mime(self, mime_type: str) -> str:
        m = (mime_type or "").lower()
        if m == "image/png":
            return ".png"
        if m in {"image/jpg", "image/jpeg"}:
            return ".jpg"
        if m == "image/webp":
            return ".webp"
        return ".png"

