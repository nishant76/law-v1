import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { useState, useEffect } from "react";
import { listDeadlines } from "@/api/deadlines";
import { syncEcourtsHearings } from "@/api/ecourts";
import type { Deadline } from "@/types";
import { MapPin, RefreshCw, Loader2, AlertTriangle } from "lucide-react";

export const Route = createFileRoute("/app/hearings")({
  head: () => ({ meta: [{ title: "Hearings — SuperAdvocate.Ai" }] }),
  component: Hearings,
});

function Hearings() {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<string | null>(null);

  useEffect(() => {
    loadDeadlines();
  }, []);

  const loadDeadlines = async () => {
    setLoading(true);
    try {
      const res = await listDeadlines();
      setDeadlines(res.data.data ?? []);
    } catch {
      setError("Failed to load hearings. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      await syncEcourtsHearings();
      setLastSync(new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }));
      await loadDeadlines();
    } catch {
      setError("eCourts sync failed. Please try again later.");
    } finally {
      setSyncing(false);
    }
  };

  const upcoming = deadlines.filter((d) => d.status === "upcoming" || d.status === "urgent");
  const missed = deadlines.filter((d) => d.status === "missed");
  const hearings = deadlines.filter((d) => d.deadline_type === "hearing");
  const limitations = deadlines.filter((d) => d.deadline_type === "limitation");

  return (
    <>
      <AppTopbar
        eyebrow="Practice"
        title="Hearings & deadlines"
        actions={
          <button
            onClick={handleSync}
            disabled={syncing}
            className="hairline inline-flex h-9 items-center gap-2 rounded-md bg-card px-3 text-sm disabled:opacity-50"
          >
            {syncing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Sync from eCourts
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
        <div className="flex items-baseline justify-between">
          <h2 className="font-serif text-xl">Upcoming hearings & deadlines</h2>
          {lastSync && <div className="text-xs text-muted-foreground">Last eCourts sync · {lastSync} IST</div>}
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
          <>
            {upcoming.length === 0 && missed.length === 0 ? (
              <div className="mt-16 text-center text-sm text-muted-foreground">
                <p>No upcoming hearings or deadlines found.</p>
                <p className="mt-2">Add cases and hearings to track them here, or sync from eCourts.</p>
              </div>
            ) : (
              <div className="mt-8 grid gap-6 lg:grid-cols-2">
                {/* Upcoming hearings */}
                {hearings.length > 0 && (
                  <div className="hairline rounded-xl bg-card p-6">
                    <h3 className="font-serif text-lg">Hearings</h3>
                    <ul className="mt-4 divide-y divide-border">
                      {hearings.map((d) => (
                        <li key={d.id} className="flex items-start gap-4 py-4">
                          <div className="w-24 shrink-0 font-mono text-sm text-muted-foreground">{d.due_date}</div>
                          <div className="flex-1">
                            <div className="text-sm font-medium">{d.matter_title}</div>
                            <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                              <MapPin className="h-3 w-3" /> {d.court}
                            </div>
                            {d.case_number && <div className="mt-1 font-mono text-[11px] text-muted-foreground">{d.case_number}</div>}
                          </div>
                          <StatusBadge status={d.status} />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Limitation deadlines */}
                {limitations.length > 0 && (
                  <div className="hairline rounded-xl bg-card p-6">
                    <h3 className="font-serif text-lg">Limitation & filing deadlines</h3>
                    <ul className="mt-4 space-y-3">
                      {limitations.map((d) => (
                        <li key={d.id} className={`flex items-start gap-3 rounded-md p-3 ${d.status === "urgent" ? "bg-destructive/10" : "bg-sand/40"}`}>
                          <StatusBadge status={d.status} />
                          <div className="flex-1 text-sm">
                            <div className="font-medium">{d.matter_title}</div>
                            <div className="text-xs text-muted-foreground">{d.due_date} · {d.court}</div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Missed */}
                {missed.length > 0 && (
                  <div className="hairline rounded-xl bg-card p-6 lg:col-span-2">
                    <h3 className="font-serif text-lg text-destructive">Missed deadlines</h3>
                    <ul className="mt-4 divide-y divide-border">
                      {missed.map((d) => (
                        <li key={d.id} className="flex items-center gap-4 py-3 text-sm">
                          <div className="w-24 font-mono text-muted-foreground">{d.due_date}</div>
                          <div className="flex-1">
                            <span className="font-medium">{d.matter_title}</span>
                            <span className="ml-2 text-xs text-muted-foreground">{d.court}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}

function StatusBadge({ status }: { status: Deadline["status"] }) {
  const styles = {
    upcoming: "bg-sand text-foreground",
    urgent: "bg-destructive/20 text-destructive",
    missed: "bg-muted text-muted-foreground",
  };
  return (
    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${styles[status]}`}>
      {status}
    </span>
  );
}
