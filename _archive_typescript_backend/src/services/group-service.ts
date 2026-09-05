import type { Pool, PoolClient } from "pg";
import { badRequest, conflict, forbidden, notFound } from "../errors.js";
import type { GroupSnapshot } from "../types/domain.js";
import { transaction } from "../db/transaction.js";

interface GroupRow {
  id: string;
  drop_id: string;
  leader_id: string;
  status: GroupSnapshot["status"];
  open_to_nearby: boolean;
  minimum_size: number;
  maximum_size: number;
  expires_at: Date;
}

interface MemberRow {
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  role: "leader" | "member";
  joined_at: Date;
}

async function snapshot(client: Pool | PoolClient, groupId: string): Promise<GroupSnapshot> {
  const groupResult = await client.query<GroupRow>(
    `SELECT id, drop_id, leader_id, status, open_to_nearby, minimum_size, maximum_size, expires_at
     FROM groups WHERE id = $1`,
    [groupId],
  );
  const group = groupResult.rows[0];
  if (!group) throw notFound("GROUP_NOT_FOUND", "Squad not found");

  const membersResult = await client.query<MemberRow>(
    `SELECT gm.user_id, u.display_name, u.avatar_url, gm.role, gm.joined_at
     FROM group_members gm
     JOIN users u ON u.id = gm.user_id
     WHERE gm.group_id = $1
     ORDER BY gm.joined_at ASC`,
    [groupId],
  );

  return {
    id: group.id,
    dropId: group.drop_id,
    leaderId: group.leader_id,
    status: group.status,
    openToNearby: group.open_to_nearby,
    minimumSize: group.minimum_size,
    maximumSize: group.maximum_size,
    memberCount: membersResult.rowCount ?? 0,
    expiresAt: group.expires_at.toISOString(),
    members: membersResult.rows.map((member) => ({
      userId: member.user_id,
      displayName: member.display_name,
      avatarUrl: member.avatar_url,
      role: member.role,
      joinedAt: member.joined_at.toISOString(),
    })),
  };
}

export async function getGroup(db: Pool, groupId: string, userId: string): Promise<GroupSnapshot> {
  const membership = await db.query(
    "SELECT 1 FROM group_members WHERE group_id = $1 AND user_id = $2",
    [groupId, userId],
  );
  if (membership.rowCount === 0) throw forbidden("NOT_A_MEMBER", "You are not a member of this squad");
  return snapshot(db, groupId);
}

export async function createGroup(
  db: Pool,
  userId: string,
  dropId: string,
  openToNearby: boolean,
): Promise<GroupSnapshot> {
  return transaction(db, async (client) => {
    const dropResult = await client.query<{
      id: string;
      minimum_group_size: number;
      maximum_group_size: number;
      expires_at: Date;
      available_groups: number;
    }>(
      `SELECT d.id, d.minimum_group_size, d.maximum_group_size, d.expires_at, d.available_groups
       FROM drops d
       JOIN users u ON u.id = $2
       WHERE d.id = $1
         AND d.status = 'active'
         AND d.starts_at <= now()
         AND d.expires_at > now()
         AND u.last_location_at > now() - interval '5 minutes'
         AND ST_DWithin(d.location, u.last_location, d.full_reveal_radius_m)
       FOR UPDATE OF d`,
      [dropId, userId],
    );
    const drop = dropResult.rows[0];
    if (!drop) {
      throw forbidden("DROP_NOT_DISCOVERED", "Move close enough to fully reveal this Drop first");
    }
    if (drop.available_groups < 1) throw conflict("DROP_FULL", "No redemptions remain for this Drop");

    const existing = await client.query(
      `SELECT 1 FROM group_members gm
       JOIN groups g ON g.id = gm.group_id
       WHERE gm.user_id = $1 AND g.drop_id = $2
         AND g.status IN ('forming', 'ready', 'en_route', 'checked_in')`,
      [userId, dropId],
    );
    if ((existing.rowCount ?? 0) > 0) {
      throw conflict("ALREADY_GROUPED", "You already belong to an active squad for this Drop");
    }

    const initialStatus = drop.minimum_group_size === 1 ? "ready" : "forming";
    const groupResult = await client.query<{ id: string }>(
      `INSERT INTO groups
        (drop_id, leader_id, status, open_to_nearby, minimum_size, maximum_size, expires_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING id`,
      [
        drop.id,
        userId,
        initialStatus,
        openToNearby,
        drop.minimum_group_size,
        drop.maximum_group_size,
        drop.expires_at,
      ],
    );
    const groupId = groupResult.rows[0]?.id;
    if (!groupId) throw new Error("Failed to create squad");

    await client.query(
      "INSERT INTO group_members (group_id, user_id, role) VALUES ($1, $2, 'leader')",
      [groupId, userId],
    );
    if (initialStatus === "ready") {
      await client.query("UPDATE drops SET available_groups = available_groups - 1 WHERE id = $1", [drop.id]);
    }

    return snapshot(client, groupId);
  });
}

