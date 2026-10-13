import { useState } from "react";
import {
  startSession,
  pauseSession,
  resumeSession,
  stopSession,
} from "../api/rest";

interface SessionControlsProps {
  sessionState: "running" | "paused" | "stopped";
  plannedMinutes: number;
  onPlannedMinutesChange: (m: number) => void;
}

const PRESET_MINUTES = [25, 45, 60, 90];

export default function SessionControls({
  sessionState,
  plannedMinutes,
  onPlannedMinutesChange,
}: SessionControlsProps) {
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    if (loading) return;
    try {
      setLoading(true);
      await startSession(plannedMinutes * 60);
    } catch (e) {
      console.error("Failed to start session", e);
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    if (loading) return;
    try {
      setLoading(true);
      await pauseSession();
    } catch (e) {
      console.error("Failed to pause session", e);
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async () => {
    if (loading) return;
    try {
      setLoading(true);
      await resumeSession();
    } catch (e) {
      console.error("Failed to resume session", e);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (loading) return;
    try {
      setLoading(true);
      await stopSession();
    } catch (e) {
      console.error("Failed to stop session", e);
    } finally {
      setLoading(false);
    }
  };

  const btnBase =
    "px-6 py-2.5 rounded-lg font-semibold text-sm transition-all cursor-pointer shadow-sm disabled:opacity-50 disabled:cursor-not-allowed";

  if (sessionState === "stopped") {
    return (
      <div className="space-y-4 max-w-lg mx-auto w-full">
        {/* Duration picker */}
        <div className="flex items-center justify-center gap-2 flex-wrap">
          {PRESET_MINUTES.map((m) => (
            <button
              key={m}
              onClick={() => onPlannedMinutesChange(m)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                plannedMinutes === m
                  ? "bg-blue-600 text-white shadow-sm"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700/60"
              }`}
            >
              {m}m
            </button>
          ))}
          <div className="flex items-center gap-1 bg-gray-800 px-2 py-1 rounded-lg border border-gray-700/60">
            <input
              type="number"
              min={1}
              max={480}
              value={plannedMinutes}
              onChange={(e) => onPlannedMinutesChange(Math.max(1, Number(e.target.value) || 25))}
              className="w-14 bg-transparent text-gray-100 text-xs text-center focus:outline-none font-mono"
            />
            <span className="text-gray-400 text-xs">min</span>
          </div>
        </div>
        <div className="flex justify-center">
          <button
            onClick={handleStart}
            disabled={loading}
            className={`${btnBase} bg-blue-600 hover:bg-blue-500 text-white px-8`}
          >
            {loading ? "Starting..." : "Start Session"}
          </button>
        </div>
      </div>
    );
  }

  if (sessionState === "running") {
    return (
      <div className="flex justify-center gap-3">
        <button
          onClick={handlePause}
          disabled={loading}
          className={`${btnBase} bg-amber-600 hover:bg-amber-500 text-white`}
        >
          {loading ? "..." : "Pause"}
        </button>
        <button
          onClick={handleStop}
          disabled={loading}
          className={`${btnBase} bg-rose-700 hover:bg-rose-600 text-white`}
        >
          {loading ? "..." : "Stop"}
        </button>
      </div>
    );
  }

  // paused
  return (
    <div className="flex justify-center gap-3">
      <button
        onClick={handleResume}
        disabled={loading}
        className={`${btnBase} bg-emerald-600 hover:bg-emerald-500 text-white`}
      >
        {loading ? "..." : "Resume"}
      </button>
      <button
        onClick={handleStop}
        disabled={loading}
        className={`${btnBase} bg-rose-700 hover:bg-rose-600 text-white`}
      >
        {loading ? "..." : "Stop"}
      </button>
    </div>
  );
}
