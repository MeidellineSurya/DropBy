export const dropRarities = ["common", "uncommon", "rare", "epic", "legendary"] as const;
export type DropRarity = (typeof dropRarities)[number];

export type RevealStage = "detection" | "partial" | "full";

export interface NearbyDropRow {
  id: string;
  venue_name: string;
  offer_title: string;
  offer_description: string | null;
  category: string;
  broad_category: string;
  rarity: DropRarity;
  address: string;
  minimum_group_size: number;
  maximum_group_size: number;
  expires_at: Date;
  distance_m: number;
  partial_reveal_radius_m: number;
  full_reveal_radius_m: number;
  check_in_radius_m: number;
  longitude: number;
  latitude: number;
}

export interface GroupSnapshot {
  id: string;
  dropId: string;
  leaderId: string;
  status: "forming" | "ready" | "en_route" | "checked_in" | "completed" | "expired" | "cancelled";
  openToNearby: boolean;
  minimumSize: number;
  maximumSize: number;
  memberCount: number;
  expiresAt: string;
  members: Array<{
    userId: string;
    displayName: string;
    avatarUrl: string | null;
    role: "leader" | "member";
    joinedAt: string;
  }>;
}
