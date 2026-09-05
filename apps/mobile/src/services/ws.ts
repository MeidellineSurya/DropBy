import type { WsEvent } from "@dropby/shared-types";

const WS_URL = "ws://localhost:8000/ws/live";

export function connectLiveSocket(token: string, onEvent: (event: WsEvent) => void): WebSocket {
  const socket = new WebSocket(`${WS_URL}?token=${token}`);
  socket.onmessage = (message) => {
    const envelope = JSON.parse(message.data);
    onEvent(envelope.payload as WsEvent);
  };
  return socket;
}
