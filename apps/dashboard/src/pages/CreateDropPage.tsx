import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, api } from "../services/api";
import type { DropCategory, DropRarity, DropType } from "../types";
import "./CreateDropPage.css";

function toIso(localDateTime: string): string {
  return new Date(localDateTime).toISOString();
}

// Mirrors app/services/drop_lifecycle.compute_rarity on the backend — this
// is a preview only, so a business can see roughly what tier their offer
// will land in before submitting. The server always computes the real
// value; there is no rarity field sent to the API at all.
const DISCOUNT_TIER_THRESHOLDS: [number, DropRarity][] = [
  [80, "legendary"],
  [60, "epic"],
  [40, "rare"],
  [20, "uncommon"],
  [0, "common"],
];
const RARITY_ORDER: DropRarity[] = ["common", "uncommon", "rare", "epic", "legendary"];

// venueCapacity here is the business's registered Business.venue_capacity,
// NOT the per-Drop max_capacity_participants input below — scarcity is
// judged from the one-time registration value so it can't be gamed per Drop.
function previewRarity(discountPercent: number, minGroupSize: number, venueCapacity: number): DropRarity {
  const match = DISCOUNT_TIER_THRESHOLDS.find(([threshold]) => discountPercent >= threshold);
  const base = match ? match[1] : "common";
  const scarceOrDemanding = venueCapacity <= 6 || minGroupSize >= 6;
  if (!scarceOrDemanding) return base;
  const nextIndex = Math.min(RARITY_ORDER.indexOf(base) + 1, RARITY_ORDER.length - 1);
  return RARITY_ORDER[nextIndex];
}

// Mirrors app/services/drop_lifecycle.compute_xp_reward — also a preview
// only. There is no xp_reward_base field sent to the API either.
const XP_REWARD_BY_RARITY: Record<DropRarity, number> = {
  common: 10,
  uncommon: 20,
  rare: 40,
  epic: 80,
  legendary: 160,
};

