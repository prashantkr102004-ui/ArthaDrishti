import pymupdf as fitz


SUPPORTED_SYNTHETIC_TEXT = """ARTHADRISHTI SYNTHETIC BANK STATEMENT
Bank: Example Cooperative Bank
Account: XXXX1234
Statement Period: 01/08/2026 - 31/08/2026
Opening Balance: INR 10000.00
Closing Balance: INR 26250.75
Currency: INR
Date | Value Date | Description | Debit | Credit | Balance
01/08/2026 | 01/08/2026 | Salary Credit | | 50000.00 | 60000.00
02/08/2026 | 02/08/2026 | Grocery Store | 1234.56 | | 58765.44
03/08/2026 | 03/08/2026 | ATM Withdrawal Cash | 500 | | 58265.44
04/08/2026 | 04/08/2026 | Online Transfer NEFT ABC | 1000.00 | | 57265.44
Ref: ABC123
15/08/2026 | 15/08/2026 | Rent Payment | 25000.00 | | 32265.44
20/08/2026 | 20/08/2026 | Refund | | 2985.31 | 35250.75
31/08/2026 | 31/08/2026 | Utilities | 9000.00 | | 26250.75
Generated On: 01/09/2026
End of statement
"""

SUPPORTED_SYNTHETIC_TEXT_PAGE_TWO = """ARTHADRISHTI SYNTHETIC BANK STATEMENT
Page 2
Date | Value Date | Description | Debit | Credit | Balance
"""

MALFORMED_SYNTHETIC_TEXT = """ARTHADRISHTI SYNTHETIC BANK STATEMENT
Bank: Example Cooperative Bank
Account: XXXX1234
Statement Period: 01/08/2026 - 31/08/2026
Opening Balance: INR 10000.00
Closing Balance: INR 26250.75
Currency: INR
Date | Value Date | Description | Debit | Credit | Balance
01/08/2026 | 01/08/2026 | Salary Credit | | 50000.00 | 60000.00
05/08/2026 | 05/08/2026 | Broken Amount | not-money | | 60000.00
07/08/2026 | Missing Columns | 100.00
02/08/2026 | 02/08/2026 | Grocery Store | 1234.56 | | 58765.44
"""

UNSUPPORTED_TEXT = """Example Bank Statement
This is a valid text-based PDF, but it does not use the supported
ArthaDrishti synthetic statement layout.
Date Description Amount
2026-08-01 Salary 50000
"""

OVERLAPPING_SYNTHETIC_TEXT = """ARTHADRISHTI SYNTHETIC BANK STATEMENT
Bank: Example Cooperative Bank
Account: XXXX1234
Statement Period: 20/08/2026 - 01/09/2026
Opening Balance: INR 32265.44
Closing Balance: INR 35260.75
Currency: INR
Date | Value Date | Description | Debit | Credit | Balance
20/08/2026 | 20/08/2026 | Refund | | 2985.31 | 35250.75
01/09/2026 | 01/09/2026 | Interest Credit | | 10.00 | 35260.75
Generated On: 02/09/2026
End of statement
"""

SAME_DAY_DISTINCT_SYNTHETIC_TEXT = """ARTHADRISHTI SYNTHETIC BANK STATEMENT
Bank: Example Cooperative Bank
Account: XXXX1234
Statement Period: 10/09/2026 - 10/09/2026
Opening Balance: INR 1000.00
Closing Balance: INR 0.00
Currency: INR
Date | Value Date | Description | Debit | Credit | Balance
10/09/2026 | 10/09/2026 | ATM Withdrawal Cash | 500.00 | | 500.00
10/09/2026 | 10/09/2026 | ATM Withdrawal Cash | 500.00 | | 0.00
Generated On: 11/09/2026
End of statement
"""

GENERIC_BANK_STATEMENT_TEXT = """ArthaDrishti Demo Bank Statement
Bank: Artha Demo Bank
Account: XXXX-9876
Statement Period: 01-08-2026 - 31-08-2026
Currency: INR
Transaction Details
Date | Description | Debit (INR) | Credit (INR) | Balance (INR)
01-08-2026 | OPENING BALANCE | | | 35,000.00
02-08-2026 | SALARY CREDIT - DEMO TECH PVT LTD | | 55,000.00 | 90,000.00
03-08-2026 | UPI - SWIGGY FOOD ORDER | 650.00 | | 89,350.00
04-08-2026 | UPI - UBER TRIP | 420.00 | | 88,930.00
05-08-2026 | NETFLIX SUBSCRIPTION | 649.00 | | 88,281.00
06-08-2026 | MUTUAL FUND SIP | 5,000.00 | | 83,281.00
07-08-2026 | AMAZON REFUND | | 999.00 | 84,280.00
08-08-2026 | UNUSUAL ELECTRONICS PURCHASE | 18,500.00 | | 65,780.00
End of Transaction Details
"""

GENERIC_BANK_STATEMENT_INFO_PAGE = """Important Information
Late-payment fee: INR 500.00
Interest rate: 3.5% per month
Minimum payment is 5% of outstanding balance.
Cash withdrawal charges may apply.
This page is document text for search and must not be parsed as transactions.
09-08-2026 This informational line has a date and INR 500.00 fee but no transaction table.
"""

