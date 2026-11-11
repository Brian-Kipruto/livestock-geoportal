import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { AboutPage } from "@/features/about/AboutPage";
import { ComparePage } from "@/features/compare/ComparePage";
import { ExplorePage } from "@/features/explore/ExplorePage";
import { FinderPage } from "@/features/finder/FinderPage";
import { MovementPage } from "@/features/movement/MovementPage";
import { ProfilesPage } from "@/features/profiles/ProfilesPage";
import { AppShell } from "./AppShell";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to={`/explore${window.location.search}`} replace /> },
      { path: "explore", element: <ExplorePage /> },
      { path: "movement", element: <MovementPage /> },
      { path: "finder", element: <FinderPage /> },
      { path: "compare", element: <ComparePage /> },
      { path: "profiles/:areaId?", element: <ProfilesPage /> },
      { path: "about", element: <AboutPage /> },
      { path: "methods", element: <AboutPage /> },
      { path: "data", element: <AboutPage /> },
      { path: "*", element: <Navigate to="/explore" replace /> },
    ],
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
