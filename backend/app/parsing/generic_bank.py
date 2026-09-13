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

DATE_AT_START_PATTERN = re.compile(r"^\s*\d{2}[/-]\d{2}[/-]\d{4}\b")
DATE_PREFIX_PATTERN = re.compile(r"^\s*(\d{2}[/-]\d{2}[/-]\d{4})\s*")
DATE_ONLY_PATTERN = re.compile(r"^\d{2}[/-]\d{2}[/-]\d{4}$")
GENERIC_HEADER_TOKENS = ("DATE", "DESCRIPTION", "DEBIT", "CREDIT", "BALANCE")
TABLE_END_MARKERS = (
    "FEES",
    "FEE SCHEDULE",
    "INTEREST",
    "TERMS",
    "IMPORTANT INFORMATION",
    "MINIMUM PAYMENT",
    "DOCUMENT NOTES",
    "END OF TRANSACTION",
    "END OF STATEMENT",
)


@dataclass(frozen=True)
class GenericHeaderLayout:
    has_value_date: bool
    description_start: int
    debit_start: int
    credit_start: int
    balance_start: int


@dataclass
class GenericRawTransactionRow:
    page_number: int
    row_number: int
    transaction_date: str
    value_date: str | None
    description: str
    raw_debit: str
    raw_credit: str
    raw_balance: str
    matched_expected_columns: bool = True

    def append_description(self, continuation: str) -> None:
        self.description = f"{self.description} {continuation.strip()}".strip()


