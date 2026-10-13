import { useState, useEffect } from "react";

interface CameraPreviewProps {
  visible: boolean;
}

const VIDEO_FEED_URL = "http://localhost:8000/video_feed";

export default function CameraPreview({ visible }: CameraPreviewProps) {
  const [streamError, setStreamError] = useState(false);
  const [feedUrl, setFeedUrl] = useState("");

  useEffect(() => {
    if (visible) {
      setStreamError(false);
      // Append cache buster timestamp to ensure a fresh multipart stream connection
      setFeedUrl(`${VIDEO_FEED_URL}?t=${Date.now()}`);
    } else {
      setFeedUrl("");
    }
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="flex flex-col items-center gap-2 max-w-lg mx-auto w-full">
      <div className="w-full relative aspect-video bg-gray-950 rounded-xl overflow-hidden border border-gray-700/80 shadow-lg flex items-center justify-center">
        {streamError ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 gap-2 p-4 text-center">
            <span className="text-amber-400 text-sm font-semibold">Camera Stream Offline</span>
            <span className="text-xs font-mono text-gray-500">
              Ensure backend server is running on port 8000.
            </span>
            <button
              onClick={() => {
                setStreamError(false);
                setFeedUrl(`${VIDEO_FEED_URL}?t=${Date.now()}`);
              }}
              className="mt-2 px-3 py-1 text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 rounded border border-gray-600 transition-colors cursor-pointer"
            >
              Retry Connection
            </button>
          </div>
        ) : (
          feedUrl && (
            <img
              src={feedUrl}
              alt="Live camera stream"
              onError={() => setStreamError(true)}
              className="w-full h-full object-cover"
            />
          )
        )}
      </div>
      <span className="text-[11px] text-gray-400 font-mono tracking-tight">
        Local Camera Stream • No video stored
      </span>
    </div>
  );
}
