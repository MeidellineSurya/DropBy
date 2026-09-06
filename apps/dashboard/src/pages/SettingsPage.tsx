import { useEffect, useState } from "react";

import { ApiError, api } from "../services/api";
import type { Business, DropCategory } from "../types";
import "./SettingsPage.css";

// Everything editable about a business's own profile — PATCH
// /business/auth/me. owner_email and password aren't here on purpose:
// changing sign-in identity is a separate concern from editing a profile,
// not yet built (see STATUS.md).
export function SettingsPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [name, setName] = useState("");
  const [category, setCategory] = useState<DropCategory>("food_dining");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [venueCapacity, setVenueCapacity] = useState(1);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");

  useEffect(() => {
    api
      .me()
      .then((loaded) => {
        setBusiness(loaded);
        setName(loaded.name);
        setCategory(loaded.category as DropCategory);
        setDescription(loaded.description ?? "");
        setAddress(loaded.address ?? "");
        setPhone(loaded.phone ?? "");
        setVenueCapacity(loaded.venue_capacity);
        setLatitude(String(loaded.latitude));
        setLongitude(String(loaded.longitude));
      })
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Failed to load"));
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!business) return;
    setSaveError(null);
    setSaved(false);
    setSaving(true);
    try {
      const updated = await api.updateProfile({
        name,
        category,
        description: description || null,
        address: address || null,
        phone: phone || null,
        venue_capacity: venueCapacity,
        latitude: Number(latitude),
        longitude: Number(longitude),
      });
      setBusiness(updated);
      setSaved(true);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (loadError) return <p className="page-error">{loadError}</p>;
  if (!business) return <p>Loading…</p>;

  return (
    <div className="settings-page">
      <h1>Settings</h1>
      <p className="form-hint">
        Your venue's profile — every Drop you create is placed at the location below and capped
        at the capacity below, so keep both current.
      </p>

      <form className="settings-form" onSubmit={handleSubmit}>
        <section>
          <h2>Business profile</h2>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
          </label>
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
            Description
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
          </label>
          <div className="form-row">
            <label>
              Address
              <input value={address} onChange={(e) => setAddress(e.target.value)} />
            </label>
            <label>
              Phone
              <input value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" />
            </label>
          </div>
          <label>
            Owner email
            <input value={business.owner_email} disabled />
          </label>
          <p className="form-hint">
            Email isn't editable here — changing sign-in details is a separate step, not yet
            built.
          </p>
        </section>

        <section>
          <h2>Venue</h2>
          <label>
            Venue capacity (total seats/spots)
            <input
              type="number"
              min={1}
              max={10000}
              value={venueCapacity}
              onChange={(e) => setVenueCapacity(Number(e.target.value))}
              required
            />
          </label>
          <p className="form-hint">
            Feeds the scarcity check behind every future Drop's computed rarity — see the Create
            Drop page. Doesn't change any Drop you've already created.
          </p>
          <div className="form-row">
            <label>
              Latitude
              <input value={latitude} onChange={(e) => setLatitude(e.target.value)} required />
            </label>
            <label>
              Longitude
              <input value={longitude} onChange={(e) => setLongitude(e.target.value)} required />
            </label>
          </div>
          <p className="form-hint">
            Where every new Drop is placed. Existing Drops keep their own location, so correcting
            this won't move anything you've already created.
          </p>
        </section>

        {saveError && <p className="page-error">{saveError}</p>}
        {saved && <p className="settings-saved">Saved.</p>}

        <button type="submit" className="settings-form__submit" disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </button>
      </form>
    </div>
  );
}
