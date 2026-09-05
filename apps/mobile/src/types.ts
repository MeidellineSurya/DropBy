export type Stage = "detect" | "reveal";

export type DropCategory =
  | "food_dining"
  | "activity_entertainment"
  | "nightlife"
  | "wellness_beauty"
  | "retail"
  | "other";

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  preferences: string[];
  location_permission: string;
  onboarding_complete: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user: UserProfile;
}

export interface DropSnapshot {
  id: string;
  stage: Stage;
  distance_m: number;
  rarity?: "common" | "uncommon" | "rare" | "epic" | "legendary";
  category?: DropCategory;
  interest_tag?: string;
  title?: string;
  description?: string;
  business_name?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  drop_type?: "solo" | "squad" | "raid";
  min_group_size?: number;
  max_group_size?: number;
  ends_at?: string;
  can_assemble?: boolean;
}

export interface GroupMember {
  user_id: string;
  display_name: string;
  role: "leader" | "member";
  status: "invited" | "joined" | "left";
}

export interface GroupSnapshot {
  id: string;
  drop_id: string;
  created_by_user_id: string;
  status: "forming" | "ready" | "checked_in" | "completed" | "expired" | "cancelled";
  current_count: number;
  min_required: number;
  max_allowed: number;
  open_to_nearby: boolean;
  expires_at?: string;
  members: GroupMember[];
}

export interface DropStageEvent {
  type: "drop.stage_update";
  drop_id: string;
  stage: Stage;
  distance_m: number;
  data: DropSnapshot;
}

export interface GroupEvent {
  type: "group.state_update" | "group.member_joined" | "group.ready";
  group_id: string;
  [key: string]: unknown;
}

export type LiveEvent =
  | DropStageEvent
  | GroupEvent
  | { type: "drop.capacity_reached" | "drop.expired" | "drop.countdown_warning"; drop_id: string; [key: string]: unknown };
