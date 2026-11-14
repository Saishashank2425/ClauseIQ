"""Extract PDF/DOCX text while preserving PDF page provenance."""
from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import fitz
from docx import Document

@dataclass
class ExtractedPage:
    page: int | None
    text: str

def extract_document(filename: str, content: bytes, enable_ocr: bool = False) -> list[ExtractedPage]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(content, enable_ocr)
    if suffix == ".docx":
        doc = Document(BytesIO(content))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return [ExtractedPage(page=None, text="\n".join(paragraphs))]
    raise ValueError("Unsupported file type. Upload a PDF or DOCX document.")

def _extract_pdf(content: bytes, enable_ocr: bool) -> list[ExtractedPage]:
    pages = []
    with fitz.open(stream=content, filetype="pdf") as pdf:
        for index, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()
            if not text and enable_ocr:
                try:
                    import pytesseract
                    from PIL import Image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    text = pytesseract.image_to_string(Image.open(BytesIO(pix.tobytes("png")))).strip()
                except Exception as exc:
                    raise RuntimeError("OCR was requested but Tesseract/Pillow is unavailable or misconfigured.") from exc
            pages.append(ExtractedPage(page=index, text=text))
    return pages
