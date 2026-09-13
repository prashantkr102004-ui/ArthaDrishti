"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { PeriodKey, PeriodSelector, periodLabels } from "@/components/period-selector";
import { Badge, Card, EmptyState, ErrorState, LoadingSkeleton, PrimaryLink } from "@/components/ui";
import {
  AnalyticsSummaryResponse,
  ApiError,
  CategorySpendingResponse,
  MerchantSpendingResponse,
  MonthlyAnalyticsResponse,
  PeriodComparisonResponse,
  TransactionRead,
  UserRead,
  compareAnalyticsPeriods,
  getAnalyticsSummary,
  getCategorySpending,
  getCurrentUser,
  getMonthlyAnalytics,
  getTopMerchants,
  listTransactions,
} from "@/lib/api";
import { clearAccessToken } from "@/lib/auth";
import { formatDateLabel, formatInr, formatMonthLabel, formatPercent } from "@/lib/format";
import { DateRange, getPeriodRange, getPreviousPeriodRange } from "@/lib/periods";

type DashboardStatus = "loading" | "ready" | "empty" | "error";

type DashboardData = {
  summary: AnalyticsSummaryResponse;
  categories: CategorySpendingResponse | null;
  monthly: MonthlyAnalyticsResponse | null;
  merchants: MerchantSpendingResponse | null;
  comparison: PeriodComparisonResponse | null;
  recentTransactions: TransactionRead[];
};

type WidgetErrors = Partial<
  Record<"categories" | "monthly" | "merchants" | "comparison" | "recent", string>
>;

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserRead | null>(null);
  const [period, setPeriod] = useState<PeriodKey>("this_month");
  const [data, setData] = useState<DashboardData | null>(null);
  const [status, setStatus] = useState<DashboardStatus>("loading");
  const [pageError, setPageError] = useState<string | null>(null);
  const [widgetErrors, setWidgetErrors] = useState<WidgetErrors>({});

  const selectedRange = useMemo(() => getPeriodRange(period), [period]);
  const previousRange = useMemo(
    () => getPreviousPeriodRange(selectedRange),
    [selectedRange],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      setStatus("loading");
      setPageError(null);
      setWidgetErrors({});

      try {
        const currentUser = await getCurrentUser();
        const summary = await getAnalyticsSummary(selectedRange);
        const [categories, monthly, merchants, comparison, recent] =
          await Promise.allSettled([
            getCategorySpending(selectedRange),
            getMonthlyAnalytics(selectedRange),
            getTopMerchants(selectedRange, 5),
            compareAnalyticsPeriods(selectedRange, previousRange),
            listTransactions({ limit: 8, offset: 0 }),
          ]);

        if (!isMounted) {
          return;
        }

        setUser(currentUser);
        setData({
          summary,
          categories: resultValue(categories),
          monthly: resultValue(monthly),
          merchants: resultValue(merchants),
          comparison: resultValue(comparison),
          recentTransactions: resultValue(recent)?.items ?? [],
        });
        setWidgetErrors({
          categories: resultError(categories),
          monthly: resultError(monthly),
          merchants: resultError(merchants),
          comparison: resultError(comparison),
          recent: resultError(recent),
        });
        setStatus(summary.transaction_count === 0 ? "empty" : "ready");
      } catch (caughtError) {
        if (isAuthError(caughtError)) {
          clearAccessToken();
          router.replace("/login");
          return;
        }

        if (isMounted) {
          setStatus("error");
          setPageError(
            caughtError instanceof Error
              ? caughtError.message
              : "Dashboard data could not be loaded.",
          );
        }
      }
    }

    loadDashboard();

    return () => {
      isMounted = false;
    };
  }, [previousRange, router, selectedRange]);

  return (
    <AppShell
      subtitle="Smart Financial Assistant"
      title="Financial Dashboard"
      userEmail={user?.email}
    >
      <section className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">Selected period</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">
            {periodLabels[period]}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {formatDateLabel(selectedRange.startDate)} to{" "}
            {formatDateLabel(selectedRange.endDate)}
          </p>
        </div>
        <PeriodSelector onChange={setPeriod} value={period} />
      </section>

      {status === "loading" ? (
        <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card className="p-5" key={index}>
              <LoadingSkeleton lines={3} />
            </Card>
          ))}
        </section>
      ) : null}

      {status === "error" ? (
        <div className="mt-6">
          <ErrorState
            message={pageError ?? "The analytics service could not be reached."}
            title="Dashboard unavailable"
          />
        </div>
      ) : null}

      {status === "empty" ? (
        <div className="mt-6">
          <EmptyState
            action={<PrimaryLink href="/documents">Go to Documents</PrimaryLink>}
            message="Upload and process a bank or credit-card statement to see income, expenses, category spending, monthly trends, and top merchants."
            title="No financial data yet"
          />
        </div>
      ) : null}

      {status === "ready" && data ? (
        <DashboardContent data={data} widgetErrors={widgetErrors} />
      ) : null}
    </AppShell>
  );
}

