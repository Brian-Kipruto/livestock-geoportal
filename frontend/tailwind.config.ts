import type { Config } from "tailwindcss";
import { tokens } from "./src/styles/tokens";

// Design tokens: SDD §11.3. Keep raw values in src/styles/tokens.ts (shared with map ramps).
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pigment: tokens.pigment,
        indigo: tokens.indigoNamed,
        parchment: tokens.neutral.parchment,
        surface: tokens.neutral.surface,
        ink: tokens.neutral.ink,
        muted: tokens.neutral.muted,
        line: tokens.neutral.line,
        panel: tokens.neutral.panel,
      },
      fontFamily: {
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: { panel: "12px", control: "8px" },
      boxShadow: { float: "0 8px 24px rgba(42, 38, 34, 0.12)" },
      minHeight: { touch: "44px" },
      minWidth: { touch: "44px" },
    },
  },
  plugins: [],
} satisfies Config;
