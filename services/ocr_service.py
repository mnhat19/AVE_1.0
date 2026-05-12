from __future__ import annotations

from PIL import Image


def extract_text(path: str) -> dict:
    """Extract text from an image using OCR."""
    try:
        import pytesseract
    except Exception as exc:
        return {"text": "", "error": f"ocr_unavailable:{exc}"}

    try:
        image = Image.open(path)
        text = pytesseract.image_to_string(image, lang="vie+eng")
        return {"text": text}
    except Exception as exc:
        return {"text": "", "error": f"ocr_failed:{exc}"}
