"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Badge, Card, EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui";
import {
  ApiError,
  CategoryRead,
  TransactionDirection,
  TransactionRead,
  listCategories,
  listTransactions,
  updateTransactionCategory,
} from "@/lib/api";
import { clearAccessToken } from "@/lib/auth";
import { formatDateLabel, formatInr } from "@/lib/format";

const pageSize = 20;

export default function TransactionsPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<CategoryRead[]>([]);
  const [transactions, setTransactions] = useState<TransactionRead[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [direction, setDirection] = useState<TransactionDirection | "">("");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const currentPage = useMemo(() => Math.floor(offset / pageSize) + 1, [offset]);
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total]);

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

  const loadTransactions = useCallback(
    async (nextOffset = 0) => {
      try {
        setStatus("loading");
        setError("");
        const response = await listTransactions({
          startDate,
          endDate,
          direction,
          limit: pageSize,
          offset: nextOffset,
        });
        setTransactions(response.items);
        setSelectedCategories(
          Object.fromEntries(
            response.items.map((transaction) => [
              transaction.id,
              transaction.category_id ?? "",
            ]),
          ),
        );
        setTotal(response.total);
        setOffset(response.offset);
        setStatus("ready");
      } catch (caughtError) {
        if (handleAuthError(caughtError)) return;
        setError(
          caughtError instanceof ApiError
            ? caughtError.message
            : "Transactions could not be loaded.",
        );
        setStatus("error");
      }
    },
    [direction, endDate, handleAuthError, startDate],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadInitialTransactions() {
      try {
        const [categoryResponse, transactionResponse] = await Promise.all([
          listCategories(),
          listTransactions({ limit: pageSize, offset: 0 }),
        ]);

        if (!isMounted) return;

        setCategories(categoryResponse.items);
        setTransactions(transactionResponse.items);
        setSelectedCategories(
          Object.fromEntries(
            transactionResponse.items.map((transaction) => [
              transaction.id,
              transaction.category_id ?? "",
            ]),
          ),
        );
        setTotal(transactionResponse.total);
        setOffset(transactionResponse.offset);
        setStatus("ready");
      } catch (caughtError) {
        if (handleAuthError(caughtError)) return;

        if (isMounted) {
          setError(
            caughtError instanceof ApiError
              ? caughtError.message
              : "Transactions could not be loaded.",
          );
          setStatus("error");
        }
      }
    }

    loadInitialTransactions();

    return () => {
      isMounted = false;
    };
  }, [handleAuthError]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    loadTransactions(0);
  }

  async function handleCategorySave(transactionId: string) {
    const categoryId = selectedCategories[transactionId];
    if (!categoryId) {
      setError("Choose a category before saving.");
      return;
    }

    try {
      setSavingId(transactionId);
      setError("");
      setMessage("");
      const updated = await updateTransactionCategory(transactionId, categoryId, true);
      setTransactions((current) =>
        current.map((transaction) =>
          transaction.id === transactionId ? updated : transaction,
        ),
      );
      setSelectedCategories((current) => ({
        ...current,
        [transactionId]: updated.category_id ?? "",
      }));
      setMessage("Category override saved for this merchant.");
      await loadTransactions(offset);
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Category could not be saved.",
      );
    } finally {
      setSavingId(null);
    }
  }

  return (
    <AppShell
      subtitle="Review imported transactions and manage category overrides."
      title="Transactions"
    >
      <Card className="p-5">
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr_180px_auto] lg:items-end">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Start date</span>
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950 outline-none focus:border-emerald-700"
                onChange={(event) => setStartDate(event.target.value)}
                type="date"
                value={startDate}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">End date</span>
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950 outline-none focus:border-emerald-700"
                onChange={(event) => setEndDate(event.target.value)}
                type="date"
                value={endDate}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Direction</span>
              <select
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950 outline-none focus:border-emerald-700"
                onChange={(event) =>
                  setDirection(event.target.value as TransactionDirection | "")
                }
                value={direction}
              >
                <option value="">All</option>
                <option value="debit">Debit</option>
                <option value="credit">Credit</option>
              </select>
            </label>
            <button
              className="rounded-md bg-emerald-700 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={status === "loading"}
              type="submit"
            >
              Apply
            </button>
          </div>
        </form>
        {message ? <p className="mt-4 text-sm text-emerald-700">{message}</p> : null}
        {error && status !== "error" ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
      </Card>

      <section className="mt-6">
        {status === "error" ? (
          <ErrorState message={error} title="Transactions unavailable" />
        ) : status === "loading" ? (
          <Card className="p-5">
            <LoadingSkeleton lines={5} />
          </Card>
        ) : transactions.length === 0 ? (
          <EmptyState
            message="Process a supported statement from the Documents page to populate this table."
            title="No imported transactions yet"
          />
        ) : (
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="bg-slate-100 text-slate-600">
                  <tr>
                    <th className="px-4 py-3 font-medium">Date</th>
                    <th className="px-4 py-3 font-medium">Merchant</th>
                    <th className="px-4 py-3 font-medium">Description</th>
                    <th className="px-4 py-3 font-medium">Category</th>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 text-right font-medium">Amount</th>
                    <th className="px-4 py-3 text-right font-medium">Balance</th>
                    <th className="px-4 py-3 text-right font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((transaction) => (
                    <tr className="border-t border-slate-200" key={transaction.id}>
                      <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                        {formatDateLabel(transaction.transaction_date)}
                      </td>
                      <td className="max-w-44 px-4 py-3 font-medium text-slate-950">
                        <span className="block truncate">
                          {transaction.canonical_merchant ?? "-"}
                        </span>
                      </td>
                      <td className="min-w-72 px-4 py-3 text-slate-700">
                        <span className="line-clamp-2">
                          {transaction.normalized_description}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <label className="sr-only" htmlFor={`category-${transaction.id}`}>
                          Category for {transaction.normalized_description}
                        </label>
                        <select
                          className="w-48 rounded-md border border-slate-300 px-2 py-1.5 text-slate-950 outline-none focus:border-emerald-700"
                          id={`category-${transaction.id}`}
                          onChange={(event) =>
                            setSelectedCategories((current) => ({
                              ...current,
                              [transaction.id]: event.target.value,
                            }))
                          }
                          value={selectedCategories[transaction.id] ?? ""}
                        >
                          <option value="">Uncategorized</option>
                          {categories.map((category) => (
                            <option key={category.id} value={category.id}>
                              {category.parent_id ? `- ${category.name}` : category.name}
                            </option>
                          ))}
                        </select>
                        <p className="mt-1 text-xs text-slate-500">
                          {transaction.category_name ?? "Uncategorized"}
                        </p>
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone={transaction.direction === "debit" ? "danger" : "success"}>
                          {transaction.direction === "debit" ? "Outflow" : "Inflow"}
                        </Badge>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right font-medium text-slate-950">
                        {formatInr(transaction.amount)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-slate-700">
                        {transaction.balance ? formatInr(transaction.balance) : "-"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          className="rounded-md border border-emerald-200 px-3 py-1.5 text-sm font-medium text-emerald-700 disabled:cursor-not-allowed disabled:text-slate-400"
                          disabled={savingId === transaction.id}
                          onClick={() => handleCategorySave(transaction.id)}
                          type="button"
                        >
                          {savingId === transaction.id ? "Saving..." : "Save"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </section>

      <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
        <p>
          Page {currentPage} of {totalPages}
        </p>
        <div className="flex gap-2">
          <button
            className="rounded-md border border-slate-300 px-3 py-1.5 font-medium text-slate-900 disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={offset === 0 || status === "loading"}
            onClick={() => loadTransactions(Math.max(0, offset - pageSize))}
            type="button"
          >
            Previous
          </button>
          <button
            className="rounded-md border border-slate-300 px-3 py-1.5 font-medium text-slate-900 disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={offset + pageSize >= total || status === "loading"}
            onClick={() => loadTransactions(offset + pageSize)}
            type="button"
          >
            Next
          </button>
        </div>
      </div>
    </AppShell>
  );
}
