import { useState } from "react";
import { useWebSocket } from "../api/useWebSocket";
import Timer from "../components/Timer";
import ActivityBadge from "../components/ActivityBadge";
import ActiveAppBadge from "../components/ActiveAppBadge";
import CameraPreview from "../components/CameraPreview";
import SessionControls from "../components/SessionControls";

export default function SessionPage() {
  const { state, isConnected } = useWebSocket();
  const [plannedMinutes, setPlannedMinutes] = useState(25);

  const isActive = state.session_state !== "stopped";

  return (
    <div className="bg-gray-900 text-gray-100 min-h-screen">
      <main className="max-w-3xl mx-auto px-6 py-8 space-y-8">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono uppercase tracking-wider text-gray-500">
            Live Session Mode
          </span>
          <span
            className={`text-xs px-2.5 py-1 rounded-full border ${
              isConnected
                ? "bg-green-950/60 text-green-300 border-green-800"
                : "bg-red-950/60 text-red-300 border-red-800"
            }`}
          >
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>

        {/* Timer */}
        <Timer
          elapsedSec={state.elapsed_sec}
          plannedDurationSec={
            isActive ? state.planned_duration_sec : plannedMinutes * 60
          }
        />

        {/* Live Detected Activities (Posture & Objects) */}
        {isActive && (
          <ActivityBadge activities={state.current_activities} />
        )}

        {/* Active Foreground Application */}
        {isActive && (
          <ActiveAppBadge activeApp={state.active_app} />
        )}

        {/* Controls */}
        <SessionControls
          sessionState={state.session_state}
          plannedMinutes={plannedMinutes}
          onPlannedMinutesChange={setPlannedMinutes}
        />

        {/* Camera Preview Stream - active during session */}
        <CameraPreview visible={isActive} />
      </main>
    </div>
  );
}
