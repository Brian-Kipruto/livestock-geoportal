import { useTranslation } from "react-i18next";
import { useLayers } from "@/api/hooks";
import type { MapLayer } from "@/api/types";
import { FreshnessToken } from "@/components/FreshnessToken";
import { Panel } from "@/components/Panel";
import { Token } from "@/components/Token";
import { useView } from "@/state/view";

/** Layer dock grouped by theme with toggle + freshness token (FR-E1). */
export function LayerDock() {
  const { t } = useTranslation();
  const { country, role, layers: active, toggleLayer } = useView();
  const { data, isError, isLoading } = useLayers(country, role);

  const groups = new Map<string, MapLayer[]>();
  for (const l of data ?? []) groups.set(l.theme, [...(groups.get(l.theme) ?? []), l]);

  return (
    <Panel
      as="aside"
      aria-label={t("layers.title")}
      className="absolute left-4 top-[196px] z-10 flex max-h-[calc(100vh-196px-96px)] w-[360px] flex-col"
      title={t("layers.title")}
      actions={<Token tone="emergency">{t("layers.on", { n: active.length })}</Token>}
    >
      <div className="overflow-y-auto px-4 pb-3">
        {isLoading && <p className="py-3 text-sm text-muted">…</p>}
        {isError && (
          <p className="py-3 text-sm text-muted" role="status">
            {t("layers.unavailable")}
          </p>
        )}
        {[...groups.entries()].map(([theme, items]) => (
          <div key={theme} className="mt-3">
            <h3 className="section-label">{t(`layers.theme.${theme}`, theme)}</h3>
            <ul>
              {items.map((l) => (
                <li key={l.key} className="flex min-h-touch items-center gap-2 border-b border-line">
                  <input
                    id={`layer-${l.key}`}
                    type="checkbox"
                    checked={active.includes(l.key)}
                    onChange={() => toggleLayer(l.key)}
                  />
                  <label htmlFor={`layer-${l.key}`} className="flex-1 text-sm">
                    {l.name}
                  </label>
                  <FreshnessToken source={l.source} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Panel>
  );
}
