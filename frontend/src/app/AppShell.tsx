import { Outlet, useLocation } from "react-router-dom";
import { MapFooter } from "@/components/MapFooter";
import { StatusStrip } from "@/components/StatusStrip";
import { ToolRail } from "@/components/ToolRail";
import { TopNav } from "@/components/TopNav";
import { TopRight } from "@/components/TopRight";
import { MapView } from "@/map/MapView";

/** Layout zones (SDD §11.2): the map is full-bleed and shared; screens float panels over it. */
export function AppShell() {
  const { pathname } = useLocation();
  return (
    <div className="relative h-full w-full overflow-hidden max-[899px]:h-auto max-[899px]:overflow-visible">
      <div className="absolute inset-0 max-[899px]:relative max-[899px]:h-[60vh]">
        <MapView />
      </div>
      <TopNav />
      <TopRight />
      {pathname.startsWith("/explore") && <StatusStrip />}
      <ToolRail />
      <MapFooter />
      <main>
        <Outlet />
      </main>
    </div>
  );
}
