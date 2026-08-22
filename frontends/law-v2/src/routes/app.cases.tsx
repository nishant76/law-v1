import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { AppTopbar } from "@/components/app/AppTopbar";
import {
  Plus, Search, Scale, CalendarClock, RefreshCw, User2, X, Loader2,
  Check, IndianRupee, ChevronRight,
} from "lucide-react";
import { listMatters, createMatter, updateMatter, addFeeInstallment, type Matter } from "@/api/matters";

const inr = (n: number) =>
  "₹" + Math.round(n).toLocaleString("en-IN");

type SortKey = "hearing" | "name" | "due";

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

const STATUS_OPTIONS = [
  { value: "PENDING", label: "Pending" },
  { value: "DISPOSED", label: "Disposed" },
  { value: "STAYED", label: "Stayed" },
  { value: "SETTLED", label: "Settled" },
] as const;

export const Route = createFileRoute("/app/cases")({
  head: () => ({ meta: [{ title: "Cases — SuperAdvocate.Ai" }] }),
  component: Cases,
});

function statusColor(status: string | null, isActive: boolean) {
  if (!isActive || status?.toUpperCase() === "DISPOSED")
    return "bg-sand text-muted-foreground";
  if (status?.toUpperCase() === "PENDING")
    return "bg-amber-accent/15 text-amber-accent";
  if (status?.toUpperCase() === "STAYED")
    return "bg-blue-100 text-blue-700";
  if (status?.toUpperCase() === "SETTLED")
    return "bg-emerald-100 text-emerald-700";
  return "bg-foreground/10 text-foreground";
}

/* ── Inline editable cell ────────────────────────────────── */

function InlineText({
  value,
  placeholder,
  matterId,
  field,
  onSaved,
  icon,
}: {
  value: string | null;
  placeholder: string;
  matterId: string;
  field: string;
  onSaved: (updates: Partial<Matter>) => void;
  icon?: React.ReactNode;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? "");
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      setDraft(value ?? "");
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [editing, value]);

  const save = async () => {
    const trimmed = draft.trim();
    if (trimmed === (value ?? "")) { setEditing(false); return; }
    setSaving(true);
    try {
      const res = await updateMatter(matterId, { [field]: trimmed || undefined });
      onSaved(res.data.matter);
      toast.success("Updated.");
      setEditing(false);
    } catch {
      toast.error("Could not save.");
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <div className="flex items-center gap-1">
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={save}
          onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
          disabled={saving}
          className="h-7 w-full min-w-0 rounded border border-amber-accent/40 bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
        />
      </div>
    );
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className="group flex items-center gap-1.5 text-left"
      title={`Click to edit ${placeholder.toLowerCase()}`}
    >
      {icon}
      <span className={`${value ? "text-foreground" : "text-muted-foreground italic"} group-hover:text-amber-accent transition-colors`}>
        {value || placeholder}
      </span>
    </button>
  );
}

/* ── Inline date cell ────────────────────────────────────── */

function InlineDate({
  value,
  matterId,
  onSaved,
}: {
  value: string | null;
  matterId: string;
  onSaved: (updates: Partial<Matter>) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? "");
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      setDraft(value ?? "");
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [editing, value]);

  const save = async () => {
    if (draft === (value ?? "")) { setEditing(false); return; }
    setSaving(true);
    try {
      const res = await updateMatter(matterId, { next_hearing_date: draft || "" });
      onSaved(res.data.matter);
      toast.success("Updated.");
      setEditing(false);
    } catch {
      toast.error("Could not save.");
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="date"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
        disabled={saving}
        className="h-7 w-36 rounded border border-amber-accent/40 bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
      />
    );
  }

  const today = new Date().toISOString().slice(0, 10);
  const isOverdue = value && value < today;
  const isToday = value === today;

  return (
    <button
      onClick={() => setEditing(true)}
      className="group flex items-center gap-1.5 text-left"
      title="Click to edit hearing date"
    >
      <CalendarClock className="h-3.5 w-3.5 text-muted-foreground" />
      {value ? (
        <span className={`font-mono text-xs group-hover:text-amber-accent transition-colors ${isOverdue ? "text-red-600 font-semibold" : isToday ? "text-amber-accent font-semibold" : "text-foreground"}`}>
          {value}
        </span>
      ) : (
        <span className="text-xs text-muted-foreground italic group-hover:text-amber-accent transition-colors">Set date</span>
      )}
    </button>
  );
}

