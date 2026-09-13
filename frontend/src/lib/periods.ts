import { PeriodKey } from "@/components/period-selector";

export type DateRange = {
  startDate: string;
  endDate: string;
};

export function getPeriodRange(period: PeriodKey, today = new Date()): DateRange {
  const year = today.getFullYear();
  const month = today.getMonth();

  if (period === "last_month") {
    return {
      startDate: formatDate(new Date(year, month - 1, 1)),
      endDate: formatDate(new Date(year, month, 0)),
    };
  }

  if (period === "last_3_months") {
    return {
      startDate: formatDate(new Date(year, month - 2, 1)),
      endDate: formatDate(new Date(year, month + 1, 0)),
    };
  }

  if (period === "last_6_months") {
    return {
      startDate: formatDate(new Date(year, month - 5, 1)),
      endDate: formatDate(new Date(year, month + 1, 0)),
    };
  }

  return {
    startDate: formatDate(new Date(year, month, 1)),
    endDate: formatDate(new Date(year, month + 1, 0)),
  };
}

export function getPreviousPeriodRange(range: DateRange): DateRange {
  const start = parseDate(range.startDate);
  const end = parseDate(range.endDate);
  const dayCount = Math.round((end.getTime() - start.getTime()) / 86400000) + 1;
  const previousEnd = new Date(start);
  previousEnd.setDate(previousEnd.getDate() - 1);
  const previousStart = new Date(previousEnd);
  previousStart.setDate(previousStart.getDate() - dayCount + 1);

  return {
    startDate: formatDate(previousStart),
    endDate: formatDate(previousEnd),
  };
}

function parseDate(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

function formatDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
