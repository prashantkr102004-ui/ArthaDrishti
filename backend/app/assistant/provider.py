from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.assistant.date_resolution import resolve_periods
from app.schemas.assistant import FinancialToolCall, FinancialToolResult


class LLMProviderError(RuntimeError):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def plan_tools(self, question: str, today: date) -> list[FinancialToolCall]:
        raise NotImplementedError

    @abstractmethod
    def compose_answer(
        self,
        question: str,
        tool_results: list[FinancialToolResult],
        warnings: list[str],
    ) -> str:
        raise NotImplementedError


class MockFinancialLLMProvider(LLMProvider):
    """Development provider that simulates tool-calling behavior for safe local tests."""

    def plan_tools(self, question: str, today: date) -> list[FinancialToolCall]:
        normalized = question.casefold()
        periods = resolve_periods(question, today)
        primary = _range_args(periods.primary)
        comparison = periods.comparison

        if _is_non_financial(normalized):
            return []
        if _is_unsupported_forecast(normalized):
            return []

        if _is_hybrid_document_analytics_question(normalized):
            if comparison is None:
                comparison = resolve_periods("compare this month with last month", today).comparison
            calls = [FinancialToolCall(name="search_financial_documents", arguments={"query": question, "top_k": 5})]
            if comparison is not None:
                calls.append(
                    FinancialToolCall(
                        name="compare_periods",
                        arguments={
                            "period_a_start": periods.primary.start_date.isoformat(),
                            "period_a_end": periods.primary.end_date.isoformat(),
                            "period_b_start": comparison.start_date.isoformat(),
                            "period_b_end": comparison.end_date.isoformat(),
                        },
                    )
                )
            else:
                calls.append(FinancialToolCall(name="get_financial_summary", arguments=primary))
            return calls

        if _is_document_question(normalized):
            return [FinancialToolCall(name="search_financial_documents", arguments={"query": question, "top_k": 5})]

        if "subscription" in normalized or "subscriptions" in normalized:
            return [FinancialToolCall(name="get_subscriptions")]

        if "recurring" in normalized or "repeat" in normalized:
            return [FinancialToolCall(name="get_recurring_payments")]

        if "budget" in normalized:
            return [FinancialToolCall(name="get_budget_status", arguments=primary)]

        if "goal" in normalized or "afford" in normalized or "on track" in normalized:
            return [FinancialToolCall(name="get_goal_status")]

        if "forecast" in normalized or "project" in normalized or "might i spend" in normalized:
            return [FinancialToolCall(name="forecast_spending")]

        if "anomaly" in normalized or "unusual" in normalized or "anything unusual" in normalized:
            return [FinancialToolCall(name="get_financial_anomalies", arguments=primary)]

        if "why" in normalized or "compare" in normalized or "higher" in normalized or "more" in normalized:
            if comparison is None:
                comparison = resolve_periods("compare this month with last month", today).comparison
            if comparison is not None:
                return [
                    FinancialToolCall(
                        name="compare_periods",
                        arguments={
                            "period_a_start": periods.primary.start_date.isoformat(),
                            "period_a_end": periods.primary.end_date.isoformat(),
                            "period_b_start": comparison.start_date.isoformat(),
                            "period_b_end": comparison.end_date.isoformat(),
                        },
                    )
                ]

        if "merchant" in normalized or "merchants" in normalized:
            return [FinancialToolCall(name="get_top_merchants", arguments={**primary, "limit": 5})]

        if "food" in normalized or "category" in normalized or "where did" in normalized or "money go" in normalized:
            return [FinancialToolCall(name="get_category_spending", arguments=primary)]

        if "biggest" in normalized or "largest" in normalized:
            return [
                FinancialToolCall(
                    name="list_transactions",
                    arguments={**primary, "direction": "debit", "limit": 5, "order_by": "amount_desc"},
                )
            ]

        return [FinancialToolCall(name="get_financial_summary", arguments=primary)]

    def compose_answer(
        self,
        question: str,
        tool_results: list[FinancialToolResult],
        warnings: list[str],
    ) -> str:
        if not tool_results:
            normalized = question.casefold()
            if _is_non_financial(normalized):
                return "I can only answer questions about your financial data in ArthaDrishti."
            if _is_unsupported_forecast(normalized):
                return "Forecasting is not available yet, so I cannot predict future spending."
            return "I could not identify a supported financial question for the available tools."

        result = tool_results[0]
        data = result.data
        if result.name == "get_financial_summary":
            return (
                f"For {_format_answer_date(data['start_date'])} to {_format_answer_date(data['end_date'])}, "
                f"your savings were {_format_inr(data['savings'])}. Income was "
                f"{_format_inr(data['total_income'])} and expenses were {_format_inr(data['total_expenses'])}."
            )
        if result.name == "get_category_spending":
            items = data.get("items", [])
            if not items:
                return (
                    f"No expense categories were found for {_format_answer_date(data['start_date'])} "
                    f"to {_format_answer_date(data['end_date'])}."
                )
            top = items[0]
            return (
                f"Most of your spending went to {top['category_name']} at {_format_inr(top['amount'])} "
                f"({_format_percent(top['percentage_of_total_expenses'])} of expenses)."
            )
        if result.name == "get_top_merchants":
            items = data.get("items", [])
            if not items:
                return (
                    f"No merchant spending was found for {_format_answer_date(data['start_date'])} "
                    f"to {_format_answer_date(data['end_date'])}."
                )
            top = items[0]
            return f"Your top merchant was {top['merchant_name']} with {_format_inr(top['amount'])} in spending."
        if result.name == "compare_periods":
            deltas = data.get("category_deltas", [])
            leading = deltas[0] if deltas else None
            reason = (
                f" The largest category change was {leading['category_name']} at {_format_inr(leading['difference'])}."
                if leading
                else ""
            )
            return (
                f"Expenses changed by {_format_inr(data['expense_difference'])} compared with the previous period."
                f"{reason}"
            )
        if result.name == "list_transactions":
            items = data.get("items", [])
            if not items:
                return "No matching transactions were found for that period."
            top = items[0]
            return (
                f"Your largest matching transaction was {top['description']} for {_format_inr(top['amount'])} "
                f"on {top['transaction_date']}."
            )
        if result.name == "search_financial_documents":
            items = data.get("items", [])
            if not items:
                return "I couldn't find relevant information in your indexed documents."
            excerpt = _document_answer_excerpt(items, question)
            return excerpt or "I couldn't find a clear answer in the retrieved document text."
        if result.name == "get_subscriptions":
            items = data.get("items", [])
            total = data.get("total_estimated_monthly_cost", "0.0000")
            if not items:
                return "I did not find likely subscriptions in your transaction history yet."
            return f"I found {len(items)} likely subscriptions costing about {_format_inr(total)} per month."
        if result.name == "get_recurring_payments":
            items = data.get("items", [])
            if not items:
                return "I did not find enough repeated transactions to identify recurring payments yet."
            top = items[0]
            return (
                f"I found {len(items)} likely recurring payments. The strongest pattern is "
                f"{top['merchant']} at about {_format_inr(top['average_amount'])}."
            )
        if result.name == "get_budget_status":
            items = data.get("items", [])
            if not items:
                return "No budgets are configured for this period yet."
            exceeded = [item for item in items if item.get("status") == "exceeded"]
            return f"{len(exceeded)} of your {len(items)} budgets are exceeded for the selected period."
        if result.name == "get_goal_status":
            items = data.get("items", [])
            if not items:
                return "No financial goals are configured yet."
            top = items[0]
            return (
                f"Your goal '{top['name']}' requires about "
                f"{_format_inr(top['required_monthly_saving'])} per month based on its target date."
            )
        if result.name == "forecast_spending":
            if data.get("status") == "insufficient_history":
                return data.get("explanation", "There is not enough history to forecast spending yet.")
            return (
                f"Projected next-month expenses are about "
                f"{_format_inr(data.get('projected_next_month_expenses'))} using {data.get('method')}."
            )
        if result.name == "get_financial_anomalies":
            items = data.get("items", [])
            if not items:
                return "No financial anomalies were found for that period."
            return (
                f"I found {len(items)} unusual financial transaction patterns. The largest flagged item is "
                f"{_format_inr(items[0]['amount'])} at {items[0].get('merchant') or 'an unknown merchant'}."
            )
        return "I found verified financial data, but this response type is not supported yet."


