import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { authenticate } from "../plugins/auth.js";
import { findNearbyDrops } from "../services/drop-service.js";

const coordinatesSchema = z.object({
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
});

export async function dropRoutes(app: FastifyInstance): Promise<void> {
  app.get("/nearby", { preHandler: authenticate }, async (request) => {
    const { latitude, longitude } = coordinatesSchema.parse(request.query);
    const drops = app.demo
      ? app.demo.nearby(request.user.sub, latitude, longitude)
      : await findNearbyDrops(app.db, request.user.sub, latitude, longitude);
    return { drops, observedAt: new Date().toISOString() };
  });
}
