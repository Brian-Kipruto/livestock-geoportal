/** Design tokens — SDD §11.3. Single source for Tailwind and map colour ramps. */
export const tokens = {
  pigment: {
    umber: "#6B4226",
    sienna: "#B8652B",
    ochre: "#C8932B",
    bone: "#D9C9A3",
    sage: "#9AAE84",
    verte: "#5E7744",
  },
  /** Suitability & water ramp, light → dark. */
  indigo: ["#E4E2D6", "#B9C3C4", "#8EA3AE", "#5E7F96", "#3C5A73", "#22394C"],
  indigoNamed: {
    50: "#E4E2D6",
    100: "#B9C3C4",
    300: "#8EA3AE",
    500: "#5E7F96",
    700: "#3C5A73",
    900: "#22394C",
  },
  neutral: {
    parchment: "#E9E0CC",
    panel: "rgba(250,246,238,0.88)",
    surface: "#FFFDF8",
    ink: "#2A2622",
    muted: "#5C4E3F",
    line: "rgba(107,66,38,0.18)",
    charcoal: "#2A2622",
  },
} as const;

/** Pasture/climate diverging ramp, far below → well above normal. */
export const pigmentRamp = [
  tokens.pigment.umber,
  tokens.pigment.sienna,
  tokens.pigment.ochre,
  tokens.pigment.bone,
  tokens.pigment.sage,
  tokens.pigment.verte,
] as const;
