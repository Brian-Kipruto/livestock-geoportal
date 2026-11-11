import { useTranslation } from "react-i18next";
import { Panel } from "@/components/Panel";
import { Playback } from "@/components/Playback";
import { Token } from "@/components/Token";

/** Movement screen shell (FR-M1…M10). Data wiring lands in M2/M3. */
export function MovementPage() {
  const { t } = useTranslation();
  return (
    <>
      <Panel
        as="aside"
        className="absolute left-4 top-[196px] z-10 w-[360px] p-4"
        title={t("movement.title")}
        actions={<Token tone="pending">{t("movement.awaiting")}</Token>}
      >
        <p className="px-4 pb-3 pt-2 text-xs text-muted">{t("movement.privacy")}</p>
      </Panel>
      <Panel as="aside" className="absolute right-20 top-24 z-10 w-[330px] p-4">
        <h2 className="panel-title">{t("movement.insights")}</h2>
        <p className="mt-2 text-sm text-muted">{t("movement.awaiting")}</p>
      </Panel>
      <Playback subtitle="Track replay" />
    </>
  );
}
