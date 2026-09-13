"use client";

import { useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Badge, Card, EmptyState, ErrorState, LoadingSkeleton, PrimaryLink } from "@/components/ui";
import {
  ApiError,
  DocumentIndexResponse,
  DocumentParseResponse,
  DocumentRead,
  DocumentType,
  deleteDocument,
  indexDocument,
  listDocuments,
  parseDocument,
  uploadDocument,
} from "@/lib/api";
import { clearAccessToken } from "@/lib/auth";
import { formatDateTimeLabel, formatFileSize, formatInr } from "@/lib/format";

const maxUploadSizeMb = 10;

function formatDocumentType(type: DocumentType): string {
  return type === "bank_statement" ? "Bank statement" : "Credit-card statement";
}

function statusTone(status: DocumentRead["processing_status"]) {
  if (status === "completed") return "success";
  if (status === "processing") return "warning";
  if (status === "failed") return "danger";
  return "muted";
}

function indexingTone(status: DocumentRead["indexing_status"]) {
  if (status === "indexed") return "success";
  if (status === "indexing") return "warning";
  if (status === "indexing_failed") return "danger";
  return "muted";
}

function formatStatus(status: DocumentRead["processing_status"]): string {
  const labels: Record<DocumentRead["processing_status"], string> = {
    ready_for_processing: "Ready",
    processing: "Processing",
    completed: "Parsed",
    failed: "Failed",
  };
  return labels[status];
}

function formatIndexingStatus(status: DocumentRead["indexing_status"]): string {
  const labels: Record<DocumentRead["indexing_status"], string> = {
    not_indexed: "Search off",
    indexing: "Indexing",
    indexed: "Search ready",
    indexing_failed: "Search failed",
  };
  return labels[status];
}

