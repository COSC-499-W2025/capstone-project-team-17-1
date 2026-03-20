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
