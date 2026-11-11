import { MapboxOverlay } from "@deck.gl/mapbox";
import maplibregl from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMapStore } from "@/state/map";
import { parchmentStyle } from "./basemap";
import { setMapInstance } from "./mapInstance";

const UGANDA_BOUNDS: [number, number, number, number] = [29.5, -1.5, 35.1, 4.3];

function hasWebGL2(): boolean {
  try {
    return !!document.createElement("canvas").getContext("webgl2");
  } catch {
    return false;
  }
}

/** Full-bleed map shared by all screens. Screens push deck.gl layers via useMapStore. */
export function MapView() {
  const { t } = useTranslation();
  const container = useRef<HTMLDivElement>(null);
  const overlay = useRef<MapboxOverlay | null>(null);
  const deckLayers = useMapStore((s) => s.deckLayers);
  const setCursor = useMapStore((s) => s.setCursor);
  const [supported] = useState(hasWebGL2);

  useEffect(() => {
    if (!supported || !container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: parchmentStyle(window.location.origin),
      bounds: UGANDA_BOUNDS,
      fitBoundsOptions: { padding: 40 },
      attributionControl: { compact: true },
      dragRotate: false,
    });
    const deck = new MapboxOverlay({ interleaved: false, layers: [] });
    map.addControl(deck);
    map.on("mousemove", (e) => setCursor({ lng: e.lngLat.lng, lat: e.lngLat.lat }));
    map.on("error", (e) => console.warn("[map]", e.error?.message ?? e));
    overlay.current = deck;
    setMapInstance(map);
    return () => {
      setMapInstance(null);
      overlay.current = null;
      map.remove();
    };
  }, [supported, setCursor]);

  useEffect(() => {
    overlay.current?.setProps({ layers: deckLayers });
  }, [deckLayers]);

  if (!supported) {
    return (
      <div role="alert" className="flex h-full items-center justify-center p-8 text-center text-muted">
        {t("map.webgl")}
      </div>
    );
  }
  return <div ref={container} className="absolute inset-0" aria-label="Map" role="application" />;
}
