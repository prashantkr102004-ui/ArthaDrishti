from datetime import date
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.assistant import AssistantPeriod, FinancialToolResult
from app.schemas.parsing import TransactionDirection
from app.rag.retrieval import search_user_document_chunks
from app.services.advanced import (
    AdvancedDateRange,
    forecast_spending,
    get_financial_anomalies,
    get_recurring_payments,
    get_subscriptions,
)
from app.services.analytics import (
    DateRange,
    compare_periods,
    get_category_spending,
    get_financial_summary,
    get_top_merchants,
)
from app.services.budgets import get_budget_progress
from app.services.goals import list_goals


class ToolValidationError(ValueError):
    pass


class DateRangeArgs(BaseModel):
    start_date: date
    end_date: date
    account_id: str | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date.")
        if self.account_id is not None:
            raise ValueError("account_id filters are not supported yet.")
        return self

    def period(self) -> DateRange:
        return DateRange(start_date=self.start_date, end_date=self.end_date)


class TopMerchantsArgs(DateRangeArgs):
    limit: int = Field(default=5, ge=1, le=10)


class ComparePeriodsArgs(BaseModel):
    period_a_start: date
    period_a_end: date
    period_b_start: date
    period_b_end: date
    account_id: str | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.period_a_start > self.period_a_end:
            raise ValueError("period_a_start must be on or before period_a_end.")
        if self.period_b_start > self.period_b_end:
            raise ValueError("period_b_start must be on or before period_b_end.")
        if self.account_id is not None:
            raise ValueError("account_id filters are not supported yet.")
        return self


class ListTransactionsArgs(DateRangeArgs):
    direction: TransactionDirection | None = None
    category_slug: str | None = Field(default=None, max_length=100)
    merchant: str | None = Field(default=None, max_length=120)
    limit: int = Field(default=5, ge=1, le=10)
    order_by: Literal["date_desc", "amount_desc"] = "date_desc"


class SearchFinancialDocumentsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    document_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)

    model_config = ConfigDict(extra="forbid")


class EmptyArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OptionalDateRangeArgs(BaseModel):
    start_date: date | None = None
    end_date: date | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_optional_range(self):
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("Both start_date and end_date are required when filtering by date.")
        if self.start_date is not None and self.end_date is not None and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date.")
        return self


def execute_financial_tool(
    *,
    db: Session,
    current_user: User,
    name: str,
    arguments: dict[str, Any],
) -> FinancialToolResult:
    try:
        if name == "get_financial_summary":
            args = DateRangeArgs.model_validate(arguments)
            data = get_financial_summary(db, current_user, args.period())
            return _tool_result(name, arguments, data.model_dump(mode="json"), args.period())

        if name == "get_category_spending":
            args = DateRangeArgs.model_validate(arguments)
            data = get_category_spending(db, current_user, args.period())
            return _tool_result(name, arguments, data.model_dump(mode="json"), args.period())

        if name == "get_top_merchants":
            args = TopMerchantsArgs.model_validate(arguments)
            data = get_top_merchants(db, current_user, args.period(), args.limit)
            return _tool_result(name, arguments, data.model_dump(mode="json"), args.period())

        if name == "compare_periods":
            args = ComparePeriodsArgs.model_validate(arguments)
            period_a = DateRange(args.period_a_start, args.period_a_end)
            period_b = DateRange(args.period_b_start, args.period_b_end)
            data = compare_periods(db, current_user, period_a, period_b)
            return _tool_result(name, arguments, data.model_dump(mode="json"), period_a)

        if name == "list_transactions":
            args = ListTransactionsArgs.model_validate(arguments)
            data = _list_transactions(db, current_user, args)
            return _tool_result(name, arguments, data, args.period())

        if name == "search_financial_documents":
            args = SearchFinancialDocumentsArgs.model_validate(arguments)
            data = _search_financial_documents(db, current_user, args)
            return _tool_result(name, arguments, data, None)

        if name == "get_recurring_payments":
            EmptyArgs.model_validate(arguments)
            data = get_recurring_payments(db, current_user).model_dump(mode="json")
            return _tool_result(name, arguments, data, None)

        if name == "get_subscriptions":
            EmptyArgs.model_validate(arguments)
            data = get_subscriptions(db, current_user).model_dump(mode="json")
            return _tool_result(name, arguments, data, None)

        if name == "get_budget_status":
            args = DateRangeArgs.model_validate(arguments)
            data = get_budget_progress(
                db,
                current_user,
                args.start_date,
                args.end_date,
            ).model_dump(mode="json")
            return _tool_result(name, arguments, data, args.period())

        if name == "get_goal_status":
            EmptyArgs.model_validate(arguments)
            data = list_goals(db, current_user).model_dump(mode="json")
            return _tool_result(name, arguments, data, None)

        if name == "forecast_spending":
            EmptyArgs.model_validate(arguments)
            data = forecast_spending(db, current_user).model_dump(mode="json")
            return _tool_result(name, arguments, data, None)

        if name == "get_financial_anomalies":
            args = OptionalDateRangeArgs.model_validate(arguments)
            period = (
                AdvancedDateRange(args.start_date, args.end_date)
                if args.start_date is not None and args.end_date is not None
                else None
            )
            data = get_financial_anomalies(db, current_user, period).model_dump(mode="json")
            return _tool_result(
                name,
                arguments,
                data,
                DateRange(args.start_date, args.end_date)
                if args.start_date is not None and args.end_date is not None
                else None,
            )
    except ValidationError as exc:
        raise ToolValidationError("Invalid tool arguments.") from exc
    except ValueError as exc:
        raise ToolValidationError(str(exc)) from exc

    raise ToolValidationError(f"Unsupported financial tool: {name}")


