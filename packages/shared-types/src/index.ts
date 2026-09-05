// Generated from packages/ws-contracts/ws_contracts/events.py — do not hand-edit
// once a generation step exists. For now this is a hand-mirrored placeholder
// so both frontends have a single import path to start against.

export type Stage = "detect" | "reveal";

export interface DropStageUpdate {
  type: "drop.stage_update";
  drop_id: string;
  stage: Stage;
  distance_m: number;
  data: Record<string, unknown>;
}

export interface DropCapacityReached {
  type: "drop.capacity_reached";
  drop_id: string;
}

export interface DropExpired {
  type: "drop.expired";
  drop_id: string;
  reason: "time" | "capacity" | "cancelled";
}

export interface DropCountdownWarning {
  type: "drop.countdown_warning";
  drop_id: string;
  minutes_remaining: number;
}

export type GroupStatus = "forming" | "ready" | "checked_in" | "completed" | "expired" | "cancelled";

export interface GroupMemberSummary {
  user_id: string;
  display_name: string;
  role: "leader" | "member";
  status: "invited" | "joined" | "left";
}

export interface GroupStateUpdate {
  type: "group.state_update";
  group_id: string;
  drop_id: string;
  status: GroupStatus;
  current_count: number;
  min_required: number;
  max_allowed: number;
  members: GroupMemberSummary[];
  expires_at: string | null;
}

export interface GroupMemberJoined {
  type: "group.member_joined";
  group_id: string;
  user_id: string;
  display_name: string;
  current_count: number;
}

export interface GroupReady {
  type: "group.ready";
  group_id: string;
  drop_id: string;
  venue_directions_url: string;
}

export interface RedemptionCheckedIn {
  type: "redemption.checked_in";
  group_id: string;
  redemption_id: string;
  checked_in_at: string;
}

export interface RedemptionConfirmed {
  type: "redemption.confirmed";
  group_id: string;
  redemption_id: string;
  xp_awarded: Record<string, number>;
}

export interface BadgeUnlocked {
  type: "badge.unlocked";
  badge_code: string;
  name: string;
  icon_url: string | null;
}

export type WsEvent =
  | DropStageUpdate
  | DropCapacityReached
  | DropExpired
  | DropCountdownWarning
  | GroupStateUpdate
  | GroupMemberJoined
  | GroupReady
  | RedemptionCheckedIn
  | RedemptionConfirmed
  | BadgeUnlocked;
