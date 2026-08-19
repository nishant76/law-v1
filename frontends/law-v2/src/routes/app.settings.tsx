import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Check, Loader2, Pencil, X } from "lucide-react";

import { AppTopbar } from "@/components/app/AppTopbar";
import { getProfile, updateProfile, type AdvocateProfile, type ProfileUpdate } from "@/api/settings";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/app/settings")({
  head: () => ({ meta: [{ title: "Settings — SuperAdvocate.Ai" }] }),
  component: Settings,
});

/**
 * Settings.
 *
 * Everything here reads and writes real columns. The previous version was
 * entirely hardcoded — it showed another advocate's name and bar council
 * number, invented a WhatsApp reminder window, and claimed two-factor auth was
 * enabled. A settings page that asserts protections which do not exist is worse
 * than no settings page, so nothing is displayed unless the server reports it.
 */
function Settings() {
  const [profile, setProfile] = useState<AdvocateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await getProfile();
      setProfile(res.data.data ?? null);
      setError(null);
    } catch {
      setError("Could not load your profile.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const save = async (body: ProfileUpdate) => {
    setSaving(true);
    try {
      const res = await updateProfile(body);
      setProfile(res.data.data ?? null);
      setEditing(null);
      toast.success("Saved.");
    } catch (e: unknown) {
      // Surface the server's own validation message (e.g. a bad phone number)
      // rather than a generic failure the lawyer cannot act on.
      const detail =
        (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail) && detail[0]?.msg
            ? String(detail[0].msg).replace(/^Value error, /, "")
            : "Could not save. Please try again.";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <>
        <AppTopbar eyebrow="Account" title="Settings" />
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </>
    );
  }

  if (error || !profile) {
    return (
      <>
        <AppTopbar eyebrow="Account" title="Settings" />
        <div className="flex-1 px-6 py-8 lg:px-10">
          <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4" /> {error ?? "No profile found."}
          </div>
        </div>
      </>
    );
  }

  const { user, firm, capabilities } = profile;

  const Row = ({
    label,
    value,
    field,
    placeholder,
    hint,
    editable = true,
  }: {
    label: string;
    value: string | null;
    field: keyof ProfileUpdate;
    placeholder?: string;
    hint?: string;
    editable?: boolean;
  }) => {
    const isEditing = editing === field;
    return (
      <div className="flex items-start justify-between gap-4 border-b border-border py-3.5 last:border-0">
        <div className="min-w-0">
          <div className="text-sm text-foreground">{label}</div>
          {hint && <div className="mt-0.5 text-[11px] text-muted-foreground">{hint}</div>}
        </div>
        <div className="flex min-w-0 items-center gap-2">
          {isEditing ? (
            <>
              <Input
                autoFocus
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") save({ [field]: draft } as ProfileUpdate);
                  if (e.key === "Escape") setEditing(null);
                }}
                placeholder={placeholder}
                className="h-8 w-56 text-sm"
              />
              <button
                onClick={() => save({ [field]: draft } as ProfileUpdate)}
                disabled={saving}
                aria-label="Save"
                className="rounded p-1 text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
              >
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
              </button>
              <button
                onClick={() => setEditing(null)}
                aria-label="Cancel"
                className="rounded p-1 text-muted-foreground hover:bg-muted"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </>
          ) : (
            <>
              <span className={`truncate text-sm ${value ? "text-foreground" : "text-muted-foreground"}`}>
                {value || "Not set"}
              </span>
              {editable && (
                <button
                  onClick={() => {
                    setEditing(field);
                    setDraft(value ?? "");
                  }}
                  aria-label={`Edit ${label}`}
                  className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <Pencil className="h-3 w-3" />
                </button>
              )}
            </>
          )}
        </div>
      </div>
    );
  };

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <section className="hairline rounded-xl bg-card p-5">
      <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {title}
      </h2>
      {children}
    </section>
  );

  return (
    <>
      <AppTopbar eyebrow="Account" title="Settings" />
      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
        <div className="mx-auto max-w-2xl space-y-6">

          <Section title="Advocate">
            <Row label="Name" value={user.name} field="name" />
            <Row label="Email" value={user.email} field="name" editable={false} hint="Sign-in address — contact support to change" />
            <Row label="Mobile" value={user.phone} field="phone" placeholder="98765 43210" />
            <Row
              label="Bar Council No."
              value={user.bar_council_number}
              field="bar_council_number"
              placeholder="P/1234/2020"
              hint="Appears on vakalatnamas and filings"
            />
          </Section>

          <Section title="Chamber">
            <Row label="Chamber name" value={firm.name} field="firm_name" />
            <Row label="City" value={firm.city} field="firm_city" placeholder="Panchkula" />
            <Row label="State" value={firm.state} field="firm_state" placeholder="Haryana" />
            <Row label="Plan" value={firm.plan} field="firm_name" editable={false} />
          </Section>

          <Section title="eCourts">
            <Row
              label="Advocate name on eCourts"
              value={user.ecourts_advocate_name}
              field="ecourts_advocate_name"
              hint="Must match your eCourts registration exactly, or the sync finds nothing"
            />
            <Row
              label="State code"
              value={user.ecourts_state_code}
              field="ecourts_state_code"
              placeholder="HR / PB / CH"
            />
            <div className="pt-3 text-[11px] text-muted-foreground">
              {capabilities.ecourts_configured
                ? "eCourts integration is configured on the server."
                : "eCourts is not configured on the server — case sync is unavailable."}
            </div>
          </Section>

          <Section title="Reminders">
            <div className="border-b border-border py-3.5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-sm">Daily cause list on WhatsApp</div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground">
                    Your own next-day list, sent each evening. Nothing is sent on days
                    with no listings.
                  </div>
                </div>
                <button
                  role="switch"
                  aria-checked={user.daily_cause_list_enabled}
                  onClick={() =>
                    save({ daily_cause_list_enabled: !user.daily_cause_list_enabled })
                  }
                  disabled={saving}
                  className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50 ${
                    user.daily_cause_list_enabled ? "bg-amber-accent" : "bg-border"
                  }`}
                >
                  <span
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                      user.daily_cause_list_enabled ? "translate-x-[22px]" : "translate-x-0.5"
                    }`}
                  />
                </button>
              </div>
            </div>

            <Row
              label="WhatsApp number"
              value={user.whatsapp_number}
              field="whatsapp_number"
              placeholder="98765 43210"
              hint="Falls back to your mobile if left blank"
            />

            <div className="space-y-1 pt-3 text-[11px] text-muted-foreground">
              <p>
                Hearing and deadline reminders are sent{" "}
                {capabilities.reminder_offsets_days.join(", ")} days before the date.
              </p>
              <p>Times shown in {capabilities.timezone}.</p>
              {!capabilities.email_configured && (
                <p className="text-amber-700 dark:text-amber-500">
                  Email delivery is not configured on the server — reminders will
                  appear in the app only.
                </p>
              )}
              {!capabilities.whatsapp_configured && (
                <p className="text-amber-700 dark:text-amber-500">
                  WhatsApp delivery is not configured on the server — client
                  reminders and the cause list cannot be sent.
                </p>
              )}
            </div>
          </Section>

          <p className="px-1 text-[11px] text-muted-foreground">
            Client WhatsApp reminders are switched on per matter, on the matter's page.
          </p>
        </div>
      </div>
    </>
  );
}
