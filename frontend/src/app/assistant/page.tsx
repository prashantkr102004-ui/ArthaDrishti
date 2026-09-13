"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { Badge, Card, EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui";
import {
  ApiError,
  AssistantQueryResponse,
  UserRead,
  askAssistant,
  getCurrentUser,
} from "@/lib/api";
import { clearAccessToken } from "@/lib/auth";
import { formatDateLabel, formatInr, formatPercent } from "@/lib/format";

const starterQuestions = [
  "Where did most of my money go this month?",
  "Compare this month with last month.",
  "What late-payment fee is mentioned in my statement?",
  "Which merchants did I spend the most on?",
  "How much did I save last month?",
];

export default function AssistantPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserRead | null>(null);
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<AssistantQueryResponse | null>(null);
  const [status, setStatus] = useState<"checking" | "ready" | "asking" | "error">("checking");
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadUser() {
      try {
        const currentUser = await getCurrentUser();
        if (isMounted) {
          setUser(currentUser);
          setStatus("ready");
        }
      } catch (caughtError) {
        if (
          caughtError instanceof ApiError &&
          (caughtError.status === 401 || caughtError.status === 403)
        ) {
          clearAccessToken();
          router.replace("/login");
          return;
        }
        if (isMounted) {
          setError("Your session could not be verified.");
          setStatus("error");
        }
      }
    }

    loadUser();

    return () => {
      isMounted = false;
    };
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setError("Enter a financial question first.");
      return;
    }

    setStatus("asking");
    setError("");
    try {
      const answer = await askAssistant(trimmed);
      setResponse(answer);
      setStatus("ready");
    } catch (caughtError) {
      if (
        caughtError instanceof ApiError &&
        (caughtError.status === 401 || caughtError.status === 403)
      ) {
        clearAccessToken();
        router.replace("/login");
        return;
      }
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "The assistant could not answer right now.",
      );
      setStatus("ready");
    }
  }

  return (
    <AppShell
      subtitle="Ask simple questions about your financial data and indexed documents."
      title="Assistant"
      userEmail={user?.email}
    >
      {status === "checking" ? (
        <Card className="p-5">
          <LoadingSkeleton lines={4} />
        </Card>
      ) : null}

      {status === "error" ? (
        <ErrorState message={error} title="Assistant unavailable" />
      ) : null}

      {status !== "checking" && status !== "error" ? (
        <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
          <section>
            <Card className="p-5">
              <form onSubmit={handleSubmit}>
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">
                    Financial question
                  </span>
                  <textarea
                    className="mt-2 min-h-32 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950 outline-none focus:border-emerald-700"
                    maxLength={500}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Example: Where did most of my money go this month?"
                    value={question}
                  />
                </label>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs text-slate-500">
                    Answers use approved backend tools. Document answers show sources when available.
                  </p>
                  <button
                    className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
                    disabled={status === "asking"}
                    type="submit"
                  >
                    {status === "asking" ? "Asking..." : "Ask"}
                  </button>
                </div>
              </form>
              {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
            </Card>

            {status === "asking" ? (
              <Card className="mt-6 p-5">
                <LoadingSkeleton lines={5} />
              </Card>
            ) : null}

            {response ? <AnswerPanel response={response} /> : null}

            {!response && status !== "asking" ? (
              <div className="mt-6">
                <EmptyState
                  message="Ask about income, expenses, savings, top categories, top merchants, comparisons, or text found inside indexed documents."
                  title="No question answered yet"
                />
              </div>
            ) : null}
          </section>

          <aside>
            <Card className="p-5">
              <h2 className="text-lg font-semibold text-slate-950">
                Starter questions
              </h2>
              <div className="mt-4 space-y-2">
                {starterQuestions.map((starter) => (
                  <button
                    className="w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    key={starter}
                    onClick={() => setQuestion(starter)}
                    type="button"
                  >
                    {starter}
                  </button>
                ))}
              </div>
            </Card>
          </aside>
        </div>
      ) : null}
    </AppShell>
  );
}