class UnavailableLLMProvider(LLMProvider):
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def plan_tools(self, question: str, today: date) -> list[FinancialToolCall]:
        raise LLMProviderError(self.reason)

    def compose_answer(
        self,
        question: str,
        tool_results: list[FinancialToolResult],
        warnings: list[str],
    ) -> str:
        raise LLMProviderError(self.reason)


def get_provider(provider_name: str, api_key: str | None, model: str) -> LLMProvider:
    normalized = provider_name.strip().casefold()
    if normalized in {"mock", "local", "development"}:
        return MockFinancialLLMProvider()
    if normalized in {"openai", "openai_compatible"} and not api_key:
        return UnavailableLLMProvider("LLM provider is configured but LLM_API_KEY is missing.")
    return UnavailableLLMProvider(
        f"LLM provider '{provider_name}' is not available in this development build."
    )


def _range_args(period) -> dict[str, str]:
    return {
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat(),
    }


def _is_non_financial(text: str) -> bool:
    non_financial_markers = ("world cup", "weather", "capital of", "movie", "sports score")
    financial_markers = ("spend", "spent", "income", "save", "saving", "expense", "merchant", "money")
    return any(marker in text for marker in non_financial_markers) and not any(
        marker in text for marker in financial_markers
    )


def _is_unsupported_forecast(text: str) -> bool:
    return (
        "exactly" in text
        and any(marker in text for marker in ("predict", "forecast", "next month", "future spending"))
    )


