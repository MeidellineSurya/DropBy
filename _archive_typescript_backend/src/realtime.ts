import { createAdapter } from "@socket.io/redis-adapter";
import { Redis } from "ioredis";
import type { FastifyInstance } from "fastify";
import { Server as SocketServer } from "socket.io";

export function configureRealtime(app: FastifyInstance): { pub: Redis | null; sub: Redis | null } {
  const io = new SocketServer(app.server, {
    cors: {
      origin: app.config.CORS_ORIGIN.split(",").map((origin) => origin.trim()),
      credentials: true,
    },
  });
  io.use(async (socket, next) => {
    try {
      const rawToken = socket.handshake.auth.token ?? socket.handshake.headers.authorization;
      if (typeof rawToken !== "string") return next(new Error("AUTH_REQUIRED"));
      const token = rawToken.startsWith("Bearer ") ? rawToken.slice(7) : rawToken;
      const payload = app.jwt.verify<{ sub: string; email: string }>(token);
      socket.data.userId = payload.sub;
      next();
    } catch {
      next(new Error("INVALID_TOKEN"));
    }
  });

  if (app.config.DEMO_MODE) {
    io.on("connection", async (socket) => {
      const userId = socket.data.userId as string;
      await socket.join(`user:${userId}`);
      await socket.join(app.demo?.activeGroupIds(userId).map((id) => `group:${id}`) ?? []);
    });
    app.decorate("io", io);
    return { pub: null, sub: null };
  }

  const pub = new Redis(app.config.REDIS_URL, { lazyConnect: true, maxRetriesPerRequest: 1 });
  // Redis subscriptions are long-lived. Disabling their per-request retry limit
  // prevents a temporary Redis outage from crashing the API during startup.
  const sub = new Redis(app.config.REDIS_URL, { lazyConnect: true, maxRetriesPerRequest: null });
  let redisWarningLogged = false;
  const handleRedisError = (error: Error): void => {
    if (redisWarningLogged) return;
    redisWarningLogged = true;
    app.log.warn({ error: error.message }, "Redis unavailable; realtime fan-out will reconnect automatically");
  };
  pub.on("error", handleRedisError);
  sub.on("error", handleRedisError);
  pub.on("ready", () => {
    if (redisWarningLogged) app.log.info("Redis connection restored");
    redisWarningLogged = false;
  });
  io.adapter(createAdapter(pub, sub));

  io.on("connection", async (socket) => {
    const userId = socket.data.userId as string;
    await socket.join(`user:${userId}`);
    try {
      const result = await app.db.query<{ group_id: string }>(
        `SELECT gm.group_id
         FROM group_members gm JOIN groups g ON g.id = gm.group_id
         WHERE gm.user_id = $1
           AND g.status IN ('forming', 'ready', 'en_route', 'checked_in')`,
        [userId],
      );
      await socket.join(result.rows.map((row) => `group:${row.group_id}`));
    } catch (error) {
      app.log.error({ error, userId }, "Failed to restore socket squad subscriptions");
      socket.disconnect(true);
    }
  });

  app.decorate("io", io);
  return { pub, sub };
}
