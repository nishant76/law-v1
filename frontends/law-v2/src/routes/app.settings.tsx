import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";

export const Route = createFileRoute("/app/settings")({
  head: () => ({ meta: [{ title: "Settings — SuperAdvocate.Ai" }] }),
  component: Settings,
});

function Settings() {
  return (
    <>
      <AppTopbar eyebrow="Account" title="Settings" />
      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
        <div className="mx-auto grid max-w-4xl gap-6">
          <Section title="Chamber profile">
            <Row label="Name" value="Adv. Ananya Rao" />
            <Row label="Bar Council No." value="KAR/2847/2018" />
            <Row label="Practising court" value="HC Karnataka, Bengaluru" />
            <Row label="Mobile" value="+91 98000 12345" />
            <Row label="Email" value="ananya@chambers.in" />
          </Section>

          <Section title="Preferences">
            <Row label="Currency" value="Indian Rupee (₹) · lakhs & crores" />
            <Row label="Date format" value="DD/MM/YYYY" />
            <Row label="Default language" value="English (with Hindi support)" />
            <Row label="Time zone" value="Asia/Kolkata (IST)" />
          </Section>

          <Section title="WhatsApp reminders">
            <Row label="Sender number" value="+91 80 4718 2200 (SuperAdvocate)" />
            <Row label="Reminder window" value="18 hours before hearing" />
            <Row label="Fee reminders" value="On · 3 days before due date" />
          </Section>

          <Section title="Data & privacy">
            <Row label="Region" value="ap-south-1 (Mumbai, India)" />
            <Row label="Two-factor auth" value="Enabled (TOTP)" />
            <Row label="Export data" value="Download a complete archive" action />
            <Row label="Delete account" value="Permanently remove your chamber" action danger />
          </Section>
        </div>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="hairline rounded-xl bg-card">
      <header className="border-b border-border px-6 py-4">
        <h2 className="font-serif text-lg">{title}</h2>
      </header>
      <div className="divide-y divide-border">{children}</div>
    </section>
  );
}

function Row({ label, value, action, danger }: { label: string; value: string; action?: boolean; danger?: boolean }) {
  return (
    <div className="flex items-center justify-between px-6 py-4">
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className={`mt-0.5 text-xs ${danger ? "text-destructive" : "text-muted-foreground"}`}>{value}</div>
      </div>
      <button className={`text-sm ${danger ? "text-destructive hover:underline" : action ? "text-foreground hover:underline" : "text-muted-foreground hover:text-foreground"} underline-offset-4`}>
        {action ? "Manage" : "Edit"}
      </button>
    </div>
  );
}
