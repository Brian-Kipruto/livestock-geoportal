import { parseViewState, serializeViewState, type ViewState } from "./urlState";

const defaults: ViewState = {
  country: "UGA",
  area: null,
  layers: ["ndvi_anom_z"],
  time: "2026-10",
  scenario: "obs",
  role: "policy",
  lite: false,
};

describe("URL view state (FR-G5)", () => {
  it("round-trips", () => {
    const v: ViewState = { ...defaults, area: 123, layers: ["a", "b"], scenario: "ssp245", role: "technical", lite: true };
    expect(parseViewState(`?${serializeViewState(v)}`, defaults)).toEqual(v);
  });
  it("falls back on invalid values", () => {
    const v = parseViewState("?c=ken&a=-4&t=2026-13x&r=hacker&s=ssp999", defaults);
    expect(v).toEqual({ ...defaults, country: "KEN" });
  });
  it("matches the SDD example", () => {
    const v = parseViewState("?c=UGA&a=123&l=ndvi_anom_z,water_points&t=2026-10&s=ssp245&r=policy&lite=1", defaults);
    expect(v).toMatchObject({ area: 123, layers: ["ndvi_anom_z", "water_points"], scenario: "ssp245", lite: true });
  });
});
