import logging
import time
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.transaction import Transaction
from app.models.user import User
from app.parsing.exceptions import ParserErrorDetail, ParsingError
from app.parsing.pdf import extract_pdf_text
from app.parsing.registry import select_parser
from app.schemas.document import DocumentProcessingStatus
from app.schemas.parsing import (
    DocumentParseResponse,
    ParseResult,
    ParseResultStatus,
    ParserIssue,
)
from app.schemas.transaction import TransactionImportSummary
from app.services.document_storage import DocumentStorageService
from app.services.documents import get_user_document
from app.services.transactions import import_extracted_transactions

logger = logging.getLogger(__name__)

PREVIEW_TRANSACTION_LIMIT = 5


def parse_user_document(
    db: Session,
    current_user: User,
    document_id: UUID,
    storage: DocumentStorageService,
) -> DocumentParseResponse:
    document = get_user_document(db, current_user, document_id)
    started_at = time.perf_counter()

    _set_processing_status(db, document, DocumentProcessingStatus.processing, None)

    try:
        document_path = storage.path_for_read(document.storage_key)
        if not document_path.exists() or not document_path.is_file():
            return _fail_document(
                db,
                document,
                ParserErrorDetail(
                    code="missing_document_file",
                    message="Stored document file is missing.",
                ),
            )

        parse_result = _parse_file(document.id, document_path)
        if parse_result.status == ParseResultStatus.failed:
            import_summary = TransactionImportSummary(
                document_id=document.id,
                parsed=0,
                inserted=0,
                duplicates=0,
                failed=len(parse_result.errors),
            )
            first_error = parse_result.errors[0] if parse_result.errors else ParserIssue(
                code="parse_failed",
                message="Document parsing failed.",
            )
            _set_processing_status(
                db,
                document,
                DocumentProcessingStatus.failed,
                first_error.message,
            )
        else:
            import_summary = import_extracted_transactions(
                db=db,
                document=document,
                extracted_transactions=parse_result.transactions,
                currency=parse_result.metadata.currency,
                failed_rows=len(parse_result.errors),
            )
            _set_processing_status(
                db,
                document,
                DocumentProcessingStatus.completed,
                None,
            )

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "Document parsed",
            extra={
                "document_id": str(document_id),
                "parser_name": parse_result.parser_name,
                "transaction_count": parse_result.transaction_count,
                "duration_ms": duration_ms,
            },
        )
        return _response_from_result(db, document, parse_result, import_summary)
    except HTTPException as exc:
        _set_processing_status(
            db,
            document,
            DocumentProcessingStatus.failed,
            "Transaction import failed.",
        )
        raise
    except ParsingError as exc:
        logger.info(
            "Document parsing failed",
            extra={"document_id": str(document_id), "error_code": exc.detail.code},
        )
        return _fail_document(db, document, exc.detail)


def _parse_file(document_id: UUID, document_path: Path) -> ParseResult:
    pdf_text = extract_pdf_text(document_path)
    parser = select_parser(pdf_text)
    if parser is None:
        raise ParsingError(
            "unsupported_statement_format",
            "This statement format is not supported yet.",
        )

    return parser.extract(document_id, pdf_text)


def _response_from_result(
    db: Session,
    document: Document,
    parse_result: ParseResult,
    import_summary: TransactionImportSummary,
) -> DocumentParseResponse:
    stored_preview = list(
        db.scalars(
            select(Transaction)
            .where(
                Transaction.document_id == document.id,
                Transaction.user_id == document.user_id,
            )
            .order_by(
                Transaction.source_page.asc().nullslast(),
                Transaction.source_row.asc().nullslast(),
                Transaction.transaction_date.asc(),
                Transaction.id.desc(),
            )
            .limit(PREVIEW_TRANSACTION_LIMIT)
        )
    )
    return DocumentParseResponse(
        document_id=document.id,
        status=DocumentProcessingStatus(document.processing_status),
        parser_name=parse_result.parser_name,
        parser_version=parse_result.parser_version,
        result_status=parse_result.status,
        transaction_count=parse_result.transaction_count,
        warning_count=len(parse_result.warnings),
        error_count=len(parse_result.errors),
        warnings=parse_result.warnings,
        errors=parse_result.errors,
        rows_parsed=import_summary.parsed,
        inserted_count=import_summary.inserted,
        duplicate_count=import_summary.duplicates,
        failed_count=import_summary.failed,
        preview_transactions=stored_preview,
    )


def _fail_document(
    db: Session,
    document: Document,
    error: ParserErrorDetail,
) -> DocumentParseResponse:
    _set_processing_status(
        db,
        document,
        DocumentProcessingStatus.failed,
        error.message,
    )
    return DocumentParseResponse(
        document_id=document.id,
        status=DocumentProcessingStatus.failed,
        parser_name=None,
        parser_version=None,
        result_status=ParseResultStatus.failed,
        transaction_count=0,
        warning_count=0,
        error_count=1,
        rows_parsed=0,
        inserted_count=0,
        duplicate_count=0,
        failed_count=1,
        errors=[
            ParserIssue(
                code=error.code,
                message=error.message,
                source_page=error.source_page,
                source_row=error.source_row,
            )
        ],
        preview_transactions=[],
    )


def _set_processing_status(
    db: Session,
    document: Document,
    status: DocumentProcessingStatus,
    processing_error: str | None,
) -> None:
    document.processing_status = status.value
    document.processing_error = processing_error
    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except SQLAlchemyError:
        db.rollback()
        raise
