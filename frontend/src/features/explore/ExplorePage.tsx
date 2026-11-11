import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useCountries } from "@/api/hooks";
import { Legend } from "@/components/Legend";
import { Playback } from "@/components/Playback";
import { Token } from "@/components/Token";
import { makeRamp } from "@/lib/ramp";
import { sampleHexes } from "@/map/sampleHexes";
import { useMapStore } from "@/state/map";
import { useView } from "@/state/view";
import { pigmentRamp } from "@/styles/tokens";
import { AreaPanel } from "./AreaPanel";
import { LayerDock } from "./LayerDock";

const FALLBACK_BBOX: [number, number, number, number] = [29.5, -1.5, 35.1, 4.3];
const colour = makeRamp(pigmentRamp, -2, 2);

export function ExplorePage() {
  const { t } = useTranslation();
  const { country, time, layers } = useView();
  const setDeckLayers = useMapStore((s) => s.setDeckLayers);
  const { data: countries } = useCountries();
  const bbox = countries?.find((c) => c.iso3 === country)?.bbox ?? FALLBACK_BBOX;
  const showNdvi = layers.includes("ndvi_anom_z");

  // TODO(M1/M3): replace sample data with GET /api/v1/hex/ndvi_anom_z/series/ (typed arrays).
  const data = useMemo(() => sampleHexes(bbox, time), [bbox, time]);

  useEffect(() => {
    setDeckLayers(
      showNdvi
        ? [
            new H3HexagonLayer<{ h3: string; value: number }>({
              id: "ndvi_anom_z",
              data,
              getHexagon: (d) => d.h3,
              getFillColor: (d) => colour(d.value),
              getLineColor: [255, 253, 248, 140],
              lineWidthMinPixels: 0.5,
              extruded: false,
              pickable: true,
              updateTriggers: { getFillColor: time },
            }),
          ]
        : [],
    );
    return () => setDeckLayers([]);
  }, [data, showNdvi, time, setDeckLayers]);

  return (
    <>
      <LayerDock />
      <AreaPanel />
      {showNdvi && (
        <Legend
          title="NDVI anomaly"
          ramp={pigmentRamp}
          token={<Token tone="pending">{t("token.illustrative")}</Token>}
          note={t("legend.sampleNote")}
          source="MODIS MOD13Q1 · DE Africa"
        />
      )}
      <Playback />
    </>
  );
}
