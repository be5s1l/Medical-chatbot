from pathlib import Path

DOCUMENT_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}


def detect_kind(file_path: str) -> str:
    suf = Path(file_path).suffix.lower()
    if suf in DOCUMENT_EXTENSIONS:
        return "document"
    if suf in IMAGE_EXTENSIONS:
        return "image"
    return "unknown"
