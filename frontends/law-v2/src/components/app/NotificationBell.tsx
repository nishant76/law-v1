import { useEffect, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Bell, Check, Loader2 } from "lucide-react";
import type { AppNotification } from "@/api/notifications";
import {
  startNotificationPolling,
  useNotificationStore,
} from "@/store/notificationStore";

/**
 * Notification bell. The dot only appears when there is something unread —
 * a permanently-lit indicator teaches people to ignore it.
 *
 * The dropdown is plain markup rather than the Radix Popover in components/ui:
 * no Radix primitive renders anywhere else in this app, and under this project's
 * TanStack Start / Vite setup importing one gets a second React instance
 * ("Invalid hook call" inside <Popover>). The other overlays here — the drafting
 * brief modal, CitationSearchModal — are hand-rolled for the same reason.
 *
 * State and polling live in notificationStore, not here: AppTopbar is rendered
 * per route, so this component remounts on every navigation and per-component
 * state would refetch each time and stack a timer per mount.
 */
export function NotificationBell() {
  const items = useNotificationStore((s) => s.items);
  const unread = useNotificationStore((s) => s.unread);
  const loading = useNotificationStore((s) => s.loading);
  const refresh = useNotificationStore((s) => s.refresh);
  const markRead = useNotificationStore((s) => s.markRead);
  const markAllRead = useNotificationStore((s) => s.markAllRead);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Joins the shared poller; the last bell to unmount stops the timer.
  useEffect(() => startNotificationPolling(), []);

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) void refresh(); // opening is an explicit "show me now"
  };

  const handleRead = (n: AppNotification) => void markRead(n.id);
  const handleReadAll = () => void markAllRead();

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={toggle}
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
        aria-expanded={open}
        className="hairline relative inline-flex h-9 w-9 items-center justify-center rounded-md bg-card"
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-accent px-1 text-[9px] font-bold text-amber-accent-fg">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Notifications"
          className="hairline absolute right-0 top-11 z-50 w-96 overflow-hidden rounded-md bg-card shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <span className="text-sm font-medium">Notifications</span>
            {unread > 0 && (
              <button
                type="button"
                onClick={handleReadAll}
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                <Check className="h-3 w-3" /> Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {loading && items.length === 0 ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : items.length === 0 ? (
              <p className="px-4 py-10 text-center text-sm text-muted-foreground">
                Nothing yet. Hearing and deadline alerts will appear here.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {items.map((n) => {
                  const content = (
                    <div className="flex gap-3 px-4 py-3">
                      <span
                        className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                          n.read ? "bg-transparent" : "bg-amber-accent"
                        }`}
                      />
                      <div className="min-w-0 flex-1">
                        <div className={`text-sm ${n.read ? "text-muted-foreground" : "font-medium"}`}>
                          {n.title}
                        </div>
                        {n.body && (
                          <div className="mt-0.5 line-clamp-2 whitespace-pre-line text-xs text-muted-foreground">
                            {n.body}
                          </div>
                        )}
                        <div className="mt-1 text-[11px] text-muted-foreground">
                          {new Date(n.created_at).toLocaleString("en-IN", {
                            day: "2-digit",
                            month: "short",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    </div>
                  );

                  return (
                    <li key={n.id} onClick={() => handleRead(n)} className="hover:bg-sand/40">
                      {n.link_path ? (
                        <Link to={n.link_path} onClick={() => setOpen(false)} className="block">
                          {content}
                        </Link>
                      ) : (
                        <div className="cursor-default">{content}</div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
