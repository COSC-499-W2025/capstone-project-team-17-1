import test from "node:test";
import assert from "node:assert/strict";

function getHeatmapBucket(intensity) {
  if (intensity >= 0.8) return 4;
  if (intensity >= 0.6) return 3;
  if (intensity >= 0.35) return 2;
  if (intensity > 0) return 1;
  return 0;
}

function buildContributionHeatmapModel(cells) {
  const entries = [...cells]
    .map((cell) => {
      const rawDate = String(cell.period || "").trim();
      const parsed = new Date(`${rawDate}T00:00:00`);
      return {
        dateKey: rawDate,
        date: parsed,
        count: Number(cell.count || 0),
        intensity: Number(cell.intensity || 0),
      };
    })
    .filter((cell) => !Number.isNaN(cell.date.getTime()))
    .sort((a, b) => a.date - b.date);

  if (!entries.length) {
    return { monthLabels: [], weeks: [] };
  }

  const byDate = new Map(entries.map((entry) => [entry.dateKey, entry]));
  const start = new Date(entries[0].date);
  start.setDate(start.getDate() - start.getDay());
  const end = new Date(entries[entries.length - 1].date);
  end.setDate(end.getDate() + (6 - end.getDay()));

  const weeks = [];
  const monthLabels = [];
  let cursor = new Date(start);
  let weekIndex = 0;

  while (cursor <= end) {
    const weekDays = [];
    const weekStart = new Date(cursor);

    for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
      const current = new Date(cursor);
      current.setDate(cursor.getDate() + dayIndex);
      const key = current.toISOString().slice(0, 10);
      const entry = byDate.get(key);
      weekDays.push({
        key,
        label: current.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        }),
        count: entry?.count || 0,
        bucket: getHeatmapBucket(entry?.intensity || 0),
        inRange: current >= entries[0].date && current <= entries[entries.length - 1].date,
      });
    }

    const firstOfMonth = weekDays.find((day) => day.key.endsWith("-01"));
    monthLabels.push(
      firstOfMonth ? weekStart.toLocaleDateString("en-US", { month: "short" }) : ""
    );
    weeks.push({ index: weekIndex, days: weekDays });
    cursor.setDate(cursor.getDate() + 7);
    weekIndex += 1;
  }

  return { monthLabels, weeks };
}

function formatHeatmapPeriod(period, granularity) {
  const raw = String(period || "").trim();
  if (!raw) return "Unknown";

  if (granularity === "year" && /^\d{4}$/.test(raw)) {
    return raw;
  }

  if (granularity === "month" && /^\d{4}-\d{2}$/.test(raw)) {
    const [year, month] = raw.split("-");
    const date = new Date(Number(year), Number(month) - 1, 1);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
    }
  }

  return raw;
}

function buildAggregatedHeatmapCalendar(cells, granularity) {
  const entries = [...cells]
    .map((cell) => ({
      key: String(cell.period || "").trim(),
      count: Number(cell.count || 0),
      bucket: getHeatmapBucket(Number(cell.intensity || 0)),
      label: formatHeatmapPeriod(cell.period, granularity),
    }))
    .filter((cell) => cell.key)
    .sort((a, b) => a.key.localeCompare(b.key));

  if (!entries.length) {
    return { columnLabels: [], rows: [] };
  }

  if (granularity === "month") {
    const byKey = new Map(entries.map((entry) => [entry.key, entry]));
    const years = [...new Set(entries.map((entry) => entry.key.slice(0, 4)))].sort();
    const columnLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const rows = years.map((year) => ({
      label: year,
      cells: columnLabels.map((monthLabel, index) => {
        const key = `${year}-${String(index + 1).padStart(2, "0")}`;
        const entry = byKey.get(key);
        return {
          key,
          label: entry?.label || `${monthLabel} ${year}`,
          count: entry?.count || 0,
          bucket: entry?.bucket || 0,
          inRange: Boolean(entry),
        };
      }),
    }));
    return { columnLabels, rows };
  }

  const byKey = new Map(entries.map((entry) => [entry.key, entry]));
  const years = entries.map((entry) => Number(entry.key)).filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  const startYear = years[0];
  const endYear = years[years.length - 1];
  const columnLabels = Array.from({ length: 12 }, (_, index) => `+${index}`);
  const rows = [];

  for (let cursor = startYear; cursor <= endYear; cursor += 12) {
    const rowYears = Array.from({ length: 12 }, (_, index) => cursor + index).filter((year) => year <= endYear);
    rows.push({
      label: `${cursor}${rowYears.length > 1 ? `-${rowYears[rowYears.length - 1]}` : ""}`,
      cells: rowYears.map((year) => {
        const key = String(year);
        const entry = byKey.get(key);
        return {
          key,
          label: entry?.label || key,
          count: entry?.count || 0,
          bucket: entry?.bucket || 0,
          inRange: Boolean(entry),
        };
      }),
    });
  }

  return { columnLabels, rows };
}

test("buildContributionHeatmapModel does not throw for daily heatmap data", () => {
  const model = buildContributionHeatmapModel([
    { period: "2026-03-01", count: 2, intensity: 0.2 },
    { period: "2026-03-02", count: 6, intensity: 0.8 },
    { period: "2026-03-10", count: 1, intensity: 0.1 },
  ]);

  assert.ok(model.weeks.length > 0);
  assert.equal(model.weeks[0].days.length, 7);
  assert.ok(Array.isArray(model.monthLabels));
});

test("buildAggregatedHeatmapCalendar supports month and year calendar layouts", () => {
  const monthCalendar = buildAggregatedHeatmapCalendar([
    { period: "2026-01", count: 3, intensity: 0.3 },
    { period: "2026-02", count: 8, intensity: 0.9 },
    { period: "2027-03", count: 4, intensity: 0.5 },
  ], "month");

  const yearCalendar = buildAggregatedHeatmapCalendar([
    { period: "2025", count: 10, intensity: 0.6 },
    { period: "2026", count: 12, intensity: 0.8 },
    { period: "2031", count: 5, intensity: 0.3 },
  ], "year");

  assert.equal(monthCalendar.columnLabels.length, 12);
  assert.equal(monthCalendar.rows.length, 2);
  assert.equal(monthCalendar.rows[0].label, "2026");
  assert.equal(monthCalendar.rows[0].cells[0].label, "Jan 2026");
  assert.equal(monthCalendar.rows[0].cells[2].inRange, false);

  assert.equal(yearCalendar.columnLabels.length, 12);
  assert.equal(yearCalendar.rows.length, 1);
  assert.equal(yearCalendar.rows[0].label, "2025-2031");
  assert.equal(yearCalendar.rows[0].cells[1].label, "2026");
});
