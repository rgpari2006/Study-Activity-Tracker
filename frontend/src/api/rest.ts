const BASE_URL = "http://localhost:8000";

async function post(path: string, body?: unknown): Promise<unknown> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export function startSession(plannedDurationSec: number) {
  return post("/sessions/start", { planned_duration_sec: plannedDurationSec });
}

export function pauseSession() {
  return post("/sessions/pause");
}

export function resumeSession() {
  return post("/sessions/resume");
}

export function stopSession() {
  return post("/sessions/stop");
}
