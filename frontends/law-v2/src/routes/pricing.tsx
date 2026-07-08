import { createFileRoute, Link } from "@tanstack/react-router";
import { SiteHeader } from "@/components/marketing/SiteHeader";
import { SiteFooter } from "@/components/marketing/SiteFooter";
import { Check } from "lucide-react";

export const Route = createFileRoute("/pricing")({
  head: () => ({
    meta: [
      { title: "Pricing — SuperAdvocate.Ai" },
      { name: "description", content: "Simple, transparent pricing in ₹ for solo lawyers and small firms. 14-day free trial on every plan." },
      { property: "og:title", content: "Pricing — SuperAdvocate.Ai" },
      { property: "og:description", content: "Simple, transparent pricing for solo lawyers and small firms in India." },
    ],
  }),
  component: PricingPage,
});

const PLANS = [
  {
    name: "Junior",
    tagline: "For lawyers just starting out.",
    price: "₹1,499",
    cadence: "per month",
    cta: "Start free trial",
    features: [
      "AI drafting — 50 drafts / month",
      "Document chat — 100 PDFs / month",
      "Judgment search (Supreme Court + 5 HCs)",
      "Up to 25 active matters",
      "WhatsApp reminders",
      "Email support",
    ],
  },
  {
    name: "Advocate",
    tagline: "Most popular with solo practitioners.",
    price: "₹3,499",
    cadence: "per month",
    cta: "Start free trial",
    highlight: true,
    features: [
      "Everything in Junior",
      "Unlimited drafts & PDFs",
      "All High Courts + tribunals",
      "Up to 200 active matters",
      "Notice reply assistant",
      "eCourts auto-sync",
      "Priority WhatsApp support",
    ],
  },
  {
    name: "Chambers",
    tagline: "For small firms up to 8 lawyers.",
    price: "₹8,999",
    cadence: "per month",
    cta: "Talk to sales",
    features: [
      "Everything in Advocate",
      "Up to 8 user seats",
      "Shared matter workspaces",
      "Fee & invoicing dashboard",
      "Role-based permissions",
      "Dedicated success manager",
      "Onboarding workshop",
    ],
  },
];

function PricingPage() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <section className="border-b border-border bg-paper">
        <div className="mx-auto max-w-5xl px-6 py-20 text-center">
          <div className="eyebrow">Pricing</div>
          <h1 className="serif-display mt-4 text-5xl text-foreground sm:text-6xl">
            One quiet workspace.<br />Three sensible plans.
          </h1>
          <p className="mt-6 text-muted-foreground">
            All plans include a 14-day free trial. Pay in ₹. GST invoice on every payment.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-6 lg:grid-cols-3">
          {PLANS.map((p) => (
            <div
              key={p.name}
              className={`flex flex-col rounded-xl border p-8 ${
                p.highlight
                  ? "border-foreground bg-foreground text-background shadow-2xl"
                  : "border-border bg-card text-foreground"
              }`}
            >
              <div className={`eyebrow ${p.highlight ? "!text-background/60" : ""}`}>{p.name}</div>
              <div className="mt-2 font-serif text-2xl leading-tight">{p.tagline}</div>
              <div className="mt-8 flex items-baseline gap-2">
                <span className="font-serif text-5xl">{p.price}</span>
                <span className={p.highlight ? "text-background/60" : "text-muted-foreground"}>{p.cadence}</span>
              </div>
              <Link
                to="/auth"
                search={{ mode: "signup" }}
                className={`mt-8 inline-flex h-11 items-center justify-center rounded-md text-sm font-medium ${
                  p.highlight
                    ? "bg-background text-foreground hover:bg-sand"
                    : "bg-foreground text-background hover:opacity-90"
                }`}
              >
                {p.cta}
              </Link>
              <ul className="mt-8 space-y-3 text-sm">
                {p.features.map((f) => (
                  <li key={f} className="flex gap-3">
                    <Check className={`mt-0.5 h-4 w-4 shrink-0 ${p.highlight ? "text-accent" : "text-foreground"}`} />
                    <span className={p.highlight ? "text-background/85" : "text-foreground/85"}>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mx-auto mt-16 max-w-3xl rounded-xl border border-border bg-sand p-8">
          <div className="eyebrow">For Bar Associations</div>
          <h3 className="mt-3 font-serif text-2xl">Discounted rates for state Bar Council members.</h3>
          <p className="mt-3 text-sm text-muted-foreground">
            We partner with several state Bar Councils to offer up to 40% off for members in their
            first three years of practice. Write to us at <a className="underline" href="mailto:bar@superadvocate.ai">bar@superadvocate.ai</a>.
          </p>
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto max-w-4xl px-6 py-20">
          <div className="eyebrow">FAQ</div>
          <h2 className="serif-display mt-3 text-3xl">Common questions</h2>
          <div className="mt-10 divide-y divide-border">
            {[
              ["Can I switch plans later?", "Yes. Upgrade or downgrade anytime from your subscription page. Prorated to the day."],
              ["Is my client data confidential?", "Absolutely. All matter data is stored in Indian data centres, encrypted at rest, and never used to train shared models."],
              ["Do you support physical court filing?", "Not yet — SuperAdvocate.Ai prepares court-ready documents. Filing is still done by you or your clerk."],
              ["What payment methods do you accept?", "UPI, all major Indian credit and debit cards, NEFT, and net banking via our PCI-compliant partner."],
            ].map(([q, a]) => (
              <div key={q} className="py-6">
                <div className="font-serif text-lg">{q}</div>
                <div className="mt-2 text-sm leading-relaxed text-muted-foreground">{a}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
      <SiteFooter />
    </div>
  );
}
