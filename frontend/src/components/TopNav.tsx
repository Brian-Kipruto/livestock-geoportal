import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

const SCREENS = ["explore", "movement", "finder", "compare", "profiles"] as const;

/** Top-left: brand, search, primary nav (SDD §11.2). */
export function TopNav() {
  const { t } = useTranslation();
  return (
    <nav aria-label="Primary" className="panel map-zone absolute left-4 top-4 z-20 w-[360px] p-3">
      <div className="flex items-center gap-3">
        <span aria-hidden className="h-8 w-8 shrink-0 rounded-control bg-pigment-umber" />
        <h1 className="font-serif text-lg font-semibold leading-tight">{t("app.title")}</h1>
      </div>
      <label className="sr-only" htmlFor="global-search">
        {t("app.search")}
      </label>
      <input
        id="global-search"
        type="search"
        placeholder={t("app.search")}
        className="mt-3 min-h-touch w-full rounded-control border border-line bg-surface px-3 text-sm placeholder:text-muted/70"
      />
      <ul className="mt-3 flex flex-wrap gap-1">
        {SCREENS.map((s) => (
          <li key={s}>
            <NavLink
              to={`/${s}${window.location.search}`}
              className={({ isActive }) =>
                `inline-flex min-h-[36px] items-center rounded-control px-3 text-sm ${
                  isActive ? "bg-pigment-umber font-semibold text-surface" : "text-ink hover:bg-white/60"
                }`
              }
            >
              {t(`nav.${s}`)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
