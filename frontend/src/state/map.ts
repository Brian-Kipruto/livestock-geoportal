import type { Layer } from "@deck.gl/core";
import { create } from "zustand";

/** Screens publish their deck.gl layers here; the single shared MapView renders them. */
interface MapStore {
  deckLayers: Layer[];
  cursor: { lng: number; lat: number } | null;
  setDeckLayers: (layers: Layer[]) => void;
  setCursor: (c: { lng: number; lat: number } | null) => void;
}

export const useMapStore = create<MapStore>((set) => ({
  deckLayers: [],
  cursor: null,
  setDeckLayers: (deckLayers) => set({ deckLayers }),
  setCursor: (cursor) => set({ cursor }),
}));
