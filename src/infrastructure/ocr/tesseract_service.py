import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from pathlib import Path

from src.core.config import settings
from src.domain.interfaces.ocr_service import IOCRService

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path


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
        img = Image.open(path)
        return pytesseract.image_to_string(img).strip()
