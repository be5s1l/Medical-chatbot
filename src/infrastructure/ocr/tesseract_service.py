import subprocess
import tempfile
from pathlib import Path

from PIL import Image
from PyPDF2 import PdfReader

from src.core.config import settings
from src.domain.interfaces.ocr_service import IOCRService


class TesseractOCRService(IOCRService):
    def extract_text(self, file_path: str) -> str:
        path = Path(file_path)
        if path.suffix.lower() == ".pdf":
            return self._extract_from_pdf(path)
        return self._extract_from_image(path)

    def _extract_from_pdf(self, path: Path) -> str:
        text_parts: list[str] = []
        with path.open("rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        return "\n".join(text_parts).strip()

    def _extract_from_image(self, path: Path) -> str:
        """
        Use the Tesseract CLI instead of `pytesseract`.

        Reason: some environments enforce Windows Application Control policies that block
        native wheels (e.g., pandas), and `pytesseract` imports `pandas` at import time.
        Calling the CLI keeps OCR working without importing DLL-backed Python modules.
        """
        tesseract = (settings.tesseract_path or "").strip()
        if not tesseract:
            raise RuntimeError("TESSERACT_PATH is not configured")

        # Tesseract works best on common raster formats. Ensure we pass a file path it can read.
        # If the upload is not directly readable, convert to a temp PNG.
        img_path = path
        tmp_png: str | None = None
        try:
            try:
                Image.open(path).verify()
            except Exception:
                # Some formats may not verify; attempt a conversion.
                img = Image.open(path)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp_png = tmp.name
                img.convert("RGB").save(tmp_png, format="PNG")
                img_path = Path(tmp_png)

            # `stdout` makes tesseract write text to stdout.
            # `--psm 3` is "fully automatic page segmentation" and is a reasonable default.
            result = subprocess.run(
                [tesseract, str(img_path), "stdout", "--psm", "3"],
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
