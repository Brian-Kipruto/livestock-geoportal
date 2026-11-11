/** Status token helpers — SDD FR-G9, §8.6. Tokens are never colour-only (NFR-8). */

export type Tone = "good" | "watch" | "alert" | "emergency" | "pending";
export type DatasetStatus = "live" | "stale" | "pending" | "error";
export type Hazard = "normal" | "watch" | "alert" | "emergency";

export interface FreshnessToken {
  tone: Tone;
  /** i18n key + interpolation values */
  key: string;
  values?: Record<string, number>;
}

const DAY = 86_400_000;

export function freshness(
  status: DatasetStatus | undefined,
  dataDate: string | null | undefined,
  today: Date = new Date(),
): FreshnessToken {
  if (!status || status === "pending" || !dataDate) return { tone: "pending", key: "token.pending" };
  if (status === "error") return { tone: "alert", key: "token.error" };
  if (status === "stale") return { tone: "alert", key: "token.stale" };
  const days = Math.max(0, Math.floor((today.getTime() - new Date(dataDate).getTime()) / DAY));
  if (days <= 1) return { tone: "good", key: "token.live" };
  if (days < 60) return { tone: days <= 7 ? "good" : "watch", key: "token.daysAgo", values: { n: days } };
  return { tone: "watch", key: "token.monthsAgo", values: { n: Math.round(days / 30) } };
}

/** NDVI-anomaly z → hazard class (SDD §9.1, provisional thresholds). */
export function hazardFromZ(z: number): Hazard {
  if (z < -1.5) return "emergency";
  if (z < -1.0) return "alert";
  if (z < -0.5) return "watch";
  return "normal";
}

export const hazardTone: Record<Hazard, Tone> = {
  normal: "good",
  watch: "watch",
  alert: "alert",
  emergency: "emergency",
};