GENERIC_STACKED_BANK_STATEMENT_TEXT = """ArthaDrishti Demo Bank Statement
SYNTHETIC TEST DOCUMENT - NO REAL BANK OR CUSTOMER DATA
Customer Name
Demo User
Bank
Sample National Bank
Account Type
Savings Account
Account Number
XXXX XXXX 1234
Statement Period
01 Aug 2026 - 31 Aug 2026
Currency
INR
Transaction Details
Date
Description
Debit (INR)
Credit (INR)
Balance (INR)
01-08-2026
OPENING BALANCE
35,000.00
02-08-2026
SALARY CREDIT - DEMO TECH PVT LTD
55,000.00
90,000.00
03-08-2026
UPI - SWIGGY FOOD ORDER
650.00
89,350.00
04-08-2026
UPI - UBER TRIP
420.00
88,930.00
05-08-2026
RENT TRANSFER - DEMO LANDLORD
15,000.00
73,930.00
06-08-2026
NETFLIX SUBSCRIPTION
649.00
73,281.00
07-08-2026
SPOTIFY SUBSCRIPTION
119.00
73,162.00
08-08-2026
ELECTRICITY BILL PAYMENT
1,850.00
71,312.00
09-08-2026
UPI - BIGBASKET GROCERIES
2,340.00
68,972.00
10-08-2026
ATM CASH WITHDRAWAL
2,000.00
66,972.00
11-08-2026
UPI - APOLLO PHARMACY
780.00
66,192.00
12-08-2026
UPI - AMAZON SHOPPING
3,499.00
62,693.00
14-08-2026
METRO CARD RECHARGE
500.00
62,193.00
15-08-2026
MUTUAL FUND SIP
5,000.00
57,193.00
17-08-2026
UPI - CAFE COFFEE DAY
325.00
56,868.00
18-08-2026
MOBILE BILL PAYMENT
799.00
56,069.00
20-08-2026
UPI - BOOKMYSHOW
850.00
55,219.00
21-08-2026
REFUND - AMAZON
999.00
56,218.00
23-08-2026
FLIGHT BOOKING - DEMO AIR
6,800.00
49,418.00
25-08-2026
UPI - SWIGGY FOOD ORDER
720.00
48,698.00
27-08-2026
UPI - UBER TRIP
390.00
48,308.00
29-08-2026
GYM MEMBERSHIP
1,200.00
47,108.00
30-08-2026
UNUSUAL ELECTRONICS PURCHASE
18,500.00
28,608.00
31-08-2026
INTEREST CREDIT
125.00
28,733.00
"""

GENERIC_STACKED_INFO_PAGE = """Statement Information & Terms
This page exists to test ArthaDrishti's document search and RAG capabilities. All values below are fictional.
Item
Demo Terms
Minimum balance
INR 10,000
Annual debit-card fee
INR 499
Late-payment fee
INR 500 where applicable
Cash withdrawal charge
INR 25 after the free monthly limit
Interest rate
3.5% per annum on eligible savings balance
Minimum payment clause
For credit products, minimum payment is 5% of the outstanding balance or INR 500, whichever is higher.
Suggested test questions
- What late-payment fee is mentioned in this document?
- What annual debit-card fee is listed?
"""

GENERIC_UNRELATED_TEXT_WITH_SIGNALS = """Financial Education Notes
This valid PDF mentions Date, Description, Debit, Credit, and Balance in prose.
It is not a bank statement transaction table.
Date Description Debit Credit Balance are glossary terms here only.
"""

GENERIC_MALFORMED_TEXT = """ArthaDrishti Demo Bank Statement
Transaction Details
Date | Description | Debit (INR) | Credit (INR) | Balance (INR)
01-08-2026 | OPENING BALANCE | | | 35,000.00
02-08-2026 | SALARY CREDIT - DEMO TECH PVT LTD | | 55,000.00 | 90,000.00
03-08-2026 | BROKEN AMOUNT | not-money | | 89,350.00
04-08-2026 | MISSING COLUMNS | 420.00
"""


def make_pdf_from_pages(pages: list[str]) -> bytes:
    document = fitz.open()
    for text in pages:
        page = document.new_page(width=595, height=842)
        page.insert_text(
            (36, 36),
            text,
            fontsize=10,
            fontname="courier",
        )
    return document.tobytes()


def make_supported_statement_pdf() -> bytes:
    return make_pdf_from_pages([SUPPORTED_SYNTHETIC_TEXT, SUPPORTED_SYNTHETIC_TEXT_PAGE_TWO])


def make_unsupported_statement_pdf() -> bytes:
    return make_pdf_from_pages([UNSUPPORTED_TEXT])


def make_overlapping_statement_pdf() -> bytes:
    return make_pdf_from_pages([OVERLAPPING_SYNTHETIC_TEXT])


def make_same_day_distinct_statement_pdf() -> bytes:
    return make_pdf_from_pages([SAME_DAY_DISTINCT_SYNTHETIC_TEXT])


def make_generic_bank_statement_pdf() -> bytes:
    return make_pdf_from_pages(
        [GENERIC_BANK_STATEMENT_TEXT, GENERIC_BANK_STATEMENT_INFO_PAGE]
    )


def make_generic_stacked_bank_statement_pdf() -> bytes:
    return make_pdf_from_pages(
        [GENERIC_STACKED_BANK_STATEMENT_TEXT, GENERIC_STACKED_INFO_PAGE]
    )


def make_generic_unrelated_pdf_with_signals() -> bytes:
    return make_pdf_from_pages([GENERIC_UNRELATED_TEXT_WITH_SIGNALS])


def make_generic_malformed_statement_pdf() -> bytes:
    return make_pdf_from_pages([GENERIC_MALFORMED_TEXT])


def make_textless_pdf() -> bytes:
    document = fitz.open()
    document.new_page(width=595, height=842)
    return document.tobytes()


def make_malformed_statement_pdf() -> bytes:
    return make_pdf_from_pages([MALFORMED_SYNTHETIC_TEXT])


def make_password_protected_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((36, 36), SUPPORTED_SYNTHETIC_TEXT, fontsize=10, fontname="courier")
    return document.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )
