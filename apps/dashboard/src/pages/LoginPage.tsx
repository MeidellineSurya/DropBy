import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, api } from "../services/api";
import { setToken } from "../services/auth";
import "./LoginPage.css";

export function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [ownerEmail, setOwnerEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("food_dining");
  const [address, setAddress] = useState("");
  const [latitude, setLatitude] = useState("-37.8119");
  const [longitude, setLongitude] = useState("144.9674");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response =
        mode === "login"
          ? await api.login(ownerEmail, password)
          : await api.register({
              name,
              category,
              owner_email: ownerEmail,
              password,
              address,
              latitude: Number(latitude),
              longitude: Number(longitude),
            });
      setToken(response.access_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <span className="login-card__brand-mark">D</span>
        <span className="login-card__eyebrow">DROPBY</span>
        <h1>Partner portal</h1>
        <div className="login-card__tabs">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Log in
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Register business
          </button>
        </div>

        {mode === "register" && (
          <>
            <label>
              Business name
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="food_dining">Food & dining</option>
                <option value="activity_entertainment">Activity & entertainment</option>
                <option value="nightlife">Nightlife</option>
                <option value="wellness_beauty">Wellness & beauty</option>
                <option value="retail">Retail</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>
              Address
              <input value={address} onChange={(e) => setAddress(e.target.value)} />
            </label>
            <div className="login-card__row">
              <label>
                Latitude
                <input value={latitude} onChange={(e) => setLatitude(e.target.value)} />
              </label>
              <label>
                Longitude
                <input value={longitude} onChange={(e) => setLongitude(e.target.value)} />
              </label>
            </div>
          </>
        )}

        <label>
          Email
          <input
            type="email"
            value={ownerEmail}
            onChange={(e) => setOwnerEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={10}
            required
          />
        </label>

        {error && <p className="login-card__error">{error}</p>}

        <button type="submit" className="login-card__submit" disabled={submitting}>
          {mode === "login" ? "Log in" : "Create account"}
        </button>
      </form>
    </div>
  );
}
