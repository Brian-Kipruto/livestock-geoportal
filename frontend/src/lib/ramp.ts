/** Linear colour ramp interpolation for deck.gl fills. */

export type RGBA = [number, number, number, number];

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function makeRamp(colors: readonly string[], min: number, max: number, alpha = 220) {
  const stops = colors.map(hexToRgb);
  return (value: number | null | undefined): RGBA => {
    if (value == null || Number.isNaN(value)) return [0, 0, 0, 0];
    const t = Math.min(1, Math.max(0, (value - min) / (max - min)));
    const pos = t * (stops.length - 1);
    const i = Math.min(stops.length - 2, Math.floor(pos));
    const f = pos - i;
    const [a, b] = [stops[i], stops[i + 1]];
    return [
      Math.round(a[0] + (b[0] - a[0]) * f),
      Math.round(a[1] + (b[1] - a[1]) * f),
      Math.round(a[2] + (b[2] - a[2]) * f),
      alpha,
    ];
  };
}
