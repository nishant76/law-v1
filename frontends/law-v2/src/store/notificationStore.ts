import { create } from 'zustand'
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from '@/api/notifications'

const POLL_INTERVAL_MS = 60_000

interface NotificationState {
  items: AppNotification[]
  unread: number
  loading: boolean
  loaded: boolean
  refresh: () => Promise<void>
  markRead: (id: string) => Promise<void>
  markAllRead: () => Promise<void>
}

/**
 * Shared notification state.
 *
 * AppTopbar is rendered by each route rather than by the layout, so the bell
 * remounts on every navigation. Holding this in a store instead of component
 * state means N mounts share ONE fetch and ONE poll timer — otherwise every
 * click around the app refires the request and stacks another interval.
 *
 * Plain async/await throughout, never useMutation: TanStack Query v5 cancels
 * in-flight calls under Strict Mode dev (CLAUDE.md, GAP-050).
 */
export const useNotificationStore = create<NotificationState>()((set, get) => ({
  items: [],
  unread: 0,
  loading: false,
  loaded: false,

  refresh: async () => {
    if (get().loading) return // collapse concurrent callers
    set({ loading: true })
    try {
      const res = await listNotifications()
      set({
        items: res.data.data?.notifications ?? [],
        unread: res.data.data?.unread_count ?? 0,
        loaded: true,
      })
    } catch {
      // A failed poll is not worth interrupting the user for — the next tick
      // retries and nothing in the UI depends on it succeeding.
    } finally {
      set({ loading: false })
    }
  },

  markRead: async (id) => {
    const { items, unread } = get()
    const target = items.find((i) => i.id === id)
    if (!target || target.read) return
    // Optimistic, then resync on failure rather than leaving a lie on screen.
    set({
      items: items.map((i) => (i.id === id ? { ...i, read: true } : i)),
      unread: Math.max(0, unread - 1),
    })
    try {
      await markNotificationRead(id)
    } catch {
      void get().refresh()
    }
  },

  markAllRead: async () => {
    set({ items: get().items.map((i) => ({ ...i, read: true })), unread: 0 })
    try {
      await markAllNotificationsRead()
    } catch {
      void get().refresh()
    }
  },
}))

// ── Ref-counted shared poller ───────────────────────────────────────────────
// One timer for the whole app regardless of how many bells are mounted.
let subscribers = 0
let timer: ReturnType<typeof setInterval> | null = null

export function startNotificationPolling(): () => void {
  subscribers += 1
  if (subscribers === 1) {
    // First mount in this session kicks off the initial load; later mounts
    // reuse whatever the store already holds.
    if (!useNotificationStore.getState().loaded) {
      void useNotificationStore.getState().refresh()
    }
    timer = setInterval(() => void useNotificationStore.getState().refresh(), POLL_INTERVAL_MS)
  }
  return () => {
    subscribers -= 1
    if (subscribers <= 0 && timer) {
      clearInterval(timer)
      timer = null
      subscribers = 0
    }
  }
}
