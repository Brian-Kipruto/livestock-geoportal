import { useTranslation } from "react-i18next";
import { getMap } from "@/map/mapInstance";

const UGANDA: [number, number, number, number] = [29.5, -1.5, 35.1, 4.3];

/** Right-edge tool rail (SDD §11.2). Identify/draw/measure/basemap/3D arrive in M3/pilot. */
export function ToolRail() {
  const { t } = useTranslation();
  const tools = [
    { label: t("tools.zoomIn"), glyph: "+", run: () => getMap()?.zoomIn() },
    { label: t("tools.zoomOut"), glyph: "−", run: () => getMap()?.zoomOut() },
    { label: t("tools.reset"), glyph: "⌖", run: () => getMap()?.fitBounds(UGANDA, { padding: 40 }) },
    {
      label: t("tools.fullscreen"),
      glyph: "⛶",
      run: () =>
        document.fullscreenElement
          ? void document.exitFullscreen()
          : void document.documentElement.requestFullscreen(),
    },
  ];
  return (
    <div className="panel absolute right-4 top-1/2 z-20 flex -translate-y-1/2 flex-col p-1 max-[899px]:hidden">
      {tools.map((tool) => (
        <button
          key={tool.label}
          type="button"
          aria-label={tool.label}
          title={tool.label}
          onClick={tool.run}
          className="h-11 w-11 rounded-control text-lg text-ink hover:bg-white/70"
        >
          {tool.glyph}
        </button>
      ))}
    </div>
  );
}
