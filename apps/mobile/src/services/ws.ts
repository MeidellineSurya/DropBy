import type { LiveEvent } from "../types";
import { API_ORIGIN } from "./api";

const WS_URL = `${API_ORIGIN.replace(/^http/, "ws")}/ws/live`;

export function connectLiveSocket(
  token: string,
  onEvent: (event: LiveEvent) => void,
  onConnectionChange?: (connected: boolean) => void,
): WebSocket {
  const socket = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
  socket.onopen = () => onConnectionChange?.(true);
  socket.onclose = () => onConnectionChange?.(false);
  socket.onerror = () => onConnectionChange?.(false);
  socket.onmessage = (message) => {
    onEvent(JSON.parse(message.data) as LiveEvent);
  };
  return socket;
}
