// Mirrors apps/mobile/src/services/ws.ts — the dashboard subscribes to the
// same ws/live endpoint, listening for ws:drop:{id} and ws:business:{id}
// topics for its live capacity/redemption queue view. Event shapes are
// defined once in packages/ws-contracts/ws_contracts/events.py.

const WS_URL = "ws://localhost:8000/ws/live";

export function connectLiveSocket(token: string, onEvent: (event: unknown) => void): WebSocket {
  const socket = new WebSocket(`${WS_URL}?token=${token}`);
  socket.onmessage = (message) => {
    const envelope = JSON.parse(message.data);
    onEvent(envelope.payload);
  };
  return socket;
}
