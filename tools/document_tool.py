"""Document Tool: extracts clean text from PDF bytes."""
from io import BytesIO

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf. Returns cleaned text."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf is required: pip install pypdf")
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        pages.append(t.strip())
    text = "\n\n".join(pages)
    # basic cleaning
    lines = [ln.strip() for ln in text.splitlines()]
    cleaned = "\n".join(ln for ln in lines if ln)
    if not cleaned.strip():
        raise ValueError("No extractable text found in PDF (scanned image? OCR needed).")
    return cleaned

def truncate_for_prompt(text: str, max_chars: int = 12000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated for prompt length ...]"
