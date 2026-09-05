CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE drop_rarity AS ENUM ('common', 'uncommon', 'rare', 'epic', 'legendary');
CREATE TYPE drop_status AS ENUM ('draft', 'scheduled', 'active', 'claimed', 'expired', 'cancelled');
CREATE TYPE group_status AS ENUM ('forming', 'ready', 'en_route', 'checked_in', 'completed', 'expired', 'cancelled');
CREATE TYPE group_member_role AS ENUM ('leader', 'member');
CREATE TYPE location_permission AS ENUM ('unknown', 'denied', 'while_using', 'always');

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email citext NOT NULL UNIQUE,
  password_hash text NOT NULL,
  display_name varchar(80) NOT NULL,
  birth_date date,
  avatar_url text,
  interest_tags text[] NOT NULL DEFAULT '{}',
  vibe_tags text[] NOT NULL DEFAULT '{}',
  location_permission location_permission NOT NULL DEFAULT 'unknown',
  onboarding_completed_at timestamptz,
  last_location geography(Point, 4326),
  last_location_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE drops (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  venue_name varchar(160) NOT NULL,
  offer_title varchar(160) NOT NULL,
  offer_description text,
  category varchar(60) NOT NULL,
  broad_category varchar(60) NOT NULL,
  rarity drop_rarity NOT NULL DEFAULT 'common',
  status drop_status NOT NULL DEFAULT 'draft',
  location geography(Point, 4326) NOT NULL,
  address text NOT NULL,
  detection_radius_m integer NOT NULL DEFAULT 800 CHECK (detection_radius_m > 0),
  partial_reveal_radius_m integer NOT NULL DEFAULT 250 CHECK (partial_reveal_radius_m > 0),
  full_reveal_radius_m integer NOT NULL DEFAULT 75 CHECK (full_reveal_radius_m > 0),
  check_in_radius_m integer NOT NULL DEFAULT 30 CHECK (check_in_radius_m > 0),
  minimum_group_size integer NOT NULL DEFAULT 1 CHECK (minimum_group_size > 0),
  maximum_group_size integer NOT NULL DEFAULT 1 CHECK (maximum_group_size >= minimum_group_size),
  available_groups integer NOT NULL DEFAULT 1 CHECK (available_groups >= 0),
  starts_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL CHECK (expires_at > starts_at),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (detection_radius_m >= partial_reveal_radius_m),
  CHECK (partial_reveal_radius_m >= full_reveal_radius_m),
  CHECK (full_reveal_radius_m >= check_in_radius_m)
);

CREATE INDEX drops_location_gix ON drops USING gist (location);
CREATE INDEX drops_active_time_idx ON drops (status, starts_at, expires_at);

CREATE TABLE groups (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  drop_id uuid NOT NULL REFERENCES drops(id) ON DELETE CASCADE,
  leader_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status group_status NOT NULL DEFAULT 'forming',
  open_to_nearby boolean NOT NULL DEFAULT false,
  minimum_size integer NOT NULL CHECK (minimum_size > 0),
  maximum_size integer NOT NULL CHECK (maximum_size >= minimum_size),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX groups_drop_status_idx ON groups (drop_id, status);

CREATE TABLE group_members (
  group_id uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role group_member_role NOT NULL DEFAULT 'member',
  checked_in_at timestamptz,
  joined_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (group_id, user_id)
);

CREATE INDEX group_members_user_idx ON group_members (user_id);

CREATE TABLE drop_claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  drop_id uuid NOT NULL REFERENCES drops(id) ON DELETE RESTRICT,
  group_id uuid NOT NULL UNIQUE REFERENCES groups(id) ON DELETE RESTRICT,
  redeemed_at timestamptz,
  venue_code_hash text,
  created_at timestamptz NOT NULL DEFAULT now()
);
