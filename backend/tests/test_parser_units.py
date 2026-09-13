from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.parsing.dates import parse_statement_date
from app.parsing.exceptions import ParsingError
from app.parsing.generic_bank import GenericBankStatementParser
from app.parsing.money import parse_money
from app.parsing.pdf import PdfPageText, PdfText
from app.parsing.registry import select_parser
from app.parsing.synthetic_bank import SyntheticBankStatementParser
from app.schemas.parsing import ParseResultStatus, TransactionDirection
from tests.fixtures.statements import (
    GENERIC_BANK_STATEMENT_INFO_PAGE,
    GENERIC_BANK_STATEMENT_TEXT,
    GENERIC_MALFORMED_TEXT,
    GENERIC_STACKED_BANK_STATEMENT_TEXT,
    GENERIC_STACKED_INFO_PAGE,
    GENERIC_UNRELATED_TEXT_WITH_SIGNALS,
    MALFORMED_SYNTHETIC_TEXT,
    SUPPORTED_SYNTHETIC_TEXT,
    SUPPORTED_SYNTHETIC_TEXT_PAGE_TWO,
)


def test_parse_money_handles_supported_formats_without_float_precision() -> None:
    assert parse_money("1,234.56") == Decimal("1234.56")
    assert parse_money("\u20b91,234.56") == Decimal("1234.56")
    assert parse_money("1234.56") == Decimal("1234.56")
    assert parse_money("1,00,000.00") == Decimal("100000.00")
    assert parse_money("500") == Decimal("500")
    assert parse_money("", required=False) is None


def test_parse_money_rejects_malformed_values() -> None:
    with pytest.raises(ParsingError, match="Invalid amount"):
        parse_money("12.345")

    with pytest.raises(ParsingError, match="Amounts must be positive"):
        parse_money("-500.00")


def test_parse_statement_date_is_deterministic_day_first() -> None:
    assert parse_statement_date("01/08/2026") == date(2026, 8, 1)
    assert parse_statement_date("31-08-2026") == date(2026, 8, 31)

    with pytest.raises(ParsingError, match="Invalid date"):
        parse_statement_date("08/31/2026")


def test_synthetic_parser_extracts_exact_expected_transactions() -> None:
    parser = SyntheticBankStatementParser()
    pdf_text = PdfText(
        pages=[
            PdfPageText(page_number=1, text=SUPPORTED_SYNTHETIC_TEXT),
            PdfPageText(page_number=2, text=SUPPORTED_SYNTHETIC_TEXT_PAGE_TWO),
        ]
    )

    result = parser.extract(uuid4(), pdf_text)

    assert result.status == ParseResultStatus.success
    assert result.metadata.bank_name == "Example Cooperative Bank"
    assert result.metadata.masked_account_number == "XXXX1234"
    assert result.metadata.statement_start_date == date(2026, 8, 1)
    assert result.metadata.statement_end_date == date(2026, 8, 31)
    assert result.metadata.opening_balance == Decimal("10000.00")
    assert result.metadata.closing_balance == Decimal("26250.75")
    assert result.transaction_count == 7
    assert not result.errors
    assert not result.warnings

    expected = [
        (date(2026, 8, 1), "Salary Credit", Decimal("50000.00"), TransactionDirection.credit, Decimal("60000.00")),
        (date(2026, 8, 2), "Grocery Store", Decimal("1234.56"), TransactionDirection.debit, Decimal("58765.44")),
        (date(2026, 8, 3), "ATM Withdrawal Cash", Decimal("500"), TransactionDirection.debit, Decimal("58265.44")),
        (date(2026, 8, 4), "Online Transfer NEFT ABC Ref: ABC123", Decimal("1000.00"), TransactionDirection.debit, Decimal("57265.44")),
        (date(2026, 8, 15), "Rent Payment", Decimal("25000.00"), TransactionDirection.debit, Decimal("32265.44")),
        (date(2026, 8, 20), "Refund", Decimal("2985.31"), TransactionDirection.credit, Decimal("35250.75")),
        (date(2026, 8, 31), "Utilities", Decimal("9000.00"), TransactionDirection.debit, Decimal("26250.75")),
    ]
    actual = [
        (
            transaction.transaction_date,
            transaction.raw_description,
            transaction.amount,
            transaction.direction,
            transaction.balance,
        )
        for transaction in result.transactions
    ]
    assert actual == expected


def test_synthetic_parser_reports_malformed_rows_without_discarding_good_rows() -> None:
    parser = SyntheticBankStatementParser()
    result = parser.extract(
        uuid4(),
        PdfText(pages=[PdfPageText(page_number=1, text=MALFORMED_SYNTHETIC_TEXT)]),
    )

    assert result.status == ParseResultStatus.partial_success
    assert result.transaction_count == 2
    assert {error.code for error in result.errors} == {
        "invalid_amount",
        "malformed_transaction_row",
    }


def test_generic_parser_is_selected_for_generic_statement_content() -> None:
    pdf_text = PdfText(
        pages=[
            PdfPageText(page_number=1, text=GENERIC_BANK_STATEMENT_TEXT),
            PdfPageText(page_number=2, text=GENERIC_BANK_STATEMENT_INFO_PAGE),
        ]
    )

    parser = select_parser(pdf_text)

    assert isinstance(parser, GenericBankStatementParser)
    assert parser.can_parse(pdf_text).confidence >= 0.9


def test_generic_parser_does_not_select_unrelated_pdf_with_header_words() -> None:
    parser = GenericBankStatementParser()
    pdf_text = PdfText(
        pages=[PdfPageText(page_number=1, text=GENERIC_UNRELATED_TEXT_WITH_SIGNALS)]
    )

    assert parser.can_parse(pdf_text).matched is False
    assert select_parser(pdf_text) is None


