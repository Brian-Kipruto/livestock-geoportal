import { useTranslation } from "react-i18next";
import { Token } from "./Token";

/** Top-centre status strip (FR-E12). Counts come from /status/hazard/ in the pilot. */
export function StatusStrip() {
  const { t } = useTranslation();
  return (
    <div className="panel absolute left-1/2 top-4 z-20 flex -translate-x-1/2 items-center gap-2 px-3 py-2 text-sm max-[1400px]:hidden">
      <span className="font-medium">{t("status.drought")}</span>
      <Token tone="good">{t("token.normal")} · —</Token>
      <Token tone="watch">{t("token.watch")} · —</Token>
      <Token tone="alert">{t("token.alert")} · —</Token>
      <Token tone="emergency">{t("token.emergency")} · —</Token>
    </div>
  );
}
