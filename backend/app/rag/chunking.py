from dataclasses import dataclass

from app.core.config import settings
from app.parsing.pdf import PdfText


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page_number: int
    text: str

    @property
    def character_count(self) -> int:
        return len(self.text)


def clean_document_text(text: str) -> str:
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        cleaned = " ".join(line.split())
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def chunk_pdf_text(
    pdf_text: PdfText,
    *,
    chunk_size_chars: int | None = None,
    overlap_chars: int | None = None,
) -> list[TextChunk]:
    chunk_size = chunk_size_chars or settings.rag_chunk_size_chars
    overlap = overlap_chars if overlap_chars is not None else settings.rag_chunk_overlap_chars
    if chunk_size < 200:
        raise ValueError("RAG chunk size must be at least 200 characters.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("RAG chunk overlap must be non-negative and smaller than chunk size.")

    chunks: list[TextChunk] = []
    next_index = 0
    for page in pdf_text.pages:
        page_text = clean_document_text(page.text)
        if not page_text:
            continue
        paragraphs = _paragraphs(page_text)
        buffer = ""
        for paragraph in paragraphs:
            if not buffer:
                buffer = paragraph
                continue
            candidate = f"{buffer}\n{paragraph}"
            if len(candidate) <= chunk_size:
                buffer = candidate
                continue
            chunks.append(TextChunk(next_index, page.page_number, buffer))
            next_index += 1
            buffer = _overlap_tail(buffer, overlap)
            buffer = f"{buffer}\n{paragraph}" if buffer else paragraph

        if buffer:
            while len(buffer) > chunk_size:
                head = buffer[:chunk_size].strip()
                chunks.append(TextChunk(next_index, page.page_number, head))
                next_index += 1
                buffer = f"{_overlap_tail(head, overlap)}{buffer[chunk_size:]}"
            if buffer.strip():
                chunks.append(TextChunk(next_index, page.page_number, buffer.strip()))
                next_index += 1

    return chunks


def _paragraphs(text: str) -> list[str]:
    raw_paragraphs = text.split("\n")
    return [paragraph.strip() for paragraph in raw_paragraphs if paragraph.strip()]


def _overlap_tail(text: str, overlap_chars: int) -> str:
    if overlap_chars == 0:
        return ""
    return text[-overlap_chars:].strip()
