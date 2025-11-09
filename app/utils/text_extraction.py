import io
import re
from typing import Optional, Tuple
from pypdf import PdfReader
import pytesseract

try:
    from pdf2image import convert_from_bytes  # optional (for OCR)
    _HAS_PDF2IMAGE = True
except Exception:
    _HAS_PDF2IMAGE = False


def _normalize_text(text: str) -> str:
    # Simple normalization: collapse whitespace and normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_from_txt(data: bytes) -> str:
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = data.decode(errors="ignore")
    return _normalize_text(text)


def extract_from_pdf(data: bytes, use_ocr: bool = True) -> Tuple[str, bool]:
    """
    Returns (text, used_ocr)
    - Tries digital text extraction via pypdf
    - Falls back to OCR if not enough text and use_ocr is True
    """
    text_chunks = []
    try:
        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t:
                text_chunks.append(t)
    except Exception:
        # Broken PDF? Force OCR path if allowed
        text_chunks = []

    extracted_text = _normalize_text("\n\n".join(text_chunks))
    if len(extracted_text) >= 200:  # heuristic threshold
        return extracted_text, False

    if not use_ocr:
        return extracted_text, False

    if not _HAS_PDF2IMAGE:
        raise RuntimeError(
            "Scanned PDF detected but pdf2image is not installed. "
            "Install it with: pip install pdf2image (and ensure Poppler is installed)."
        )

    # OCR path
    images = convert_from_bytes(data, dpi=200)  # requires Poppler
    ocr_texts = []
    for img in images:
        try:
            ocr_texts.append(pytesseract.image_to_string(img))
        except Exception:
            ocr_texts.append("")
    final_text = _normalize_text("\n\n".join(ocr_texts))
    return final_text, True


def extract_text_from_file(
    filename: str, content_type: Optional[str], data: bytes, use_ocr: bool = True
) -> Tuple[str, bool]:
    """
    Returns (text, used_ocr)
    """
    name = (filename or "").lower()
    ctype = (content_type or "").lower()

    if name.endswith(".txt") or ctype.startswith("text/"):
        return extract_from_txt(data), False
    if name.endswith(".pdf") or "pdf" in ctype:
        return extract_from_pdf(data, use_ocr=use_ocr)
    # Fallback: try UTF-8
    return extract_from_txt(data), False