import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.parsing.base import ParserMatch, StatementParser
from app.parsing.dates import parse_statement_date
from app.parsing.exceptions import ParserErrorDetail, ParsingError
from app.parsing.money import parse_money
from app.parsing.pdf import PdfText
from app.schemas.parsing import (
    ExtractedTransaction,
    ParseResult,
    ParseResultStatus,
    ParserIssue,
    StatementMetadata,
    TransactionDirection,
)

PARSER_MARKER = "ARTHADRISHTI SYNTHETIC BANK STATEMENT"
HEADER_PREFIX = "Date | Value Date | Description | Debit | Credit | Balance"
DATE_PREFIX_PATTERN = re.compile(r"^\d{2}[/-]\d{2}[/-]\d{4}\s*\|")


@dataclass
class RawTransactionRow:
    page_number: int
    row_number: int
    cells: list[str]

    def append_description(self, continuation: str) -> None:
        self.cells[2] = f"{self.cells[2]} {continuation.strip()}".strip()


class SyntheticBankStatementParser(StatementParser):
    name = "synthetic_bank_statement"
    version = "1.0"

    def can_parse(self, pdf_text: PdfText) -> ParserMatch:
        text = pdf_text.full_text
        has_marker = PARSER_MARKER in text
        has_header = HEADER_PREFIX in text
        return ParserMatch(matched=has_marker and has_header, confidence=1.0)

    def extract(self, document_id: UUID, pdf_text: PdfText) -> ParseResult:
        metadata = self._extract_metadata(pdf_text.full_text)
        raw_rows, row_errors = self._extract_raw_rows(pdf_text)
        transactions: list[ExtractedTransaction] = []
        errors = [
            ParserIssue(
                code=error.code,
                message=error.message,
                source_page=error.source_page,
                source_row=error.source_row,
            )
            for error in row_errors
        ]

        for raw_row in raw_rows:
            try:
                transactions.append(self._parse_row(raw_row))
            except ParsingError as exc:
                errors.append(
                    ParserIssue(
                        code=exc.detail.code,
                        message=exc.detail.message,
                        source_page=raw_row.page_number,
                        source_row=raw_row.row_number,
                    )
                )

        warnings = self._balance_warnings(metadata, transactions)
        if not transactions:
            errors.append(
                ParserIssue(
                    code="no_transactions_found",
                    message="No transactions were found in the supported statement.",
                )
            )
            status = ParseResultStatus.failed
        elif errors:
            status = ParseResultStatus.partial_success
        else:
            status = ParseResultStatus.success

        return ParseResult(
            parser_name=self.name,
            parser_version=self.version,
            document_id=document_id,
            status=status,
            metadata=metadata,
            transactions=transactions,
            warnings=warnings,
            errors=errors,
        )

    def _extract_metadata(self, text: str) -> StatementMetadata:
        bank_name = self._match_text(text, r"Bank:\s*(.+)")
        masked_account_number = self._match_text(text, r"Account:\s*([Xx*\d-]+)")
        period_match = re.search(
            r"Statement Period:\s*(\d{2}[/-]\d{2}[/-]\d{4})\s*-\s*(\d{2}[/-]\d{2}[/-]\d{4})",
            text,
        )
        opening_balance = self._match_money(text, r"Opening Balance:\s*([^\n]+)")
        closing_balance = self._match_money(text, r"Closing Balance:\s*([^\n]+)")
        currency = self._match_text(text, r"Currency:\s*([A-Z]{3})") or "INR"

        return StatementMetadata(
            bank_name=bank_name,
            masked_account_number=masked_account_number,
            statement_start_date=(
                parse_statement_date(period_match.group(1)) if period_match else None
            ),
            statement_end_date=(
                parse_statement_date(period_match.group(2)) if period_match else None
            ),
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            currency=currency,
        )

    def _extract_raw_rows(
        self,
        pdf_text: PdfText,
    ) -> tuple[list[RawTransactionRow], list[ParserErrorDetail]]:
        rows: list[RawTransactionRow] = []
        errors: list[ParserErrorDetail] = []
        current_row: RawTransactionRow | None = None

        for page in pdf_text.pages:
            for row_number, raw_line in enumerate(page.text.splitlines(), start=1):
                line = raw_line.strip()
                if not line or self._is_noise(line):
                    continue

                if DATE_PREFIX_PATTERN.match(line):
                    if current_row is not None:
                        rows.append(current_row)

                    cells = [cell.strip() for cell in line.split("|")]
                    if len(cells) != 6:
                        current_row = None
                        errors.append(
                            ParserErrorDetail(
                                code="malformed_transaction_row",
                                message="Transaction row did not match the expected six columns.",
                                source_page=page.page_number,
                                source_row=row_number,
                            )
                        )
                        continue

                    current_row = RawTransactionRow(
                        page_number=page.page_number,
                        row_number=row_number,
                        cells=cells,
                    )
                    continue

                if current_row is not None:
                    current_row.append_description(line)

        if current_row is not None:
            rows.append(current_row)

        return rows, errors

    def _parse_row(self, raw_row: RawTransactionRow) -> ExtractedTransaction:
        (
            transaction_date,
            value_date,
            description,
            raw_debit,
            raw_credit,
            raw_balance,
        ) = raw_row.cells

        warnings: list[str] = []
        debit = parse_money(raw_debit, required=False)
        credit = parse_money(raw_credit, required=False)

        if debit is not None and credit is not None:
            raise ParsingError("ambiguous_direction", "Both debit and credit are present.")
        if debit is None and credit is None:
            raise ParsingError("invalid_amount", "Either debit or credit is required.")

        direction = TransactionDirection.debit if debit is not None else TransactionDirection.credit
        amount = debit if debit is not None else credit
        if amount is None:
            raise ParsingError("invalid_amount", "Amount could not be parsed.")

        balance = parse_money(raw_balance, required=False)
        if balance is None:
            warnings.append("balance_missing")

        clean_description = " ".join(description.split())
        if not clean_description:
            raise ParsingError("empty_description", "Description is required.")

        confidence = 1.0 if balance is not None and not warnings else 0.9

        return ExtractedTransaction(
            transaction_date=parse_statement_date(transaction_date),
            value_date=parse_statement_date(value_date) if value_date else None,
            raw_description=clean_description,
            amount=amount,
            direction=direction,
            balance=balance,
            raw_debit=raw_debit or None,
            raw_credit=raw_credit or None,
            source_page=raw_row.page_number,
            source_row=raw_row.row_number,
            extraction_confidence=confidence,
            warnings=warnings,
        )

    def _balance_warnings(
        self,
        metadata: StatementMetadata,
        transactions: list[ExtractedTransaction],
    ) -> list[str]:
        if metadata.opening_balance is None:
            return []

        warnings: list[str] = []
        previous_balance = metadata.opening_balance
        for transaction in transactions:
            if transaction.balance is None:
                continue

            expected = (
                previous_balance - transaction.amount
                if transaction.direction == TransactionDirection.debit
                else previous_balance + transaction.amount
            )
            if expected != transaction.balance:
                warnings.append(
                    f"balance_mismatch_page_{transaction.source_page}_row_{transaction.source_row}"
                )
            previous_balance = transaction.balance

        if metadata.closing_balance is not None and previous_balance != metadata.closing_balance:
            warnings.append("closing_balance_mismatch")

        return warnings

    def _is_noise(self, line: str) -> bool:
        return (
            line == PARSER_MARKER
            or line == HEADER_PREFIX
            or line.startswith("Bank:")
            or line.startswith("Account:")
            or line.startswith("Statement Period:")
            or line.startswith("Opening Balance:")
            or line.startswith("Closing Balance:")
            or line.startswith("Currency:")
            or line.startswith("Page ")
            or line.startswith("Generated On:")
            or line.startswith("End of statement")
        )

    def _match_text(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text)
        if match is None:
            return None
        return match.group(1).strip()

    def _match_money(self, text: str, pattern: str) -> Decimal | None:
        value = self._match_text(text, pattern)
        return parse_money(value, required=False)
