from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.parsing.pdf import PdfText
from app.schemas.parsing import ParseResult


@dataclass(frozen=True)
class ParserMatch:
    matched: bool
    confidence: float = 0.0


class StatementParser(ABC):
    name: str
    version: str

    @abstractmethod
    def can_parse(self, pdf_text: PdfText) -> ParserMatch:
        raise NotImplementedError

    @abstractmethod
    def extract(self, document_id: UUID, pdf_text: PdfText) -> ParseResult:
        raise NotImplementedError