export default function DocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [documentType, setDocumentType] = useState<DocumentType>("bank_statement");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [parsingId, setParsingId] = useState<string | null>(null);
  const [indexingId, setIndexingId] = useState<string | null>(null);
  const [parseResult, setParseResult] = useState<DocumentParseResponse | null>(null);
  const [indexResult, setIndexResult] = useState<DocumentIndexResponse | null>(null);

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

  const refreshDocuments = useCallback(async () => {
    try {
      const response = await listDocuments();
      setDocuments(response.items);
      setStatus("ready");
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setStatus("error");
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Documents could not be loaded.",
      );
    }
  }, [handleAuthError]);

  useEffect(() => {
    let isMounted = true;

    async function loadInitialDocuments() {
      try {
        const response = await listDocuments();
        if (isMounted) {
          setDocuments(response.items);
          setStatus("ready");
        }
      } catch (caughtError) {
        if (handleAuthError(caughtError)) return;
        if (isMounted) {
          setStatus("error");
          setError(
            caughtError instanceof ApiError
              ? caughtError.message
              : "Documents could not be loaded.",
          );
        }
      }
    }

    loadInitialDocuments();

    return () => {
      isMounted = false;
    };
  }, [handleAuthError]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFile = event.target.files?.[0] ?? null;
    setFile(selectedFile);
    setError("");
    setMessage("");
    setParseResult(null);
    setIndexResult(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!file) {
      setError("Choose a PDF statement before uploading.");
      return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf") || file.type !== "application/pdf") {
      setError("Only PDF statements are supported.");
      return;
    }

    if (file.size > maxUploadSizeMb * 1024 * 1024) {
      setError(`File exceeds the ${maxUploadSizeMb} MB upload limit.`);
      return;
    }

    setIsUploading(true);
    try {
      await uploadDocument(file, documentType);
      setFile(null);
      setParseResult(null);
      setIndexResult(null);
      setMessage("Document uploaded successfully.");
      await refreshDocuments();
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Document upload failed. Please try again.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDelete(documentId: string) {
    setError("");
    setMessage("");
    setParseResult(null);
    setIndexResult(null);
    setDeletingId(documentId);

    try {
      await deleteDocument(documentId);
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      setMessage("Document deleted.");
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Document could not be deleted.",
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function handleParse(documentId: string) {
    setError("");
    setMessage("");
    setParseResult(null);
    setIndexResult(null);
    setParsingId(documentId);

    try {
      const result = await parseDocument(documentId);
      setParseResult(result);
      await refreshDocuments();
      if (result.result_status === "failed") {
        setError(result.errors[0]?.message ?? "Document parsing failed.");
      } else {
        setMessage(
          `Imported ${result.inserted_count} transactions. Skipped ${result.duplicate_count} duplicates.`,
        );
      }
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Document parsing failed. Please try again.",
      );
    } finally {
      setParsingId(null);
    }
  }

  async function handleIndex(documentId: string) {
    setError("");
    setMessage("");
    setParseResult(null);
    setIndexResult(null);
    setIndexingId(documentId);

    try {
      const result = await indexDocument(documentId);
      setIndexResult(result);
      await refreshDocuments();
      if (result.status === "indexing_failed") {
        setError(result.error ?? "Document indexing failed.");
      } else {
        setMessage(`Document search enabled with ${result.chunks_created} chunks.`);
      }
    } catch (caughtError) {
      if (handleAuthError(caughtError)) return;
      setError(
        caughtError instanceof ApiError
          ? caughtError.message
          : "Document indexing failed. Please try again.",
      );
    } finally {
      setIndexingId(null);
    }
  }

  return (
    <AppShell subtitle="Upload, process, and monitor statement files." title="Documents">
      {status === "loading" ? (
        <Card className="p-5">
          <LoadingSkeleton lines={4} />
        </Card>
      ) : null}

      {status === "error" ? <ErrorState message={error} title="Documents unavailable" /> : null}

      {status !== "loading" ? (
        <>
          <Card className="p-5">
            <form onSubmit={handleSubmit}>
              <div className="grid gap-4 lg:grid-cols-[220px_1fr_auto] lg:items-end">
                <label className="block">
                  <span className="text-sm font-medium text-slate-700">Document type</span>
                  <select
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950 outline-none focus:border-emerald-700"
                    onChange={(event) => setDocumentType(event.target.value as DocumentType)}
                    value={documentType}
                  >
                    <option value="bank_statement">Bank statement</option>
                    <option value="credit_card_statement">Credit-card statement</option>
                  </select>
                </label>

                <label className="block">
                  <span className="text-sm font-medium text-slate-700">PDF file</span>
                  <input
                    accept="application/pdf,.pdf"
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700"
                    onChange={handleFileChange}
                    type="file"
                  />
                </label>

                <button
                  className="rounded-md bg-emerald-700 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
                  disabled={isUploading}
                  type="submit"
                >
                  {isUploading ? "Uploading..." : "Upload"}
                </button>
              </div>

              <p className="mt-3 text-xs text-slate-500">
                PDF only. Development upload limit: {maxUploadSizeMb} MB.
              </p>
              {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
              {message ? <p className="mt-4 text-sm text-emerald-700">{message}</p> : null}
            </form>
          </Card>

          {parseResult ? <ParseSummary result={parseResult} /> : null}
          {indexResult ? <IndexSummary result={indexResult} /> : null}

          {documents.length === 0 ? (
            <div className="mt-6">
              <EmptyState
                message="Upload a supported PDF bank or credit-card statement to begin processing financial data."
                title="No documents uploaded yet"
              />
            </div>
          ) : (
            <Card className="mt-6 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-sm">
                  <thead className="bg-slate-100 text-slate-600">
                    <tr>
                      <th className="px-4 py-3 font-medium">Filename</th>
                      <th className="px-4 py-3 font-medium">Type</th>
                      <th className="px-4 py-3 font-medium">Uploaded</th>
                      <th className="px-4 py-3 font-medium">Size</th>
                      <th className="px-4 py-3 font-medium">Processing</th>
                      <th className="px-4 py-3 font-medium">Search</th>
                      <th className="px-4 py-3 text-right font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((document) => (
                      <tr className="border-t border-slate-200" key={document.id}>
                        <td className="max-w-xs px-4 py-3 font-medium text-slate-950">
                          <span className="block truncate">{document.original_filename}</span>
                        </td>
                        <td className="px-4 py-3 text-slate-700">
                          {formatDocumentType(document.document_type)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                          {formatDateTimeLabel(document.uploaded_at)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                          {formatFileSize(document.file_size_bytes)}
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={statusTone(document.processing_status)}>
                            {formatStatus(document.processing_status)}
                          </Badge>
                          {document.processing_error ? (
                            <span className="mt-1 block text-xs text-red-700">
                              {document.processing_error}
                            </span>
                          ) : null}
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={indexingTone(document.indexing_status)}>
                            {formatIndexingStatus(document.indexing_status)}
                          </Badge>
                          {document.indexing_error ? (
                            <span className="mt-1 block text-xs text-red-700">
                              {document.indexing_error}
                            </span>
                          ) : null}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap justify-end gap-2">
                            <button
                              className="rounded-md border border-emerald-200 px-3 py-1.5 text-sm font-medium text-emerald-700 disabled:cursor-not-allowed disabled:text-slate-400"
                              disabled={parsingId === document.id}
                              onClick={() => handleParse(document.id)}
                              type="button"
                            >
                              {parsingId === document.id ? "Processing..." : "Process"}
                            </button>
                            <button
                              className="rounded-md border border-sky-200 px-3 py-1.5 text-sm font-medium text-sky-700 disabled:cursor-not-allowed disabled:text-slate-400"
                              disabled={indexingId === document.id}
                              onClick={() => handleIndex(document.id)}
                              type="button"
                            >
                              {indexingId === document.id
                                ? "Indexing..."
                                : document.indexing_status === "indexed"
                                  ? "Reindex"
                                  : "Enable search"}
                            </button>
                            <button
                              className="rounded-md border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 disabled:cursor-not-allowed disabled:text-slate-400"
                              disabled={deletingId === document.id}
                              onClick={() => handleDelete(document.id)}
                              type="button"
                            >
                              {deletingId === document.id ? "Deleting..." : "Delete"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      ) : null}
    </AppShell>
  );
}

function IndexSummary({ result }: { result: DocumentIndexResponse }) {
  return (
    <Card className="mt-6 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Document search summary</h2>
          <p className="mt-1 text-sm text-slate-600">
            Embedding model: {result.embedding_model}
          </p>
        </div>
        <Badge tone={result.status === "indexed" ? "success" : "danger"}>
          {result.status.replaceAll("_", " ")}
        </Badge>
      </div>
      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <SummaryStat label="Chunks indexed" value={result.chunks_created} />
        <SummaryStat label="Search status" value={result.status === "indexed" ? 1 : 0} />
      </div>
      {result.error ? <p className="mt-4 text-sm text-red-700">{result.error}</p> : null}
    </Card>
  );
}

function ParseSummary({ result }: { result: DocumentParseResponse }) {
  return (
    <Card className="mt-6 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Processing summary</h2>
          <p className="mt-1 text-sm text-slate-600">
            {result.parser_name
              ? `${result.parser_name} v${result.parser_version}`
              : "No parser selected"}
          </p>
        </div>
        <Badge tone={result.result_status === "failed" ? "danger" : "success"}>
          {result.result_status.replaceAll("_", " ")}
        </Badge>
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-6">
        <SummaryStat label="Rows parsed" value={result.rows_parsed} />
        <SummaryStat label="Transactions" value={result.transaction_count} />
        <SummaryStat label="Imported" value={result.inserted_count} />
        <SummaryStat label="Duplicates" value={result.duplicate_count} />
        <SummaryStat label="Failed" value={result.failed_count} />
        <SummaryStat label="Warnings" value={result.warning_count} />
      </div>

      {result.inserted_count > 0 || result.duplicate_count > 0 ? (
        <div className="mt-4">
          <PrimaryLink href="/transactions">View transactions</PrimaryLink>
        </div>
      ) : null}

      {result.errors.length > 0 ? (
        <ul className="mt-4 space-y-1 text-sm text-red-700">
          {result.errors.map((issue) => (
            <li key={`${issue.code}-${issue.source_page}-${issue.source_row}`}>
              {issue.message}
            </li>
          ))}
        </ul>
      ) : null}

      {result.preview_transactions.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                <th className="px-3 py-2 font-medium">Date</th>
                <th className="px-3 py-2 font-medium">Description</th>
                <th className="px-3 py-2 font-medium">Direction</th>
                <th className="px-3 py-2 font-medium">Amount</th>
                <th className="px-3 py-2 font-medium">Balance</th>
              </tr>
            </thead>
            <tbody>
              {result.preview_transactions.map((transaction) => (
                <tr className="border-t border-slate-200" key={transaction.id}>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">
                    {transaction.transaction_date}
                  </td>
                  <td className="min-w-64 px-3 py-2 text-slate-950">
                    {transaction.raw_description}
                  </td>
                  <td className="px-3 py-2 text-slate-700">{transaction.direction}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">
                    {formatInr(transaction.amount)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-700">
                    {transaction.balance ? formatInr(transaction.balance) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </Card>
  );
}

function SummaryStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-950">{value}</p>
    </div>
  );
}
