import { useTranslation } from "react-i18next";
import { Panel } from "./Panel";
import { Token } from "./Token";

/** Placeholder for screens cut from the December demo (SDD §16.3). */
export function ComingSoon({ screen }: { screen: "finder" | "compare" | "profiles" }) {
  const { t } = useTranslation();
  return (
    <Panel
      className="absolute left-4 top-[196px] w-[360px] p-4"
      title={t(`nav.${screen}`)}
      actions={<Token tone="pending">{t("pilot.badge")}</Token>}
    >
      <p className="px-4 pb-4 pt-2 text-sm leading-relaxed text-muted">{t(`pilot.${screen}`)}</p>
    </Panel>
  );
}
