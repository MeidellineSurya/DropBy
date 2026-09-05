// Mirrors apps/api/app/schemas/business_*.py — kept as a hand-written
// counterpart until a real codegen step exists (see packages/shared-types).

export type DropStatus =
  | "draft"
  | "scheduled"
  | "active"
  | "paused"
  | "capacity_reached"
  | "expired"
  | "completed"
  | "cancelled";

export type DropCategory =
  | "food_dining"
  | "activity_entertainment"
  | "nightlife"
  | "wellness_beauty"
  | "retail"
  | "other";

export type DropRarity = "common" | "uncommon" | "rare" | "epic" | "legendary";
export type DropType = "solo" | "squad" | "raid";

export interface Business {
  id: string;
  name: string;
  category: string;
  description: string | null;
  address: string | null;
  owner_email: string;
  verified: boolean;
  status: string;
}

export interface BusinessDrop {
  id: string;
  title: string;
  description: string | null;
  category: DropCategory;
  rarity: DropRarity;
  drop_type: DropType;
  min_group_size: number;
  max_group_size: number;
  discovery_radius_m: number;
  reveal_radius_m: number;
  discover_radius_m: number;
  max_capacity_participants: number;
  reserved_count: number;
  starts_at: string;
  ends_at: string;
  status: DropStatus;
  xp_reward_base: number;
}

export interface DropFunnel {
  drop_id: string;
  status: DropStatus;
  detect_count: number;
  reveal_count: number;
  discover_count: number;
  reserved_count: number;
  max_capacity_participants: number;
  squads_forming: number;
  squads_ready: number;
  squads_checked_in: number;
  squads_completed: number;
}

export interface BusinessOverview {
  active_drops: number;
  draft_drops: number;
  scheduled_drops: number;
  total_reserved_participants: number;
  total_capacity_participants: number;
  distinct_viewers_last_7_days: number;
}
