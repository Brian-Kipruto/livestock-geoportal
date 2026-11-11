import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";
import type { Country, MapLayer } from "./types";

export function useCountries() {
  return useQuery({
    queryKey: ["countries"],
    queryFn: ({ signal }) => apiGet<Country[]>("/countries/", signal),
    staleTime: 60 * 60 * 1000,
  });
}

export function useLayers(country: string, role: string) {
  return useQuery({
    queryKey: ["layers", country, role],
    queryFn: ({ signal }) =>
      apiGet<MapLayer[]>(`/layers/?country=${encodeURIComponent(country)}&role=${role}`, signal),
    staleTime: 5 * 60 * 1000,
  });
}
