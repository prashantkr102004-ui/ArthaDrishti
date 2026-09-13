from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz

from app.parsing.exceptions import ParsingError


@dataclass(frozen=True)
class PdfPageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class PdfText:
    pages: list[PdfPageText]

    @property
    def full_text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    @property
    def meaningful_text_length(self) -> int:
        return len("".join(self.full_text.split()))


def extract_pdf_text(path: Path) -> PdfText:
    try:
        with fitz.open(path) as pdf:
            if pdf.is_encrypted or pdf.needs_pass:
                raise ParsingError(
                    "password_protected_pdf",
                    "Password-protected PDFs are not supported yet.",
                )

            pages = [
                PdfPageText(page_number=index + 1, text=page.get_text("text"))
                for index, page in enumerate(pdf)
            ]
    except ParsingError:
        raise
    except fitz.FileDataError as exc:
        raise ParsingError(
            "pdf_text_extraction_failed",
            "PDF text could not be extracted.",
        ) from exc
    except Exception as exc:
        raise ParsingError(
            "pdf_text_extraction_failed",
            "PDF text extraction failed.",
        ) from exc

    extracted = PdfText(pages=pages)
    if extracted.meaningful_text_length == 0:
        raise ParsingError(
            "ocr_required",
            "This PDF has no extractable text and may require OCR.",
        )
    if extracted.meaningful_text_length < 20:
        raise ParsingError(
            "no_extractable_text",
            "This PDF does not contain enough extractable text to parse.",
        )

    return extracted