export async function joinGroup(db: Pool, userId: string, groupId: string): Promise<GroupSnapshot> {
  return transaction(db, async (client) => {
    const groupResult = await client.query<GroupRow & { available_groups: number }>(
      `SELECT g.id, g.drop_id, g.leader_id, g.status, g.open_to_nearby, g.minimum_size,
              g.maximum_size, g.expires_at, d.available_groups
       FROM groups g
       JOIN drops d ON d.id = g.drop_id
       WHERE g.id = $1
       FOR UPDATE OF g, d`,
      [groupId],
    );
    const group = groupResult.rows[0];
    if (!group) throw notFound("GROUP_NOT_FOUND", "Squad not found");
    if (!group.open_to_nearby) throw forbidden("GROUP_PRIVATE", "This squad is invite-only");
    if (group.status !== "forming" || group.expires_at <= new Date()) {
      throw conflict("GROUP_CLOSED", "This squad is no longer accepting members");
    }

    const nearby = await client.query(
      `SELECT 1
       FROM users u JOIN drops d ON d.id = $2
       WHERE u.id = $1
         AND u.last_location_at > now() - interval '5 minutes'
         AND ST_DWithin(d.location, u.last_location, d.detection_radius_m)`,
      [userId, group.drop_id],
    );
    if (nearby.rowCount === 0) throw forbidden("NOT_NEARBY", "You must be near this Drop to join its squad");

    const alreadyJoined = await client.query(
      "SELECT 1 FROM group_members WHERE group_id = $1 AND user_id = $2",
      [groupId, userId],
    );
    if ((alreadyJoined.rowCount ?? 0) > 0) return snapshot(client, groupId);

    const otherGroup = await client.query(
      `SELECT 1 FROM group_members gm
       JOIN groups g ON g.id = gm.group_id
       WHERE gm.user_id = $1
         AND g.drop_id = $2
         AND g.status IN ('forming', 'ready', 'en_route', 'checked_in')`,
      [userId, group.drop_id],
    );
    if ((otherGroup.rowCount ?? 0) > 0) {
      throw conflict("ALREADY_GROUPED", "You already belong to an active squad for this Drop");
    }

    const countResult = await client.query<{ count: number }>(
      "SELECT count(*)::int AS count FROM group_members WHERE group_id = $1",
      [groupId],
    );
    const count = countResult.rows[0]?.count ?? 0;
    if (count >= group.maximum_size) throw conflict("GROUP_FULL", "This squad is full");

    await client.query("INSERT INTO group_members (group_id, user_id) VALUES ($1, $2)", [groupId, userId]);
    const newCount = count + 1;
    if (newCount >= group.minimum_size) {
      if (group.available_groups < 1) {
        throw conflict("DROP_FULL", "The final redemption was claimed by another squad");
      }
      await client.query("UPDATE groups SET status = 'ready', updated_at = now() WHERE id = $1", [groupId]);
      await client.query("UPDATE drops SET available_groups = available_groups - 1, updated_at = now() WHERE id = $1", [group.drop_id]);
    }

    return snapshot(client, groupId);
  });
}

export async function leaveGroup(db: Pool, userId: string, groupId: string): Promise<GroupSnapshot | null> {
  return transaction(db, async (client) => {
    const groupResult = await client.query<GroupRow>(
      `SELECT id, drop_id, leader_id, status, open_to_nearby, minimum_size, maximum_size, expires_at
       FROM groups WHERE id = $1 FOR UPDATE`,
      [groupId],
    );
    const group = groupResult.rows[0];
    if (!group) throw notFound("GROUP_NOT_FOUND", "Squad not found");
    if (!["forming", "ready"].includes(group.status)) {
      throw conflict("CANNOT_LEAVE", "You cannot leave after the squad has departed");
    }

    const member = await client.query(
      "DELETE FROM group_members WHERE group_id = $1 AND user_id = $2 RETURNING role",
      [groupId, userId],
    );
    if (member.rowCount === 0) throw badRequest("NOT_A_MEMBER", "You are not a member of this squad");

    const members = await client.query<{ user_id: string }>(
      "SELECT user_id FROM group_members WHERE group_id = $1 ORDER BY joined_at ASC",
      [groupId],
    );
    if (members.rowCount === 0) {
      await client.query("UPDATE groups SET status = 'cancelled', updated_at = now() WHERE id = $1", [groupId]);
      if (group.status === "ready") {
        await client.query("UPDATE drops SET available_groups = available_groups + 1, updated_at = now() WHERE id = $1", [group.drop_id]);
      }
      return null;
    }

    if (group.leader_id === userId) {
      const newLeaderId = members.rows[0]?.user_id;
      await client.query("UPDATE groups SET leader_id = $2, updated_at = now() WHERE id = $1", [groupId, newLeaderId]);
      await client.query("UPDATE group_members SET role = 'leader' WHERE group_id = $1 AND user_id = $2", [groupId, newLeaderId]);
    }

    if (group.status === "ready" && (members.rowCount ?? 0) < group.minimum_size) {
      await client.query("UPDATE groups SET status = 'forming', updated_at = now() WHERE id = $1", [groupId]);
      await client.query("UPDATE drops SET available_groups = available_groups + 1, updated_at = now() WHERE id = $1", [group.drop_id]);
    }

    return snapshot(client, groupId);
  });
}
