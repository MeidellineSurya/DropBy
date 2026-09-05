// Subscribes to the same /ws/live endpoint the mobile app uses. Business
// tokens are routed by app/main.py's ws_live handler onto ws:business:{id}
// and a ws:drop:{id} topic per currently live Drop (see apps/api/app/main.py).
//
// The server publishes each ws_contracts event as a flat JSON object (its
// own "type" field identifies it, e.g. {"type": "drop.capacity_reached", ...})
// rather than wrapping it in an envelope — see app/ws/manager.py's dispatch().

import { getToken } from "./auth";

const WS_URL = "ws://localhost:8000/ws/live";

export function connectLiveSocket(onEvent: (event: unknown) => void): WebSocket | null {
  const token = getToken();
  if (!token) return null;
  const socket = new WebSocket(`${WS_URL}?token=${token}`);
  socket.onmessage = (message) => {
    onEvent(JSON.parse(message.data));
  };
  return socket;
}
