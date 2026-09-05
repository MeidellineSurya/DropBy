import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, api } from "../services/api";
import type { DropCategory, DropRarity, DropType } from "../types";
import "./CreateDropPage.css";

function toIso(localDateTime: string): string {
  return new Date(localDateTime).toISOString();
}

export function CreateDropPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [interestTag, setInterestTag] = useState("");
  const [category, setCategory] = useState<DropCategory>("food_dining");
  const [rarity, setRarity] = useState<DropRarity>("common");
  const [dropType, setDropType] = useState<DropType>("solo");
  const [minGroupSize, setMinGroupSize] = useState(1);
  const [maxGroupSize, setMaxGroupSize] = useState(1);
  const [maxCapacity, setMaxCapacity] = useState(10);
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [discoveryRadius, setDiscoveryRadius] = useState(700);
  const [discoverRadius, setDiscoverRadius] = useState(100);
  const [xpRewardBase, setXpRewardBase] = useState(10);
  const [publishNow, setPublishNow] = useState(true);

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
        rarity,
        drop_type: dropType,
        min_group_size: dropType === "solo" ? 1 : minGroupSize,
        max_group_size: dropType === "solo" ? 1 : maxGroupSize,
        max_capacity_participants: maxCapacity,
        starts_at: toIso(startsAt),
        ends_at: toIso(endsAt),
        discovery_radius_m: discoveryRadius,
        discover_radius_m: discoverRadius,
        xp_reward_base: xpRewardBase,
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
              Rarity
              <select value={rarity} onChange={(e) => setRarity(e.target.value as DropRarity)}>
                <option value="common">Common</option>
                <option value="uncommon">Uncommon</option>
                <option value="rare">Rare</option>
                <option value="epic">Epic</option>
                <option value="legendary">Legendary</option>
              </select>
            </label>
          </div>
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
              <label>
                Min group size
                <input
                  type="number"
                  min={2}
                  value={minGroupSize}
                  onChange={(e) => setMinGroupSize(Number(e.target.value))}
                />
              </label>
              <label>
                Max group size
                <input
                  type="number"
                  min={minGroupSize}
                  value={maxGroupSize}
                  onChange={(e) => setMaxGroupSize(Number(e.target.value))}
                />
              </label>
            </div>
          )}
          <label>
            Max total participants
            <input
              type="number"
              min={1}
              value={maxCapacity}
              onChange={(e) => setMaxCapacity(Number(e.target.value))}
            />
          </label>
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
          <h2>Reward</h2>
          <label>
            Base XP reward
            <input
              type="number"
              min={0}
              value={xpRewardBase}
              onChange={(e) => setXpRewardBase(Number(e.target.value))}
            />
          </label>
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
