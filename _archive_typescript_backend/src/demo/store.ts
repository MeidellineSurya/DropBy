import bcrypt from "bcryptjs";
import { randomUUID } from "node:crypto";
import { badRequest, conflict, forbidden, notFound } from "../errors.js";
import { serializeNearbyDrop, type NearbyDrop } from "../services/drop-service.js";
import type { GroupSnapshot, NearbyDropRow } from "../types/domain.js";

export interface DemoUser {
  id: string;
  email: string;
  password_hash: string;
  display_name: string;
  onboarding_completed_at: Date | null;
  latitude?: number;
  longitude?: number;
  locationAt?: Date;
}

interface DemoGroup {
  id: string;
  dropId: string;
  leaderId: string;
  status: GroupSnapshot["status"];
  openToNearby: boolean;
  minimumSize: number;
  maximumSize: number;
  expiresAt: Date;
  members: Array<{ userId: string; role: "leader" | "member"; joinedAt: Date }>;
}

const seededDrops: Array<NearbyDropRow & { availableGroups: number; status: "active" }> = [
  {
    id: "10000000-0000-4000-8000-000000000001",
    venue_name: "Seoul Table",
    offer_title: "40% off Korean BBQ",
    offer_description: "40% off the group dining menu.",
    category: "Korean food",
    broad_category: "Food",
    rarity: "rare",
    address: "200 Little Bourke Street, Melbourne VIC",
    minimum_group_size: 4,
    maximum_group_size: 6,
    expires_at: new Date(Date.now() + 6 * 60 * 60 * 1_000),
    distance_m: 0,
    partial_reveal_radius_m: 250,
    full_reveal_radius_m: 75,
    check_in_radius_m: 30,
    longitude: 144.9674,
    latitude: -37.8119,
    availableGroups: 5,
    status: "active",
  },
  {
    id: "10000000-0000-4000-8000-000000000002",
    venue_name: "Laneway Coffee",
    offer_title: "Free coffee upgrade",
    offer_description: "Upgrade any regular coffee to a large at no charge.",
    category: "Cafe",
    broad_category: "Food",
    rarity: "common",
    address: "Centre Place, Melbourne VIC",
    minimum_group_size: 1,
    maximum_group_size: 1,
    expires_at: new Date(Date.now() + 6 * 60 * 60 * 1_000),
    distance_m: 0,
    partial_reveal_radius_m: 250,
    full_reveal_radius_m: 75,
    check_in_radius_m: 30,
    longitude: 144.9653,
    latitude: -37.8167,
    availableGroups: 5,
    status: "active",
  },
];

