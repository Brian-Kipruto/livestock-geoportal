import { freshness, hazardFromZ } from "./freshness";

const today = new Date("2026-11-11T00:00:00Z");

describe("freshness", () => {
  it("is pending without a version", () => {
    expect(freshness("pending", null, today)).toEqual({ tone: "pending", key: "token.pending" });
    expect(freshness("live", null, today).tone).toBe("pending");
  });
  it("reports age for live data", () => {
    expect(freshness("live", "2026-11-11", today).key).toBe("token.live");
    expect(freshness("live", "2026-11-08", today)).toMatchObject({ key: "token.daysAgo", values: { n: 3 } });
    expect(freshness("live", "2025-11-11", today)).toMatchObject({ key: "token.monthsAgo" });
  });
  it("flags stale and error", () => {
    expect(freshness("stale", "2026-01-01", today).key).toBe("token.stale");
    expect(freshness("error", "2026-11-01", today).key).toBe("token.error");
  });
});

describe("hazardFromZ (SDD §9.1)", () => {
  it.each([
    [0, "normal"],
    [-0.5, "normal"],
    [-0.7, "watch"],
    [-1.2, "alert"],
    [-1.6, "emergency"],
  ])("z=%s → %s", (z, expected) => expect(hazardFromZ(z)).toBe(expected));
});
