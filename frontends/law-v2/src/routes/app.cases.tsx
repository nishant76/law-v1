import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { AppTopbar } from "@/components/app/AppTopbar";
import { Plus, Search, Scale, CalendarClock, RefreshCw } from "lucide-react";
import { listMatters, type Matter } from "@/api/matters";

export const Route = createFileRoute("/app/cases")({
  head: () => ({ meta: [{ title: "Cases — SuperAdvocate.Ai" }] }),
  component: Cases,
});

function statusColor(status: string | null, isActive: boolean) {
  if (!isActive || status?.toUpperCase() === "DISPOSED")
    return "bg-sand text-muted-foreground";
  if (status?.toUpperCase() === "PENDING")
    return "bg-amber-accent/15 text-amber-accent";
  return "bg-foreground/10 text-foreground";
}

function Cases() {
  const [matters, setMatters] = useState<Matter[]>([]);
  const [filtered, setFiltered] = useState<Matter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"All" | "Active" | "Disposed">("All");

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listMatters();
      setMatters(res.data.matters);
    } catch {
      setError("Could not load cases. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    let result = matters;
    if (filter === "Active") result = result.filter((m) => m.is_active && m.case_status?.toUpperCase() !== "DISPOSED");
    if (filter === "Disposed") result = result.filter((m) => !m.is_active || m.case_status?.toUpperCase() === "DISPOSED");
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (m) =>
          m.case_name.toLowerCase().includes(q) ||
          m.cnr_number?.toLowerCase().includes(q) ||
          m.court?.toLowerCase().includes(q) ||
          m.petitioner?.toLowerCase().includes(q) ||
          m.respondent?.toLowerCase().includes(q)
      );
    }
    setFiltered(result);
  }, [matters, filter, search]);

  return (
    <>
      <AppTopbar
        eyebrow="Practice"
        title="Cases"
        actions={
          <button className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-4 text-sm font-medium text-amber-accent-fg hover:opacity-90">
            <Plus className="h-4 w-4" /> New matter
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">

        {/* Search + filter bar */}
        <div className="hairline mb-6 flex flex-wrap items-center gap-3 rounded-lg bg-card p-3">
          <div className="relative flex-1 min-w-64">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by case name, CNR, court, party…"
              className="h-10 w-full bg-transparent pl-9 text-sm placeholder:text-muted-foreground focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-2 text-xs">
            {(["All", "Active", "Disposed"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`hairline rounded-full px-3 py-1 transition-colors ${
                  filter === f
                    ? "bg-amber-accent text-amber-accent-fg"
                    : "bg-background text-muted-foreground hover:text-foreground"
                }`}
              >
                {f}
              </button>
            ))}
            <button
              onClick={load}
              className="ml-1 rounded-md p-1.5 text-muted-foreground hover:bg-sand/60 hover:text-foreground"
              title="Refresh"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
        )}

        {/* Empty state */}
        {!loading && filtered.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center rounded-xl bg-card py-20 text-center hairline">
            <Scale className="h-10 w-10 text-border" />
            <p className="mt-3 font-serif text-lg text-foreground">
              {matters.length === 0 ? "No cases yet" : "No matches"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {matters.length === 0
                ? "Import from eCourts on the dashboard, or add a matter manually."
                : "Try a different search or filter."}
            </p>
          </div>
        )}

        {/* Cases table */}
        {filtered.length > 0 && (
          <div className="hairline overflow-hidden rounded-xl bg-card">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-sand/50 text-left text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                <tr>
                  <th className="px-5 py-3 font-medium">CNR / Number</th>
                  <th className="py-3 font-medium">Case name · Court</th>
                  <th className="py-3 font-medium">Status</th>
                  <th className="py-3 font-medium">Next hearing</th>
                  <th className="px-5 py-3 font-medium">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((m) => (
                  <tr key={m.id} className="hover:bg-sand/40">
                    <td className="px-5 py-4 font-mono text-xs text-muted-foreground">
                      {m.cnr_number ?? m.matter_number ?? "—"}
                    </td>
                    <td className="py-4 max-w-xs">
                      <div className="font-medium text-foreground truncate">{m.case_name}</div>
                      {m.court && (
                        <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground truncate">
                          <Scale className="h-3 w-3 shrink-0" />
                          {m.court}
                        </div>
                      )}
                    </td>
                    <td className="py-4">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${statusColor(m.case_status, m.is_active)}`}>
                        {m.case_status ?? (m.is_active ? "Active" : "Closed")}
                      </span>
                    </td>
                    <td className="py-4">
                      {m.next_hearing_date ? (
                        <div className="flex items-center gap-1.5 font-mono text-xs">
                          <CalendarClock className="h-3.5 w-3.5 text-muted-foreground" />
                          {m.next_hearing_date}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-xs text-muted-foreground">
                      {m.ecourts_tracked ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-600">
                          eCourts
                        </span>
                      ) : "Manual"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="border-t border-border px-5 py-2.5 text-xs text-muted-foreground">
              {filtered.length} matter{filtered.length !== 1 ? "s" : ""}
              {filtered.length !== matters.length && ` (of ${matters.length} total)`}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
