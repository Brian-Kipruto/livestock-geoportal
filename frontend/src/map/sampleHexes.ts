import { cellToLatLng, polygonToCells } from "h3-js";

/**
 * ILLUSTRATIVE ONLY. Generates a smooth synthetic NDVI-anomaly-like pattern over the country
 * bbox so the hex rendering path can be exercised before real data is ingested (M1).
 * Always shown with an "Illustrative" token. Delete once /api/v1/hex/ is live.
 */
export function sampleHexes(
  bbox: [number, number, number, number],
  month: string,
  res = 5,
): { h3: string; value: number }[] {
  const [w, s, e, n] = bbox;
  const ring = [
    [s, w],
    [s, e],
    [n, e],
    [n, w],
    [s, w],
  ];
  const cells = polygonToCells(ring, res);
  const [y, m] = month.split("-").map(Number);
  const phase = ((y - 2015) * 12 + m) / 6;
  return cells.map((h3) => {
    const [lat, lng] = cellToLatLng(h3);
    const noise = (parseInt(h3.slice(-6, -3), 16) / 4096 - 0.5) * 0.5;
    const value =
      1.4 * Math.sin(phase + lat * 0.9) * Math.cos(lng * 0.7) + (lat - 1.5) * 0.35 - 0.2 + noise;
    return { h3, value };
  });
}
