import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface LegendProps {
  title: string;
  ramp: readonly string[];
  token?: ReactNode;
  source?: string;
  note?: string;
}

/** Bottom-right legend: ramp, labels, source, freshness (FR-E10). */
export function Legend({ title, ramp, token, source, note }: LegendProps) {
  const { t } = useTranslation();
  return (
    <aside
      aria-label={`Legend: ${title}`}
      className="panel map-zone absolute bottom-4 right-4 z-20 w-[290px] p-3"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">{title}</h2>
        {token}
      </div>
      <div
        className="mt-2 h-3 rounded-full"
        style={{ background: `linear-gradient(90deg, ${ramp.join(", ")})` }}
      />
      <div className="mt-1 flex justify-between text-[11px] text-muted">
        <span>{t("legend.farBelow")}</span>
        <span>{t("legend.normal")}</span>
        <span>{t("legend.wellAbove")}</span>
      </div>
      {(source || note) && (
        <p className="mt-2 border-t border-line pt-2 text-[11px] text-muted">
          {note && <span className="block">{note}</span>}
          {source}
        </p>
      )}
    </aside>
  );
}
