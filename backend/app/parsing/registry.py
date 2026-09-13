from app.parsing.base import StatementParser
from app.parsing.generic_bank import GenericBankStatementParser
from app.parsing.pdf import PdfText
from app.parsing.synthetic_bank import SyntheticBankStatementParser

PARSERS: tuple[StatementParser, ...] = (
    SyntheticBankStatementParser(),
    GenericBankStatementParser(),
)


def select_parser(pdf_text: PdfText) -> StatementParser | None:
    matches = [
        (parser, parser.can_parse(pdf_text))
        for parser in PARSERS
    ]
    matched = [
        (parser, match)
        for parser, match in matches
        if match.matched
    ]
    if not matched:
        return None

    return max(matched, key=lambda item: item[1].confidence)[0]