function DashboardContent({
  data,
  widgetErrors,
}: {
  data: DashboardData;
  widgetErrors: WidgetErrors;
}) {
  return (
    <>
      <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          comparison={comparisonText("Income", data.comparison?.income_difference)}
          label="Income"
          value={formatInr(data.summary.total_income)}
        />
        <KpiCard
          comparison={expenseComparisonText(data.comparison)}
          label="Expenses"
          value={formatInr(data.summary.total_expenses)}
        />
        <KpiCard
          comparison={comparisonText("Savings", data.comparison?.savings_difference)}
          label="Savings"
          value={formatInr(data.summary.savings)}
        />
        <KpiCard
          label="Savings Rate"
          value={formatPercent(data.summary.savings_rate_percent)}
        />
      </section>

      <section className="mt-4 grid gap-4 md:grid-cols-3">
        <KpiCard label="Investments" value={formatInr(data.summary.investment_amount)} />
        <KpiCard
          helper="Credits minus debits, including transfers."
          label="Raw Net Flow"
          value={formatInr(data.summary.raw_net_flow)}
        />
        <KpiCard label="Transactions" value={String(data.summary.transaction_count)} />
      </section>

      {widgetErrors.comparison ? (
        <p className="mt-3 text-sm text-amber-700">
          Comparison unavailable: {widgetErrors.comparison}
        </p>
      ) : null}

      <section className="mt-6 grid gap-6 xl:grid-cols-[1fr_380px]">
        <CategorySpendingPanel data={data.categories} error={widgetErrors.categories} />
        <TopMerchantsPanel data={data.merchants} error={widgetErrors.merchants} />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1fr_420px]">
        <MonthlyTrendPanel data={data.monthly} error={widgetErrors.monthly} />
        <RecentTransactionsPanel
          error={widgetErrors.recent}
          transactions={data.recentTransactions}
        />
      </section>
    </>
  );
}

function KpiCard({
  comparison,
  helper,
  label,
  value,
}: {
  comparison?: string | null;
  helper?: string;
  label: string;
  value: string;
}) {
  return (
    <Card className="p-5">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 break-words text-2xl font-semibold text-slate-950">
        {value}
      </p>
      {comparison ? (
        <p className="mt-2 text-sm text-slate-600">{comparison}</p>
      ) : helper ? (
        <p className="mt-2 text-sm text-slate-500">{helper}</p>
      ) : null}
    </Card>
  );
}