def test_generic_parser_extracts_expected_rows_and_skips_opening_balance() -> None:
    parser = GenericBankStatementParser()
    result = parser.extract(
        uuid4(),
        PdfText(
            pages=[
                PdfPageText(page_number=1, text=GENERIC_BANK_STATEMENT_TEXT),
                PdfPageText(page_number=2, text=GENERIC_BANK_STATEMENT_INFO_PAGE),
            ]
        ),
    )

    assert result.status == ParseResultStatus.success
    assert result.parser_name == "generic_bank_statement"
    assert result.metadata.opening_balance == Decimal("35000.00")
    assert result.metadata.currency == "INR"
    assert result.transaction_count == 7
    assert not result.errors
    assert not result.warnings
    assert all(transaction.source_page == 1 for transaction in result.transactions)
    assert all("late-payment fee" not in transaction.raw_description.lower() for transaction in result.transactions)

    expected = [
        (
            date(2026, 8, 2),
            "SALARY CREDIT - DEMO TECH PVT LTD",
            Decimal("55000.00"),
            TransactionDirection.credit,
            Decimal("90000.00"),
        ),
        (
            date(2026, 8, 3),
            "UPI - SWIGGY FOOD ORDER",
            Decimal("650.00"),
            TransactionDirection.debit,
            Decimal("89350.00"),
        ),
        (
            date(2026, 8, 4),
            "UPI - UBER TRIP",
            Decimal("420.00"),
            TransactionDirection.debit,
            Decimal("88930.00"),
        ),
        (
            date(2026, 8, 5),
            "NETFLIX SUBSCRIPTION",
            Decimal("649.00"),
            TransactionDirection.debit,
            Decimal("88281.00"),
        ),
        (
            date(2026, 8, 6),
            "MUTUAL FUND SIP",
            Decimal("5000.00"),
            TransactionDirection.debit,
            Decimal("83281.00"),
        ),
        (
            date(2026, 8, 7),
            "AMAZON REFUND",
            Decimal("999.00"),
            TransactionDirection.credit,
            Decimal("84280.00"),
        ),
        (
            date(2026, 8, 8),
            "UNUSUAL ELECTRONICS PURCHASE",
            Decimal("18500.00"),
            TransactionDirection.debit,
            Decimal("65780.00"),
        ),
    ]
    actual = [
        (
            transaction.transaction_date,
            transaction.raw_description,
            transaction.amount,
            transaction.direction,
            transaction.balance,
        )
        for transaction in result.transactions
    ]
    assert actual == expected


def test_generic_parser_extracts_stacked_pdf_text_layout() -> None:
    parser = GenericBankStatementParser()
    pdf_text = PdfText(
        pages=[
            PdfPageText(page_number=1, text=GENERIC_STACKED_BANK_STATEMENT_TEXT),
            PdfPageText(page_number=2, text=GENERIC_STACKED_INFO_PAGE),
        ]
    )

    assert parser.can_parse(pdf_text).matched is True
    assert parser.can_parse(pdf_text).confidence >= 0.9

    result = parser.extract(uuid4(), pdf_text)

    assert result.status == ParseResultStatus.success
    assert result.metadata.opening_balance == Decimal("35000.00")
    assert result.transaction_count == 23
    assert not result.errors
    assert not result.warnings
    assert all(transaction.source_page == 1 for transaction in result.transactions)
    assert all("late-payment fee" not in transaction.raw_description.lower() for transaction in result.transactions)

    by_date_and_description = {
        (transaction.transaction_date, transaction.raw_description): transaction
        for transaction in result.transactions
    }
    salary = by_date_and_description[(date(2026, 8, 2), "SALARY CREDIT - DEMO TECH PVT LTD")]
    swiggy = by_date_and_description[(date(2026, 8, 3), "UPI - SWIGGY FOOD ORDER")]
    netflix = by_date_and_description[(date(2026, 8, 6), "NETFLIX SUBSCRIPTION")]
    mutual_fund = by_date_and_description[(date(2026, 8, 15), "MUTUAL FUND SIP")]
    amazon_refund = by_date_and_description[(date(2026, 8, 21), "REFUND - AMAZON")]
    electronics = by_date_and_description[(date(2026, 8, 30), "UNUSUAL ELECTRONICS PURCHASE")]
    interest = by_date_and_description[(date(2026, 8, 31), "INTEREST CREDIT")]
    assert salary.direction == TransactionDirection.credit
    assert salary.amount == Decimal("55000.00")
    assert swiggy.direction == TransactionDirection.debit
    assert swiggy.amount == Decimal("650.00")
    assert netflix.direction == TransactionDirection.debit
    assert netflix.amount == Decimal("649.00")
    assert mutual_fund.direction == TransactionDirection.debit
    assert mutual_fund.amount == Decimal("5000.00")
    assert amazon_refund.direction == TransactionDirection.credit
    assert amazon_refund.amount == Decimal("999.00")
    assert electronics.direction == TransactionDirection.debit
    assert electronics.amount == Decimal("18500.00")
    assert interest.direction == TransactionDirection.credit
    assert interest.amount == Decimal("125.00")


def test_generic_parser_reports_malformed_rows_without_discarding_good_rows() -> None:
    parser = GenericBankStatementParser()
    result = parser.extract(
        uuid4(),
        PdfText(pages=[PdfPageText(page_number=1, text=GENERIC_MALFORMED_TEXT)]),
    )

    assert result.status == ParseResultStatus.partial_success
    assert result.transaction_count == 1
    assert {error.code for error in result.errors} == {
        "invalid_amount",
        "malformed_transaction_row",
    }
