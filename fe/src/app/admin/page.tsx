import { RatingBar } from "@/admin/components/RatingBar";
import { StatCard } from "@/admin/components/StatCard";
import type { StatsResponse } from "@/lib/types";

export default async function AdminPage() {
  let stats: StatsResponse;

  try {
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    const res = await fetch(`${backendUrl}/stats`, {
      next: { revalidate: 30 },
    });
    if (!res.ok) throw new Error("Stats fetch failed");
    stats = (await res.json()) as StatsResponse;
  } catch {
    return (
      <main className="max-w-4xl mx-auto p-8">
        <p className="text-red-600">Failed to load stats. Is the backend running?</p>
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
        <a href="/" className="text-sm text-blue-600 hover:underline">
          Back to Composer
        </a>
      </div>

      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <StatCard label="Total Generations" value={String(stats.total_generations)} />
        <StatCard label="Avg Rating" value={`${stats.avg_rating.toFixed(1)} / 5`} />
        <StatCard
          label="Avg Processing Time"
          value={`${Math.round(stats.avg_processing_time_ms)} ms`}
        />
      </dl>

      <section>
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Rating Distribution</h2>
        <RatingBar distribution={stats.rating_distribution} />
      </section>
    </main>
  );
}
