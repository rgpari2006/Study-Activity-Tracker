interface TimerProps {
  elapsedSec: number;
  plannedDurationSec: number;
}

function formatTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function Timer({ elapsedSec, plannedDurationSec }: TimerProps) {
  const progress =
    plannedDurationSec > 0
      ? Math.min((elapsedSec / plannedDurationSec) * 100, 100)
      : 0;

  return (
    <div className="text-center">
      <p className="text-6xl font-mono font-bold text-gray-100 tabular-nums">
        {formatTime(elapsedSec)}
      </p>
      <p className="text-lg text-gray-400 mt-1">
        of {formatTime(plannedDurationSec)}
      </p>
      {/* Progress bar */}
      <div className="mt-4 w-full bg-gray-700 rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