/* ── Inline status cell ──────────────────────────────────── */

function InlineStatus({
  value,
  isActive,
  matterId,
  onSaved,
}: {
  value: string | null;
  isActive: boolean;
  matterId: string;
  onSaved: (updates: Partial<Matter>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const pick = async (status: string) => {
    setSaving(true);
    try {
      const newActive = status !== "DISPOSED";
      const res = await updateMatter(matterId, { case_status: status, is_active: newActive });
      onSaved(res.data.matter);
      toast.success("Updated.");
    } catch {
      toast.error("Could not save.");
    } finally {
      setSaving(false);
      setOpen(false);
    }
  };

  const display = value ?? (isActive ? "Active" : "Closed");

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={saving}
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium transition-opacity hover:opacity-80 ${statusColor(value, isActive)}`}
      >
        {display}
      </button>
      {open && (
        <div className="absolute left-0 top-full z-20 mt-1 min-w-[120px] rounded-lg border border-border bg-background py-1 shadow-lg">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => pick(opt.value)}
              className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-sand/60 ${
                opt.value === (value?.toUpperCase() ?? (isActive ? "PENDING" : "DISPOSED")) ? "font-semibold text-foreground" : "text-muted-foreground"
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${statusColor(opt.value, opt.value !== "DISPOSED")}`} />
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Quick fee add popover ────────────────────────────────── */

function QuickFeeAdd({ matterId, agreedFee, currentFees, onSaved }: {
  matterId: string;
  agreedFee: number | null;
  currentFees: Matter["fees"];
  onSaved: (updates: Partial<Matter>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [totalDraft, setTotalDraft] = useState("");
  const [amount, setAmount] = useState("");
  const [label, setLabel] = useState("");
  const [saving, setSaving] = useState(false);
  const [savingTotal, setSavingTotal] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) setTotalDraft(agreedFee != null ? String(agreedFee) : "");
  }, [open, agreedFee]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const saveTotal = async () => {
    const n = parseFloat(totalDraft);
    if (isNaN(n) || n < 0) return;
    setSavingTotal(true);
    try {
      const newFee = n || null;
      const res = await updateMatter(matterId, { agreed_fee: newFee });
      const agreed = newFee ?? (currentFees?.agreed ?? 0);
      const paid = currentFees?.paid ?? 0;
      onSaved({ ...res.data.matter, fees: { agreed, paid, due: agreed - paid } });
      toast.success("Total fee updated.");
    } catch {
      toast.error("Could not save.");
    } finally {
      setSavingTotal(false);
    }
  };

  const saveInstallment = async () => {
    const n = parseFloat(amount);
    if (!n || n <= 0) return;
    setSaving(true);
    try {
      await addFeeInstallment(matterId, { amount: n, label: label.trim() || undefined });
      const paid = (currentFees?.paid ?? 0) + n;
      const agreed = currentFees?.agreed ?? 0;
      onSaved({ fees: { agreed: Math.max(agreed, paid), paid, due: Math.max(agreed, paid) - paid } });
      toast.success("Payment recorded.");
      setAmount(""); setLabel("");
    } catch {
      toast.error("Could not add fee.");
    } finally {
      setSaving(false);
    }
  };

  const hasFees = currentFees && currentFees.agreed > 0;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="group text-left"
        title="Click to manage fees"
      >
        {!hasFees ? (
          <span className="text-xs text-muted-foreground italic group-hover:text-amber-accent transition-colors">Set fee</span>
        ) : currentFees!.due > 0 ? (
          <div>
            <div className="font-medium text-foreground group-hover:text-amber-accent transition-colors">{inr(currentFees!.due)}</div>
            <div className="text-[11px] text-muted-foreground">of {inr(currentFees!.agreed)}</div>
          </div>
        ) : (
          <span className="inline-flex rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
            Paid
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-full z-20 mt-1 w-64 rounded-lg border border-border bg-background p-3 shadow-lg">
          {/* Total fee */}
          <div className="mb-3">
            <div className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Total fee</div>
            <div className="flex gap-2">
              <input
                value={totalDraft}
                onChange={(e) => setTotalDraft(e.target.value)}
                type="number"
                placeholder="e.g. 50000"
                autoFocus
                className="h-7 flex-1 rounded border border-border bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
                onKeyDown={(e) => { if (e.key === "Enter") saveTotal(); }}
              />
              <button
                onClick={saveTotal}
                disabled={savingTotal}
                className="h-7 rounded bg-amber-accent px-2 text-xs font-medium text-amber-accent-fg disabled:opacity-40"
              >
                {savingTotal ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
              </button>
            </div>
          </div>

          {/* Add installment (payment) */}
          <div className="border-t border-border pt-3">
            <div className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Record payment</div>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Label (optional)"
              className="mb-2 h-7 w-full rounded border border-border bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
            />
            <div className="flex gap-2">
              <input
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                type="number"
                placeholder="Amount"
                className="h-7 flex-1 rounded border border-border bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
                onKeyDown={(e) => { if (e.key === "Enter") saveInstallment(); }}
              />
              <button
                onClick={saveInstallment}
                disabled={saving || !amount}
                className="h-7 rounded bg-amber-accent px-2 text-xs font-medium text-amber-accent-fg disabled:opacity-40"
              >
                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
              </button>
            </div>
          </div>

          {hasFees && (
            <div className="mt-2 flex items-center justify-between border-t border-border pt-2 text-[11px] text-muted-foreground">
              <span>Agreed: {inr(currentFees!.agreed)}</span>
              <span>Paid: {inr(currentFees!.paid)}</span>
            </div>
          )}
          <Link
            to="/app/cases/$id"
            params={{ id: matterId }}
            className="mt-2 block text-center text-[11px] font-medium text-amber-accent hover:opacity-80"
          >
            Full fee details →
          </Link>
        </div>
      )}
    </div>
  );
}

/* ── Main cases page ─────────────────────────────────────── */

function Cases() {
  const [matters, setMatters] = useState<Matter[]>([]);
  const [filtered, setFiltered] = useState<Matter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"All" | "Active" | "Disposed">("All");
  const [sort, setSort] = useState<SortKey>("hearing");
  const [onlyListed, setOnlyListed] = useState(false);

  // New matter dialog
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCourt, setNewCourt] = useState("");
  const [newClient, setNewClient] = useState("");
  const [newType, setNewType] = useState("");
  const [newHearing, setNewHearing] = useState("");
  const [newFee, setNewFee] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    try {
      const fee = parseFloat(newFee);
      await createMatter({
        case_name: name,
        court: newCourt.trim() || undefined,
        client_name: newClient.trim() || undefined,
        matter_type: newType.trim() || undefined,
        next_hearing_date: newHearing || undefined,
        agreed_fee: !isNaN(fee) && fee > 0 ? fee : undefined,
      });
      toast.success("Matter added.");
      setShowNew(false);
      setNewName(""); setNewCourt(""); setNewClient(""); setNewType(""); setNewHearing(""); setNewFee("");
      load();
    } catch {
      toast.error("Could not create matter. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  const patchLocal = (matterId: string) => (updates: Partial<Matter>) => {
    setMatters((prev) => prev.map((m) => m.id === matterId ? { ...m, ...updates } : m));
  };

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
          <button
            onClick={() => setShowNew(true)}
            className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-4 text-sm font-medium text-amber-accent-fg hover:opacity-90"
          >
            <Plus className="h-4 w-4" /> New matter
          </button>
        }
      />

      {/* New matter dialog */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-background shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <h2 className="font-serif text-lg text-foreground">Add a matter</h2>
              <button onClick={() => setShowNew(false)} className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-4 px-6 py-5">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Case name *</label>
                <input
                  value={newName} onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
                  placeholder="e.g. Ram Kumar v. State of Haryana"
                  autoFocus
                  className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Court</label>
                <input
                  value={newCourt} onChange={(e) => setNewCourt(e.target.value)}
                  placeholder="e.g. District Court, Panchkula"
                  className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Client name</label>
                  <input
                    value={newClient} onChange={(e) => setNewClient(e.target.value)}
                    placeholder="e.g. Ram Kumar"
                    className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Matter type</label>
                  <select
                    value={newType} onChange={(e) => setNewType(e.target.value)}
                    className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                  >
                    <option value="">Select…</option>
                    <option value="criminal">Criminal</option>
                    <option value="civil">Civil</option>
                    <option value="cheque_bounce">Cheque Bounce (S.138)</option>
                    <option value="consumer">Consumer</option>
                    <option value="matrimonial">Matrimonial</option>
                    <option value="property">Property</option>
                    <option value="writ">Writ Petition</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Next hearing date</label>
                  <input
                    value={newHearing} onChange={(e) => setNewHearing(e.target.value)}
                    type="date"
                    className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Total fee</label>
                  <input
                    value={newFee} onChange={(e) => setNewFee(e.target.value)}
                    type="number"
                    placeholder="e.g. 50000"
                    className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
              <button onClick={() => setShowNew(false)} className="h-9 rounded-md px-4 text-sm text-muted-foreground hover:text-foreground">
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newName.trim() || creating}
                className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-5 text-sm font-medium text-amber-accent-fg hover:opacity-90 disabled:opacity-40"
              >
                {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Add matter
              </button>
            </div>
          </div>
        </div>
      )}

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

        {/* Loading */}
        {loading && filtered.length === 0 && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-amber-accent" />
          </div>
        )}

        {/* Cases table */}
        {filtered.length > 0 && (
          <div className="hairline overflow-hidden rounded-xl bg-card">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-border bg-sand/50 text-left text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                  <tr>
                    <th className="px-5 py-3 font-medium">Client</th>
                    <th className="py-3 font-medium">Case name · Court</th>
                    <th className="py-3 font-medium">Status</th>
                    <th className="py-3 font-medium">Next hearing</th>
                    <th className="py-3 font-medium">Fees</th>
                    <th className="px-4 py-3 font-medium"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filtered.map((m) => (
                    <tr key={m.id} className="group hover:bg-sand/40 transition-colors">
                      <td className="px-5 py-3.5 max-w-[150px]">
                        <InlineText
                          value={m.client_name}
                          placeholder="Add client"
                          matterId={m.id}
                          field="client_name"
                          onSaved={patchLocal(m.id)}
                          icon={<User2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                        />
                      </td>
                      <td className="py-3.5 max-w-xs">
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
                      <td className="py-3.5">
                        <InlineStatus
                          value={m.case_status}
                          isActive={m.is_active}
                          matterId={m.id}
                          onSaved={patchLocal(m.id)}
                        />
                      </td>
                      <td className="py-3.5">
                        <InlineDate
                          value={m.next_hearing_date}
                          matterId={m.id}
                          onSaved={patchLocal(m.id)}
                        />
                      </td>
                      <td className="py-3.5">
                        <QuickFeeAdd
                          matterId={m.id}
                          agreedFee={m.agreed_fee}
                          currentFees={m.fees}
                          onSaved={patchLocal(m.id)}
                        />
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <Link
                          to="/app/cases/$id"
                          params={{ id: m.id }}
                          className="inline-flex items-center gap-0.5 text-xs font-medium text-muted-foreground hover:text-amber-accent transition-colors opacity-0 group-hover:opacity-100"
                        >
                          Open <ChevronRight className="h-3.5 w-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="border-t border-border px-5 py-2.5 text-xs text-muted-foreground">
              {filtered.length} matter{filtered.length !== 1 ? "s" : ""}
              {filtered.length !== matters.length && ` (of ${matters.length} total)`}
              <span className="ml-3 text-muted-foreground/60">Click any cell to edit inline</span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
