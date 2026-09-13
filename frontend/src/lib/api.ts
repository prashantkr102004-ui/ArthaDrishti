import { getAccessToken } from "./auth";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export type UserRead = {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
};

export type DocumentType = "bank_statement" | "credit_card_statement";

export type DocumentRead = {
  id: string;
  original_filename: string;
  document_type: DocumentType;
  mime_type: string;
  file_size_bytes: number;
  processing_status: "ready_for_processing" | "processing" | "completed" | "failed";
  processing_error: string | null;
  indexing_status: "not_indexed" | "indexing" | "indexed" | "indexing_failed";
  indexing_error: string | null;
  uploaded_at: string;
  created_at: string;
  updated_at: string;
};

export type TransactionDirection = "debit" | "credit";

export type ParserIssue = {
  code: string;
  message: string;
  source_page: number | null;
  source_row: number | null;
};

export type TransactionRead = {
  id: string;
  document_id: string;
  transaction_date: string;
  value_date: string | null;
  raw_description: string;
  normalized_description: string;
  canonical_merchant: string | null;
  category_id: string | null;
  category_name: string | null;
  categorization_confidence: string | null;
  categorization_source:
    | "override"
    | "exact_merchant"
    | "alias"
    | "regex"
    | "fallback"
    | null;
  amount: string;
  direction: TransactionDirection;
  balance: string | null;
  currency: string;
  source_page: number | null;
  source_row: number | null;
  extraction_confidence: string | null;
  created_at: string;
  updated_at: string;
};

export type TransactionListResponse = {
  items: TransactionRead[];
  total: number;
  limit: number;
  offset: number;
};

export type CategoryRead = {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  is_system: boolean;
  created_at: string;
};

export type CategoryListResponse = {
  items: CategoryRead[];
};

export type AnalyticsSummaryResponse = {
  start_date: string;
  end_date: string;
  total_income: string;
  total_expenses: string;
  savings: string;
  savings_rate_percent: string | null;
  total_debits: string;
  total_credits: string;
  raw_net_flow: string;
  investment_amount: string;
  transaction_count: number;
};

export type CategorySpendingItem = {
  category_id: string | null;
  category_name: string;
  amount: string;
  transaction_count: number;
  percentage_of_total_expenses: string;
};

export type CategorySpendingResponse = {
  start_date: string;
  end_date: string;
  total_expenses: string;
  items: CategorySpendingItem[];
};

export type MonthlyAnalyticsItem = {
  month: string;
  income: string;
  expenses: string;
  savings: string;
  investments: string;
  total_debits: string;
  total_credits: string;
  raw_net_flow: string;
  transaction_count: number;
};

export type MonthlyAnalyticsResponse = {
  start_date: string;
  end_date: string;
  items: MonthlyAnalyticsItem[];
};

export type MerchantSpendingItem = {
  merchant_name: string;
  amount: string;
  transaction_count: number;
};

export type MerchantSpendingResponse = {
  start_date: string;
  end_date: string;
  items: MerchantSpendingItem[];
};

export type AnalyticsPeriod = {
  start_date: string;
  end_date: string;
};

export type CategoryDeltaItem = {
  category_id: string | null;
  category_name: string;
  amount_period_a: string;
  amount_period_b: string;
  difference: string;
  percentage_change: string | null;
};

export type PeriodComparisonResponse = {
  period_a: AnalyticsPeriod;
  period_b: AnalyticsPeriod;
  expense_period_a: string;
  expense_period_b: string;
  expense_difference: string;
  expense_percentage_change: string | null;
  income_period_a: string;
  income_period_b: string;
  income_difference: string;
  savings_period_a: string;
  savings_period_b: string;
  savings_difference: string;
  category_deltas: CategoryDeltaItem[];
};

export type RecurringPaymentItem = {
  merchant: string;
  category_name: string | null;
  frequency: "weekly" | "monthly" | "quarterly" | "yearly";
  occurrence_count: number;
  average_amount: string;
  min_amount: string;
  max_amount: string;
  first_seen: string;
  last_seen: string;
  predicted_next_date: string | null;
  confidence: string;
  status: "active" | "possibly_inactive";
  is_subscription: boolean;
  explanation: string;
};

export type SubscriptionItem = {
  merchant: string;
  category_name: string | null;
  typical_amount: string;
  billing_frequency: "weekly" | "monthly" | "quarterly" | "yearly";
  estimated_monthly_cost: string;
  last_charged_date: string;
  estimated_next_charge: string | null;
  total_spent: string;
  confidence: string;
  status: "active" | "possibly_inactive";
};

export type BudgetRead = {
  id: string;
  category_id: string | null;
  category_name: string | null;
  amount: string;
  period: "monthly";
  start_date: string;
  created_at: string;
  updated_at: string;
};

export type BudgetProgressItem = {
  budget_id: string;
  category_id: string | null;
  category_name: string;
  budget_amount: string;
  spent_amount: string;
  remaining_amount: string;
  percentage_used: string;
  status: "on_track" | "near_limit" | "exceeded";
};

