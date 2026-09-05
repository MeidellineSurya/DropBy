import "dotenv/config";
import { z } from "zod";

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  DEMO_MODE: z.enum(["true", "false"]).default("false").transform((value) => value === "true"),
  PORT: z.coerce.number().int().min(1).max(65_535).default(3000),
  HOST: z.string().default("0.0.0.0"),
  DATABASE_URL: z.string().min(1).default("postgresql://dropby:dropby@localhost:5432/dropby"),
  REDIS_URL: z.string().min(1).default("redis://localhost:6379"),
  JWT_SECRET: z.string().min(32).default("development-only-secret-change-me-now"),
  JWT_EXPIRES_IN: z.string().default("15m"),
  CORS_ORIGIN: z.string().default("http://localhost:8081"),
});

export type Config = z.infer<typeof envSchema>;

export function loadConfig(environment: NodeJS.ProcessEnv = process.env): Config {
  const result = envSchema.safeParse(environment);
  if (!result.success) {
    throw new Error(`Invalid configuration: ${z.prettifyError(result.error)}`);
  }
  return result.data;
}
