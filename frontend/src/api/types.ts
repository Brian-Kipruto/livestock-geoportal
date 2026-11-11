/** Mirrors the DRF serializers in backend/apps/{geo,catalog}/serializers.py. Later: generate from OpenAPI. */
import type { DatasetStatus } from "@/lib/freshness";

export interface Country {
  iso3: string;
  name: string;
  admin_levels: { level: number; label: string }[];
  seasons: { key: string; label: string; months: number[] }[];
  languages: string[];
  bbox: [number, number, number, number];
}

export interface LayerSource {
  dataset: string;
  name: string;
  provider: string;
  licence: string;
  status: DatasetStatus;
  data_date: string | null;
}

export interface MapLayer {
  key: string;
  name: string;
  kind: "hex" | "vector" | "raster";
  theme: string;
  indicator: string | null;
  vector_source: string;
  style: Record<string, unknown>;
  legend: Record<string, unknown>;
  roles: string[];
  default_on: boolean;
  sort_order: number;
  source: LayerSource | null;
}
