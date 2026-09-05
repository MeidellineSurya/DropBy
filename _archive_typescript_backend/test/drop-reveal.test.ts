import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { serializeNearbyDrop } from "../src/services/drop-service.js";
import type { NearbyDropRow } from "../src/types/domain.js";

const baseDrop: NearbyDropRow = {
  id: "10000000-0000-4000-8000-000000000001",
  venue_name: "Secret Restaurant",
  offer_title: "40% off dinner",
  offer_description: "The hidden offer",
  category: "Korean food",
  broad_category: "Food",
  rarity: "rare",
  address: "Hidden Lane",
  minimum_group_size: 4,
  maximum_group_size: 6,
  expires_at: new Date("2030-01-01T00:00:00.000Z"),
  distance_m: 500,
  partial_reveal_radius_m: 250,
  full_reveal_radius_m: 75,
  check_in_radius_m: 30,
  longitude: 144.96,
  latitude: -37.81,
};

describe("progressive Drop reveal", () => {
  it("omits sensitive details at detection distance", () => {
    const drop = serializeNearbyDrop(baseDrop);
    assert.equal(drop.revealStage, "detection");
    assert.equal(drop.broadCategory, "Food");
    assert.equal("venue" in drop, false);
    assert.equal("offer" in drop, false);
    assert.equal("category" in drop, false);
    assert.equal(JSON.stringify(drop).includes("Secret Restaurant"), false);
  });

  it("reveals category and group requirements at partial distance", () => {
    const drop = serializeNearbyDrop({ ...baseDrop, distance_m: 150 });
    assert.equal(drop.revealStage, "partial");
    assert.equal(drop.category, "Korean food");
    assert.equal(drop.groupRequired, true);
    assert.equal(drop.minimumGroupSize, 4);
    assert.equal("venue" in drop, false);
    assert.equal("offer" in drop, false);
  });

  it("reveals the venue and offer inside the full radius", () => {
    const drop = serializeNearbyDrop({ ...baseDrop, distance_m: 50 });
    assert.equal(drop.revealStage, "full");
    assert.equal(drop.venue?.name, "Secret Restaurant");
    assert.equal(drop.offer?.title, "40% off dinner");
    assert.equal(drop.canCheckIn, false);
  });

  it("marks check-in eligibility only inside the check-in radius", () => {
    const drop = serializeNearbyDrop({ ...baseDrop, distance_m: 20 });
    assert.equal(drop.revealStage, "full");
    assert.equal(drop.canCheckIn, true);
  });
});
