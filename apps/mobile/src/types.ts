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

export interface RedemptionSnapshot {
  id: string;
  drop_id: string;
  drop_title: string;
  group_id: string;
  business_id: string;
  status: "pending" | "checked_in" | "confirmed" | "rejected" | "expired";
  checked_in_at: string | null;
  confirmed_at: string | null;
  participant_count: number | null;
  disputed_at: string | null;
  member_count: number;
  xp_reward_base: number;
}

export type ConnectionStatusView = "none" | "pending_outgoing" | "pending_incoming" | "connected" | "blocked";

export interface UserSummary {
  user_id: string;
  display_name: string;
  avatar_url?: string | null;
}

export interface UserSearchResult extends UserSummary {
  connection_status: ConnectionStatusView;
}

export interface RecentSquadmate extends UserSummary {
  connection_status: ConnectionStatusView;
  met_via_drop_title?: string | null;
  met_at?: string | null;
}

export interface ConnectionSummary {
  id: string;
  status: "pending" | "accepted" | "declined" | "blocked";
  other_user: UserSummary;
  created_at: string;
}

export interface Message {
  id: string;
  connection_id: string;
  sender_id: string;
  body: string;
  created_at: string;
}

export interface Conversation {
  connection_id: string;
  other_user: UserSummary;
  last_message: Message | null;
}

export interface ConnectionRequestReceivedEvent {
  type: "connection.request_received";
  connection_id: string;
  requester_id: string;
  requester_display_name: string;
}

export interface ConnectionRequestAcceptedEvent {
  type: "connection.request_accepted";
  connection_id: string;
  addressee_id: string;
  addressee_display_name: string;
}

export interface MessageSentEvent {
  type: "chat.message_sent";
  connection_id: string;
  message_id: string;
  sender_id: string;
  body: string;
  created_at: string;
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

// Check-in auto-confirms (see apps/api/app/services/redemption.py), so
// redemption.checked_in fires immediately and redemption.confirmed follows
// shortly after once award_xp_for_redemption's Celery task lands.
export interface RedemptionEvent {
  type: "redemption.checked_in" | "redemption.confirmed";
  group_id: string;
  redemption_id: string;
  [key: string]: unknown;
}

export type LiveEvent =
  | DropStageEvent
  | GroupEvent
  | RedemptionEvent
  | ConnectionRequestReceivedEvent
  | ConnectionRequestAcceptedEvent
  | MessageSentEvent
  | { type: "drop.capacity_reached" | "drop.expired" | "drop.countdown_warning"; drop_id: string; [key: string]: unknown };