function CategorySpendingPanel({
  data,
  error,
}: {
  data: CategorySpendingResponse | null;
  error?: string;
}) {
  if (error) {
    return <WidgetError title="Category spending" message={error} />;
  }

  if (!data || data.items.length === 0) {
    return (
      <Card className="p-5">
        <SectionTitle title="Category Spending" />
        <p className="mt-4 text-sm text-slate-600">
          No expense categories were found for this period.
        </p>
      </Card>
    );
  }

  return (
    <Card className="p-5">
      <SectionTitle
        subtitle={`${formatInr(data.total_expenses)} total expenses`}
        title="Category Spending"
      />
      <div className="mt-5 space-y-4">
        {data.items.map((item) => (
          <div key={item.category_id ?? item.category_name}>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="min-w-0 truncate font-medium text-slate-800">
                {item.category_name}
              </span>
              <span className="shrink-0 text-slate-600">
                {formatInr(item.amount)} · {formatPercent(item.percentage_of_total_expenses)}
              </span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-slate-100">
              <div
                aria-label={`${item.category_name} ${formatPercent(
                  item.percentage_of_total_expenses,
                )}`}
                className="h-2 rounded-full bg-emerald-700"
                style={{ width: `${safePercentage(item.percentage_of_total_expenses)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function MonthlyTrendPanel({
  data,
  error,
}: {
  data: MonthlyAnalyticsResponse | null;
  error?: string;
}) {
  if (error) {
    return <WidgetError title="Monthly trend" message={error} />;
  }

  if (!data || data.items.length === 0) {
    return (
      <Card className="p-5">
        <SectionTitle title="Monthly Trend" />
        <p className="mt-4 text-sm text-slate-600">
          No month-level trend is available for this period.
        </p>
      </Card>
    );
  }

  const maxValue = maxMonthlyValue(data.items);

  return (
    <Card className="p-5">
      <SectionTitle title="Monthly Trend" />
      <div className="mt-5 space-y-5">
        {data.items.map((month) => (
          <div
            className="grid gap-3 border-b border-slate-100 pb-5 last:border-0 last:pb-0 lg:grid-cols-[100px_1fr]"
            key={month.month}
          >
            <div>
              <p className="font-medium text-slate-950">
                {formatMonthLabel(month.month)}
              </p>
              <p className="text-sm text-slate-500">
                {month.transaction_count} transactions
              </p>
            </div>
            <div className="space-y-2">
              <TrendBar label="Income" maxValue={maxValue} tone="credit" value={month.income} />
              <TrendBar label="Expenses" maxValue={maxValue} tone="debit" value={month.expenses} />
              <TrendBar label="Savings" maxValue={maxValue} tone="savings" value={month.savings} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function TopMerchantsPanel({
  data,
  error,
}: {
  data: MerchantSpendingResponse | null;
  error?: string;
}) {
  if (error) {
    return <WidgetError title="Top merchants" message={error} />;
  }

  return (
    <Card className="p-5">
      <SectionTitle title="Top Merchants" />
      {!data || data.items.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">
          No merchant spending was found for this period.
        </p>
      ) : (
        <ol className="mt-5 space-y-3">
          {data.items.map((merchant, index) => (
            <li
              className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
              key={merchant.merchant_name}
            >
              <span className="min-w-0 truncate text-sm font-medium text-slate-800">
                {index + 1}. {merchant.merchant_name}
              </span>
              <span className="shrink-0 text-sm text-slate-600">
                {formatInr(merchant.amount)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function RecentTransactionsPanel({
  error,
  transactions,
}: {
  error?: string;
  transactions: TransactionRead[];
}) {
  if (error) {
    return <WidgetError title="Recent transactions" message={error} />;
  }

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-3">
        <SectionTitle title="Recent Transactions" />
        <Link
          className="shrink-0 text-sm font-medium text-emerald-700 hover:text-emerald-800"
          href="/transactions"
        >
          View all
        </Link>
      </div>
      {transactions.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">
          No recent transactions are available.
        </p>
      ) : (
        <ul className="mt-5 divide-y divide-slate-100">
          {transactions.map((transaction) => (
            <li className="flex items-center justify-between gap-3 py-3" key={transaction.id}>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-950">
                  {transaction.canonical_merchant ?? transaction.normalized_description}
                </p>
                <p className="mt-1 truncate text-xs text-slate-500">
                  {formatDateLabel(transaction.transaction_date)} ·{" "}
                  {transaction.category_name ?? "Uncategorized"}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <Badge tone={transaction.direction === "debit" ? "danger" : "success"}>
                  {transaction.direction === "debit" ? "Outflow" : "Inflow"}
                </Badge>
                <p className="mt-1 text-sm font-medium text-slate-900">
                  {formatInr(transaction.amount)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function SectionTitle({ subtitle, title }: { subtitle?: string; title: string }) {
  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-950">{title}</h2>
      {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
    </div>
  );
}

function WidgetError({ message, title }: { message: string; title: string }) {
  return (
    <Card className="border-amber-200 bg-amber-50 p-5">
      <SectionTitle title={title} />
      <p className="mt-3 text-sm text-amber-800">Unable to load this section: {message}</p>
    </Card>
  );
}

function TrendBar({
  label,
  tone,
  value,
  maxValue,
}: {
  label: string;
  tone: "credit" | "debit" | "savings";
  value: string;
  maxValue: number;
}) {
  const numeric = Math.abs(Number(value));
  const width = maxValue > 0 ? Math.max((numeric / maxValue) * 100, 2) : 0;
  const color =
    tone === "credit"
      ? "bg-emerald-700"
      : tone === "debit"
        ? "bg-rose-600"
        : "bg-sky-700";

  return (
    <div className="grid grid-cols-[76px_1fr] gap-2 text-sm sm:grid-cols-[82px_1fr_120px] sm:items-center">
      <span className="text-slate-600">{label}</span>
      <div className="h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${width}%` }} />
      </div>
      <span className="col-start-2 text-right font-medium text-slate-800 sm:col-start-auto">
        {formatInr(value)}
      </span>
    </div>
  );
}

function maxMonthlyValue(items: MonthlyAnalyticsResponse["items"]): number {
  const values = items.flatMap((item) => [
    Math.abs(Number(item.income)),
    Math.abs(Number(item.expenses)),
    Math.abs(Number(item.savings)),
  ]);
  return Math.max(...values, 0);
}

function comparisonText(label: string, difference?: string): string | null {
  if (!difference) {
    return null;
  }

  const numeric = Number(difference);
  if (!Number.isFinite(numeric) || numeric === 0) {
    return `${label} unchanged vs previous period`;
  }

  return `${label} ${numeric > 0 ? "+" : ""}${formatInr(difference)} vs previous period`;
}

function expenseComparisonText(comparison: PeriodComparisonResponse | null): string | null {
  if (!comparison) {
    return null;
  }

  if (comparison.expense_percentage_change === null) {
    return comparisonText("Expenses", comparison.expense_difference);
  }

  const numeric = Number(comparison.expense_percentage_change);
  if (!Number.isFinite(numeric)) {
    return null;
  }

  return `Expenses ${numeric > 0 ? "+" : ""}${numeric.toFixed(2)}% vs previous period`;
}

function safePercentage(value: string): number {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  return Math.max(0, Math.min(numeric, 100));
}

function resultValue<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

function resultError<T>(result: PromiseSettledResult<T>): string | undefined {
  if (result.status === "fulfilled") {
    return undefined;
  }
  return result.reason instanceof Error ? result.reason.message : "Request failed.";
}

function isAuthError(caughtError: unknown): boolean {
  return (
    caughtError instanceof ApiError &&
    (caughtError.status === 401 || caughtError.status === 403)
  );
}
