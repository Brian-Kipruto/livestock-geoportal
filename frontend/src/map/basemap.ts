import type { StyleSpecification } from "maplibre-gl";
import { tokens } from "@/styles/tokens";

/**
 * "Pigment parchment" basemap (FR-E9): parchment background, desaturated OSM raster for
 * context, admin boundaries from Martin. No proprietary keys (SDD §7).
 * TODO(M3): replace the OSM raster with a self-hosted PMTiles basemap (Lite mode, ADR-005).
 */
export function parchmentStyle(origin: string): StyleSpecification {
  return {
    version: 8,
    glyphs: undefined,
    sources: {
      osm: {
        type: "raster",
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        maxzoom: 18,
        attribution: "© OpenStreetMap contributors",
      },
      admin: {
        type: "vector",
        url: `${origin}/tiles/v/admin_unit`,
      },
    },
    layers: [
      { id: "background", type: "background", paint: { "background-color": tokens.neutral.parchment } },
      {
        id: "osm",
        type: "raster",
        source: "osm",
        paint: {
          "raster-opacity": 0.35,
          "raster-saturation": -0.85,
          "raster-contrast": -0.15,
        },
      },
      {
        id: "admin-lines",
        type: "line",
        source: "admin",
        "source-layer": "admin_unit",
        paint: {
          "line-color": tokens.neutral.charcoal,
          "line-width": ["match", ["get", "level"], 1, 1.6, 2, 0.9, 0.5],
          "line-opacity": 0.7,
        },
      },
    ],
  };
}
