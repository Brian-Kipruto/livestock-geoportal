import { useTranslation } from "react-i18next";
import { Kpi } from "@/components/Kpi";
import { Panel } from "@/components/Panel";

/** Right panel: area card (FR-E6). KPIs are wired to /stats/admin-unit/ in M3. */
export function AreaPanel() {
  const { t } = useTranslation();
  return (
    <Panel as="aside" className="absolute right-20 top-24 z-10 w-[330px] p-4" aria-label={t("area.select")}>
      <h2 className="panel-title">{t("area.select")}</h2>
      <p className="mt-1 text-sm text-muted">{t("area.hint")}</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Kpi label="Pasture vs normal" value={null} />
        <Kpi label="SPI-3" value={null} />
        <Kpi label="Livestock (TLU)" value={null} />
        <Kpi label="km to water" value={null} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <button type="button" className="btn-primary" disabled>
          {t("area.profile")}
        </button>
        <button type="button" className="btn" disabled>
          {t("area.compare")}
        </button>
      </div>
    </Panel>
  );
}
