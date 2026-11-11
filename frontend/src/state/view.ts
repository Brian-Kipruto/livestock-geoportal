import { create } from "zustand";
import { parseViewState, serializeViewState, type ViewState } from "./urlState";

export const LATEST_MONTH = "2026-10";
export const FIRST_MONTH = "2015-01";

export const DEFAULT_VIEW: ViewState = {
  country: import.meta.env.VITE_DEFAULT_COUNTRY ?? "UGA",
  area: null,
  layers: ["ndvi_anom_z", "water_points", "admin_units"],
  time: LATEST_MONTH,
  scenario: "obs",
  role: "policy",
  lite: false,
};

interface ViewStore extends ViewState {
  set: (patch: Partial<ViewState>) => void;
  toggleLayer: (key: string) => void;
}

export const useView = create<ViewStore>((set) => ({
  ...parseViewState(typeof window === "undefined" ? "" : window.location.search, DEFAULT_VIEW),
  set: (patch) => set(patch),
  toggleLayer: (key) =>
    set((s) => ({
      layers: s.layers.includes(key) ? s.layers.filter((k) => k !== key) : [...s.layers, key],
    })),
}));

/** Mirror the store into the URL (replaceState: no history spam while scrubbing time). */
useView.subscribe((s) => {
  const qs = serializeViewState(s);
  if (window.location.search.slice(1) !== qs) {
    window.history.replaceState(null, "", `${window.location.pathname}?${qs}`);
  }
});
