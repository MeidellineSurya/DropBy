import cors from "@fastify/cors";
import Fastify, { type FastifyInstance } from "fastify";
import { ZodError, z } from "zod";
import type { Config } from "./config.js";
import { loadConfig } from "./config.js";
import { createPool } from "./db/pool.js";
import { AppError } from "./errors.js";
import { demoPage } from "./demo/page.js";
import { DemoStore } from "./demo/store.js";
import { registerAuth } from "./plugins/auth.js";
import { configureRealtime } from "./realtime.js";
import { authRoutes } from "./routes/auth.js";
import { dropRoutes } from "./routes/drops.js";
import { groupRoutes } from "./routes/groups.js";
import { onboardingRoutes } from "./routes/onboarding.js";

export async function buildApp(config: Config = loadConfig()): Promise<FastifyInstance> {
  const app = Fastify({
    logger: config.NODE_ENV !== "test" ? { level: config.NODE_ENV === "production" ? "info" : "debug" } : false,
    trustProxy: config.NODE_ENV === "production",
  });

  app.decorate("config", config);
  app.decorate("demo", config.DEMO_MODE ? new DemoStore() : null);
  const db = createPool(config.DATABASE_URL);
  app.decorate("db", db);

  await app.register(cors, {
    origin: config.CORS_ORIGIN.split(",").map((origin) => origin.trim()),
    credentials: true,
  });
  await registerAuth(app);
  const redis = configureRealtime(app);

  app.get("/health", async (_request, reply) => {
    if (config.DEMO_MODE) {
      return { status: "ok", mode: "demo", timestamp: new Date().toISOString() };
    }
    try {
      await Promise.all([db.query("SELECT 1"), redis.pub?.ping()]);
      return { status: "ok", timestamp: new Date().toISOString() };
    } catch {
      return reply.code(503).send({ status: "unavailable", timestamp: new Date().toISOString() });
    }
  });

  app.get("/", async (_request, reply) => {
    if (config.DEMO_MODE) return reply.type("text/html; charset=utf-8").send(demoPage);
    return {
      name: "DropBy API",
      status: "running",
      health: "/health",
      documentation: "README.md",
    };
  });

  await app.register(authRoutes, { prefix: "/v1/auth" });
  await app.register(onboardingRoutes, { prefix: "/v1/onboarding" });
  await app.register(dropRoutes, { prefix: "/v1/drops" });
  await app.register(groupRoutes, { prefix: "/v1/groups" });

  app.setNotFoundHandler((_request, reply) => {
    reply.code(404).send({ error: "NOT_FOUND", message: "Route not found" });
  });

  app.setErrorHandler((error, request, reply) => {
    if (error instanceof ZodError) {
      return reply.code(400).send({
        error: "VALIDATION_ERROR",
        message: "Request validation failed",
        issues: z.treeifyError(error),
      });
    }
    if (error instanceof AppError) {
      return reply.code(error.statusCode).send({ error: error.code, message: error.message });
    }
    if (typeof error === "object" && error !== null && "statusCode" in error && error.statusCode === 401) {
      return reply.code(401).send({ error: "UNAUTHORIZED", message: "Authentication required" });
    }
    request.log.error({ error }, "Unhandled request error");
    return reply.code(500).send({ error: "INTERNAL_ERROR", message: "An unexpected error occurred" });
  });

  app.addHook("onClose", async () => {
    await app.io.close();
    await Promise.allSettled([
      ...(redis.pub ? [redis.pub.quit()] : []),
      ...(redis.sub ? [redis.sub.quit()] : []),
      db.end(),
    ]);
  });

  return app;
}
