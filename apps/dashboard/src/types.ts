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
  // Declared once at registration — see Business.venue_capacity in the API.
  // Feeds the rarity scarcity check for every Drop this business creates.
  venue_capacity: number;
  verified: boolean;
  status: string;
  phone: string | null;
  // The venue's own registered location — Create Drop defaults a new
  // Drop's location to this instead of asking for coordinates again.
  latitude: number;
  longitude: number;
}

export interface BusinessDrop {
  id: string;
  title: string;
  description: string | null;
  category: DropCategory;
  // Shown even at Detect range — see apps/api/app/services/proximity.py.
  interest_tag: string;
  // Read-only — computed server-side from discount_percent/group size/
  // capacity (see compute_rarity in the API). Never sent when creating a Drop.
  rarity: DropRarity;
  discount_percent: number;
  drop_type: DropType;
  min_group_size: number;
  max_group_size: number;
  discovery_radius_m: number;
  discover_radius_m: number;
  max_capacity_participants: number;
  reserved_count: number;
  starts_at: string;
  ends_at: string;
  status: DropStatus;
  // Read-only — computed server-side from rarity (see compute_xp_reward in
  // the API). Never sent when creating a Drop.
  xp_reward_base: number;
}

// Two-stage discovery model: "revealed" is everyone who got close enough to
// unlock the full offer (there's no longer a distinct middle stage).
export interface DropFunnel {
  drop_id: string;
  status: DropStatus;
  detect_count: number;
  revealed_count: number;
  reserved_count: number;
  max_capacity_participants: number;
  squads_forming: number;
  squads_ready: number;
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

export type RedemptionStatus = "pending" | "checked_in" | "confirmed" | "rejected" | "expired";

export interface Redemption {
  id: string;
  drop_id: string;
  drop_title: string;
  group_id: string;
  status: RedemptionStatus;
  checked_in_at: string | null;
  confirmed_at: string | null;
  // Record-keeping only — see apps/api/app/services/redemption.py.
  participant_count: number | null;
  disputed_at: string | null;
  member_count: number;
  xp_reward_base: number;
}
