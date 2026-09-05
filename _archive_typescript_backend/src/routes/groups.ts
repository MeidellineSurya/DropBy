import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { authenticate } from "../plugins/auth.js";
import { createGroup, getGroup, joinGroup, leaveGroup } from "../services/group-service.js";
import { findNearbyDrops } from "../services/drop-service.js";

const paramsSchema = z.object({ groupId: z.uuid() });
const createSchema = z.object({ dropId: z.uuid(), openToNearby: z.boolean().default(false) });
const coordinatesSchema = z.object({
  latitude: z.coerce.number().min(-90).max(90),
  longitude: z.coerce.number().min(-180).max(180),
});

export async function groupRoutes(app: FastifyInstance): Promise<void> {
  app.get("/open", { preHandler: authenticate }, async (request) => {
    const { latitude, longitude } = coordinatesSchema.parse(request.query);
    if (app.demo) {
      return { groups: app.demo.openGroups(request.user.sub, latitude, longitude) };
    }
    const drops = await findNearbyDrops(app.db, request.user.sub, latitude, longitude);
    if (drops.length === 0) return { groups: [] };
    const dropById = new Map(drops.map((drop) => [drop.id, drop]));
    const result = await app.db.query<{
      id: string;
      drop_id: string;
      minimum_size: number;
      maximum_size: number;
      expires_at: Date;
      member_count: number;
    }>(
      `SELECT g.id, g.drop_id, g.minimum_size, g.maximum_size, g.expires_at,
              count(gm.user_id)::int AS member_count
       FROM groups g
       JOIN group_members gm ON gm.group_id = g.id
       WHERE g.open_to_nearby = true
         AND g.status = 'forming'
         AND g.expires_at > now()
         AND g.drop_id = ANY($1::uuid[])
       GROUP BY g.id
       ORDER BY g.expires_at ASC`,
      [drops.map((drop) => drop.id)],
    );
    return {
      groups: result.rows.map((group) => ({
        id: group.id,
        memberCount: group.member_count,
        minimumSize: group.minimum_size,
        maximumSize: group.maximum_size,
        spotsNeeded: Math.max(0, group.minimum_size - group.member_count),
        expiresAt: group.expires_at.toISOString(),
        drop: dropById.get(group.drop_id),
      })),
    };
  });

  app.post("/", { preHandler: authenticate }, async (request, reply) => {
    const body = createSchema.parse(request.body);
    const group = app.demo
      ? app.demo.createGroup(request.user.sub, body.dropId, body.openToNearby)
      : await createGroup(app.db, request.user.sub, body.dropId, body.openToNearby);
    app.io.in(`user:${request.user.sub}`).socketsJoin(`group:${group.id}`);
    app.io.to(`group:${group.id}`).emit("squad.updated", group);
    return reply.code(201).send({ group });
  });

  app.get("/:groupId", { preHandler: authenticate }, async (request) => {
    const { groupId } = paramsSchema.parse(request.params);
    return {
      group: app.demo
        ? app.demo.getGroup(groupId, request.user.sub)
        : await getGroup(app.db, groupId, request.user.sub),
    };
  });

  app.post("/:groupId/join", { preHandler: authenticate }, async (request) => {
    const { groupId } = paramsSchema.parse(request.params);
    const group = app.demo
      ? app.demo.joinGroup(request.user.sub, groupId)
      : await joinGroup(app.db, request.user.sub, groupId);
    app.io.in(`user:${request.user.sub}`).socketsJoin(`group:${group.id}`);
    app.io.to(`group:${group.id}`).emit("squad.updated", group);
    return { group };
  });

  app.post("/:groupId/leave", { preHandler: authenticate }, async (request, reply) => {
    const { groupId } = paramsSchema.parse(request.params);
    const group = app.demo
      ? app.demo.leaveGroup(request.user.sub, groupId)
      : await leaveGroup(app.db, request.user.sub, groupId);
    app.io.in(`user:${request.user.sub}`).socketsLeave(`group:${groupId}`);
    app.io.to(`group:${groupId}`).emit(group ? "squad.updated" : "squad.cancelled", group ?? { groupId });
    return reply.send({ group });
  });
}
