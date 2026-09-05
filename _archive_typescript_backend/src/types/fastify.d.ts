import type { Pool } from "pg";
import type { Server as SocketServer } from "socket.io";
import type { Config } from "../config.js";
import type { DemoStore } from "../demo/store.js";

declare module "fastify" {
  interface FastifyInstance {
    config: Config;
    db: Pool;
    io: SocketServer;
    demo: DemoStore | null;
  }

  interface FastifyRequest {
    user: {
      sub: string;
      email: string;
    };
  }
}

declare module "@fastify/jwt" {
  interface FastifyJWT {
    payload: { sub: string; email: string };
    user: { sub: string; email: string };
  }
}