function distanceMetres(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const radians = (degrees: number): number => (degrees * Math.PI) / 180;
  const earthRadius = 6_371_000;
  const latitudeDelta = radians(lat2 - lat1);
  const longitudeDelta = radians(lon2 - lon1);
  const a = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(radians(lat1)) * Math.cos(radians(lat2)) * Math.sin(longitudeDelta / 2) ** 2;
  return earthRadius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export class DemoStore {
  private readonly users = new Map<string, DemoUser>();
  private readonly groups = new Map<string, DemoGroup>();
  private readonly drops = seededDrops.map((drop) => ({ ...drop }));

  createUser(email: string, passwordHash: string, displayName: string): DemoUser {
    if ([...this.users.values()].some((user) => user.email === email)) {
      throw conflict("EMAIL_TAKEN", "An account already exists for this email");
    }
    const user: DemoUser = {
      id: randomUUID(), email, password_hash: passwordHash, display_name: displayName,
      onboarding_completed_at: null,
    };
    this.users.set(user.id, user);
    return user;
  }

  findUserByEmail(email: string): DemoUser | undefined {
    return [...this.users.values()].find((user) => user.email === email);
  }

  getUser(userId: string): DemoUser | undefined {
    return this.users.get(userId);
  }

  async passwordMatches(user: DemoUser, password: string): Promise<boolean> {
    return bcrypt.compare(password, user.password_hash);
  }

  completeOnboarding(userId: string, displayName: string): DemoUser {
    const user = this.users.get(userId);
    if (!user) throw notFound("USER_NOT_FOUND", "User not found");
    user.display_name = displayName;
    user.onboarding_completed_at = new Date();
    return user;
  }

  nearby(userId: string, latitude: number, longitude: number): NearbyDrop[] {
    const user = this.requireUser(userId);
    user.latitude = latitude;
    user.longitude = longitude;
    user.locationAt = new Date();
    return this.drops
      .map((drop) => ({
        ...drop,
        distance_m: distanceMetres(latitude, longitude, drop.latitude, drop.longitude),
      }))
      .filter((drop) => drop.distance_m <= 800 && drop.availableGroups > 0)
      .sort((a, b) => a.distance_m - b.distance_m)
      .map(serializeNearbyDrop);
  }

  openGroups(userId: string, latitude: number, longitude: number) {
    const visibleDrops = this.nearby(userId, latitude, longitude);
    const visibleById = new Map(visibleDrops.map((drop) => [drop.id, drop]));
    return [...this.groups.values()]
      .filter((group) => group.openToNearby && group.status === "forming" && visibleById.has(group.dropId))
      .map((group) => ({
        id: group.id,
        memberCount: group.members.length,
        minimumSize: group.minimumSize,
        maximumSize: group.maximumSize,
        spotsNeeded: Math.max(0, group.minimumSize - group.members.length),
        expiresAt: group.expiresAt.toISOString(),
        drop: visibleById.get(group.dropId),
      }));
  }

  createGroup(userId: string, dropId: string, openToNearby: boolean): GroupSnapshot {
    const user = this.requireFreshLocation(userId);
    const drop = this.requireDrop(dropId);
    const distance = distanceMetres(user.latitude!, user.longitude!, drop.latitude, drop.longitude);
    if (distance > drop.full_reveal_radius_m) {
      throw forbidden("DROP_NOT_DISCOVERED", "Move close enough to fully reveal this Drop first");
    }
    if (drop.availableGroups < 1) throw conflict("DROP_FULL", "No redemptions remain for this Drop");
    if (this.activeGroupFor(userId, dropId)) {
      throw conflict("ALREADY_GROUPED", "You already belong to an active squad for this Drop");
    }
    const status = drop.minimum_group_size === 1 ? "ready" : "forming";
    const group: DemoGroup = {
      id: randomUUID(), dropId, leaderId: userId, status, openToNearby,
      minimumSize: drop.minimum_group_size, maximumSize: drop.maximum_group_size,
      expiresAt: drop.expires_at,
      members: [{ userId, role: "leader", joinedAt: new Date() }],
    };
    if (status === "ready") drop.availableGroups -= 1;
    this.groups.set(group.id, group);
    return this.snapshot(group);
  }

  getGroup(groupId: string, userId: string): GroupSnapshot {
    const group = this.requireGroup(groupId);
    if (!group.members.some((member) => member.userId === userId)) {
      throw forbidden("NOT_A_MEMBER", "You are not a member of this squad");
    }
    return this.snapshot(group);
  }

  joinGroup(userId: string, groupId: string): GroupSnapshot {
    const user = this.requireFreshLocation(userId);
    const group = this.requireGroup(groupId);
    const drop = this.requireDrop(group.dropId);
    if (!group.openToNearby) throw forbidden("GROUP_PRIVATE", "This squad is invite-only");
    if (group.status !== "forming") throw conflict("GROUP_CLOSED", "This squad is no longer accepting members");
    if (distanceMetres(user.latitude!, user.longitude!, drop.latitude, drop.longitude) > 800) {
      throw forbidden("NOT_NEARBY", "You must be near this Drop to join its squad");
    }
    if (group.members.some((member) => member.userId === userId)) return this.snapshot(group);
    if (this.activeGroupFor(userId, group.dropId)) {
      throw conflict("ALREADY_GROUPED", "You already belong to an active squad for this Drop");
    }
    if (group.members.length >= group.maximumSize) throw conflict("GROUP_FULL", "This squad is full");
    group.members.push({ userId, role: "member", joinedAt: new Date() });
    if (group.members.length >= group.minimumSize) {
      if (drop.availableGroups < 1) {
        group.members.pop();
        throw conflict("DROP_FULL", "The final redemption was claimed by another squad");
      }
      group.status = "ready";
      drop.availableGroups -= 1;
    }
    return this.snapshot(group);
  }

  leaveGroup(userId: string, groupId: string): GroupSnapshot | null {
    const group = this.requireGroup(groupId);
    if (!["forming", "ready"].includes(group.status)) {
      throw conflict("CANNOT_LEAVE", "You cannot leave after the squad has departed");
    }
    const index = group.members.findIndex((member) => member.userId === userId);
    if (index < 0) throw badRequest("NOT_A_MEMBER", "You are not a member of this squad");
    const wasReady = group.status === "ready";
    group.members.splice(index, 1);
    if (group.members.length === 0) {
      if (wasReady) this.requireDrop(group.dropId).availableGroups += 1;
      this.groups.delete(groupId);
      return null;
    }
    if (group.leaderId === userId) {
      const leader = group.members[0]!;
      leader.role = "leader";
      group.leaderId = leader.userId;
    }
    if (wasReady && group.members.length < group.minimumSize) {
      group.status = "forming";
      this.requireDrop(group.dropId).availableGroups += 1;
    }
    return this.snapshot(group);
  }

  activeGroupIds(userId: string): string[] {
    return [...this.groups.values()]
      .filter((group) => group.members.some((member) => member.userId === userId))
      .map((group) => group.id);
  }

  private requireUser(userId: string): DemoUser {
    const user = this.users.get(userId);
    if (!user) throw notFound("USER_NOT_FOUND", "User not found");
    return user;
  }

  private requireFreshLocation(userId: string): DemoUser {
    const user = this.requireUser(userId);
    if (user.latitude === undefined || user.longitude === undefined || !user.locationAt
      || Date.now() - user.locationAt.getTime() > 5 * 60 * 1_000) {
      throw forbidden("LOCATION_REQUIRED", "Send a current location before using squads");
    }
    return user;
  }

  private requireDrop(dropId: string) {
    const drop = this.drops.find((item) => item.id === dropId);
    if (!drop) throw notFound("DROP_NOT_FOUND", "Drop not found");
    return drop;
  }

  private requireGroup(groupId: string): DemoGroup {
    const group = this.groups.get(groupId);
    if (!group) throw notFound("GROUP_NOT_FOUND", "Squad not found");
    return group;
  }

  private activeGroupFor(userId: string, dropId: string): DemoGroup | undefined {
    return [...this.groups.values()].find((group) => group.dropId === dropId
      && group.members.some((member) => member.userId === userId));
  }

  private snapshot(group: DemoGroup): GroupSnapshot {
    return {
      id: group.id, dropId: group.dropId, leaderId: group.leaderId, status: group.status,
      openToNearby: group.openToNearby, minimumSize: group.minimumSize, maximumSize: group.maximumSize,
      memberCount: group.members.length, expiresAt: group.expiresAt.toISOString(),
      members: group.members.map((member) => {
        const user = this.requireUser(member.userId);
        return {
          userId: user.id, displayName: user.display_name, avatarUrl: null,
          role: member.role, joinedAt: member.joinedAt.toISOString(),
        };
      }),
    };
  }
}