def _is_document_question(text: str) -> bool:
    document_markers = (
        "annual fee",
        "billing address",
        "cash withdrawal",
        "document",
        "fee",
        "interest rate",
        "late payment",
        "mentioned",
        "minimum payment",
        "statement says",
        "terms",
    )
    structured_markers = (
        "how much did i spend",
        "income",
        "merchant did i spend",
        "money go",
        "saved",
        "savings",
        "spending category",
        "top merchant",
        "total expenses",
    )
    return any(marker in text for marker in document_markers) and not any(
        marker in text for marker in structured_markers
    )


def _is_hybrid_document_analytics_question(text: str) -> bool:
    return _is_document_question(text) and any(
        marker in text for marker in ("compare", "spent more", "spending with", "higher than")
    )


def _document_answer_excerpt(items: list[dict[str, Any]], question: str) -> str:
    query_terms = _content_terms(question)
    best: tuple[int, str] | None = None

    for item in items:
        lines = [line.strip() for line in item.get("text", "").splitlines() if line.strip()]
        for index, line in enumerate(lines):
            line_terms = _content_terms(line)
            score = len(query_terms.intersection(line_terms))
            if score == 0:
                continue

            value_line = _nearby_value_line(lines, index)
            if value_line:
                score += 3
                candidate = _format_document_fact(line, value_line)
            else:
                candidate = line

            if best is None or score > best[0]:
                best = (score, candidate)

    if best is None:
        first_text = str(items[0].get("text", "")) if items else ""
        lines = [line.strip() for line in first_text.splitlines() if line.strip()]
        return " ".join(lines[:2])[:450].strip()

    return best[1][:450].strip()


def _format_answer_date(value: Any) -> str:
    if not isinstance(value, str):
        return str(value)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%d %b %Y")


def _format_inr(value: Any) -> str:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return "N/A"

    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    whole, fraction = f"{absolute:.2f}".split(".")
    if len(whole) > 3:
        last_three = whole[-3:]
        prefix = whole[:-3]
        groups: list[str] = []
        while len(prefix) > 2:
            groups.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        if prefix:
            groups.insert(0, prefix)
        whole = ",".join([*groups, last_three])
    return f"{sign}\u20b9{whole}.{fraction}"


def _format_percent(value: Any) -> str:
    try:
        percent = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return "N/A"
    return f"{percent}%"


def _content_terms(value: str) -> set[str]:
    stopwords = {
        "about",
        "document",
        "does",
        "find",
        "listed",
        "mentioned",
        "show",
        "statement",
        "tell",
        "that",
        "this",
        "what",
        "where",
        "which",
    }
    return {
        term
        for term in re.findall(r"[a-z0-9]+", value.casefold())
        if len(term) >= 3 and term not in stopwords
    }


def _nearby_value_line(lines: list[str], index: int) -> str | None:
    current = lines[index]
    if _contains_value(current):
        return None

    for candidate in lines[index + 1 : index + 3]:
        if _contains_value(candidate):
            return candidate
        if len(_content_terms(candidate)) > 2:
            break
    return None


def _contains_value(value: str) -> bool:
    return bool(
        re.search(r"\bINR\b|\u20b9|\d+(?:,\d{2,3})*(?:\.\d+)?\s*%?", value, re.IGNORECASE)
    )


def _format_document_fact(label: str, value: str) -> str:
    clean_label = label.strip().rstrip(":")
    clean_value = value.strip().rstrip(".")
    if ":" in label or clean_value.casefold().startswith(clean_label.casefold()):
        return f"{clean_label} {clean_value}."
    return f"{clean_label}: {clean_value}."
