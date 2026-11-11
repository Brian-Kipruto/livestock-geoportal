import type { ReactNode } from "react";
import type { Tone } from "@/lib/freshness";

/** Status token: pill + dot + text — never colour alone (SDD §11.3, NFR-8). */
const STYLES: Record<Tone, { bg: string; text: string; dot: string; border?: string }> = {
  good: { bg: "#DDE6CF", text: "#3F5A2C", dot: "#4E6B3A" },
  watch: { bg: "#F2E3BC", text: "#6F5212", dot: "#C8932B" },
  alert: { bg: "#F0D3BE", text: "#8A3D12", dot: "#B8652B" },
  emergency: { bg: "#E5C3BA", text: "#6A1E14", dot: "#6B4226" },
  pending: { bg: "transparent", text: "#5C4E3F", dot: "#8C7B66", border: "1px dashed #8C7B66" },
};

export function Token({ tone, children }: { tone: Tone; children: ReactNode }) {
  const s = STYLES[tone];
  return (
    <span
      data-tone={tone}
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ background: s.bg, color: s.text, border: s.border ?? "1px solid transparent" }}
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: s.dot }} />
      {children}
    </span>
  );
}
