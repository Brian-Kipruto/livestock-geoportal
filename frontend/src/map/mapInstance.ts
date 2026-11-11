import type { Map } from "maplibre-gl";

/** The one shared MapLibre instance (set by MapView), for tools like zoom/reset. */
let instance: Map | null = null;
export const setMapInstance = (m: Map | null) => {
  instance = m;
};
export const getMap = () => instance;