export type GoalRead = {
  id: string;
  name: string;
  target_amount: string;
  target_date: string;
  current_saved_amount: string;
  status: "active" | "completed" | "paused";
  remaining_amount: string;
  months_remaining: number;
  required_monthly_saving: string | null;
  historical_monthly_savings: string | null;
  monthly_gap_or_surplus: string | null;
  progress_percentage: string;
  feasibility:
    | "likely_on_track"
    | "needs_adjustment"
    | "currently_unrealistic"
    | "completed";
  recommendation: string;
  created_at: string;
  updated_at: string;
};

export type SpendingForecastResponse = {
  status: "ready" | "insufficient_history";
  method: string;
  months_used: number;
  history_required_months: number;
  months_missing: number;
  projected_next_month_expenses: string | null;
  lower_estimate: string | null;
  upper_estimate: string | null;
  explanation: string;
};

export type AnomalyItem = {
  transaction_id: string;
  transaction_date: string;
  merchant: string | null;
  category_name: string | null;
  amount: string;
  direction: string;
  method: string;
  score: string;
  reason: string;
};

export type InsightItem = {
  type: string;
  title: string;
  detail: string;
  severity: string;
};

export type AdvancedInsightsResponse = {
  recurring_payments: RecurringPaymentItem[];
  subscriptions: SubscriptionItem[];
  subscription_total_estimated_monthly_cost: string;
  budgets: BudgetProgressItem[];
  forecast: SpendingForecastResponse;
  anomalies: AnomalyItem[];
  insights: InsightItem[];
};

export type AssistantEvidence = {
  tool_name: string;
  period: AnalyticsPeriod | null;
  summary: Record<string, unknown>;
};

export type AssistantSource = {
  document_id: string;
  document_name: string;
  page_number: number | null;
  chunk_id: string;
  chunk_index: number;
};

export type AssistantQueryResponse = {
  answer: string;
  data: Record<string, unknown>;
  tools_used: string[];
  period: AnalyticsPeriod | null;
  warnings: string[];
  evidence: AssistantEvidence[];
  sources: AssistantSource[];
};

export type DocumentIndexResponse = {
  document_id: string;
  status: "not_indexed" | "indexing" | "indexed" | "indexing_failed";
  chunks_created: number;
  embedding_model: string;
  error: string | null;
};

export type DocumentParseResponse = {
  document_id: string;
  status: "ready_for_processing" | "processing" | "completed" | "failed";
  parser_name: string | null;
  parser_version: string | null;
  result_status: "success" | "partial_success" | "failed";
  transaction_count: number;
  warning_count: number;
  error_count: number;
  rows_parsed: number;
  inserted_count: number;
  duplicate_count: number;
  failed_count: number;
  warnings: string[];
  errors: ParserIssue[];
  preview_transactions: TransactionRead[];
};

export type DocumentListResponse = {
  items: DocumentRead[];
  total: number;
  limit: number;
  offset: number;
};

type ApiErrorBody = {
  detail?: unknown;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

function requireApiBaseUrl(): string {
  if (!apiBaseUrl) {
    throw new ApiError("Backend API URL is not configured.", 0);
  }

  return apiBaseUrl;
}

function formatError(detail: unknown, fallback: string): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return "Please check the form fields and try again.";
  }

  return fallback;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new ApiError(
      formatError(body.detail, "Request failed. Please try again."),
      response.status,
    );
  }

  return response.json() as Promise<T>;
}

export function registerUser(email: string, password: string): Promise<UserRead> {
  return request<UserRead>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function loginUser(
  email: string,
  password: string,
): Promise<TokenResponse> {
  return request<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getCurrentUser(): Promise<UserRead> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<UserRead>("/api/v1/users/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<DocumentListResponse>("/api/v1/documents", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function uploadDocument(
  file: File,
  documentType: DocumentType,
): Promise<DocumentRead> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  const formData = new FormData();
  formData.append("document_type", documentType);
  formData.append("file", file);

  const response = await fetch(`${requireApiBaseUrl()}/api/v1/documents`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new ApiError(
      formatError(body.detail, "Document upload failed. Please try again."),
      response.status,
    );
  }

  return response.json() as Promise<DocumentRead>;
}

export async function deleteDocument(documentId: string): Promise<void> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  const response = await fetch(
    `${requireApiBaseUrl()}/api/v1/documents/${documentId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new ApiError(
      formatError(body.detail, "Document could not be deleted."),
      response.status,
    );
  }
}

export async function parseDocument(
  documentId: string,
): Promise<DocumentParseResponse> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<DocumentParseResponse>(`/api/v1/documents/${documentId}/parse`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function indexDocument(
  documentId: string,
): Promise<DocumentIndexResponse> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<DocumentIndexResponse>(`/api/v1/documents/${documentId}/index`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export type TransactionListParams = {
  startDate?: string;
  endDate?: string;
  direction?: TransactionDirection | "";
  documentId?: string;
  limit?: number;
  offset?: number;
};

export async function listTransactions(
  params: TransactionListParams = {},
): Promise<TransactionListResponse> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  const query = new URLSearchParams();
  if (params.startDate) query.set("start_date", params.startDate);
  if (params.endDate) query.set("end_date", params.endDate);
  if (params.direction) query.set("direction", params.direction);
  if (params.documentId) query.set("document_id", params.documentId);
  if (params.limit) query.set("limit", String(params.limit));
  if (params.offset) query.set("offset", String(params.offset));

  const queryString = query.toString();
  const suffix = queryString ? `?${queryString}` : "";
  return request<TransactionListResponse>(`/api/v1/transactions${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listCategories(): Promise<CategoryListResponse> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<CategoryListResponse>("/api/v1/categories", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateTransactionCategory(
  transactionId: string,
  categoryId: string,
  applyToMerchant: boolean,
): Promise<TransactionRead> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<TransactionRead>(`/api/v1/transactions/${transactionId}/category`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      category_id: categoryId,
      apply_to_merchant: applyToMerchant,
    }),
  });
}

