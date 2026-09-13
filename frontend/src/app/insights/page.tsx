"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { PeriodKey, PeriodSelector } from "@/components/period-selector";
import { Badge, Card, EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui";
import {
  AdvancedInsightsResponse,
  ApiError,
  CategoryRead,
  GoalRead,
  UserRead,
  createBudget,
  createGoal,
  deleteBudget,
  deleteGoal,
  getAdvancedInsights,
  getCurrentUser,
  listBudgets,
  listCategories,
  listGoals,
  updateGoal,
} from "@/lib/api";
import { clearAccessToken } from "@/lib/auth";
import { formatDateLabel, formatInr } from "@/lib/format";
import { getPeriodRange } from "@/lib/periods";

export default function InsightsPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserRead | null>(null);
  const [categories, setCategories] = useState<CategoryRead[]>([]);
  const [goals, setGoals] = useState<GoalRead[]>([]);
  const [insights, setInsights] = useState<AdvancedInsightsResponse | null>(null);
  const [period, setPeriod] = useState<PeriodKey>("this_month");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [editingGoalId, setEditingGoalId] = useState<string | null>(null);

  const handleAuthError = useCallback(
    (caughtError: unknown): boolean => {
      if (
        caughtError instanceof ApiError &&
        (caughtError.status === 401 || caughtError.status === 403)
      ) {
        clearAccessToken();
        router.replace("/login");
        return true;
      }
      return false;
    },
    [router],
  );

  const loadInsights = useCallback(async () => {
    try {
      setStatus("loading");
      setError("");
      const range = getPeriodRange(period);
      const [currentUser, categoryResponse, goalResponse, insightResponse] =
        await Promise.all([
          getCurrentUser(),
          listCategories(),
          listGoals(),
          getAdvancedInsights(range),
        ]);
      setUser(currentUser);
      setCategories(categoryResponse.items);
      setGoals(goalResponse.items);
      setInsights(insightResponse);
      setStatus("ready");
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Advanced insights could not be loaded.",
      );
      setStatus("error");
    }
  }, [handleAuthError, period]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadInsights();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadInsights]);

  async function handleCreateBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const categoryId = String(form.get("category_id") ?? "");
    const amount = String(form.get("amount") ?? "");
    const startDate = String(form.get("start_date") ?? "");

    try {
      setMessage("");
      setError("");
      await createBudget({
        category_id: categoryId || null,
        amount,
        start_date: startDate,
      });
      event.currentTarget.reset();
      setMessage("Budget saved.");
      await loadInsights();
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(caughtError instanceof ApiError ? caughtError.message : "Budget could not be saved.");
    }
  }

  async function handleCreateGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setMessage("");
      setError("");
      await createGoal({
        name: String(form.get("name") ?? ""),
        target_amount: String(form.get("target_amount") ?? ""),
        target_date: String(form.get("target_date") ?? ""),
        current_saved_amount: String(form.get("current_saved_amount") ?? "0"),
      });
      event.currentTarget.reset();
      setMessage("Goal saved.");
      await loadInsights();
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(caughtError instanceof ApiError ? caughtError.message : "Goal could not be saved.");
    }
  }

  async function handleUpdateGoal(goalId: string, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      setMessage("");
      setError("");
      await updateGoal(goalId, {
        name: String(form.get("name") ?? ""),
        target_amount: String(form.get("target_amount") ?? ""),
        target_date: String(form.get("target_date") ?? ""),
        current_saved_amount: String(form.get("current_saved_amount") ?? "0"),
        status: String(form.get("status") ?? "active") as "active" | "completed" | "paused",
      });
      setEditingGoalId(null);
      setMessage("Goal updated.");
      await loadInsights();
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(caughtError instanceof ApiError ? caughtError.message : "Goal could not be updated.");
    }
  }

  async function handleDeleteBudget(budgetId: string) {
    try {
      setMessage("");
      await deleteBudget(budgetId);
      setMessage("Budget deleted.");
      await loadInsights();
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(caughtError instanceof ApiError ? caughtError.message : "Budget could not be deleted.");
    }
  }

  async function handleDeleteGoal(goalId: string) {
    try {
      setMessage("");
      await deleteGoal(goalId);
      setMessage("Goal deleted.");
      await loadInsights();
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(caughtError instanceof ApiError ? caughtError.message : "Goal could not be deleted.");
    }
  }

  return (
    <AppShell
      subtitle="Recurring payments, budgets, goals, forecasts, and unusual spending patterns."
      title="Insights"
      userEmail={user?.email}
    >
      <Card className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">Advanced financial intelligence</h2>
            <p className="mt-1 text-sm text-slate-600">
              Calculated by explainable backend heuristics and statistics.
            </p>
          </div>
          <PeriodSelector onChange={setPeriod} value={period} />
        </div>
        {message ? <p className="mt-4 text-sm text-emerald-700">{message}</p> : null}
        {error && status !== "error" ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
      </Card>

      {status === "loading" ? (
        <Card className="mt-6 p-5">
          <LoadingSkeleton lines={6} />
        </Card>
      ) : null}

      {status === "error" ? (
        <div className="mt-6">
          <ErrorState message={error} title="Insights unavailable" />
        </div>
      ) : null}

      {status === "ready" && insights ? (
        <div className="mt-6 grid gap-6">
          <SummaryStrip insights={insights} />
          <div className="grid gap-6 xl:grid-cols-2">
            <RecurringSection insights={insights} />
            <SubscriptionSection insights={insights} />
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <BudgetSection
              categories={categories}
              insights={insights}
              onCreate={handleCreateBudget}
              onDelete={handleDeleteBudget}
            />
            <GoalSection
              editingGoalId={editingGoalId}
              goals={goals}
              onCancelEdit={() => setEditingGoalId(null)}
              onCreate={handleCreateGoal}
              onDelete={handleDeleteGoal}
              onEdit={setEditingGoalId}
              onUpdate={handleUpdateGoal}
            />
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <ForecastSection insights={insights} />
            <AnomalySection insights={insights} />
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}

function SummaryStrip({ insights }: { insights: AdvancedInsightsResponse }) {
  if (insights.insights.length === 0) {
    return (
      <EmptyState
        message="Upload and process more statements to unlock recurring payments, forecasts, and anomaly explanations."
        title="No advanced insights yet"
      />
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {insights.insights.map((item) => (
        <Card className="p-4" key={`${item.type}-${item.title}`}>
          <Badge tone={item.severity === "warning" ? "warning" : "success"}>{item.type}</Badge>
          <h3 className="mt-3 font-semibold text-slate-950">{item.title}</h3>
          <p className="mt-1 text-sm text-slate-600">{item.detail}</p>
        </Card>
      ))}
    </div>
  );
}

function RecurringSection({ insights }: { insights: AdvancedInsightsResponse }) {
  return (
    <Card className="p-5">
      <h2 className="text-lg font-semibold text-slate-950">Recurring payments</h2>
      <div className="mt-4 space-y-3">
        {insights.recurring_payments.length === 0 ? (
          <p className="text-sm text-slate-600">No recurring payment patterns found yet.</p>
        ) : (
          insights.recurring_payments.slice(0, 5).map((item) => (
            <div className="rounded-md border border-slate-200 p-3" key={item.merchant}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-slate-950">{item.merchant}</p>
                <Badge>{item.frequency}</Badge>
              </div>
              <p className="mt-1 text-sm text-slate-600">{item.explanation}</p>
              <p className="mt-2 text-sm text-slate-700">
                Average {formatInr(item.average_amount)} · Next{" "}
                {item.predicted_next_date ? formatDateLabel(item.predicted_next_date) : "unknown"} · Confidence{" "}
                {formatConfidence(item.confidence)}
              </p>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function SubscriptionSection({ insights }: { insights: AdvancedInsightsResponse }) {
  return (
    <Card className="p-5">
      <h2 className="text-lg font-semibold text-slate-950">Subscriptions</h2>
      <p className="mt-1 text-sm text-slate-600">
        Estimated monthly cost: {formatInr(insights.subscription_total_estimated_monthly_cost)}
      </p>
      <div className="mt-4 space-y-3">
        {insights.subscriptions.length === 0 ? (
          <p className="text-sm text-slate-600">No likely subscriptions detected.</p>
        ) : (
          insights.subscriptions.map((item) => (
            <div className="rounded-md border border-slate-200 p-3" key={item.merchant}>
              <p className="font-medium text-slate-950">{item.merchant}</p>
              <p className="mt-1 text-sm text-slate-700">
                {formatInr(item.typical_amount)} {item.billing_frequency} · Monthly equivalent{" "}
                {formatInr(item.estimated_monthly_cost)}
              </p>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function BudgetSection({
  categories,
  insights,
  onCreate,
  onDelete,
}: {
  categories: CategoryRead[];
  insights: AdvancedInsightsResponse;
  onCreate: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: (budgetId: string) => void;
}) {
  return (
    <Card className="p-5">
      <h2 className="text-lg font-semibold text-slate-950">Budgets</h2>
      <form className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]" onSubmit={onCreate}>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Category</span>
          <select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" name="category_id">
            <option value="">Overall spending</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Monthly limit</span>
          <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" min="1" name="amount" required type="number" />
        </label>
        <input name="start_date" type="hidden" value={new Date().toISOString().slice(0, 10)} />
        <button className="self-end rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white" type="submit">
          Save
        </button>
      </form>
      <div className="mt-4 space-y-3">
        {insights.budgets.length === 0 ? (
          <p className="text-sm text-slate-600">No budgets configured yet.</p>
        ) : (
          insights.budgets.map((budget) => (
            <div className="rounded-md border border-slate-200 p-3" key={budget.budget_id}>
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-slate-950">{budget.category_name}</p>
                <Badge tone={budget.status === "exceeded" ? "danger" : budget.status === "near_limit" ? "warning" : "success"}>
                  {budget.status.replace("_", " ")}
                </Badge>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full bg-emerald-700"
                  style={{ width: `${Math.min(Number(budget.percentage_used), 100)}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between text-sm text-slate-600">
                <span>{formatInr(budget.spent_amount)} / {formatInr(budget.budget_amount)}</span>
                <button className="text-red-700" onClick={() => onDelete(budget.budget_id)} type="button">
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function GoalSection({
  editingGoalId,
  goals,
  onCancelEdit,
  onCreate,
  onDelete,
  onEdit,
  onUpdate,
}: {
  editingGoalId: string | null;
  goals: GoalRead[];
  onCancelEdit: () => void;
  onCreate: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: (goalId: string) => void;
  onEdit: (goalId: string) => void;
  onUpdate: (goalId: string, event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Card className="p-5">
      <h2 className="text-lg font-semibold text-slate-950">Goals</h2>
      <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={onCreate}>
        <input className="rounded-md border border-slate-300 px-3 py-2" name="name" placeholder="Goal name" required />
        <input className="rounded-md border border-slate-300 px-3 py-2" min="1" name="target_amount" placeholder="Target amount" required step="0.01" type="number" />
        <input className="rounded-md border border-slate-300 px-3 py-2" name="target_date" required type="date" />
        <input className="rounded-md border border-slate-300 px-3 py-2" min="0" name="current_saved_amount" placeholder="Current saved" step="0.01" type="number" />
        <button className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white sm:col-span-2" type="submit">
          Add goal
        </button>
      </form>
      <div className="mt-4 space-y-3">
        {goals.length === 0 ? (
          <p className="text-sm text-slate-600">No goals configured yet.</p>
        ) : (
          goals.map((goal) => (
            <div className="rounded-md border border-slate-200 p-3" key={goal.id}>
              {editingGoalId === goal.id ? (
                <form className="grid gap-3 sm:grid-cols-2" onSubmit={(event) => onUpdate(goal.id, event)}>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Goal name</span>
                    <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" defaultValue={goal.name} name="name" required />
                  </label>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Target amount</span>
                    <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" defaultValue={decimalInputValue(goal.target_amount)} min="1" name="target_amount" required step="0.01" type="number" />
                  </label>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Target date</span>
                    <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" defaultValue={goal.target_date} name="target_date" required type="date" />
                  </label>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Saved so far</span>
                    <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" defaultValue={decimalInputValue(goal.current_saved_amount)} min="0" name="current_saved_amount" step="0.01" type="number" />
                  </label>
                  <label className="block">
                    <span className="text-sm font-medium text-slate-700">Status</span>
                    <select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" defaultValue={goal.status} name="status">
                      <option value="active">Active</option>
                      <option value="paused">Paused</option>
                      <option value="completed">Completed</option>
                    </select>
                  </label>
                  <div className="flex items-end gap-2">
                    <button className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white" type="submit">
                      Save changes
                    </button>
                    <button className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800" onClick={onCancelEdit} type="button">
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-950">{goal.name}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        Target {formatInr(goal.target_amount)} by {formatDateLabel(goal.target_date)}
                      </p>
                    </div>
                    <Badge tone={goalBadgeTone(goal.feasibility)}>
                      {goal.feasibility.replaceAll("_", " ")}
                    </Badge>
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full bg-emerald-700"
                      style={{ width: `${Math.min(Number(goal.progress_percentage), 100)}%` }}
                    />
                  </div>
                  <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                    <GoalMetric label="Saved so far" value={formatInr(goal.current_saved_amount)} />
                    <GoalMetric label="Remaining" value={formatInr(goal.remaining_amount)} />
                    <GoalMetric
                      label="Required monthly saving"
                      value={goal.required_monthly_saving ? formatInr(goal.required_monthly_saving) : "Adjust target date"}
                    />
                    <GoalMetric
                      label="Recent average savings"
                      value={goal.historical_monthly_savings ? formatInr(goal.historical_monthly_savings) : "Need 3 completed months"}
                    />
                    <GoalMetric
                      label="Monthly gap/surplus"
                      value={goal.monthly_gap_or_surplus ? formatInr(goal.monthly_gap_or_surplus) : "Not enough history"}
                    />
                    <GoalMetric label="Months remaining" value={String(goal.months_remaining)} />
                  </div>
                  <p className="mt-3 rounded-md bg-slate-50 p-3 text-sm text-slate-700">
                    {goalRecommendation(goal)}
                  </p>
                  <div className="mt-3 flex items-center justify-end gap-3 text-sm">
                    <button className="text-emerald-700" onClick={() => onEdit(goal.id)} type="button">
                      Edit
                    </button>
                    <button className="text-red-700" onClick={() => onDelete(goal.id)} type="button">
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function GoalMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function goalBadgeTone(feasibility: GoalRead["feasibility"]) {
  if (feasibility === "completed" || feasibility === "likely_on_track") {
    return "success";
  }
  if (feasibility === "needs_adjustment") {
    return "warning";
  }
  return "danger";
}

function goalRecommendation(goal: GoalRead) {
  if (goal.feasibility === "completed") {
    return "This goal is already funded based on the saved amount entered.";
  }
  if (!goal.required_monthly_saving) {
    return "Update the target date or saved amount to make this goal realistic.";
  }
  const required = formatInr(goal.required_monthly_saving);
  if (!goal.historical_monthly_savings) {
    return `Save ${required} every month to reach this goal. Add at least 3 completed months of transactions for an affordability comparison.`;
  }
  const historical = formatInr(goal.historical_monthly_savings);
  const gap = goal.monthly_gap_or_surplus ? formatInr(goal.monthly_gap_or_surplus) : "N/A";
  if (Number(goal.monthly_gap_or_surplus) >= 0) {
    return `Save ${required} every month. Your recent average monthly savings are ${historical}, giving you a surplus of ${gap} against the required pace.`;
  }
  return `Save ${required} every month. Your recent average monthly savings are ${historical}, so you are short by ${gap.replace("-", "")} per month.`;
}

function decimalInputValue(value: string) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return value;
  }
  return numeric.toFixed(2);
}

function ForecastSection({ insights }: { insights: AdvancedInsightsResponse }) {
  const forecast = insights.forecast;
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Forecast</h2>
          <p className="mt-1 text-sm text-slate-600">
            Conservative next-month estimate from completed monthly expense history.
          </p>
        </div>
        <Badge tone={forecast.status === "ready" ? "success" : "warning"}>
          {forecast.status === "ready" ? "Ready" : "Needs history"}
        </Badge>
      </div>
      {forecast.status === "insufficient_history" ? (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-4">
          <p className="font-medium text-amber-950">Forecast is not ready yet.</p>
          <p className="mt-2 text-sm text-amber-900">{forecast.explanation}</p>
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <GoalMetric label="Completed months found" value={String(forecast.months_used)} />
            <GoalMetric label="Required months" value={String(forecast.history_required_months)} />
            <GoalMetric label="More months needed" value={String(forecast.months_missing)} />
          </div>
          <p className="mt-3 text-sm text-amber-900">
            Upload and process older statements, or wait until more complete months are available.
          </p>
        </div>
      ) : (
        <div className="mt-3">
          <p className="text-2xl font-semibold text-slate-950">
            {formatInr(forecast.projected_next_month_expenses)}
          </p>
          <p className="mt-1 text-sm text-slate-600">
            Range {formatInr(forecast.lower_estimate)} to{" "}
            {formatInr(forecast.upper_estimate)}
          </p>
          <p className="mt-3 text-sm text-slate-600">
            {forecast.explanation} It used {forecast.months_used} completed months.
          </p>
        </div>
      )}
    </Card>
  );
}

function AnomalySection({ insights }: { insights: AdvancedInsightsResponse }) {
  return (
    <Card className="p-5">
      <h2 className="text-lg font-semibold text-slate-950">Unusual transactions</h2>
      <div className="mt-4 space-y-3">
        {insights.anomalies.length === 0 ? (
          <p className="text-sm text-slate-600">No financial anomalies found for this period.</p>
        ) : (
          insights.anomalies.map((item) => (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3" key={item.transaction_id}>
              <p className="font-medium text-amber-950">
                {formatInr(item.amount)} · {item.merchant ?? "Unknown merchant"}
              </p>
              <p className="mt-1 text-sm text-amber-900">{item.reason}</p>
              <p className="mt-1 text-xs text-amber-800">{formatDateLabel(item.transaction_date)}</p>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function formatConfidence(value: string): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "N/A";
  }
  return `${(numeric * 100).toFixed(0)}%`;
}
