import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, type ReactNode } from "react";
import { toast } from "sonner";
import {
  ArrowLeft, Pencil, Check, Scale, Gavel, CalendarClock, FileText, Bell,
  Plus, Trash2, Loader2, Phone,
} from "lucide-react";
import { AppTopbar } from "@/components/app/AppTopbar";
import {
  getMatter, updateMatter, addFeeInstallment, updateFeeInstallment, deleteFeeInstallment,
  type MatterDetailResponse,
} from "@/api/matters";
import { getCaseOrderPdf } from "@/api/ecourts";

export const Route = createFileRoute("/app/cases_/$id")({
  head: () => ({ meta: [{ title: "Matter — SuperAdvocate.Ai" }] }),
  component: MatterDetailPage,
});

function fmtMoney(n: number) {
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function Section({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="border-t border-border pt-4 pb-5 first:border-t-0">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-[10px] font-bold uppercase tracking-[1px] text-muted-foreground">{title}</div>
        {action}
      </div>
      {children}
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

function PartyChip({ role, name }: { role: "client" | "opponent" | "counsel"; name: string }) {
  const styles = {
    client: "bg-blue-50 text-blue-700 border-blue-200",
    opponent: "bg-red-50 text-red-600 border-red-200",
    counsel: "bg-muted text-muted-foreground border-border",
  }[role];
  const label = { client: "Client", opponent: "Opponent", counsel: "Advocate" }[role];
  return (
    <div className={`inline-flex items-center gap-[7px] rounded-md border px-2.5 py-1.5 ${styles}`}>
      <span className="text-[9.5px] font-bold uppercase tracking-wide opacity-70">{label}</span>
      <span className="text-[12.5px] font-semibold">{name}</span>
    </div>
  );
}

function MatterDetailPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MatterDetailResponse | null>(null);

  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ case_name: "", court: "", client_name: "", client_phone: "" });

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
      setForm({
        case_name: res.data.matter.case_name,
        court: res.data.matter.court ?? "",
        client_name: res.data.matter.client_name ?? "",
        client_phone: res.data.matter.client_phone ?? "",
      });
    } catch {
      setError("Could not load this matter.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateMatter(id, form);
      await load();
      setEditing(false);
      toast.success("Matter updated.");
    } catch {
      toast.error("Could not save changes.");
    } finally {
      setSaving(false);
    }
  };

  const handleAddFee = async () => {
    const amount = parseFloat(feeForm.amount);
    if (!amount || amount <= 0) return;
    setSavingFee(true);
    try {
      await addFeeInstallment(id, {
        label: feeForm.label || undefined,
        amount,
        due_date: feeForm.due_date || undefined,
      });
      setFeeForm({ label: "", amount: "", due_date: "" });
      setAddingFee(false);
      await load();
    } catch {
      toast.error("Could not add installment.");
    } finally {
      setSavingFee(false);
    }
  };

  const togglePaid = async (feeId: string, isPaid: boolean) => {
    try {
      await updateFeeInstallment(id, feeId, {
        is_paid: !isPaid,
        paid_date: !isPaid ? new Date().toISOString().slice(0, 10) : undefined,
      });
      await load();
    } catch {
      toast.error("Could not update installment.");
    }
  };

  const removeFee = async (feeId: string) => {
    try {
      await deleteFeeInstallment(id, feeId);
      await load();
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

  return (
    <>
      <AppTopbar eyebrow="Practice" title="Matter" />
      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">

        {/* Dark hero */}
        <div className="rounded-xl bg-sidebar p-6">
          <div className="flex items-start justify-between">
            <button
              onClick={() => navigate({ to: "/app/cases" })}
              className="inline-flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </button>
            {editing ? (
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-md bg-amber-accent px-3 py-1.5 text-xs font-medium text-amber-accent-fg disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" /> {saving ? "Saving…" : "Save"}
              </button>
            ) : (
              <button
                onClick={() => setEditing(true)}
                className="inline-flex items-center gap-1.5 rounded-md bg-white/10 px-3 py-1.5 text-xs text-white/70 hover:bg-white/15"
              >
                <Pencil className="h-3.5 w-3.5" /> Edit
              </button>
            )}
          </div>

          {editing ? (
            <input
              value={form.case_name}
              onChange={(e) => setForm((f) => ({ ...f, case_name: e.target.value }))}
              className="mt-3 w-full border-b border-white/20 bg-transparent font-serif text-xl text-white focus:outline-none"
            />
          ) : (
            <h1 className="mt-3 font-serif text-xl text-white">{matter.case_name}</h1>
          )}

          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-white/50">
            <span className="rounded-full bg-white/10 px-2 py-0.5 font-medium">
              {matter.case_status ?? (matter.is_active ? "Active" : "Closed")}
            </span>
            {editing ? (
              <input
                value={form.court}
                onChange={(e) => setForm((f) => ({ ...f, court: e.target.value }))}
                placeholder="Court"
                className="border-b border-white/20 bg-transparent focus:outline-none"
              />
            ) : (
              matter.court && <span>{matter.court}</span>
            )}
            {matter.cnr_number && <span className="font-mono">{matter.cnr_number}</span>}
          </div>

          {/* Stats grid */}
          <div className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-lg bg-white/10 sm:grid-cols-4">
            <div className="bg-sidebar p-3">
              <div className="text-[10px] uppercase tracking-wide text-white/40">Client</div>
              {editing ? (
                <input
                  value={form.client_name}
                  onChange={(e) => setForm((f) => ({ ...f, client_name: e.target.value }))}
                  placeholder="Client name"
                  className="mt-1 w-full border-b border-white/20 bg-transparent text-sm text-white focus:outline-none"
                />
              ) : (
                <div className="mt-1 text-sm text-white">{matter.client_name ?? "—"}</div>
              )}
            </div>
            <div className="bg-sidebar p-3">
              <div className="text-[10px] uppercase tracking-wide text-white/40">Next Hearing</div>
              <div className="mt-1 font-mono text-sm text-white">{matter.next_hearing_date ?? "—"}</div>
            </div>
            <div className="bg-sidebar p-3">
              <div className="text-[10px] uppercase tracking-wide text-white/40">Total Fees</div>
              <div className="mt-1 text-sm text-white">{fmtMoney(fees.total)}</div>
            </div>
            <div className="bg-sidebar p-3">
              <div className="text-[10px] uppercase tracking-wide text-white/40">Balance Due</div>
              <div className={`mt-1 text-sm ${fees.due > 0 ? "text-red-400" : "text-green-400"}`}>
                {fmtMoney(fees.due)}
              </div>
            </div>
          </div>
        </div>

        {/* Sections */}
        <div className="mt-6 rounded-xl bg-card px-5 hairline">

          <Section title="Client">
            <div className="flex flex-wrap items-center gap-4">
              <div className="min-w-48">
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Name</div>
                <div className="mt-0.5 text-sm text-foreground">{matter.client_name ?? "—"}</div>
              </div>
              <div className="min-w-48">
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Phone</div>
                {editing ? (
                  <input
                    value={form.client_phone}
                    onChange={(e) => setForm((f) => ({ ...f, client_phone: e.target.value }))}
                    placeholder="98765 43210"
                    className="mt-0.5 w-full rounded-md border border-border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                  />
                ) : (
                  <div className="mt-0.5 flex items-center gap-1.5 text-sm text-foreground">
                    {matter.client_phone && <Phone className="h-3.5 w-3.5 text-muted-foreground" />}
                    {matter.client_phone ?? "—"}
                  </div>
                )}
              </div>
            </div>

            {/* The switch that actually gates client messages. Without it the
                backend flag stayed false forever, so a phone number could be
                entered but no client ever received a reminder. */}
            <div className="mt-4 flex items-start justify-between gap-4 border-t border-border pt-4">
              <div>
                <div className="text-sm text-foreground">WhatsApp reminders to client</div>
                <div className="mt-0.5 text-[11px] text-muted-foreground">
                  {matter.client_phone
                    ? "Sent 7 days and 1 day before each hearing."
                    : "Add the client's phone number first."}
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
                    toast.error("Could not update. Please try again.");
                  } finally {
                    setSavingWhatsapp(false);
                  }
                }}
                className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-40 ${
                  matter.whatsapp_reminders_enabled ? "bg-amber-accent" : "bg-border"
                }`}
              >
                <span
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                    matter.whatsapp_reminders_enabled ? "translate-x-[22px]" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>
          </Section>

          <Section
            title="Fees"
            action={
              <button
                onClick={() => setAddingFee((v) => !v)}
                className="inline-flex items-center gap-1 text-xs font-medium text-amber-accent hover:opacity-80"
              >
                <Plus className="h-3.5 w-3.5" /> Add installment
              </button>
            }
          >
            <div className="mb-3 inline-flex items-center divide-x divide-border rounded-md border border-border text-xs">
              <div className="px-3 py-1.5">Agreed <span className="font-semibold text-foreground">{fmtMoney(fees.total)}</span></div>
              <div className="px-3 py-1.5">Paid <span className="font-semibold text-green-600">{fmtMoney(fees.paid)}</span></div>
              <div className="px-3 py-1.5">Due <span className={`font-semibold ${fees.due > 0 ? "text-red-600" : "text-green-600"}`}>{fmtMoney(fees.due)}</span></div>
            </div>

            {addingFee && (
              <div className="mb-3 flex flex-wrap items-end gap-2 rounded-md border border-border bg-muted/20 p-3">
                <div>
                  <div className="text-[10px] uppercase text-muted-foreground">Label</div>
                  <input
                    value={feeForm.label}
                    onChange={(e) => setFeeForm((f) => ({ ...f, label: e.target.value }))}
                    placeholder="e.g. First installment"
                    className="mt-0.5 h-8 w-40 rounded-md border border-border bg-background px-2 text-xs focus:outline-none"
                  />
                </div>
                <div>
                  <div className="text-[10px] uppercase text-muted-foreground">Amount</div>
                  <input
                    value={feeForm.amount}
                    onChange={(e) => setFeeForm((f) => ({ ...f, amount: e.target.value }))}
                    placeholder="15000"
                    type="number"
                    className="mt-0.5 h-8 w-28 rounded-md border border-border bg-background px-2 text-xs focus:outline-none"
                  />
                </div>
                <div>
                  <div className="text-[10px] uppercase text-muted-foreground">Due date</div>
                  <input
                    value={feeForm.due_date}
                    onChange={(e) => setFeeForm((f) => ({ ...f, due_date: e.target.value }))}
                    type="date"
                    className="mt-0.5 h-8 w-36 rounded-md border border-border bg-background px-2 text-xs focus:outline-none"
                  />
                </div>
                <button
                  onClick={handleAddFee}
                  disabled={savingFee}
                  className="h-8 rounded-md bg-amber-accent px-3 text-xs font-medium text-amber-accent-fg disabled:opacity-50"
                >
                  {savingFee ? "Adding…" : "Add"}
                </button>
              </div>
            )}

            {fees.installments.length === 0 ? (
              <p className="text-xs text-muted-foreground">No installments added yet.</p>
            ) : (
              <ul className="divide-y divide-border rounded-md border border-border">
                {fees.installments.map((f) => (
                  <li key={f.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                    <div className="min-w-0 flex-1">
                      <span className="font-medium text-foreground">{f.label ?? "Installment"}</span>
                      <span className="ml-2 text-muted-foreground">{fmtMoney(f.amount)}</span>
                      {f.due_date && <span className="ml-2 text-xs text-muted-foreground">due {f.due_date}</span>}
                    </div>
                    <button
                      onClick={() => togglePaid(f.id, f.is_paid)}
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        f.is_paid ? "bg-green-50 text-green-700" : "bg-amber-accent-subtle text-amber-accent"
                      }`}
                    >
                      {f.is_paid ? `Paid ${f.paid_date ?? ""}` : "Mark paid"}
                    </button>
                    <button onClick={() => removeFee(f.id)} className="shrink-0 text-muted-foreground hover:text-red-600">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          {ec && (
            <>
              <Section title="eCourts Overview">
                <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
                  <Field label="Case type" value={[ec.case_type_raw, ec.case_type_sub].filter(Boolean).join(" — ") || ec.case_type} />
                  <Field label="Stage of case" value={ec.stage_of_case} />
                  <Field label="Purpose" value={ec.purpose} />
                  <Field label="Filing number" value={ec.filing_number} />
                  <Field label="Registration number" value={ec.registration_number} />
                  <Field label="District" value={[ec.district, ec.state].filter(Boolean).join(", ")} />
                </div>
              </Section>

              <Section title="Key Dates">
                <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
                  <Field label="Filing date" value={ec.filing_date} />
                  <Field label="Registration date" value={ec.registration_date} />
                  <Field label="First hearing" value={ec.first_hearing_date} />
                  <Field label="Last hearing" value={ec.last_hearing_date} />
                  <Field label="Next hearing" value={ec.next_hearing_date} />
                  <Field label="Decision date" value={ec.decision_date} />
                </div>
              </Section>

              {(ec.petitioners.length > 0 || ec.respondents.length > 0) && (
                <Section title="Parties">
                  <div className="flex flex-wrap gap-2">
                    {ec.petitioners.map((p) => <PartyChip key={p} role="client" name={p} />)}
                    {ec.respondents.map((r) => <PartyChip key={r} role="opponent" name={r} />)}
                    {ec.petitioner_advocates.map((a) => <PartyChip key={a} role="counsel" name={a} />)}
                    {ec.respondent_advocates.map((a) => <PartyChip key={a} role="counsel" name={a} />)}
                  </div>
                </Section>
              )}

              {ec.judges.length > 0 && (
                <Section title="Judges">
                  <div className="flex items-start gap-2 text-sm text-foreground">
                    <Gavel className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    {ec.judges.join(", ")}
                  </div>
                </Section>
              )}

              {ec.hearing_history.length > 0 && (
                <Section title={`Hearing History (${ec.hearing_history.length})`}>
                  <ul className="max-h-64 space-y-2.5 overflow-y-auto">
                    {ec.hearing_history.slice().reverse().map((h, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <CalendarClock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <div>
                          <span className="font-mono text-xs text-foreground">{h.business_on_date}</span>
                          {h.purpose && <span className="ml-2 text-foreground">{h.purpose}</span>}
                          {h.judge && <span className="ml-2 text-xs text-muted-foreground">· {h.judge}</span>}
                        </div>
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {(ec.orders.length > 0 || ec.judgment_orders.length > 0) && (
                <Section title={`Orders${ec.order_count ? ` (${ec.order_count})` : ""}`}>
                  <ul className="max-h-64 space-y-2 overflow-y-auto">
                    {[...ec.judgment_orders, ...ec.orders].map((o, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <div>
                          <span className="font-mono text-xs text-foreground">{o.date}</span>
                          {o.description && <span className="ml-2 text-foreground">{o.description}</span>}
                          {o.url && (
                            <button
                              onClick={() => openOrder(ec.cnr, o.url as string)}
                              disabled={openingOrder === o.url}
                              className="ml-2 text-xs font-medium text-amber-accent hover:opacity-80 disabled:opacity-50"
                            >
                              {openingOrder === o.url ? "Opening…" : "View →"}
                            </button>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                  {orderError && <p className="mt-2 text-xs text-red-600">{orderError}</p>}
                  {!ec.has_order_documents && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      No digitised order text is available from eCourts for this case yet — dates and descriptions only.
                    </p>
                  )}
                </Section>
              )}

              {ec.processes.length > 0 && (
                <Section title="Processes & Notices">
                  <ul className="space-y-2">
                    {ec.processes.map((p, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
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
            <Section title="eCourts">
              <p className="text-xs text-muted-foreground">{data.ecourts_error}</p>
            </Section>
          )}
        </div>
      </div>
    </>
  );
}
