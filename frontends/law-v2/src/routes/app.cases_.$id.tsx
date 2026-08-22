import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useRef, type ReactNode } from "react";
import { toast } from "sonner";
import {
  ArrowLeft, Pencil, Check, Scale, Gavel, CalendarClock, FileText, Bell,
  Plus, Trash2, Loader2, Phone, User2, Sparkles, AlertTriangle, Clock,
  IndianRupee, MessageSquare, X, ChevronDown, ChevronRight,
} from "lucide-react";
import { AppTopbar } from "@/components/app/AppTopbar";
import {
  getMatter, updateMatter, addFeeInstallment, updateFeeInstallment, deleteFeeInstallment,
  type MatterDetailResponse, type MatterDetail,
} from "@/api/matters";
import { getCaseOrderPdf } from "@/api/ecourts";

export const Route = createFileRoute("/app/cases_/$id")({
  head: () => ({ meta: [{ title: "Matter — SuperAdvocate.Ai" }] }),
  component: MatterDetailPage,
});

const inr = (n: number) =>
  `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const d = new Date(dateStr + "T00:00:00");
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return Math.ceil((d.getTime() - now.getTime()) / 86400000);
}

function daysSince(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const d = new Date(dateStr + "T00:00:00");
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return Math.floor((now.getTime() - d.getTime()) / 86400000);
}

/* ── Section wrapper ─────────────────────────────────────── */

function Section({ title, icon, children, action, defaultOpen = true }: {
  title: string; icon?: ReactNode; children: ReactNode; action?: ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-border first:border-t-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 py-4 text-left"
      >
        {icon}
        <span className="text-[11px] font-bold uppercase tracking-[1px] text-muted-foreground flex-1">{title}</span>
        {action && <span onClick={(e) => e.stopPropagation()}>{action}</span>}
        {open ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
      </button>
      {open && <div className="pb-5">{children}</div>}
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string | number | null }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-sm text-foreground">{value}</div>
    </div>
  );
}

function PartyChip({ role, name }: { role: "client" | "opponent" | "counsel" | "judge"; name: string }) {
  const styles = {
    client: "bg-blue-50 text-blue-700 border-blue-200",
    opponent: "bg-red-50 text-red-600 border-red-200",
    counsel: "bg-muted text-muted-foreground border-border",
    judge: "bg-purple-50 text-purple-700 border-purple-200",
  }[role];
  const label = { client: "Petitioner", opponent: "Respondent", counsel: "Advocate", judge: "Judge" }[role];
  return (
    <div className={`inline-flex items-center gap-[7px] rounded-md border px-2.5 py-1.5 ${styles}`}>
      <span className="text-[9.5px] font-bold uppercase tracking-wide opacity-70">{label}</span>
      <span className="text-[12.5px] font-semibold">{name}</span>
    </div>
  );
}

/* ── Editable field ──────────────────────────────────────── */

function EditableField({ label, value, field, matterId, onSaved, type = "text", placeholder }: {
  label: string; value: string | null; field: string; matterId: string;
  onSaved: (updates: Partial<MatterDetail>) => void; type?: "text" | "date" | "number"; placeholder?: string;
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
      let payload: Record<string, unknown>;
      if (type === "number") {
        const n = parseFloat(trimmed);
        payload = { [field]: trimmed ? (isNaN(n) ? null : n) : null };
      } else {
        payload = { [field]: trimmed || undefined };
      }
      const res = await updateMatter(matterId, payload as Parameters<typeof updateMatter>[1]);
      onSaved(res.data.matter);
      setEditing(false);
      toast.success("Updated.");
    } catch {
      toast.error("Could not save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      {editing ? (
        <div className="mt-0.5 flex items-center gap-1">
          <input
            ref={inputRef}
            type={type}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={save}
            onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
            disabled={saving}
            className="h-7 w-full rounded border border-amber-accent/40 bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
          />
        </div>
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="group mt-0.5 flex items-center gap-1 text-left"
        >
          <span className={`text-sm ${value ? "text-foreground" : "text-muted-foreground italic"} group-hover:text-amber-accent transition-colors`}>
            {value ? (type === "number" ? inr(parseFloat(value)) : value) : placeholder || "Not set"}
          </span>
          <Pencil className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
      )}
    </div>
  );
}

/* ── AI Case Overview ────────────────────────────────────── */

function CaseOverview({ matter, fees }: { matter: MatterDetail; fees: MatterDetailResponse["fees"] }) {
  const insights: { icon: ReactNode; text: string; color: string }[] = [];

  const hearingDays = daysUntil(matter.next_hearing_date);
  if (hearingDays !== null) {
    if (hearingDays < 0) {
      insights.push({ icon: <AlertTriangle className="h-3.5 w-3.5" />, text: `Hearing was ${Math.abs(hearingDays)} day${Math.abs(hearingDays) !== 1 ? "s" : ""} ago — update the next date`, color: "text-red-600" });
    } else if (hearingDays === 0) {
      insights.push({ icon: <CalendarClock className="h-3.5 w-3.5" />, text: "Hearing is today", color: "text-amber-accent" });
    } else if (hearingDays <= 3) {
      insights.push({ icon: <CalendarClock className="h-3.5 w-3.5" />, text: `Hearing in ${hearingDays} day${hearingDays !== 1 ? "s" : ""} — prepare filings`, color: "text-amber-accent" });
    } else if (hearingDays <= 7) {
      insights.push({ icon: <CalendarClock className="h-3.5 w-3.5" />, text: `Next hearing in ${hearingDays} days`, color: "text-foreground" });
    }
  } else if (!matter.next_hearing_date && matter.is_active) {
    insights.push({ icon: <CalendarClock className="h-3.5 w-3.5" />, text: "No hearing date set", color: "text-muted-foreground" });
  }

  if (fees.due > 0) {
    const pct = fees.total > 0 ? Math.round((fees.paid / fees.total) * 100) : 0;
    insights.push({ icon: <IndianRupee className="h-3.5 w-3.5" />, text: `${inr(fees.due)} outstanding (${pct}% collected)`, color: fees.due > fees.paid ? "text-red-600" : "text-amber-accent" });
  } else if (fees.total > 0) {
    insights.push({ icon: <IndianRupee className="h-3.5 w-3.5" />, text: "All fees collected", color: "text-emerald-600" });
  } else {
    insights.push({ icon: <IndianRupee className="h-3.5 w-3.5" />, text: "No fee schedule set", color: "text-muted-foreground" });
  }

  if (!matter.client_phone) {
    insights.push({ icon: <Phone className="h-3.5 w-3.5" />, text: "No phone — client won't get hearing reminders", color: "text-muted-foreground" });
  } else if (!matter.whatsapp_reminders_enabled) {
    insights.push({ icon: <MessageSquare className="h-3.5 w-3.5" />, text: "WhatsApp reminders are off", color: "text-muted-foreground" });
  }

  const filedDays = daysSince(matter.filing_date);
  if (filedDays !== null && filedDays > 0 && matter.is_active) {
    const months = Math.floor(filedDays / 30);
    if (months >= 1) {
      insights.push({ icon: <Clock className="h-3.5 w-3.5" />, text: `Case pending for ${months} month${months !== 1 ? "s" : ""}`, color: "text-muted-foreground" });
    }
  }

  if (insights.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-accent/20 bg-amber-accent/5 p-4">
      <div className="mb-3 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-[1px] text-amber-accent">
        <Sparkles className="h-3.5 w-3.5" /> Case overview
      </div>
      <ul className="space-y-2">
        {insights.map((ins, i) => (
          <li key={i} className={`flex items-start gap-2 text-sm ${ins.color}`}>
            <span className="mt-0.5 shrink-0">{ins.icon}</span>
            {ins.text}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────── */

function MatterDetailPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MatterDetailResponse | null>(null);

  const [savingWhatsapp, setSavingWhatsapp] = useState(false);
  const [addingFee, setAddingFee] = useState(false);
  const [feeForm, setFeeForm] = useState({ label: "", amount: "", due_date: "" });
  const [savingFee, setSavingFee] = useState(false);

  const [openingOrder, setOpeningOrder] = useState<string | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getMatter(id);
      setData(res.data);
    } catch {
      setError("Could not load this matter.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const patchLocal = (updates: Partial<MatterDetail>) => {
    setData((prev) => {
      if (!prev) return prev;
      const m = { ...prev.matter, ...updates };
      const newAgreed = updates.agreed_fee !== undefined ? updates.agreed_fee : prev.matter.agreed_fee;
      const total = newAgreed != null ? Number(newAgreed) : prev.fees.total;
      return {
        ...prev,
        matter: m,
        fees: { ...prev.fees, total, due: total - prev.fees.paid },
      };
    });
  };

  const handleAddFee = async () => {
    const amount = parseFloat(feeForm.amount);
    if (!amount || amount <= 0) return;
    setSavingFee(true);
    try {
      const res = await addFeeInstallment(id, {
        label: feeForm.label || undefined,
        amount,
        due_date: feeForm.due_date || undefined,
      });
      setData((prev) => {
        if (!prev) return prev;
        const inst = [...prev.fees.installments, res.data.fee];
        const paid = inst.filter((f) => f.is_paid).reduce((s, f) => s + f.amount, 0);
        const total = prev.matter.agreed_fee != null ? Number(prev.matter.agreed_fee) : inst.reduce((s, f) => s + f.amount, 0);
        return { ...prev, fees: { total, paid, due: total - paid, installments: inst } };
      });
      setFeeForm({ label: "", amount: "", due_date: "" });
      setAddingFee(false);
      toast.success("Installment added.");
    } catch {
      toast.error("Could not add installment.");
    } finally {
      setSavingFee(false);
    }
  };

  const togglePaid = async (feeId: string, isPaid: boolean) => {
    try {
      const res = await updateFeeInstallment(id, feeId, {
        is_paid: !isPaid,
        paid_date: !isPaid ? new Date().toISOString().slice(0, 10) : undefined,
      });
      setData((prev) => {
        if (!prev) return prev;
        const inst = prev.fees.installments.map((f) => f.id === feeId ? res.data.fee : f);
        const paid = inst.filter((f) => f.is_paid).reduce((s, f) => s + f.amount, 0);
        return { ...prev, fees: { ...prev.fees, paid, due: prev.fees.total - paid, installments: inst } };
      });
      toast.success(isPaid ? "Marked unpaid." : "Marked paid.");
    } catch {
      toast.error("Could not update installment.");
    }
  };

  const removeFee = async (feeId: string) => {
    try {
      await deleteFeeInstallment(id, feeId);
      setData((prev) => {
        if (!prev) return prev;
        const inst = prev.fees.installments.filter((f) => f.id !== feeId);
        const paid = inst.filter((f) => f.is_paid).reduce((s, f) => s + f.amount, 0);
        const total = prev.matter.agreed_fee != null ? Number(prev.matter.agreed_fee) : inst.reduce((s, f) => s + f.amount, 0);
        return { ...prev, fees: { total, paid, due: total - paid, installments: inst } };
      });
      toast.success("Installment removed.");
    } catch {
      toast.error("Could not remove installment.");
    }
  };

  const openOrder = async (cnr: string, filename: string) => {
    const win = window.open("", "_blank", "noopener,noreferrer");
    if (!win) {
      setOrderError("Your browser blocked the popup. Allow popups for this site to view orders.");
      return;
    }
    setOpeningOrder(filename);
    setOrderError(null);
    try {
      const res = await getCaseOrderPdf(cnr, filename);
      const url = URL.createObjectURL(res.data as Blob);
      win.location.href = url;
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (err: unknown) {
      win.close();
      const d = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setOrderError(d ?? "Could not open this order.");
    } finally {
      setOpeningOrder(null);
    }
  };

  if (loading) {
    return (
      <>
        <AppTopbar eyebrow="Practice" title="Matter" />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-amber-accent" />
        </div>
      </>
    );
  }

  if (error || !data) {
    return (
      <>
        <AppTopbar eyebrow="Practice" title="Matter" />
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
          <Scale className="h-8 w-8 text-border" />
          <p className="text-sm text-muted-foreground">{error ?? "Matter not found."}</p>
          <button onClick={() => navigate({ to: "/app/cases" })} className="text-xs font-medium text-amber-accent">
            ← Back to Cases
          </button>
        </div>
      </>
    );
  }

  const { matter, fees, ecourts_case: ec } = data;
  const statusDisplay = matter.case_status ?? (matter.is_active ? "Active" : "Closed");
  const statusStyle = !matter.is_active || matter.case_status?.toUpperCase() === "DISPOSED"
    ? "bg-sand text-muted-foreground"
    : matter.case_status?.toUpperCase() === "PENDING"
      ? "bg-amber-accent/15 text-amber-accent"
      : matter.case_status?.toUpperCase() === "STAYED"
        ? "bg-blue-100 text-blue-700"
        : "bg-emerald-100 text-emerald-700";

  const feePercent = fees.total > 0 ? Math.round((fees.paid / fees.total) * 100) : 0;

  return (
    <>
      <AppTopbar eyebrow="Practice" title="Matter" />
      <div className="flex-1 overflow-y-auto px-6 py-6 lg:px-10">

        {/* ── Breadcrumb ── */}
        <button
          onClick={() => navigate({ to: "/app/cases" })}
          className="mb-4 inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Cases
        </button>

        {/* ── Header ── */}
        <div className="mb-6 rounded-xl border border-border bg-card p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${statusStyle}`}>
                  {statusDisplay}
                </span>
                {matter.matter_type && (
                  <span className="rounded-full bg-sand px-2.5 py-0.5 text-[11px] font-medium text-muted-foreground capitalize">
                    {matter.matter_type.replace(/_/g, " ")}
                  </span>
                )}
                {matter.ecourts_tracked && (
                  <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-medium text-blue-600">
                    eCourts linked
                  </span>
                )}
              </div>
              <h1 className="mt-2 font-serif text-2xl text-foreground leading-tight">{matter.case_name}</h1>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                {matter.court && (
                  <span className="inline-flex items-center gap-1">
                    <Scale className="h-3.5 w-3.5" /> {matter.court}
                  </span>
                )}
                {matter.cnr_number && (
                  <span className="font-mono text-xs">{matter.cnr_number}</span>
                )}
                {matter.matter_number && !matter.cnr_number && (
                  <span className="font-mono text-xs">{matter.matter_number}</span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Link
                to="/app/drafting"
                search={{ court: matter.court ?? undefined, brief: matter.case_name, matter: id }}
                className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-3 text-xs font-medium text-foreground hover:bg-sand transition-colors"
              >
                <FileText className="h-3.5 w-3.5" /> Draft filing
              </Link>
            </div>
          </div>

          {/* Stats strip */}
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-background p-3 border border-border">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Client</div>
              <div className="mt-1 text-sm font-medium text-foreground truncate">
                {matter.client_name || <span className="text-muted-foreground italic font-normal">Not set</span>}
              </div>
            </div>
            <div className="rounded-lg bg-background p-3 border border-border">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Next hearing</div>
              <div className={`mt-1 font-mono text-sm font-medium ${
                (() => {
                  const d = daysUntil(matter.next_hearing_date);
                  if (d === null) return "text-muted-foreground";
                  if (d < 0) return "text-red-600";
                  if (d <= 3) return "text-amber-accent";
                  return "text-foreground";
                })()
              }`}>
                {matter.next_hearing_date ?? <span className="font-sans text-muted-foreground italic font-normal">Not set</span>}
              </div>
            </div>
            <div className="rounded-lg bg-background p-3 border border-border">
              <EditableField
                label="Total fees"
                value={matter.agreed_fee != null ? String(matter.agreed_fee) : null}
                field="agreed_fee"
                matterId={id}
                onSaved={patchLocal}
                placeholder="Set fee"
                type="number"
              />
            </div>
            <div className="rounded-lg bg-background p-3 border border-border">
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Balance due</div>
              <div className={`mt-1 text-sm font-medium ${fees.due > 0 ? "text-red-600" : fees.total > 0 ? "text-emerald-600" : "text-muted-foreground"}`}>
                {inr(fees.due)}
              </div>
              {fees.total > 0 && (
                <div className="mt-1.5 h-1.5 w-full rounded-full bg-border overflow-hidden">
                  <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${feePercent}%` }} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Two-column layout ── */}
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">

          {/* ── Main column ── */}
          <div className="space-y-0 rounded-xl bg-card px-5 hairline">

            {/* Case Details — editable fields */}
            <Section title="Case Details" icon={<Scale className="h-3.5 w-3.5 text-muted-foreground" />}>
              <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                <EditableField label="Case name" value={matter.case_name} field="case_name" matterId={id} onSaved={patchLocal} placeholder="Enter case name" />
                <EditableField label="Court" value={matter.court} field="court" matterId={id} onSaved={patchLocal} placeholder="e.g. District Court, Panchkula" />
                <EditableField label="Next hearing" value={matter.next_hearing_date} field="next_hearing_date" matterId={id} onSaved={patchLocal} type="date" placeholder="Set date" />
                <EditableField label="Client name" value={matter.client_name} field="client_name" matterId={id} onSaved={patchLocal} placeholder="Add client" />
                <EditableField label="Client phone" value={matter.client_phone} field="client_phone" matterId={id} onSaved={patchLocal} placeholder="98765 43210" />
                <Field label="Judge" value={matter.judge_name} />
                <Field label="Filing date" value={matter.filing_date} />
                <Field label="Limitation date" value={matter.limitation_date} />
                {matter.description && <div className="col-span-full"><Field label="Description" value={matter.description} /></div>}
              </div>
            </Section>

            {/* Fees */}
            <Section
              title={`Fees${fees.total > 0 ? ` — ${inr(fees.due)} due` : ""}`}
              icon={<IndianRupee className="h-3.5 w-3.5 text-muted-foreground" />}
              action={
                <button
                  onClick={() => setAddingFee((v) => !v)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-amber-accent hover:opacity-80"
                >
                  <Plus className="h-3.5 w-3.5" /> Add
                </button>
              }
            >
              {/* Fee summary strip */}
              {fees.total > 0 && (
                <div className="mb-4 flex items-center gap-4">
                  <div className="inline-flex items-center divide-x divide-border rounded-md border border-border text-xs">
                    <div className="px-3 py-1.5">Agreed <span className="font-semibold text-foreground">{inr(fees.total)}</span></div>
                    <div className="px-3 py-1.5">Paid <span className="font-semibold text-emerald-600">{inr(fees.paid)}</span></div>
                    <div className="px-3 py-1.5">Due <span className={`font-semibold ${fees.due > 0 ? "text-red-600" : "text-emerald-600"}`}>{inr(fees.due)}</span></div>
                  </div>
                  <div className="hidden sm:flex items-center gap-2 flex-1">
                    <div className="h-2 flex-1 rounded-full bg-border overflow-hidden">
                      <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${feePercent}%` }} />
                    </div>
                    <span className="text-[11px] text-muted-foreground">{feePercent}%</span>
                  </div>
                </div>
              )}

              {/* Add installment form */}
              {addingFee && (
                <div className="mb-4 rounded-lg border border-border bg-background p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-semibold text-foreground">New installment</span>
                    <button onClick={() => setAddingFee(false)} className="text-muted-foreground hover:text-foreground">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div className="flex flex-wrap items-end gap-3">
                    <div className="flex-1 min-w-[120px]">
                      <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Label</label>
                      <input
                        value={feeForm.label}
                        onChange={(e) => setFeeForm((f) => ({ ...f, label: e.target.value }))}
                        placeholder="e.g. First installment"
                        className="mt-0.5 h-8 w-full rounded-md border border-border bg-card px-2 text-xs focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
                      />
                    </div>
                    <div className="w-28">
                      <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Amount *</label>
                      <input
                        value={feeForm.amount}
                        onChange={(e) => setFeeForm((f) => ({ ...f, amount: e.target.value }))}
                        placeholder="15000"
                        type="number"
                        autoFocus
                        className="mt-0.5 h-8 w-full rounded-md border border-border bg-card px-2 text-xs focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
                      />
                    </div>
                    <div className="w-36">
                      <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Due date</label>
                      <input
                        value={feeForm.due_date}
                        onChange={(e) => setFeeForm((f) => ({ ...f, due_date: e.target.value }))}
                        type="date"
                        className="mt-0.5 h-8 w-full rounded-md border border-border bg-card px-2 text-xs focus:outline-none focus:ring-2 focus:ring-amber-accent/30"
                      />
                    </div>
                    <button
                      onClick={handleAddFee}
                      disabled={savingFee || !feeForm.amount}
                      className="h-8 rounded-md bg-amber-accent px-4 text-xs font-medium text-amber-accent-fg disabled:opacity-40"
                    >
                      {savingFee ? "Adding…" : "Add"}
                    </button>
                  </div>
                </div>
              )}

              {/* Installment list */}
              {fees.installments.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-6 text-center">
                  <IndianRupee className="h-6 w-6 text-border" />
                  <p className="text-xs text-muted-foreground">No installments recorded yet.</p>
                  <button
                    onClick={() => setAddingFee(true)}
                    className="text-xs font-medium text-amber-accent hover:opacity-80"
                  >
                    Add your first installment →
                  </button>
                </div>
              ) : (
                <div className="rounded-lg border border-border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-sand/50 text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2 font-medium">Installment</th>
                        <th className="px-3 py-2 font-medium">Amount</th>
                        <th className="px-3 py-2 font-medium">Due</th>
                        <th className="px-3 py-2 font-medium">Status</th>
                        <th className="px-3 py-2 font-medium"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {fees.installments.map((f) => (
                        <tr key={f.id} className="hover:bg-sand/30">
                          <td className="px-3 py-2.5 font-medium text-foreground">{f.label ?? "Installment"}</td>
                          <td className="px-3 py-2.5 text-foreground">{inr(f.amount)}</td>
                          <td className="px-3 py-2.5 text-muted-foreground font-mono text-xs">{f.due_date ?? "—"}</td>
                          <td className="px-3 py-2.5">
                            <button
                              onClick={() => togglePaid(f.id, f.is_paid)}
                              className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
                                f.is_paid ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100" : "bg-amber-accent/10 text-amber-accent hover:bg-amber-accent/20"
                              }`}
                            >
                              {f.is_paid ? `Paid${f.paid_date ? ` ${f.paid_date}` : ""}` : "Mark paid"}
                            </button>
                          </td>
                          <td className="px-3 py-2.5 text-right">
                            <button onClick={() => removeFee(f.id)} className="text-muted-foreground hover:text-red-600 transition-colors">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Section>

            {/* eCourts sections */}
            {ec && (
              <>
                <Section title="eCourts Overview" icon={<Scale className="h-3.5 w-3.5 text-muted-foreground" />}>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
                    <Field label="Case type" value={[ec.case_type_raw, ec.case_type_sub].filter(Boolean).join(" — ") || ec.case_type} />
                    <Field label="Stage of case" value={ec.stage_of_case} />
                    <Field label="Purpose" value={ec.purpose} />
                    <Field label="Filing number" value={ec.filing_number} />
                    <Field label="Registration number" value={ec.registration_number} />
                    <Field label="District" value={[ec.district, ec.state].filter(Boolean).join(", ")} />
                  </div>
                </Section>

                <Section title="Key Dates" icon={<CalendarClock className="h-3.5 w-3.5 text-muted-foreground" />}>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
                    <Field label="Filing date" value={ec.filing_date} />
                    <Field label="Registration date" value={ec.registration_date} />
                    <Field label="First hearing" value={ec.first_hearing_date} />
                    <Field label="Last hearing" value={ec.last_hearing_date} />
                    <Field label="Next hearing (eCourts)" value={ec.next_hearing_date} />
                    <Field label="Decision date" value={ec.decision_date} />
                  </div>
                </Section>

                {(ec.petitioners.length > 0 || ec.respondents.length > 0) && (
                  <Section title="Parties" icon={<User2 className="h-3.5 w-3.5 text-muted-foreground" />}>
                    <div className="flex flex-wrap gap-2">
                      {ec.petitioners.map((p) => <PartyChip key={`pet-${p}`} role="client" name={p} />)}
                      {ec.respondents.map((r) => <PartyChip key={`res-${r}`} role="opponent" name={r} />)}
                      {ec.petitioner_advocates.map((a) => <PartyChip key={`pa-${a}`} role="counsel" name={a} />)}
                      {ec.respondent_advocates.map((a) => <PartyChip key={`ra-${a}`} role="counsel" name={a} />)}
                    </div>
                  </Section>
                )}

                {ec.judges.length > 0 && (
                  <Section title="Bench" icon={<Gavel className="h-3.5 w-3.5 text-muted-foreground" />}>
                    <div className="flex flex-wrap gap-2">
                      {ec.judges.map((j) => <PartyChip key={j} role="judge" name={j} />)}
                    </div>
                  </Section>
                )}

                {ec.hearing_history.length > 0 && (
                  <Section
                    title={`Hearing History (${ec.hearing_history.length})`}
                    icon={<CalendarClock className="h-3.5 w-3.5 text-muted-foreground" />}
                    defaultOpen={false}
                  >
                    <div className="max-h-72 overflow-y-auto rounded-lg border border-border">
                      <table className="w-full text-sm">
                        <thead className="sticky top-0 bg-sand/80 text-left text-[10px] uppercase tracking-wide text-muted-foreground backdrop-blur">
                          <tr>
                            <th className="px-3 py-2 font-medium">Date</th>
                            <th className="px-3 py-2 font-medium">Purpose</th>
                            <th className="px-3 py-2 font-medium">Judge</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {ec.hearing_history.slice().reverse().map((h, i) => (
                            <tr key={i} className="hover:bg-sand/30">
                              <td className="px-3 py-2 font-mono text-xs text-foreground whitespace-nowrap">{h.business_on_date}</td>
                              <td className="px-3 py-2 text-foreground">{h.purpose ?? "—"}</td>
                              <td className="px-3 py-2 text-muted-foreground text-xs">{h.judge ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Section>
                )}

                {(ec.orders.length > 0 || ec.judgment_orders.length > 0) && (
                  <Section
                    title={`Orders${ec.order_count ? ` (${ec.order_count})` : ""}`}
                    icon={<FileText className="h-3.5 w-3.5 text-muted-foreground" />}
                    defaultOpen={false}
                  >
                    <ul className="max-h-64 space-y-2 overflow-y-auto">
                      {[...ec.judgment_orders, ...ec.orders].map((o, i) => (
                        <li key={i} className="flex items-start gap-2 rounded-md border border-border px-3 py-2 text-sm">
                          <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          <div className="flex-1">
                            <span className="font-mono text-xs text-foreground">{o.date}</span>
                            {o.description && <span className="ml-2 text-foreground">{o.description}</span>}
                          </div>
                          {o.url && (
                            <button
                              onClick={() => openOrder(ec.cnr, o.url as string)}
                              disabled={openingOrder === o.url}
                              className="shrink-0 text-xs font-medium text-amber-accent hover:opacity-80 disabled:opacity-50"
                            >
                              {openingOrder === o.url ? "Opening…" : "View →"}
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                    {orderError && <p className="mt-2 text-xs text-red-600">{orderError}</p>}
                    {!ec.has_order_documents && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        No digitised order text is available from eCourts for this case yet.
                      </p>
                    )}
                  </Section>
                )}

                {ec.processes.length > 0 && (
                  <Section title="Processes & Notices" icon={<Bell className="h-3.5 w-3.5 text-muted-foreground" />} defaultOpen={false}>
                    <ul className="space-y-2">
                      {ec.processes.map((p, i) => (
                        <li key={i} className="flex items-start gap-2 rounded-md border border-border px-3 py-2 text-sm">
                          <Bell className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                          <div>
                            <span className="font-mono text-xs text-foreground">{p.date}</span>
                            {p.title && <span className="ml-2 text-foreground">{p.title}</span>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </Section>
                )}
              </>
            )}

            {!ec && data.ecourts_error && (
              <Section title="eCourts" icon={<Scale className="h-3.5 w-3.5 text-muted-foreground" />}>
                <p className="text-xs text-muted-foreground">{data.ecourts_error}</p>
              </Section>
            )}
          </div>

          {/* ── Right sidebar ── */}
          <div className="space-y-5">

            {/* AI Overview */}
            <CaseOverview matter={matter} fees={fees} />

            {/* Client & reminders card */}
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="mb-4 text-[11px] font-bold uppercase tracking-[1px] text-muted-foreground flex items-center gap-1.5">
                <User2 className="h-3.5 w-3.5" /> Client & Reminders
              </div>

              <div className="space-y-3">
                <EditableField label="Client name" value={matter.client_name} field="client_name" matterId={id} onSaved={patchLocal} placeholder="Add client" />
                <EditableField label="Phone" value={matter.client_phone} field="client_phone" matterId={id} onSaved={patchLocal} placeholder="Add phone for reminders" />
              </div>

              <div className="mt-5 flex items-start justify-between gap-3 border-t border-border pt-4">
                <div>
                  <div className="text-sm text-foreground">WhatsApp reminders</div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground leading-relaxed">
                    {matter.client_phone
                      ? "7 days and 1 day before each hearing."
                      : "Add phone number first."}
                  </div>
                </div>
                <button
                  role="switch"
                  aria-checked={!!matter.whatsapp_reminders_enabled}
                  disabled={!matter.client_phone || savingWhatsapp}
                  onClick={async () => {
                    setSavingWhatsapp(true);
                    try {
                      const res = await updateMatter(matter.id, {
                        whatsapp_reminders_enabled: !matter.whatsapp_reminders_enabled,
                      });
                      setData((prev) => (prev ? { ...prev, matter: res.data.matter } : prev));
                      toast.success(
                        res.data.matter.whatsapp_reminders_enabled
                          ? "Client will receive WhatsApp reminders."
                          : "Client WhatsApp reminders turned off.",
                      );
                    } catch {
                      toast.error("Could not update.");
                    } finally {
                      setSavingWhatsapp(false);
                    }
                  }}
                  className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-40 ${
                    matter.whatsapp_reminders_enabled ? "bg-amber-accent" : "bg-border"
                  }`}
                >
                  <span
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${
                      matter.whatsapp_reminders_enabled ? "translate-x-[22px]" : "translate-x-0.5"
                    }`}
                  />
                </button>
              </div>
            </div>

            {/* Quick actions */}
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="mb-3 text-[11px] font-bold uppercase tracking-[1px] text-muted-foreground">Quick actions</div>
              <div className="space-y-2">
                <Link
                  to="/app/drafting"
                  search={{ court: matter.court ?? undefined, brief: matter.case_name, matter: id }}
                  className="flex items-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm text-foreground hover:bg-sand/60 transition-colors"
                >
                  <FileText className="h-4 w-4 text-amber-accent" /> Draft a filing for this matter
                </Link>
                <Link
                  to="/app/research"
                  search={{ q: matter.case_name, matter: id }}
                  className="flex items-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm text-foreground hover:bg-sand/60 transition-colors"
                >
                  <Sparkles className="h-4 w-4 text-amber-accent" /> Research judgments
                </Link>
                <Link
                  to="/app/hearings"
                  className="flex items-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm text-foreground hover:bg-sand/60 transition-colors"
                >
                  <CalendarClock className="h-4 w-4 text-amber-accent" /> View court diary
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
