import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { Logo } from "@/components/brand/Logo";
import { useAuthStore } from "@/store/authStore";
import { logout } from "@/api/auth";
import {
  FileText,
  FileSearch,
  MessageSquareReply,
  Search,
  ScrollText,
  Briefcase,
  CalendarClock,
  BookOpen,
  CreditCard,
  LayoutDashboard,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const PRIMARY = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/app/drafting", label: "Drafting", icon: FileText },
  { to: "/app/documents", label: "Documents", icon: FileSearch },
  { to: "/app/notice-reply", label: "Notice reply", icon: MessageSquareReply },
  { to: "/app/research", label: "Research", icon: Search },
  { to: "/app/summaries", label: "Summaries", icon: ScrollText },
] as const;

const PRACTICE = [
  { to: "/app/cases", label: "Cases", icon: Briefcase },
  { to: "/app/hearings", label: "Hearings", icon: CalendarClock },
  { to: "/app/process-guide", label: "Process guide", icon: BookOpen },
] as const;

const ACCOUNT = [
  { to: "/app/subscription", label: "Subscription", icon: CreditCard },
  { to: "/app/settings", label: "Settings", icon: Settings },
] as const;

function Section({
  label,
  items,
  collapsed,
}: {
  label: string;
  items: readonly { to: string; label: string; icon: any; exact?: boolean }[];
  collapsed: boolean;
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div className="mb-4">
      {collapsed ? (
        <div className="mx-2 mb-2 h-px bg-sidebar-border" />
      ) : (
        <div className="px-3 pb-2 text-[10px] font-medium uppercase tracking-[0.18em] text-sidebar-foreground/50">
          {label}
        </div>
      )}
      <ul className="space-y-0.5">
        {items.map((it) => {
          const active = it.exact
            ? pathname === it.to
            : pathname === it.to || pathname.startsWith(it.to + "/");
          const Icon = it.icon;
          return (
            <li key={it.to}>
              <Link
                to={it.to}
                title={collapsed ? it.label : undefined}
                className={`group flex items-center rounded-md text-sm transition-colors ${
                  collapsed ? "justify-center px-2 py-2.5" : "gap-3 px-3 py-2"
                } ${
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0 opacity-80" />
                {!collapsed && <span>{it.label}</span>}
                {!collapsed && active && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-amber-accent" />
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

interface AppSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function AppSidebar({ collapsed, onToggle }: AppSidebarProps) {
  const user = useAuthStore((s) => s.user);
  const logoutStore = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = async () => {
    try { await logout(); } catch { /* ignore */ }
    logoutStore();
    navigate({ to: "/auth", search: { mode: "login" } });
  };

  const displayName = user?.full_name ?? "Advocate";
  const initials = user?.initials ?? displayName.slice(0, 2).toUpperCase();

  return (
    <aside
      className={`hidden shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 md:flex ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Header / Logo */}
      <div
        className={`flex h-16 items-center border-b border-sidebar-border ${
          collapsed ? "justify-center px-2" : "gap-2 px-4"
        }`}
      >
        {!collapsed && (
          <Logo to="/app" className="flex-1 [&_*]:!text-sidebar-foreground" />
        )}
        <button
          onClick={onToggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="shrink-0 rounded-md p-1.5 text-sidebar-foreground/50 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Nav */}
      <div className={`flex-1 overflow-y-auto py-5 ${collapsed ? "px-1" : "px-3"}`}>
        <Section label="Work" items={PRIMARY} collapsed={collapsed} />
        <Section label="Practice" items={PRACTICE} collapsed={collapsed} />
        <Section label="Account" items={ACCOUNT} collapsed={collapsed} />
      </div>

      {/* User */}
      <div className="border-t border-sidebar-border p-3">
        {collapsed ? (
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-sidebar-primary text-sm font-medium text-sidebar-primary-foreground">
              {initials}
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="text-sidebar-foreground/50 hover:text-sidebar-foreground"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sidebar-primary text-sm font-medium text-sidebar-primary-foreground">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm text-sidebar-foreground">{displayName}</div>
              <div className="truncate text-xs text-sidebar-foreground/60">{user?.firm_name ?? ""}</div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="text-sidebar-foreground/50 hover:text-sidebar-foreground"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
