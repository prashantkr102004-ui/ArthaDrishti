import Link from "next/link";
import { ReactNode } from "react";

type Tone = "default" | "success" | "warning" | "danger" | "muted";

const toneClasses: Record<Tone, string> = {
  default: "border-slate-200 bg-white text-slate-950",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  danger: "border-red-200 bg-red-50 text-red-800",
  muted: "border-slate-200 bg-slate-50 text-slate-700",
};

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-md border border-slate-200 bg-white shadow-sm ${className}`}>
      {children}
    </section>
  );
}

export function Badge({ children, tone = "muted" }: { children: ReactNode; tone?: Tone }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}

export function PrimaryLink({ children, href }: { children: ReactNode; href: string }) {
  return (
    <Link
      className="inline-flex rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
      href={href}
    >
      {children}
    </Link>
  );
}

export function SecondaryLink({ children, href }: { children: ReactNode; href: string }) {
  return (
    <Link
      className="inline-flex rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-100"
      href={href}
    >
      {children}
    </Link>
  );
}

export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3" aria-label="Loading" role="status">
      {Array.from({ length: lines }).map((_, index) => (
        <div
          className="h-4 rounded bg-slate-100"
          key={index}
          style={{ width: `${92 - index * 12}%` }}
        />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <Card className="p-6">
      <h2 className="text-xl font-semibold text-slate-950">{title}</h2>
      <p className="mt-2 max-w-2xl text-slate-600">{message}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </Card>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <Card className="border-red-200 bg-red-50 p-5">
      <h2 className="text-lg font-semibold text-red-900">{title}</h2>
      <p className="mt-2 text-sm text-red-800">{message}</p>
    </Card>
  );
}
