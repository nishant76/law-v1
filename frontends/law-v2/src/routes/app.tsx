import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { AppSidebar } from "@/components/app/AppSidebar";
import { Toaster } from "@/components/ui/sonner";
import { useAuthStore } from "@/store/authStore";
import { useState } from "react";

export const Route = createFileRoute("/app")({
  beforeLoad: () => {
    // beforeLoad runs on the server during SSR where localStorage doesn't exist.
    // Zustand persist returns null initial state on the server → redirect loop on every refresh.
    // Skip the check server-side; the client re-runs beforeLoad after hydration.
    if (typeof window === "undefined") return;
    const { accessToken, user } = useAuthStore.getState();
    if (!accessToken || !user) {
      throw redirect({ to: "/auth", search: { mode: "login" } });
    }
  },
  component: AppLayout,
});

function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try { return localStorage.getItem("sa-sidebar-collapsed") === "true"; } catch { return false; }
  });

  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem("sa-sidebar-collapsed", String(next)); } catch {}
      return next;
    });
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <AppSidebar collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
      <Toaster richColors position="bottom-right" />
    </div>
  );
}
