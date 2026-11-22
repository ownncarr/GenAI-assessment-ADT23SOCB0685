from dataclasses import dataclass
from io import BytesIO
import re

from pypdf import PdfReader

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PAGES = 200


@dataclass(frozen=True)
class Report:
    text: str
    page_count: int
    word_count: int
    empty_pages: int


def extract_report(data: bytes) -> Report:
    if not data:
        raise ValueError("The uploaded file is empty. Upload a text-based PDF.")
    if len(data) > MAX_PDF_BYTES:
        raise ValueError("The PDF exceeds the 20 MB limit. Upload a smaller report.")
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("This PDF is password protected. Upload an unlocked copy.")
        count = len(reader.pages)
        if not count:
            raise ValueError("The PDF has no pages.")
        if count > MAX_PAGES:
            raise ValueError("The PDF exceeds 200 pages. Upload a shorter report.")
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Could not read this PDF. It may be damaged or an unsupported PDF.") from exc
    words = sum(len(re.findall(r"\b\w+\b", page)) for page in pages)
    if words < 10:
        raise ValueError("Too little readable text was found. Scanned PDFs need OCR first; upload a text-based report.")
    text = "\n\n".join(f"[Page {i}]\n{page}" for i, page in enumerate(pages, 1) if page)
    return Report(text, count, words, sum(not page for page in pages))


def prepare_report(text: str, limit: int = 24000) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    chunks = 12
    separator = "\n\n[... omitted report text ...]\n\n"
    width = (limit - len(separator) * (chunks - 1)) // chunks
    starts = [round(i * (len(text) - width) / (chunks - 1)) for i in range(chunks)]
    return separator.join(text[start:start + width] for start in starts), True
