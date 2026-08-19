import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { AppTopbar } from "@/components/app/AppTopbar";
import { Plus, Search, Scale, CalendarClock, RefreshCw, Info, User2 } from "lucide-react";
import { listMatters, type Matter } from "@/api/matters";

/** Indian-format money, no decimals — fees are quoted in whole rupees. */
const inr = (n: number) =>
  "\u20b9" + Math.round(n).toLocaleString("en-IN");

type SortKey = "hearing" | "name" | "due";

/**
 * Sort comparators. "hearing" is the default because the daily question is
 * "what is coming up", not "what is alphabetical" — matters with no date sort
 * last rather than first, so an unscheduled matter never buries a listed one.
 */
const SORTS: Record<SortKey, { label: string; cmp: (a: Matter, b: Matter) => number }> = {
  hearing: {
    label: "Next hearing",
    cmp: (a, b) => {
      if (a.next_hearing_date === b.next_hearing_date) return 0;
      if (!a.next_hearing_date) return 1;
      if (!b.next_hearing_date) return -1;
      return a.next_hearing_date < b.next_hearing_date ? -1 : 1;
    },
  },
  name: { label: "Case name", cmp: (a, b) => a.case_name.localeCompare(b.case_name) },
  due: { label: "Balance due", cmp: (a, b) => (b.fees?.due ?? 0) - (a.fees?.due ?? 0) },
};

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
  const [sort, setSort] = useState<SortKey>("hearing");
  // Narrows to matters that actually have a date, for the "what's coming up" view.
  const [onlyListed, setOnlyListed] = useState(false);

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
    if (onlyListed) result = result.filter((m) => !!m.next_hearing_date);
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
          m.respondent?.toLowerCase().includes(q) ||
          m.client_name?.toLowerCase().includes(q)
      );
    }
    setFiltered([...result].sort(SORTS[sort].cmp));
  }, [matters, filter, search, sort, onlyListed]);

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
              placeholder="Search by client, case name, CNR, court, party…"
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
              onClick={() => setOnlyListed((v) => !v)}
              title="Show only matters with a hearing date"
              className={`hairline rounded-full px-3 py-1 transition-colors ${
                onlyListed
                  ? "bg-amber-accent text-amber-accent-fg"
                  : "bg-background text-muted-foreground hover:text-foreground"
              }`}
            >
              Listed only
            </button>

            <label className="ml-1 flex items-center gap-1.5 text-muted-foreground">
              <span className="sr-only">Sort by</span>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                className="hairline rounded-full bg-background px-2 py-1 text-xs text-foreground"
              >
                {(Object.keys(SORTS) as SortKey[]).map((k) => (
                  <option key={k} value={k}>Sort: {SORTS[k].label}</option>
                ))}
              </select>
            </label>

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
                  <th className="px-5 py-3 font-medium">Client</th>
                  <th className="py-3 font-medium">Case name · Court</th>
                  <th className="py-3 font-medium">Status</th>
                  <th className="py-3 font-medium">Next hearing</th>
                  <th className="py-3 font-medium">Balance due</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((m) => (
                  <tr key={m.id} className="hover:bg-sand/40">
                    <td className="px-5 py-4 max-w-[150px]">
                      {m.client_name ? (
                        <div className="flex items-center gap-1.5 truncate text-foreground">
                          <User2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          <span className="truncate">{m.client_name}</span>
                        </div>
                      ) : (
                        <span
                          className="text-xs text-muted-foreground"
                          title="No client recorded — add one to enable reminders"
                        >
                          Not set
                        </span>
                      )}
                    </td>
                    <td className="py-4 max-w-xs">
                      <div className="font-medium text-foreground truncate">{m.case_name}</div>
                      <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground truncate">
                        {m.court && (
                          <span className="inline-flex items-center gap-1 truncate">
                            <Scale className="h-3 w-3 shrink-0" />
                            {m.court}
                          </span>
                        )}
                      </div>
                      {(m.cnr_number || m.matter_number) && (
                        <div className="mt-0.5 font-mono text-[11px] text-muted-foreground/70 truncate">
                          {m.cnr_number ?? m.matter_number}
                          {m.ecourts_tracked && " · eCourts"}
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
                    <td className="py-4">
                      {/* No installments recorded is not the same as nothing owed —
                          say which, so an unbilled matter is visible rather than
                          reading as settled. */}
                      {!m.fees || m.fees.agreed === 0 ? (
                        <span className="text-xs text-muted-foreground">No fee set</span>
                      ) : m.fees.due > 0 ? (
                        <div>
                          <div className="font-medium text-foreground">{inr(m.fees.due)}</div>
                          <div className="text-[11px] text-muted-foreground">
                            of {inr(m.fees.agreed)}
                          </div>
                        </div>
                      ) : (
                        <span className="inline-flex rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                          Paid
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        to="/app/cases/$id"
                        params={{ id: m.id }}
                        className="inline-flex items-center gap-1 text-xs font-medium text-amber-accent hover:opacity-80"
                      >
                        <Info className="h-3.5 w-3.5" />
                        Details
                      </Link>
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