type AnalyticsDateRange = {
  startDate: string;
  endDate: string;
};

function analyticsQuery({ startDate, endDate }: AnalyticsDateRange): string {
  return new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  }).toString();
}

function authenticatedAnalyticsRequest<T>(path: string): Promise<T> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<T>(path, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function getAnalyticsSummary(
  range: AnalyticsDateRange,
): Promise<AnalyticsSummaryResponse> {
  return authenticatedAnalyticsRequest<AnalyticsSummaryResponse>(
    `/api/v1/analytics/summary?${analyticsQuery(range)}`,
  );
}

export function getCategorySpending(
  range: AnalyticsDateRange,
): Promise<CategorySpendingResponse> {
  return authenticatedAnalyticsRequest<CategorySpendingResponse>(
    `/api/v1/analytics/categories?${analyticsQuery(range)}`,
  );
}

export function getMonthlyAnalytics(
  range: AnalyticsDateRange,
): Promise<MonthlyAnalyticsResponse> {
  return authenticatedAnalyticsRequest<MonthlyAnalyticsResponse>(
    `/api/v1/analytics/monthly?${analyticsQuery(range)}`,
  );
}

export function getTopMerchants(
  range: AnalyticsDateRange,
  limit = 5,
): Promise<MerchantSpendingResponse> {
  const query = new URLSearchParams({
    start_date: range.startDate,
    end_date: range.endDate,
    limit: String(limit),
  }).toString();

  return authenticatedAnalyticsRequest<MerchantSpendingResponse>(
    `/api/v1/analytics/merchants?${query}`,
  );
}

export function compareAnalyticsPeriods(
  periodA: AnalyticsDateRange,
  periodB: AnalyticsDateRange,
): Promise<PeriodComparisonResponse> {
  const query = new URLSearchParams({
    period_a_start: periodA.startDate,
    period_a_end: periodA.endDate,
    period_b_start: periodB.startDate,
    period_b_end: periodB.endDate,
  }).toString();

  return authenticatedAnalyticsRequest<PeriodComparisonResponse>(
    `/api/v1/analytics/compare?${query}`,
  );
}

export function getAdvancedInsights(
  range: AnalyticsDateRange,
): Promise<AdvancedInsightsResponse> {
  return authenticatedAnalyticsRequest<AdvancedInsightsResponse>(
    `/api/v1/advanced/insights?${analyticsQuery(range)}`,
  );
}

export function listBudgets(): Promise<{ items: BudgetRead[] }> {
  return authenticatedAnalyticsRequest<{ items: BudgetRead[] }>("/api/v1/budgets");
}

export function createBudget(payload: {
  category_id?: string | null;
  amount: string;
  start_date: string;
}): Promise<BudgetRead> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<BudgetRead>("/api/v1/budgets", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ ...payload, period: "monthly" }),
  });
}

export function deleteBudget(budgetId: string): Promise<void> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return fetch(`${requireApiBaseUrl()}/api/v1/budgets/${budgetId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }).then(async (response) => {
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
      throw new ApiError(formatError(body.detail, "Budget could not be deleted."), response.status);
    }
  });
}

export function listGoals(): Promise<{ items: GoalRead[] }> {
  return authenticatedAnalyticsRequest<{ items: GoalRead[] }>("/api/v1/goals");
}

export function createGoal(payload: {
  name: string;
  target_amount: string;
  target_date: string;
  current_saved_amount: string;
}): Promise<GoalRead> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<GoalRead>("/api/v1/goals", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export function updateGoal(
  goalId: string,
  payload: {
    name?: string;
    target_amount?: string;
    target_date?: string;
    current_saved_amount?: string;
    status?: "active" | "completed" | "paused";
  },
): Promise<GoalRead> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<GoalRead>(`/api/v1/goals/${goalId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export function deleteGoal(goalId: string): Promise<void> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return fetch(`${requireApiBaseUrl()}/api/v1/goals/${goalId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }).then(async (response) => {
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
      throw new ApiError(formatError(body.detail, "Goal could not be deleted."), response.status);
    }
  });
}

export function askAssistant(question: string): Promise<AssistantQueryResponse> {
  const token = getAccessToken();

  if (!token) {
    throw new ApiError("Authentication required.", 401);
  }

  return request<AssistantQueryResponse>("/api/v1/assistant/query", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
  });
}
