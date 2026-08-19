import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  AlertTriangle,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Gavel,
  Loader2,
  MapPin,
  Plus,
  RefreshCw,
} from "lucide-react";

import { AppTopbar } from "@/components/app/AppTopbar";
import { RecordOutcomeDialog } from "@/components/app/RecordOutcomeDialog";
import { AddHearingDialog } from "@/components/app/AddHearingDialog";
import { getDiary, type HearingEntry } from "@/api/diary";
import { listDeadlines } from "@/api/deadlines";
import { syncEcourtsHearings } from "@/api/ecourts";
import type { Deadline } from "@/types";

export const Route = createFileRoute("/app/hearings")({
  head: () => ({ meta: [{ title: "Diary — SuperAdvocate.Ai" }] }),
  component: Diary,
});

/** Local (IST) YYYY-MM-DD for a Date — the diary API keys on the IST calendar. */
function istDateKey(d: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}

function addDays(key: string, delta: number): string {
  const [y, m, d] = key.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + delta);
  return dt.toISOString().slice(0, 10);
}

function prettyDate(key: string): string {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-IN", {
    timeZone: "UTC",
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function Diary() {
  const today = istDateKey(new Date());
  const [day, setDay] = useState(today);
  const [entries, setEntries] = useState<HearingEntry[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState<HearingEntry | null>(null);
  const [adding, setAdding] = useState(false);
  // Day view answers "what is listed now"; week view is what you scan on a
  // Sunday to plan. The API already supports a range, so this is a read shape.
  const [range, setRange] = useState<"day" | "week">("day");

  const load = useCallback(async (target: string, span: "day" | "week" = "day") => {
    setLoading(true);
    setError(null);
    try {
      const [diaryRes, deadlineRes] = await Promise.all([
        getDiary(target, span === "week" ? 7 : 1),
        listDeadlines(),
      ]);
      setEntries(diaryRes.data.data?.entries ?? []);
      setDeadlines(deadlineRes.data.data ?? []);
    } catch {
      setError("Could not load your diary. Please check your connection and retry.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(day, range);
  }, [day, range, load]);

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    const id = toast.loading("Syncing hearing dates from eCourts…");
    try {
      await syncEcourtsHearings();
      await load(day, range);
      toast.success("eCourts sync complete.", { id });
    } catch {
      toast.error("eCourts sync failed. Please try again later.", { id });
    } finally {
      setSyncing(false);
    }
  };

  // Deadlines that are not hearings — limitation periods and filing dates get
  // their own column; they are not "in court today" items.
  const otherDeadlines = deadlines.filter((d) => d.deadline_type !== "hearing");
  const missed = deadlines.filter((d) => d.urgency === "missed");
  const pending = entries.filter((e) => e.status === "scheduled");
  const isPast = day < today;

  return (
    <>
      <AppTopbar
        eyebrow="Practice"
        title="Diary"
        actions={
          <button
            onClick={handleSync}
            disabled={syncing}
            className="hairline inline-flex h-9 items-center gap-2 rounded-md bg-card px-3 text-sm disabled:opacity-50"
          >
            {syncing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Sync from eCourts
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
        {/* Date navigator */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            aria-label={range === "week" ? "Previous week" : "Previous day"}
            onClick={() => setDay((d) => addDays(d, range === "week" ? -7 : -1))}
            className="hairline inline-flex h-9 w-9 items-center justify-center rounded-md bg-card"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            aria-label={range === "week" ? "Next week" : "Next day"}
            onClick={() => setDay((d) => addDays(d, range === "week" ? 7 : 1))}
            className="hairline inline-flex h-9 w-9 items-center justify-center rounded-md bg-card"
          >
            <ChevronRight className="h-4 w-4" />
          </button>

          <div>
            <h2 className="font-serif text-xl leading-tight">
              {range === "week"
                ? `${prettyDate(day)} — ${prettyDate(addDays(day, 6))}`
                : prettyDate(day)}
            </h2>
            <p className="text-xs text-muted-foreground">
              {day === today
                ? "Today"
                : day === addDays(today, 1)
                  ? "Tomorrow"
                  : isPast
                    ? "Past date"
                    : "Upcoming"}
              {" · "}
              {entries.length} matter{entries.length === 1 ? "" : "s"} listed
            </p>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <div className="hairline inline-flex overflow-hidden rounded-md">
              {(["day", "week"] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={`h-9 px-3 text-sm capitalize transition-colors ${
                    range === r
                      ? "bg-amber-accent text-amber-accent-fg"
                      : "bg-card text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
            <button
              onClick={() => setAdding(true)}
              className="inline-flex h-9 items-center gap-1.5 rounded-md bg-foreground px-3 text-sm text-background"
            >
              <Plus className="h-3.5 w-3.5" /> Add hearing
            </button>
            <input
              type="date"
              value={day}
              onChange={(e) => e.target.value && setDay(e.target.value)}
              className="hairline h-9 rounded-md bg-card px-3 text-sm"
            />
            {day !== today && (
              <button
                onClick={() => setDay(today)}
                className="hairline h-9 rounded-md bg-card px-3 text-sm"
              >
                Today
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4" /> {error}
          </div>
        )}

        {loading ? (
          <div className="mt-16 flex justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            {/* ---------------------------------------------- cause list */}
            <div className="hairline rounded-xl bg-card p-6">
              <div className="flex items-baseline justify-between">
                <h3 className="font-serif text-lg">{range === "week" ? "This week" : "Cause list"}</h3>
                {pending.length > 0 && isPast && (
                  <span className="text-xs text-amber-accent">
                    {pending.length} not yet recorded
                  </span>
                )}
              </div>

              {entries.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  <CalendarDays className="mx-auto h-6 w-6 opacity-40" />
                  <p className="mt-3">Nothing listed {range === "week" ? "this week" : "on this date"}.</p>
                  <p className="mt-1 text-xs">
                    Hearing dates arrive automatically from eCourts once your cases are
                    imported.
                  </p>
                </div>
              ) : (
                <ul className="mt-4 divide-y divide-border">
                  {entries.map((e) => (
                    <li key={e.id} className="py-4">
                      <div className="flex items-start gap-4">
                        <div className="w-14 shrink-0 text-center">
                          {range === "week" ? (
                            <>
                              <div className="font-mono text-sm">
                                {new Date(e.hearing_date).toLocaleDateString("en-IN", {
                                  timeZone: "Asia/Kolkata",
                                  day: "2-digit",
                                  month: "short",
                                })}
                              </div>
                              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                                {e.board_number ? `item ${e.board_number}` : "date"}
                              </div>
                            </>
                          ) : (
                            <>
                              <div className="font-mono text-sm">{e.board_number ?? "—"}</div>
                              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                                item
                              </div>
                            </>
                          )}
                        </div>

                        <div className="min-w-0 flex-1">
                          <Link
                            to="/app/cases/$id"
                            params={{ id: e.matter_id }}
                            className="text-sm font-medium hover:underline"
                          >
                            {e.case_name}
                          </Link>
                          <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                            {e.court && (
                              <span className="inline-flex items-center gap-1">
                                <MapPin className="h-3 w-3" /> {e.court}
                              </span>
                            )}
                            {e.judge_name && (
                              <span className="inline-flex items-center gap-1">
                                <Gavel className="h-3 w-3" /> {e.judge_name}
                              </span>
                            )}
                            {e.matter_number && (
                              <span className="font-mono">{e.matter_number}</span>
                            )}
                          </div>
                          {e.purpose && (
                            <div className="mt-1 text-xs text-muted-foreground">
                              For: {e.purpose}
                            </div>
                          )}
                          {e.outcome && (
                            <div className="mt-2 whitespace-pre-line rounded-md bg-sand/50 p-3 text-xs">
                              {e.outcome}
                              {e.next_date && (
                                <div className="mt-1 font-medium">
                                  Adjourned to{" "}
                                  {new Date(e.next_date).toLocaleDateString("en-IN", {
                                    timeZone: "Asia/Kolkata",
                                    day: "numeric",
                                    month: "short",
                                    year: "numeric",
                                  })}
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        <div className="flex shrink-0 flex-col items-end gap-2">
                          <HearingStatusBadge status={e.status} />
                          <button
                            onClick={() => setRecording(e)}
                            className="hairline rounded-md bg-card px-2.5 py-1 text-xs"
                          >
                            {e.status === "scheduled" ? "Record" : "Edit"}
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* ------------------------------------------ side: deadlines */}
            <div className="space-y-6">
              <div className="hairline rounded-xl bg-card p-6">
                <h3 className="font-serif text-lg">Filing & limitation dates</h3>
                {otherDeadlines.length === 0 ? (
                  <p className="mt-4 text-xs text-muted-foreground">
                    No filing or limitation deadlines in the next 30 days.
                  </p>
                ) : (
                  <ul className="mt-4 space-y-2">
                    {otherDeadlines.map((d) => (
                      <li
                        key={d.id}
                        className={`rounded-md p-3 text-sm ${
                          d.urgency === "urgent" ? "bg-destructive/10" : "bg-sand/40"
                        }`}
                      >
                        <div className="font-medium">{d.matter_title}</div>
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {new Date(d.due_date).toLocaleDateString("en-IN", {
                            timeZone: "Asia/Kolkata",
                            day: "numeric",
                            month: "short",
                          })}
                          {" · "}
                          {d.days_remaining >= 0
                            ? `${d.days_remaining} day${d.days_remaining === 1 ? "" : "s"} left`
                            : "overdue"}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {missed.length > 0 && (
                <div className="hairline rounded-xl bg-card p-6">
                  <h3 className="font-serif text-lg text-destructive">Missed</h3>
                  <ul className="mt-4 space-y-2 text-sm">
                    {missed.map((d) => (
                      <li key={d.id}>
                        <div className="font-medium">{d.matter_title}</div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(d.due_date).toLocaleDateString("en-IN", {
                            timeZone: "Asia/Kolkata",
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <RecordOutcomeDialog
        entry={recording}
        onClose={() => setRecording(null)}
        onSaved={() => {
          setRecording(null);
          load(day, range);
        }}
      />

      <AddHearingDialog
        open={adding}
        defaultDate={day}
        onClose={() => setAdding(false)}
        onSaved={() => {
          setAdding(false);
          load(day, range);
        }}
      />
    </>
  );
}

function HearingStatusBadge({ status }: { status: HearingEntry["status"] }) {
  const styles: Record<HearingEntry["status"], string> = {
    scheduled: "bg-sand text-foreground",
    held: "bg-emerald-500/15 text-emerald-700",
    adjourned: "bg-amber-accent/20 text-amber-accent",
    not_taken_up: "bg-muted text-muted-foreground",
    disposed: "bg-muted text-muted-foreground",
  };
  const labels: Record<HearingEntry["status"], string> = {
    scheduled: "Listed",
    held: "Heard",
    adjourned: "Adjourned",
    not_taken_up: "Not taken up",
    disposed: "Disposed",
  };
  return (
    <span
      className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}
