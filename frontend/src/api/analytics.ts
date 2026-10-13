const BASE_URL = "http://localhost:8000";

export interface ActivitySummaryItem {
  label: string;
  duration_sec: number;
}

export interface AppSummaryItem {
  app_name: string;
  duration_sec: number;
}

export interface AnalyticsSummary {
  session_count: number;
  total_session_sec: number;
  total_paused_sec: number;
  activities: ActivitySummaryItem[];
  apps: AppSummaryItem[];
}

export interface DailyAnalyticsItem {
  date: string;
  session_count: number;
  total_session_sec: number;
  total_paused_sec: number;
  activities: Record<string, number>;
}

export interface WeeklyAnalyticsItem {
  week: string;
  session_count: number;
  total_session_sec: number;
  total_paused_sec: number;
}

export interface SessionRecord {
  id: number;
  start_time: number;
  end_time: number | null;
  planned_duration_sec: number;
  paused_total_sec: number;
}

export async function fetchSummary(from?: number, to?: number): Promise<AnalyticsSummary> {
  const params = new URLSearchParams();
  if (from !== undefined) params.append("from", String(from));
  if (to !== undefined) params.append("to", String(to));
  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${BASE_URL}/analytics/summary${query}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchDaily(): Promise<DailyAnalyticsItem[]> {
  const res = await fetch(`${BASE_URL}/analytics/daily`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchWeekly(): Promise<WeeklyAnalyticsItem[]> {
  const res = await fetch(`${BASE_URL}/analytics/weekly`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchSessions(): Promise<SessionRecord[]> {
  const res = await fetch(`${BASE_URL}/sessions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
