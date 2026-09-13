"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type BackendStatus = "checking" | "connected" | "unavailable";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export default function Home() {
  const [backendStatus, setBackendStatus] =
    useState<BackendStatus>(apiBaseUrl ? "checking" : "unavailable");

  useEffect(() => {
    if (!apiBaseUrl) {
      return;
    }

    const controller = new AbortController();

    async function checkBackend() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          signal: controller.signal,
        });

        setBackendStatus(response.ok ? "connected" : "unavailable");
      } catch {
        setBackendStatus("unavailable");
      }
    }

    checkBackend();

    return () => controller.abort();
  }, []);

  const statusLabel =
    backendStatus === "checking"
      ? "Checking..."
      : backendStatus === "connected"
        ? "Connected"
        : "Unavailable";

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <section className="w-full max-w-2xl">
        <p className="mb-3 text-sm font-medium uppercase tracking-wide text-emerald-700">
          Phase 3 Foundation
        </p>
        <h1 className="text-5xl font-semibold text-slate-950">
          ArthaDrishti
        </h1>
        <p className="mt-4 text-xl text-slate-700">
          Smart Financial Assistant
        </p>
        <div className="mt-8 rounded-md border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Backend Status</p>
          <p className="mt-1 text-2xl font-semibold text-slate-950">
            {statusLabel}
          </p>
        </div>
        <div className="mt-6 flex gap-3">
          <Link
            className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white"
            href="/register"
          >
            Register
          </Link>
          <Link
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-900"
            href="/login"
          >
            Login
          </Link>
        </div>
      </section>
    </main>
  );
}
