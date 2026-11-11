import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Role } from "@/state/urlState";
import { useView } from "@/state/view";

const ROLES: Role[] = ["policy", "investor", "technical"];

/** Top-right: role switch (presentation preset, not permissions), Lite, language, share, help. */
export function TopRight() {
  const { t, i18n } = useTranslation();
  const { role, lite, set } = useView();
  const [copied, setCopied] = useState(false);

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked: URL bar already holds the state */
    }
  };

  return (
    <div className="panel map-zone absolute right-4 top-4 z-20 flex flex-wrap items-center gap-2 p-2">
      <div className="seg" role="group" aria-label={t("role.label")}>
        {ROLES.map((r) => (
          <button key={r} type="button" aria-pressed={role === r} onClick={() => set({ role: r })}>
            {t(`role.${r}`)}
          </button>
        ))}
      </div>
      <label className="flex min-h-touch items-center gap-2 px-2 text-sm">
        <input type="checkbox" checked={lite} onChange={(e) => set({ lite: e.target.checked })} />
        {t("top.lite")}
      </label>
      <label className="sr-only" htmlFor="lang">
        {t("top.language")}
      </label>
      <select
        id="lang"
        className="min-h-touch rounded-control border border-line bg-surface px-2 text-sm"
        value={i18n.language}
        onChange={(e) => void i18n.changeLanguage(e.target.value)}
      >
        <option value="en">EN</option>
        <option value="sw">SW</option>
      </select>
      <button type="button" className="btn" onClick={share} aria-live="polite">
        {copied ? t("top.copied") : t("top.share")}
      </button>
      <button type="button" className="btn w-11 rounded-full px-0" aria-label={t("top.help")}>
        ?
      </button>
    </div>
  );
}