class GenericBankStatementParser(StatementParser):
    name = "generic_bank_statement"
    version = "1.0"

    def can_parse(self, pdf_text: PdfText) -> ParserMatch:
        header_count = self._header_count(pdf_text)
        has_transaction_details = "TRANSACTION DETAILS" in pdf_text.full_text.upper()

        raw_rows, _row_errors = self._extract_raw_rows(pdf_text)
        transaction_like_rows = 0
        for raw_row in raw_rows:
            if self._is_opening_balance_row(raw_row):
                continue
            try:
                self._parse_row(raw_row)
            except ParsingError:
                continue
            transaction_like_rows += 1

        matched = header_count > 0 and transaction_like_rows > 0
        if not matched:
            return ParserMatch(matched=False, confidence=0.0)

        confidence = 0.88
        if has_transaction_details:
            confidence += 0.04
        if transaction_like_rows >= 3:
            confidence += 0.03
        return ParserMatch(matched=True, confidence=min(confidence, 0.95))

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

        opening_balance = self._opening_balance_from_rows(raw_rows)
        if metadata.opening_balance is None:
            metadata.opening_balance = opening_balance

        for raw_row in raw_rows:
            if self._is_opening_balance_row(raw_row):
                continue
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
                    message="No transactions were found in the generic bank statement.",
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

    def _extract_raw_rows(
        self,
        pdf_text: PdfText,
    ) -> tuple[list[GenericRawTransactionRow], list[ParserErrorDetail]]:
        rows: list[GenericRawTransactionRow] = []
        errors: list[ParserErrorDetail] = []

        for page in pdf_text.pages:
            numbered_lines = [
                (row_number, raw_line)
                for row_number, raw_line in enumerate(page.text.splitlines(), start=1)
                if raw_line.strip()
            ]
            table_active = False
            layout: GenericHeaderLayout | None = None
            current_row: GenericRawTransactionRow | None = None
            previous_balance: Decimal | None = None
            index = 0

            while index < len(numbered_lines):
                row_number, raw_line = numbered_lines[index]
                line = raw_line.strip()

                if self._is_header_line(line):
                    if current_row is not None:
                        rows.append(current_row)
                        current_row = None
                    table_active = True
                    layout = self._header_layout(raw_line)
                    index += 1
                    continue

                if self._is_stacked_header_at(numbered_lines, index):
                    if current_row is not None:
                        rows.append(current_row)
                        current_row = None
                    table_active = True
                    layout = None
                    index += 5
                    continue

                if not table_active:
                    index += 1
                    continue

                if layout is None and DATE_ONLY_PATTERN.match(line):
                    if current_row is not None:
                        rows.append(current_row)
                        current_row = None
                    parsed_row, next_index, new_balance = self._parse_stacked_row(
                        numbered_lines=numbered_lines,
                        start_index=index,
                        page_number=page.page_number,
                        previous_balance=previous_balance,
                    )
                    if isinstance(parsed_row, ParserErrorDetail):
                        errors.append(parsed_row)
                    else:
                        rows.append(parsed_row)
                    previous_balance = new_balance
                    index = next_index
                    continue

                if DATE_AT_START_PATTERN.match(line):
                    if current_row is not None:
                        rows.append(current_row)
                    parsed_row = self._parse_raw_line(
                        raw_line=raw_line,
                        layout=layout,
                        page_number=page.page_number,
                        row_number=row_number,
                    )
                    if isinstance(parsed_row, ParserErrorDetail):
                        current_row = None
                        errors.append(parsed_row)
                    else:
                        current_row = parsed_row
                        previous_balance = parse_money(parsed_row.raw_balance, required=False)
                    index += 1
                    continue

                if self._is_table_end(line):
                    if current_row is not None:
                        rows.append(current_row)
                        current_row = None
                    table_active = False
                    layout = None
                    index += 1
                    continue

                if current_row is not None and not self._is_noise(line):
                    current_row.append_description(line)
                index += 1

            if current_row is not None:
                rows.append(current_row)

        return rows, errors

    def _parse_raw_line(
        self,
        *,
        raw_line: str,
        layout: GenericHeaderLayout | None,
        page_number: int,
        row_number: int,
    ) -> GenericRawTransactionRow | ParserErrorDetail:
        cells = [cell.strip() for cell in raw_line.strip().split("|")]
        if len(cells) in {5, 6}:
            if len(cells) == 5:
                transaction_date, description, raw_debit, raw_credit, raw_balance = cells
                value_date = None
            else:
                transaction_date, value_date, description, raw_debit, raw_credit, raw_balance = cells
            return GenericRawTransactionRow(
                page_number=page_number,
                row_number=row_number,
                transaction_date=transaction_date,
                value_date=value_date or None,
                description=description,
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_balance=raw_balance,
            )

        if layout is not None and "|" not in raw_line:
            row = self._parse_fixed_width_line(raw_line, layout, page_number, row_number)
            if row is not None:
                return row

        return ParserErrorDetail(
            code="malformed_transaction_row",
            message="Transaction row did not match the expected generic columns.",
            source_page=page_number,
            source_row=row_number,
        )

    def _parse_fixed_width_line(
        self,
        raw_line: str,
        layout: GenericHeaderLayout,
        page_number: int,
        row_number: int,
    ) -> GenericRawTransactionRow | None:
        date_match = DATE_PREFIX_PATTERN.match(raw_line)
        if date_match is None:
            return None

        transaction_date = date_match.group(1)
        if layout.has_value_date:
            value_date_slice = raw_line[layout.description_start - 12 : layout.description_start]
            value_date = value_date_slice.strip() or None
        else:
            value_date = None

        description_start = layout.description_start
        if len(raw_line) < layout.balance_start:
            return None

        return GenericRawTransactionRow(
            page_number=page_number,
            row_number=row_number,
            transaction_date=transaction_date,
            value_date=value_date,
            description=raw_line[description_start:layout.debit_start].strip(),
            raw_debit=raw_line[layout.debit_start:layout.credit_start].strip(),
            raw_credit=raw_line[layout.credit_start:layout.balance_start].strip(),
            raw_balance=raw_line[layout.balance_start:].strip(),
        )

    def _parse_stacked_row(
        self,
        *,
        numbered_lines: list[tuple[int, str]],
        start_index: int,
        page_number: int,
        previous_balance: Decimal | None,
    ) -> tuple[GenericRawTransactionRow | ParserErrorDetail, int, Decimal | None]:
        row_number, raw_date = numbered_lines[start_index]
        collected: list[str] = []
        next_index = start_index + 1

        while next_index < len(numbered_lines):
            _next_row_number, next_line = numbered_lines[next_index]
            line = next_line.strip()
            if DATE_ONLY_PATTERN.match(line) or self._is_header_line(line) or self._is_stacked_header_at(numbered_lines, next_index):
                break
            if self._is_table_end(line) and any(self._is_parseable_money(value) for value in collected):
                break
            if not self._is_noise(line):
                collected.append(line)
            next_index += 1

        if not collected:
            return (
                ParserErrorDetail(
                    code="malformed_transaction_row",
                    message="Stacked transaction row did not include a description or amounts.",
                    source_page=page_number,
                    source_row=row_number,
                ),
                next_index,
                previous_balance,
            )

        description_parts: list[str] = []
        money_parts: list[str] = []
        for value in collected:
            if self._is_parseable_money(value):
                money_parts.append(value)
            elif not money_parts:
                description_parts.append(value)
            else:
                description_parts.append(value)

        description = " ".join(description_parts).strip()
        if not description:
            return (
                ParserErrorDetail(
                    code="empty_description",
                    message="Description is required.",
                    source_page=page_number,
                    source_row=row_number,
                ),
                next_index,
                previous_balance,
            )

        if self._looks_like_opening_balance(description) and len(money_parts) == 1:
            balance = parse_money(money_parts[0], required=False)
            return (
                GenericRawTransactionRow(
                    page_number=page_number,
                    row_number=row_number,
                    transaction_date=raw_date.strip(),
                    value_date=None,
                    description=description,
                    raw_debit="",
                    raw_credit="",
                    raw_balance=money_parts[0],
                ),
                next_index,
                balance,
            )

        if len(money_parts) != 2:
            return (
                ParserErrorDetail(
                    code="malformed_transaction_row",
                    message="Stacked transaction row must contain amount and balance values.",
                    source_page=page_number,
                    source_row=row_number,
                ),
                next_index,
                previous_balance,
            )

        amount = parse_money(money_parts[0], required=False)
        balance = parse_money(money_parts[1], required=False)
        if amount is None or balance is None:
            return (
                ParserErrorDetail(
                    code="invalid_amount",
                    message="Stacked transaction row contains an invalid amount or balance.",
                    source_page=page_number,
                    source_row=row_number,
                ),
                next_index,
                previous_balance,
            )

        raw_debit = ""
        raw_credit = ""
        if previous_balance is not None and previous_balance - amount == balance:
            raw_debit = money_parts[0]
        elif previous_balance is not None and previous_balance + amount == balance:
            raw_credit = money_parts[0]
        else:
            return (
                ParserErrorDetail(
                    code="ambiguous_direction",
                    message="Could not infer debit or credit from stacked row balance movement.",
                    source_page=page_number,
                    source_row=row_number,
                ),
                next_index,
                previous_balance,
            )

        return (
            GenericRawTransactionRow(
                page_number=page_number,
                row_number=row_number,
                transaction_date=raw_date.strip(),
                value_date=None,
                description=description,
                raw_debit=raw_debit,
                raw_credit=raw_credit,
                raw_balance=money_parts[1],
            ),
            next_index,
            balance,
        )

    def _parse_row(self, raw_row: GenericRawTransactionRow) -> ExtractedTransaction:
        warnings: list[str] = []
        debit = parse_money(raw_row.raw_debit, required=False)
        credit = parse_money(raw_row.raw_credit, required=False)

        if debit is not None and credit is not None:
            raise ParsingError("ambiguous_direction", "Both debit and credit are present.")
        if debit is None and credit is None:
            raise ParsingError("invalid_amount", "Either debit or credit is required.")

        amount = debit if debit is not None else credit
        if amount is None:
            raise ParsingError("invalid_amount", "Amount could not be parsed.")

        balance = parse_money(raw_row.raw_balance, required=False)
        if balance is None:
            warnings.append("balance_missing")

        clean_description = " ".join(raw_row.description.split())
        if not clean_description:
            raise ParsingError("empty_description", "Description is required.")

        confidence = 1.0 if raw_row.matched_expected_columns and balance is not None else 0.9

        return ExtractedTransaction(
            transaction_date=parse_statement_date(raw_row.transaction_date),
            value_date=parse_statement_date(raw_row.value_date) if raw_row.value_date else None,
            raw_description=clean_description,
            amount=amount,
            direction=TransactionDirection.debit if debit is not None else TransactionDirection.credit,
            balance=balance,
            raw_debit=raw_row.raw_debit or None,
            raw_credit=raw_row.raw_credit or None,
            source_page=raw_row.page_number,
            source_row=raw_row.row_number,
            extraction_confidence=confidence,
            warnings=warnings,
        )

    def _extract_metadata(self, text: str) -> StatementMetadata:
        period_match = re.search(
            r"Statement Period:\s*(\d{2}[/-]\d{2}[/-]\d{4})\s*-\s*(\d{2}[/-]\d{2}[/-]\d{4})",
            text,
            re.IGNORECASE,
        )
        return StatementMetadata(
            bank_name=self._match_text(text, r"Bank:\s*(.+)"),
            masked_account_number=self._match_text(text, r"Account:\s*([Xx*\d-]+)"),
            statement_start_date=(
                parse_statement_date(period_match.group(1)) if period_match else None
            ),
            statement_end_date=(
                parse_statement_date(period_match.group(2)) if period_match else None
            ),
            opening_balance=self._match_money(text, r"Opening Balance:\s*([^\n]+)"),
            closing_balance=self._match_money(text, r"Closing Balance:\s*([^\n]+)"),
            currency=(self._match_text(text, r"Currency:\s*([A-Z]{3})") or "INR"),
        )

    def _opening_balance_from_rows(
        self,
        rows: list[GenericRawTransactionRow],
    ) -> Decimal | None:
        for row in rows:
            if self._is_opening_balance_row(row):
                return parse_money(row.raw_balance, required=False)
        return None

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

    def _row_candidate(self, raw_line: str, layout: GenericHeaderLayout | None) -> bool:
        if not DATE_AT_START_PATTERN.match(raw_line):
            return False
        parsed = self._parse_raw_line(
            raw_line=raw_line,
            layout=layout,
            page_number=0,
            row_number=0,
        )
        if isinstance(parsed, ParserErrorDetail):
            return False
        try:
            if self._is_opening_balance_row(parsed):
                return parse_money(parsed.raw_balance, required=False) is not None
            debit = parse_money(parsed.raw_debit, required=False)
            credit = parse_money(parsed.raw_credit, required=False)
            balance = parse_money(parsed.raw_balance, required=False)
        except ParsingError:
            return False
        return balance is not None and ((debit is None) != (credit is None))

    def _is_header_line(self, line: str) -> bool:
        normalized = re.sub(r"[^A-Z]+", " ", line.upper())
        return all(token in normalized.split() for token in GENERIC_HEADER_TOKENS)

    def _is_stacked_header_at(
        self,
        numbered_lines: list[tuple[int, str]],
        index: int,
    ) -> bool:
        if index + 4 >= len(numbered_lines):
            return False
        window = [
            re.sub(r"[^A-Z]+", " ", numbered_lines[index + offset][1].upper()).strip()
            for offset in range(5)
        ]
        return (
            window[0] == "DATE"
            and window[1] == "DESCRIPTION"
            and window[2].startswith("DEBIT")
            and window[3].startswith("CREDIT")
            and window[4].startswith("BALANCE")
        )

    def _header_layout(self, raw_line: str) -> GenericHeaderLayout | None:
        upper = raw_line.upper()
        description_match = re.search(r"\bDESCRIPTION\b", upper)
        debit_match = re.search(r"\bDEBIT\b", upper)
        credit_match = re.search(r"\bCREDIT\b", upper)
        balance_match = re.search(r"\bBALANCE\b", upper)
        if not (description_match and debit_match and credit_match and balance_match):
            return None
        return GenericHeaderLayout(
            has_value_date=bool(re.search(r"\bVALUE\s+DATE\b", upper)),
            description_start=description_match.start(),
            debit_start=debit_match.start(),
            credit_start=credit_match.start(),
            balance_start=balance_match.start(),
        )

    def _is_opening_balance_row(self, row: GenericRawTransactionRow) -> bool:
        return (
            self._looks_like_opening_balance(row.description)
            and not row.raw_debit.strip()
            and not row.raw_credit.strip()
            and bool(row.raw_balance.strip())
        )

    def _looks_like_opening_balance(self, description: str) -> bool:
        return "OPENING BALANCE" in description.upper()

    def _is_table_end(self, line: str) -> bool:
        upper = line.upper()
        return any(marker in upper for marker in TABLE_END_MARKERS)

    def _is_noise(self, line: str) -> bool:
        upper = line.upper()
        return (
            upper.startswith("PAGE ")
            or upper.startswith("GENERATED ON:")
            or upper.startswith("CLOSING BALANCE:")
            or upper.startswith("CURRENCY:")
            or upper.startswith("BANK:")
            or upper.startswith("ACCOUNT:")
            or upper.startswith("STATEMENT PERIOD:")
        )

    def _header_count(self, pdf_text: PdfText) -> int:
        count = 0
        for page in pdf_text.pages:
            numbered_lines = [
                (row_number, raw_line)
                for row_number, raw_line in enumerate(page.text.splitlines(), start=1)
                if raw_line.strip()
            ]
            for index, (_row_number, raw_line) in enumerate(numbered_lines):
                if self._is_header_line(raw_line.strip()) or self._is_stacked_header_at(numbered_lines, index):
                    count += 1
        return count

    def _is_parseable_money(self, value: str) -> bool:
        try:
            return parse_money(value, required=False) is not None
        except ParsingError:
            return False

    def _match_text(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.IGNORECASE)
        if match is None:
            return None
        return match.group(1).strip()

    def _match_money(self, text: str, pattern: str) -> Decimal | None:
        value = self._match_text(text, pattern)
        return parse_money(value, required=False)
