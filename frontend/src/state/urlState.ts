/** Shareable view state encoded in the URL (FR-G5, SDD §11.1).
 *  ?c=UGA&a=123&l=ndvi_anom_z,water_points&t=2026-10&s=ssp245&r=policy&lite=1 */

export type Role = "policy" | "investor" | "technical";
export type Scenario = "obs" | "ssp245" | "ssp585";

export interface ViewState {
  country: string;
  area: number | null;
  layers: string[];
  time: string; // YYYY-MM
  scenario: Scenario;
  role: Role;
  lite: boolean;
}

const ROLES: Role[] = ["policy", "investor", "technical"];
const SCENARIOS: Scenario[] = ["obs", "ssp245", "ssp585"];

export function parseViewState(search: string, defaults: ViewState): ViewState {
  const q = new URLSearchParams(search);
  const role = q.get("r") as Role | null;
  const scenario = q.get("s") as Scenario | null;
  const t = q.get("t");
  const a = Number(q.get("a"));
  return {
    country: (q.get("c") ?? defaults.country).toUpperCase().slice(0, 3),
    area: q.has("a") && Number.isInteger(a) && a > 0 ? a : defaults.area,
    layers: q.has("l") ? q.get("l")!.split(",").filter(Boolean) : defaults.layers,
    time: t && /^\d{4}-\d{2}$/.test(t) ? t : defaults.time,
    scenario: scenario && SCENARIOS.includes(scenario) ? scenario : defaults.scenario,
    role: role && ROLES.includes(role) ? role : defaults.role,
    lite: q.has("lite") ? q.get("lite") === "1" : defaults.lite,
  };
}

export function serializeViewState(v: ViewState): string {
  const q = new URLSearchParams();
  q.set("c", v.country);
  if (v.area != null) q.set("a", String(v.area));
  if (v.layers.length) q.set("l", v.layers.join(","));
  q.set("t", v.time);
  if (v.scenario !== "obs") q.set("s", v.scenario);
  q.set("r", v.role);
  if (v.lite) q.set("lite", "1");
  return q.toString();
}
