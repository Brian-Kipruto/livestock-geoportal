import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";
import { getMap } from "@/map/mapInstance";
import { useMapStore } from "@/state/map";

/** Bottom-left: north arrow, scale bar, cursor coordinates (FR-E11). Overview map: M3. */
export function MapFooter() {
  const cursor = useMapStore((s) => s.cursor);
  const scaleHost = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let control: maplibregl.ScaleControl | null = null;
    const id = window.setInterval(() => {
      const map = getMap();
      if (!map || !scaleHost.current || control) return;
      control = new maplibregl.ScaleControl({ maxWidth: 100, unit: "metric" });
      scaleHost.current.appendChild(control.onAdd(map));
      window.clearInterval(id);
    }, 100);
    return () => {
      window.clearInterval(id);
      control?.onRemove();
    };
  }, []);

  const fmt = (v: number, pos: string, neg: string) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? pos : neg}`;

  return (
    <div className="panel absolute bottom-4 left-4 z-20 flex items-center gap-4 px-3 py-2 text-xs max-[899px]:hidden">
      <span aria-label="North" className="text-base">
        ▲
      </span>
      <div ref={scaleHost} className="[&_.maplibregl-ctrl-scale]:border-ink [&_.maplibregl-ctrl-scale]:bg-transparent" />
      <span className="tabular-nums text-muted" aria-live="off">
        {cursor ? `${fmt(cursor.lat, "N", "S")} · ${fmt(cursor.lng, "E", "W")}` : "—"}
      </span>
    </div>
  );
}
