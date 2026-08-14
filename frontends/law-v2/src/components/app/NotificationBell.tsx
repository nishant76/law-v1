import { useCallback, useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Bell, Check, Loader2 } from "lucide-react";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from "@/api/notifications";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const POLL_INTERVAL_MS = 60_000;

/**
 * Notification bell. The dot only appears when there is something unread —
 * a permanently-lit indicator teaches people to ignore it.
 *
 * Uses plain async/await rather than useMutation: TanStack Query v5 attaches an
 * AbortController that cancels in-flight calls under React 18 Strict Mode
 * (see CLAUDE.md, GAP-050).
 */
export function NotificationBell() {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listNotifications();
      setItems(res.data.data?.notifications ?? []);
      setUnread(res.data.data?.unread_count ?? 0);
    } catch {
      // A failed poll is not worth interrupting the user for — the next tick
      // retries, and nothing in the UI depends on it succeeding.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  const handleOpen = (next: boolean) => {
    setOpen(next);
    if (next) load();
  };

  const handleRead = async (n: AppNotification) => {
    if (n.read) return;
    setItems((prev) => prev.map((i) => (i.id === n.id ? { ...i, read: true } : i)));
    setUnread((u) => Math.max(0, u - 1));
    try {
      await markNotificationRead(n.id);
    } catch {
      load(); // resync on failure rather than leaving an optimistic lie
    }
  };

  const handleReadAll = async () => {
    setItems((prev) => prev.map((i) => ({ ...i, read: true })));
    setUnread(0);
    try {
      await markAllNotificationsRead();
    } catch {
      load();
    }
  };

  return (
    <Popover open={open} onOpenChange={handleOpen}>
      <PopoverTrigger asChild>
        <button
          aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
          className="hairline relative inline-flex h-9 w-9 items-center justify-center rounded-md bg-card"
        >
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-accent px-1 text-[9px] font-bold text-background">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </button>
      </PopoverTrigger>

      <PopoverContent align="end" className="w-96 p-0">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-sm font-medium">Notifications</span>
          {unread > 0 && (
            <button
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
      </PopoverContent>
    </Popover>
  );
}