def _search_financial_documents(
    db: Session,
    current_user: User,
    args: SearchFinancialDocumentsArgs,
) -> dict[str, Any]:
    try:
        document_id = UUID(args.document_id) if args.document_id else None
    except ValueError as exc:
        raise ToolValidationError("Invalid document_id.") from exc
    results = search_user_document_chunks(
        db=db,
        current_user=current_user,
        query=args.query,
        document_id=document_id,
        top_k=args.top_k,
    )
    return {
        "query": args.query,
        "result_count": len(results),
        "items": [
            {
                "chunk_id": str(result.chunk_id),
                "document_id": str(result.document_id),
                "document_name": result.document_name,
                "page_number": result.page_number,
                "chunk_index": result.chunk_index,
                "text": result.text,
                "score": result.score,
            }
            for result in results
        ],
    }


def _list_transactions(
    db: Session,
    current_user: User,
    args: ListTransactionsArgs,
) -> dict[str, Any]:
    filters = [
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= args.start_date,
        Transaction.transaction_date <= args.end_date,
    ]
    if args.direction is not None:
        filters.append(Transaction.direction == args.direction.value)
    if args.category_slug is not None:
        filters.append(Category.slug == args.category_slug)
    if args.merchant is not None:
        filters.append(Transaction.canonical_merchant.ilike(args.merchant))

    order_by = (
        (Transaction.amount.desc(), Transaction.transaction_date.desc(), Transaction.id.desc())
        if args.order_by == "amount_desc"
        else (Transaction.transaction_date.desc(), Transaction.created_at.desc(), Transaction.id.desc())
    )
    rows = list(
        db.scalars(
            select(Transaction)
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(*filters)
            .order_by(*order_by)
            .limit(args.limit)
        )
    )
    return {
        "start_date": args.start_date.isoformat(),
        "end_date": args.end_date.isoformat(),
        "items": [
            {
                "transaction_date": row.transaction_date.isoformat(),
                "description": row.normalized_description,
                "merchant": row.canonical_merchant,
                "category": row.category_name,
                "direction": row.direction,
                "amount": str(row.amount),
                "currency": row.currency,
            }
            for row in rows
        ],
        "count": len(rows),
    }


def _tool_result(
    name: str,
    arguments: dict[str, Any],
    data: dict[str, Any],
    period: DateRange | None,
) -> FinancialToolResult:
    return FinancialToolResult(
        name=name,
        arguments=arguments,
        data=data,
        period=AssistantPeriod(
            start_date=period.start_date,
            end_date=period.end_date,
        )
        if period
        else None,
    )


def tool_error_response(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
    )
