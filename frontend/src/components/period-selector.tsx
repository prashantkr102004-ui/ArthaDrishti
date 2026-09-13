export type PeriodKey = "this_month" | "last_month" | "last_3_months" | "last_6_months";

export const periodLabels: Record<PeriodKey, string> = {
  this_month: "This Month",
  last_month: "Last Month",
  last_3_months: "Last 3 Months",
  last_6_months: "Last 6 Months",
};

export function PeriodSelector({
  onChange,
  value,
}: {
  onChange: (value: PeriodKey) => void;
  value: PeriodKey;
}) {
  return (
    <fieldset>
      <legend className="sr-only">Dashboard period</legend>
      <div className="grid grid-cols-2 gap-2 rounded-md border border-slate-200 bg-white p-1 md:flex">
        {(Object.keys(periodLabels) as PeriodKey[]).map((key) => (
          <button
            className={`rounded px-3 py-2 text-sm font-medium ${
              value === key
                ? "bg-emerald-700 text-white"
                : "text-slate-700 hover:bg-slate-100"
            }`}
            key={key}
            onClick={() => onChange(key)}
            type="button"
          >
            {periodLabels[key]}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
