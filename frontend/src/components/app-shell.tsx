"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode } from "react";

import { clearAccessToken } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Documents" },
  { href: "/transactions", label: "Transactions" },
  { href: "/insights", label: "Insights" },
  { href: "/assistant", label: "Assistant" },
];

export function AppShell({
  children,
  subtitle,
  title,
  userEmail,
}: {
  children: ReactNode;
  subtitle?: string;
  title: string;
  userEmail?: string | null;
}) {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearAccessToken();
    router.replace("/login");
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col md:flex-row">
        <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white px-5 py-6 md:block">
          <Link href="/dashboard">
            <p className="text-lg font-semibold text-slate-950">ArthaDrishti</p>
            <p className="mt-1 text-sm text-slate-500">Smart Financial Assistant</p>
          </Link>
          <nav className="mt-8 space-y-1" aria-label="Primary">
            {navItems.map((item) => (
              <Link
                className={`block rounded-md px-3 py-2 text-sm font-medium ${
                  pathname === item.href
                    ? "bg-emerald-50 text-emerald-800"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="border-b border-slate-200 bg-white px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm font-medium uppercase text-emerald-700 md:hidden">
                  ArthaDrishti
                </p>
                <h1 className="mt-1 text-2xl font-semibold text-slate-950 sm:text-3xl">
                  {title}
                </h1>
                {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                {userEmail ? (
                  <span className="max-w-full truncate rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">
                    {userEmail}
                  </span>
                ) : null}
                <button
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-100"
                  onClick={handleLogout}
                  type="button"
                >
                  Logout
                </button>
              </div>
            </div>
            <nav className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5 md:hidden" aria-label="Primary">
              {navItems.map((item) => (
                <Link
                  className={`rounded-md px-3 py-2 text-center text-sm font-medium ${
                    pathname === item.href
                      ? "bg-emerald-700 text-white"
                      : "border border-slate-300 text-slate-800"
                  }`}
                  href={item.href}
                  key={item.href}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </header>

          <div className="px-4 py-6 sm:px-6 lg:px-8">{children}</div>
        </section>
      </div>
    </main>
  );
}
