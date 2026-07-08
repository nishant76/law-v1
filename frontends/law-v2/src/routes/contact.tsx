import { createFileRoute } from "@tanstack/react-router";
import { SiteHeader } from "@/components/marketing/SiteHeader";
import { SiteFooter } from "@/components/marketing/SiteFooter";
import { Mail, Phone, MapPin } from "lucide-react";

export const Route = createFileRoute("/contact")({
  head: () => ({
    meta: [
      { title: "Contact — SuperAdvocate.Ai" },
      { name: "description", content: "Talk to the SuperAdvocate.Ai team. Bar Council partnerships, demos and product help." },
      { property: "og:title", content: "Contact — SuperAdvocate.Ai" },
      { property: "og:description", content: "Reach the SuperAdvocate.Ai team for demos, support and partnerships." },
    ],
  }),
  component: ContactPage,
});

function ContactPage() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <section className="border-b border-border bg-paper">
        <div className="mx-auto max-w-7xl px-6 py-20">
          <div className="eyebrow">Contact</div>
          <h1 className="serif-display mt-4 max-w-3xl text-5xl text-foreground sm:text-6xl">
            We answer like a chambers clerk — quickly, and to the point.
          </h1>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[1fr_1fr]">
        <div>
          <h2 className="font-serif text-2xl">Send a note</h2>
          <form className="mt-8 space-y-5">
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Your name" placeholder="Ananya Rao" />
              <Field label="Bar Council No." placeholder="KAR/2847/2018" />
            </div>
            <Field label="Email" type="email" placeholder="ananya@chambers.in" />
            <Field label="Mobile" placeholder="+91 98000 00000" />
            <div>
              <label className="eyebrow mb-2 block">Reason</label>
              <select className="hairline h-11 w-full rounded-md bg-card px-3 text-sm">
                <option>Request a demo</option>
                <option>Bar Council partnership</option>
                <option>Product question</option>
                <option>Press / Media</option>
              </select>
            </div>
            <div>
              <label className="eyebrow mb-2 block">Message</label>
              <textarea rows={5} className="hairline w-full rounded-md bg-card p-3 text-sm" placeholder="Tell us a little about your practice…" />
            </div>
            <button type="button" className="inline-flex h-11 items-center rounded-md bg-foreground px-6 text-sm font-medium text-background hover:opacity-90">
              Send message
            </button>
          </form>
        </div>

        <div className="space-y-8">
          <div className="hairline rounded-xl bg-sand p-8">
            <div className="eyebrow">Reach us</div>
            <div className="mt-6 space-y-5 text-sm">
              <Row icon={Mail} label="Email" value="hello@superadvocate.ai" />
              <Row icon={Phone} label="Phone" value="+91 80 4718 2200" />
              <Row icon={MapPin} label="Office" value={"3rd Floor, Prestige Atlanta\n80 Feet Road, Koramangala\nBengaluru 560 095"} />
            </div>
          </div>
          <div className="hairline rounded-xl bg-card p-8">
            <div className="eyebrow">Office hours</div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>Mon — Fri</div><div>10:00 — 19:00 IST</div>
              <div>Saturday</div><div>10:00 — 14:00 IST</div>
              <div>Sunday</div><div className="text-muted-foreground">Closed</div>
            </div>
            <p className="mt-6 text-xs text-muted-foreground">
              Urgent? WhatsApp customers can reach support 7 days a week from inside the app.
            </p>
          </div>
        </div>
      </section>
      <SiteFooter />
    </div>
  );
}

function Field({ label, type = "text", placeholder }: { label: string; type?: string; placeholder?: string }) {
  return (
    <div>
      <label className="eyebrow mb-2 block">{label}</label>
      <input type={type} placeholder={placeholder} className="hairline h-11 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30" />
    </div>
  );
}

function Row({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="flex gap-4">
      <Icon className="mt-0.5 h-4 w-4 text-foreground" />
      <div>
        <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
        <div className="mt-1 whitespace-pre-line text-foreground">{value}</div>
      </div>
    </div>
  );
}