function AnswerPanel({ response }: { response: AssistantQueryResponse }) {
  const visibleSources = uniqueDisplaySources(response.sources);
  const verificationLabels = uniqueLabels(response.tools_used.map(formatToolLabel));
  const keyFigures = getAnswerKeyFigures(response);

  return (
    <Card className="mt-6 overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 bg-slate-50 px-5 py-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Answer</h2>
          {response.period ? (
            <p className="mt-1 text-sm text-slate-600">
              {formatDateLabel(response.period.start_date)} to{" "}
              {formatDateLabel(response.period.end_date)}
            </p>
          ) : null}
        </div>
        <Badge tone="success">Grounded</Badge>
      </div>
      <div className="px-5 py-5">
        <p className="whitespace-pre-line text-lg leading-8 text-slate-900">
          {response.answer}
        </p>

        {keyFigures.length > 0 ? (
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {keyFigures.map((figure) => (
              <div
                className="rounded-md border border-slate-200 bg-white p-4"
                key={figure.label}
              >
                <p className="text-xs font-medium uppercase text-slate-500">
                  {figure.label}
                </p>
                <p className={`mt-2 text-xl font-semibold ${figure.tone}`}>
                  {figure.value}
                </p>
              </div>
            ))}
          </div>
        ) : null}

        {response.warnings.length > 0 ? (
          <ul className="mt-4 space-y-1 text-sm text-amber-700">
            {response.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : null}

        {visibleSources.length > 0 ? (
          <section className="mt-6 border-t border-slate-200 pt-5">
            <h3 className="text-sm font-semibold uppercase text-slate-500">Sources</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {visibleSources.map((source) => (
                <div
                  className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm"
                  key={`${source.document_id}-${source.page_number ?? "unknown"}`}
                >
                  <p className="font-medium text-slate-950">{source.document_name}</p>
                  <p className="mt-1 text-slate-600">
                    Page {source.page_number ?? "unknown"}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {verificationLabels.length > 0 ? (
          <p className="mt-5 border-t border-slate-200 pt-4 text-xs text-slate-500">
            Verified with {joinLabels(verificationLabels)}.
          </p>
        ) : null}
      </div>
    </Card>
  );
}

type KeyFigure = {
  label: string;
  value: string;
  tone: string;
};

function getAnswerKeyFigures(response: AssistantQueryResponse): KeyFigure[] {
  const summary = getToolData(response, "get_financial_summary");
  if (!summary) {
    return [];
  }

  return [
    {
      label: "Income",
      value: formatInr(getString(summary, "total_income")),
      tone: "text-emerald-700",
    },
    {
      label: "Expenses",
      value: formatInr(getString(summary, "total_expenses")),
      tone: "text-red-700",
    },
    {
      label: "Savings",
      value: formatInr(getString(summary, "savings")),
      tone: getSignedTone(getString(summary, "savings")),
    },
    {
      label: "Savings rate",
      value: formatPercent(getNullableString(summary, "savings_rate_percent")),
      tone: "text-slate-950",
    },
  ];
}

function getToolData(response: AssistantQueryResponse, toolName: string) {
  const value = response.data[toolName];
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function getString(record: Record<string, unknown>, key: string) {
  const value = record[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : null;
}

function getNullableString(record: Record<string, unknown>, key: string) {
  const value = getString(record, key);
  return value === null ? null : value;
}

function getSignedTone(value: string | null) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "text-slate-950";
  }
  return numeric < 0 ? "text-red-700" : "text-emerald-700";
}

function formatToolLabel(toolName: string) {
  const labels: Record<string, string> = {
    compare_periods: "period comparison",
    forecast_spending: "spending forecast",
    get_budget_status: "budget status",
    get_category_spending: "category analysis",
    get_financial_anomalies: "anomaly analysis",
    get_financial_summary: "financial summary",
    get_goal_status: "goal planning",
    get_recurring_payments: "recurring-payment detection",
    get_subscriptions: "subscription detection",
    get_top_merchants: "merchant analysis",
    list_transactions: "transaction search",
    search_financial_documents: "document search",
  };

  return labels[toolName] ?? "verified backend data";
}

function uniqueLabels(labels: string[]) {
  return Array.from(new Set(labels));
}

function joinLabels(labels: string[]) {
  if (labels.length <= 1) {
    return labels[0] ?? "verified backend data";
  }

  return `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}`;
}

function uniqueDisplaySources(sources: AssistantQueryResponse["sources"]) {
  const seen = new Set<string>();
  return sources.filter((source) => {
    const key = `${source.document_id}-${source.page_number ?? "unknown"}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}
