import { useEffect, useState, useMemo } from "react";
import {
  fetchSummary,
  fetchDaily,
    fetchSessions,
  type AnalyticsSummary,
  type DailyAnalyticsItem,
    type SessionRecord,
} from "../api/analytics";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";

type DateFilterPreset = "all" | "today" | "7d" | "30d";

const CHART_COLORS = [
  "#3b82f6", // blue
  "#6366f1", // indigo
  "#0ea5e9", // sky
  "#8b5cf6", // purple
  "#64748b", // slate
  "#94a3b8", // light slate
  "#a1a1aa", // zinc
];

function formatDuration(totalSeconds: number): string {
  const sec = Math.round(totalSeconds);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) {
    return `${h}h ${m}m`;
  }
  if (m > 0) {
    return `${m}m ${s}s`;
  }
  return `${s}s`;
}

function formatHours(seconds: number): number {
  return parseFloat((seconds / 3600).toFixed(2));
}

function formatMinutes(seconds: number): number {
  return parseFloat((seconds / 60).toFixed(1));
}

export default function AnalyticsPage() {
  const [filter, setFilter] = useState<DateFilterPreset>("all");
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [daily, setDaily] = useState<DailyAnalyticsItem[]>([]);
    const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  // Compute 'from' timestamp based on active filter
  const fromTimestamp = useMemo(() => {
    const now = new Date();
    if (filter === "today") {
      const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      return todayStart.getTime() / 1000;
    }
    if (filter === "7d") {
      return (now.getTime() - 7 * 24 * 3600 * 1000) / 1000;
    }
    if (filter === "30d") {
      return (now.getTime() - 30 * 24 * 3600 * 1000) / 1000;
    }
    return undefined;
  }, [filter]);

  useEffect(() => {
    let isCancelled = false;
    setLoading(true);

    Promise.all([
      fetchSummary(fromTimestamp),
      fetchDaily(),
            fetchSessions(),
    ])
      .then(([sumData, dailyData, sessionsData]) => {
        if (!isCancelled) {
          setSummary(sumData);
          setDaily(dailyData);
                    setSessions(sessionsData);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch analytics:", err);
        if (!isCancelled) setLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [fromTimestamp]);

  // Chart data transformations
  const activityChartData = useMemo(() => {
    if (!summary) return [];
    return summary.activities.map((act) => ({
      name: act.label.charAt(0).toUpperCase() + act.label.slice(1),
      minutes: formatMinutes(act.duration_sec),
      duration: formatDuration(act.duration_sec),
    }));
  }, [summary]);

  const appChartData = useMemo(() => {
    if (!summary) return [];
    return summary.apps.slice(0, 8).map((app) => ({
      name: app.app_name,
      minutes: formatMinutes(app.duration_sec),
      duration: formatDuration(app.duration_sec),
    }));
  }, [summary]);

  const dailyChartData = useMemo(() => {
    return daily.map((d) => ({
      date: d.date.slice(5), // MM-DD
      hours: formatHours(d.total_session_sec),
      duration: formatDuration(d.total_session_sec),
    }));
  }, [daily]);

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 pb-16">
      <main className="max-w-5xl mx-auto px-6 pt-8 space-y-8">
        {/* Title & Filter Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-800">
          <div>
            <h1 className="text-2xl font-bold text-gray-100">Analytics</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              Recorded study sessions and activity intervals
            </p>
          </div>
          <div className="flex items-center gap-1.5 bg-gray-800/80 p-1 rounded-lg border border-gray-700/80 self-start sm:self-auto">
            {(
              [
                ["all", "All Time"],
                ["today", "Today"],
                ["7d", "Last 7 Days"],
                ["30d", "Last 30 Days"],
              ] as [DateFilterPreset, string][]
            ).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                  filter === key
                    ? "bg-gray-700 text-white shadow-sm"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20 text-gray-500 font-mono text-sm">
            Loading analytics data...
          </div>
        ) : (
          <>
            {/* Metric Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-5">
                <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Total Session Time
                </span>
                <p className="text-3xl font-mono font-bold text-gray-100 mt-2">
                  {summary ? formatDuration(summary.total_session_sec) : "0s"}
                </p>
              </div>
              <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-5">
                <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Total Paused Time
                </span>
                <p className="text-3xl font-mono font-bold text-gray-100 mt-2">
                  {summary ? formatDuration(summary.total_paused_sec) : "0s"}
                </p>
              </div>
              <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-5">
                <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Recorded Sessions
                </span>
                <p className="text-3xl font-mono font-bold text-gray-100 mt-2">
                  {summary?.session_count ?? 0}
                </p>
              </div>
            </div>

            {/* Plain Activity Durations Table */}
            <div className="bg-gray-800/50 border border-gray-700/70 rounded-xl p-6">
              <h2 className="text-base font-semibold text-gray-200 mb-4">
                Camera Activity Durations
              </h2>
              {summary?.activities.length === 0 ? (
                <p className="text-sm text-gray-500 italic">No activity recorded yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-gray-700 text-xs text-gray-400 uppercase tracking-wider">
                        <th className="pb-3 font-medium">Activity</th>
                        <th className="pb-3 font-medium text-right">Recorded Duration</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800 font-mono">
                      {summary?.activities.map((act) => (
                        <tr key={act.label} className="hover:bg-gray-800/30">
                          <td className="py-2.5 font-sans font-medium text-gray-200">
                            {act.label.charAt(0).toUpperCase() + act.label.slice(1)}
                          </td>
                          <td className="py-2.5 text-right text-gray-300">
                            {formatDuration(act.duration_sec)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Visual Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Camera Activities Chart */}
              <div className="bg-gray-800/50 border border-gray-700/70 rounded-xl p-6 flex flex-col">
                <h2 className="text-base font-semibold text-gray-200 mb-4">
                  Activity Distribution (Minutes)
                </h2>
                {activityChartData.length === 0 ? (
                  <p className="text-sm text-gray-500 italic my-auto">No data to display.</p>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={activityChartData} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                        <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} />
                        <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#1e293b", borderColor: "#475569", borderRadius: 8 }}
                          formatter={(value: any) => [`${value} min`, "Duration"]}
                        />
                        <Bar dataKey="minutes" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                          {activityChartData.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Application Usage Chart */}
              <div className="bg-gray-800/50 border border-gray-700/70 rounded-xl p-6 flex flex-col">
                <h2 className="text-base font-semibold text-gray-200 mb-4">
                  Application Usage (Minutes)
                </h2>
                {appChartData.length === 0 ? (
                  <p className="text-sm text-gray-500 italic my-auto">No app events recorded yet.</p>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={appChartData} layout="vertical" margin={{ top: 5, right: 20, left: 30, bottom: 5 }}>
                        <XAxis type="number" stroke="#94a3b8" fontSize={12} tickLine={false} />
                        <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={12} tickLine={false} width={80} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#1e293b", borderColor: "#475569", borderRadius: 8 }}
                          formatter={(value: any) => [`${value} min`, "Usage"]}
                        />
                        <Bar dataKey="minutes" fill="#6366f1" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Daily History Chart */}
              <div className="bg-gray-800/50 border border-gray-700/70 rounded-xl p-6 lg:col-span-2 flex flex-col">
                <h2 className="text-base font-semibold text-gray-200 mb-4">
                  Daily Session History (Hours)
                </h2>
                {dailyChartData.length === 0 ? (
                  <p className="text-sm text-gray-500 italic my-auto">No past daily history.</p>
                ) : (
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={dailyChartData} margin={{ top: 10, right: 20, left: -10, bottom: 10 }}>
                        <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickLine={false} />
                        <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: "#1e293b", borderColor: "#475569", borderRadius: 8 }}
                          formatter={(value: any) => [`${value} hrs`, "Session Time"]}
                        />
                        <Bar dataKey="hours" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </div>

            {/* Past Sessions List */}
            <div className="bg-gray-800/50 border border-gray-700/70 rounded-xl p-6">
              <h2 className="text-base font-semibold text-gray-200 mb-4">
                Recorded Sessions History
              </h2>
              {sessions.length === 0 ? (
                <p className="text-sm text-gray-500 italic">No past sessions.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-gray-700 text-xs text-gray-400 uppercase tracking-wider">
                        <th className="pb-3 font-medium">Session ID</th>
                        <th className="pb-3 font-medium">Start Time</th>
                        <th className="pb-3 font-medium text-right">Planned Duration</th>
                        <th className="pb-3 font-medium text-right">Total Elapsed</th>
                        <th className="pb-3 font-medium text-right">Paused Duration</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800 font-mono text-xs">
                      {sessions.map((s) => {
                        const startDate = new Date(s.start_time * 1000).toLocaleString();
                        const elapsed = s.end_time
                          ? Math.max(0, s.end_time - s.start_time - s.paused_total_sec)
                          : 0;
                        return (
                          <tr key={s.id} className="hover:bg-gray-800/30">
                            <td className="py-2.5 font-sans font-medium text-gray-300">
                              #{s.id}
                            </td>
                            <td className="py-2.5 text-gray-300 font-sans">
                              {startDate}
                            </td>
                            <td className="py-2.5 text-right text-gray-400">
                              {formatDuration(s.planned_duration_sec)}
                            </td>
                            <td className="py-2.5 text-right text-gray-200 font-semibold">
                              {formatDuration(elapsed)}
                            </td>
                            <td className="py-2.5 text-right text-gray-400">
                              {formatDuration(s.paused_total_sec)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
