import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.assistant.provider import LLMProviderError, get_provider
from app.core.config import settings
from app.models.user import User
from app.schemas.assistant import (
    AssistantEvidence,
    AssistantPeriod,
    AssistantQueryResponse,
    AssistantSource,
    FinancialToolResult,
)
from app.assistant.tools import ToolValidationError, execute_financial_tool

logger = logging.getLogger(__name__)


def answer_financial_question(
    *,
    db: Session,
    current_user: User,
    question: str,
    today: date | None = None,
) -> AssistantQueryResponse:
    cleaned_question = question.strip()
    if len(cleaned_question) > settings.assistant_max_question_chars:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Question is too long.",
        )

    provider = get_provider(settings.llm_provider, settings.llm_api_key, settings.llm_model)
    run_date = today or date.today()
    try:
        tool_calls = provider.plan_tools(cleaned_question, run_date)
    except LLMProviderError as exc:
        raise _provider_unavailable(exc) from exc

    if len(tool_calls) > settings.assistant_max_tool_rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The assistant requested too many tool calls.",
        )

    tool_results: list[FinancialToolResult] = []
    warnings: list[str] = []
    for call in tool_calls:
        try:
            tool_results.append(
                execute_financial_tool(
                    db=db,
                    current_user=current_user,
                    name=call.name,
                    arguments=call.arguments,
                )
            )
        except ToolValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    try:
        answer = provider.compose_answer(cleaned_question, tool_results, warnings)
    except LLMProviderError as exc:
        raise _provider_unavailable(exc) from exc

    answer = _ground_answer(answer, cleaned_question, tool_results)
    logger.info(
        "assistant_query_completed",
        extra={
            "user_id": str(current_user.id),
            "tool_names": [result.name for result in tool_results],
            "tool_rounds": len(tool_results),
        },
    )
    return AssistantQueryResponse(
        answer=answer,
        data={
            result.name: result.data
            for result in tool_results
        },
        tools_used=[result.name for result in tool_results],
        period=_primary_period(tool_results),
        warnings=warnings,
        evidence=[
            AssistantEvidence(
                tool_name=result.name,
                period=result.period,
                summary=_evidence_summary(result),
            )
            for result in tool_results
        ],
        sources=_assistant_sources(tool_results),
    )


def _provider_unavailable(exc: LLMProviderError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(exc),
    )


def _primary_period(tool_results: list[FinancialToolResult]) -> AssistantPeriod | None:
    return tool_results[0].period if tool_results else None


def _evidence_summary(result: FinancialToolResult) -> dict[str, Any]:
    data = result.data
    if result.name == "get_financial_summary":
        return {
            "total_income": data.get("total_income"),
            "total_expenses": data.get("total_expenses"),
            "savings": data.get("savings"),
            "savings_rate_percent": data.get("savings_rate_percent"),
        }
    if result.name == "get_category_spending":
        return {
            "total_expenses": data.get("total_expenses"),
            "top_categories": data.get("items", [])[:3],
        }
    if result.name == "get_top_merchants":
        return {"top_merchants": data.get("items", [])[:5]}
    if result.name == "compare_periods":
        return {
            "expense_difference": data.get("expense_difference"),
            "expense_percentage_change": data.get("expense_percentage_change"),
            "category_deltas": data.get("category_deltas", [])[:3],
        }
    if result.name == "list_transactions":
        return {"items": data.get("items", [])[:5], "count": data.get("count")}
    if result.name == "search_financial_documents":
        return {
            "query": data.get("query"),
            "result_count": data.get("result_count"),
            "sources": [
                {
                    "document_name": item.get("document_name"),
                    "page_number": item.get("page_number"),
                    "chunk_index": item.get("chunk_index"),
                }
                for item in data.get("items", [])[:5]
            ],
        }
    if result.name in {
        "get_recurring_payments",
        "get_subscriptions",
        "get_budget_status",
        "get_goal_status",
        "forecast_spending",
        "get_financial_anomalies",
    }:
        return data
    return {}


def _assistant_sources(tool_results: list[FinancialToolResult]) -> list[AssistantSource]:
    sources: list[AssistantSource] = []
    seen: set[tuple[str, str]] = set()
    for result in tool_results:
        if result.name != "search_financial_documents":
            continue
        for item in result.data.get("items", []):
            key = (str(item.get("document_id")), str(item.get("chunk_id")))
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                AssistantSource(
                    document_id=str(item.get("document_id")),
                    document_name=str(item.get("document_name")),
                    page_number=item.get("page_number"),
                    chunk_id=str(item.get("chunk_id")),
                    chunk_index=int(item.get("chunk_index") or 0),
                )
            )
    return sources


def _ground_answer(
    answer: str,
    question: str,
    tool_results: list[FinancialToolResult],
) -> str:
    if not tool_results:
        return answer

    allowed_numbers = set(_number_tokens(question))
    for result in tool_results:
        result_numbers = _number_tokens(str(result.data))
        allowed_numbers.update(result_numbers)
        allowed_numbers.update(_absolute_number_tokens(result_numbers))
        allowed_numbers.update(_formatted_date_number_tokens(str(result.data)))

    answer_numbers = _number_tokens(answer)
    unsupported = [
        token
        for token in answer_numbers
        if token not in allowed_numbers and not _looks_like_year(token)
    ]
    if unsupported:
        logger.warning("assistant_answer_replaced_due_to_ungrounded_numbers")
        return _safe_fallback_answer(tool_results)
    return answer


def _safe_fallback_answer(tool_results: list[FinancialToolResult]) -> str:
    result = tool_results[0]
    if result.name == "get_financial_summary":
        data = result.data
        return (
            f"Verified summary: income INR {data.get('total_income')}, expenses INR "
            f"{data.get('total_expenses')}, savings INR {data.get('savings')}."
        )
    if result.name == "compare_periods":
        data = result.data
        return f"Verified comparison: expenses changed by INR {data.get('expense_difference')}."
    return "I found verified financial data from the approved backend tools."


def _number_tokens(value: str) -> list[str]:
    return [
        token
        for token in (
            _canonical_number_token(match.group(0))
            for match in re.finditer(r"-?\d+(?:,\d{2,3})*(?:\.\d+)?", value)
        )
        if token is not None
    ]


def _canonical_number_token(value: str) -> str | None:
    try:
        number = Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None

    normalized = format(number.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _formatted_date_number_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for match in re.finditer(r"\b\d{4}-\d{2}-\d{2}\b", value):
        try:
            parsed = date.fromisoformat(match.group(0))
        except ValueError:
            continue
        tokens.add(str(parsed.day))
        tokens.add(str(parsed.month))
        tokens.add(str(parsed.year))
    return tokens


def _absolute_number_tokens(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value.startswith("-"):
            tokens.add(value[1:])
    return tokens


def _looks_like_year(token: str) -> bool:
    return len(token) == 4 and token.startswith(("19", "20"))
