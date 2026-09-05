import { buildApp } from "./app.js";
import { loadConfig } from "./config.js";

const config = loadConfig();
const app = await buildApp(config);

const shutdown = async (signal: string): Promise<void> => {
  app.log.info({ signal }, "Shutting down");
  await app.close();
  process.exit(0);
};

process.once("SIGINT", () => void shutdown("SIGINT"));
process.once("SIGTERM", () => void shutdown("SIGTERM"));

try {
  await app.listen({ port: config.PORT, host: config.HOST });
} catch (error) {
  app.log.error(error);
  process.exitCode = 1;
}