export function CreateDropPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [interestTag, setInterestTag] = useState("");
  const [category, setCategory] = useState<DropCategory>("food_dining");
  const [discountPercent, setDiscountPercent] = useState(20);
  const [dropType, setDropType] = useState<DropType>("solo");
  // Only meaningful once dropType !== "solo" (the form hides these controls,
  // and submission forces both back to 1, for solo) — defaulted to a
  // realistic squad size rather than 1 so the sliders below don't open at
  // their floor.
  const [minGroupSize, setMinGroupSize] = useState(2);
  const [maxGroupSize, setMaxGroupSize] = useState(4);
  const [maxCapacity, setMaxCapacity] = useState(10);
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [discoveryRadius, setDiscoveryRadius] = useState(700);
  const [discoverRadius, setDiscoverRadius] = useState(100);
  const [publishNow, setPublishNow] = useState(true);
  const [venueCapacity, setVenueCapacity] = useState<number | null>(null);

  useEffect(() => {
    api.me().then((business) => setVenueCapacity(business.venue_capacity)).catch(() => {});
  }, []);

  const effectiveMinGroupSize = dropType === "solo" ? 1 : minGroupSize;
  const estimatedRarity =
    venueCapacity === null
      ? null
      : previewRarity(discountPercent, effectiveMinGroupSize, venueCapacity);
  const estimatedXp = estimatedRarity === null ? null : XP_REWARD_BY_RARITY[estimatedRarity];

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.createDrop({
        title,
        description: description || undefined,
        interest_tag: interestTag || undefined,
        category,
        discount_percent: discountPercent,
        drop_type: dropType,
        min_group_size: dropType === "solo" ? 1 : minGroupSize,
        max_group_size: dropType === "solo" ? 1 : maxGroupSize,
        max_capacity_participants: maxCapacity,
        starts_at: toIso(startsAt),
        ends_at: toIso(endsAt),
        discovery_radius_m: discoveryRadius,
        discover_radius_m: discoverRadius,
        publish: publishNow,
      });
      navigate("/drops");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create Drop");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="create-drop-page">
      <h1>Create a Drop</h1>
      <form onSubmit={handleSubmit} className="create-drop-form">
        <section>
          <h2>Offer</h2>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Description
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <label>
            Interest tag
            <input
              value={interestTag}
              onChange={(e) => setInterestTag(e.target.value)}
              placeholder="e.g. trivia night, ramen, rooftop cinema"
            />
          </label>
          <p className="form-hint">
            Shown even at Detect range, before the venue is revealed — falls back to the category
            if left blank.
          </p>
          <div className="form-row">
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value as DropCategory)}>
                <option value="food_dining">Food & dining</option>
                <option value="activity_entertainment">Activity & entertainment</option>
                <option value="nightlife">Nightlife</option>
                <option value="wellness_beauty">Wellness & beauty</option>
                <option value="retail">Retail</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>
              Discount (%)
              <input
                type="number"
                min={1}
                max={100}
                value={discountPercent}
                onChange={(e) => setDiscountPercent(Number(e.target.value))}
                required
              />
            </label>
          </div>
          <p className="form-hint">
            Rarity — and the XP explorers earn for completing it — are computed automatically
            from your discount, group size, and your registered venue capacity (not the Max
            total participants below, which you can vary per Drop). Neither is something you
            pick directly, so both stay an honest signal.{" "}
            {estimatedRarity === null ? (
              "Loading estimate…"
            ) : (
              <>
                Estimated tier:{" "}
                <strong className={`rarity-preview rarity-${estimatedRarity}`}>
                  {estimatedRarity}
                </strong>{" "}
                ({estimatedXp} XP)
              </>
            )}
          </p>
        </section>

        <section>
          <h2>Group requirements</h2>
          <label>
            Drop type
            <select value={dropType} onChange={(e) => setDropType(e.target.value as DropType)}>
              <option value="solo">Solo — redeemable alone</option>
              <option value="squad">Squad — small group</option>
              <option value="raid">Raid — large group</option>
            </select>
          </label>
          {dropType !== "solo" && (
            <div className="form-row">
              <label className="slider-field">
                <span>
                  Min squad size <span className="slider-field__value">{minGroupSize}</span>
                </span>
                <input
                  type="range"
                  min={2}
                  max={10}
                  value={minGroupSize}
                  onChange={(e) => {
                    const value = Number(e.target.value);
                    setMinGroupSize(value);
                    // Keep the range valid from this side too — dragging min
                    // past the current max should drag max along with it,
                    // not silently produce an invalid min > max Drop.
                    if (value > maxGroupSize) setMaxGroupSize(value);
                  }}
                />
              </label>
              <label className="slider-field">
                <span>
                  Max squad size <span className="slider-field__value">{maxGroupSize}</span>
                </span>
                <input
                  type="range"
                  min={minGroupSize}
                  max={10}
                  value={maxGroupSize}
                  onChange={(e) => setMaxGroupSize(Number(e.target.value))}
                />
              </label>
            </div>
          )}
          {dropType !== "solo" && (
            <p className="form-hint">
              How many people must assemble before the squad can redeem — from
              a pair up to a small crowd. Reaching min unlocks check-in; the
              squad can keep growing up to max while it waits.
            </p>
          )}
          <label>
            Max total participants
            <input
              type="number"
              min={1}
              max={venueCapacity ?? undefined}
              value={maxCapacity}
              onChange={(e) => setMaxCapacity(Number(e.target.value))}
            />
          </label>
          <p className="form-hint">
            Can't exceed your registered venue capacity
            {venueCapacity !== null && ` (${venueCapacity})`}.
          </p>
        </section>

        <section>
          <h2>Scheduling & discovery radius</h2>
          <div className="form-row">
            <label>
              Starts at
              <input
                type="datetime-local"
                value={startsAt}
                onChange={(e) => setStartsAt(e.target.value)}
                required
              />
            </label>
            <label>
              Ends at
              <input
                type="datetime-local"
                value={endsAt}
                onChange={(e) => setEndsAt(e.target.value)}
                required
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Detect radius (m)
              <input
                type="number"
                value={discoveryRadius}
                onChange={(e) => setDiscoveryRadius(Number(e.target.value))}
              />
            </label>
            <label>
              Reveal radius (m)
              <input
                type="number"
                value={discoverRadius}
                onChange={(e) => setDiscoverRadius(Number(e.target.value))}
              />
            </label>
          </div>
          <p className="form-hint">
            Users see a mystery pin within the Detect radius, then the full offer once they're
            within the Reveal radius. Detect must be &ge; Reveal.
          </p>
        </section>

        <section>
          <h2>Publish</h2>
          <label className="form-checkbox">
            <input
              type="checkbox"
              checked={publishNow}
              onChange={(e) => setPublishNow(e.target.checked)}
            />
            Publish immediately (otherwise saved as a draft)
          </label>
        </section>

        {error && <p className="page-error">{error}</p>}

        <button type="submit" className="create-drop-form__submit" disabled={submitting}>
          {publishNow ? "Create & publish" : "Save draft"}
        </button>
      </form>
    </div>
  );
}
