import { useEffect, useRef, useState, useCallback } from "react";

export interface SessionState {
  session_state: "running" | "paused" | "stopped";
  elapsed_sec: number;
  planned_duration_sec: number;
  current_activities: string[];
  active_app: { name: string; title: string } | null;
}

const WS_URL = "ws://localhost:8000/ws";
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 8000;

export function useWebSocket() {
  const [state, setState] = useState<SessionState>({
    session_state: "stopped",
    elapsed_sec: 0,
    planned_duration_sec: 0,
    current_activities: [],
    active_app: null,
  });
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryDelay = useRef(RECONNECT_BASE_MS);

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      retryDelay.current = RECONNECT_BASE_MS;
    };

    ws.onmessage = (event) => {
      try {
        setState(JSON.parse(event.data));
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
      const delay = retryDelay.current;
      retryDelay.current = Math.min(delay * 2, RECONNECT_MAX_MS);
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { state, isConnected };
}
