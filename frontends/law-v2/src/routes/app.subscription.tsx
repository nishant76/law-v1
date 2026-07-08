import { createFileRoute } from "@tanstack/react-router";
import { AppTopbar } from "@/components/app/AppTopbar";
import { Check, Download } from "lucide-react";

export const Route = createFileRoute("/app/subscription")({
  head: () => ({ meta: [{ title: "Subscription — SuperAdvocate.Ai" }] }),
  component: Subscription,
});

function Subscription() {
  return (
    <>
      <AppTopbar eyebrow="Account" title="Subscription & billing" />
      <div className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="hairline rounded-xl bg-foreground p-8 text-background lg:col-span-2">
            <div className="text-[10px] uppercase tracking-[0.18em] text-background/60">Current plan</div>
            <div className="mt-3 flex items-baseline gap-3">
              <div className="font-serif text-4xl">Advocate</div>
              <span className="rounded-full bg-accent px-2 py-0.5 text-[11px] uppercase tracking-wider text-accent-foreground">Most popular</span>
            </div>
            <div className="mt-2 text-background/70">₹3,499 / month · renews on 02/07/2026</div>

            <div className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-lg bg-background/10 sm:grid-cols-4">
              {[
                ["Drafts", "47 / ∞"],
                ["PDFs read", "112 / ∞"],
                ["Active matters", "23 / 200"],
                ["Storage", "1.4 GB / 50 GB"],
              ].map(([k, v]) => (
                <div key={k} className="bg-foreground p-4">
                  <div className="text-[10px] uppercase tracking-[0.16em] text-background/60">{k}</div>
                  <div className="mt-1 font-mono text-sm">{v}</div>
                </div>
              ))}
            </div>

            <div className="mt-8 flex gap-3">
              <button className="inline-flex h-10 items-center rounded-md bg-background px-5 text-sm font-medium text-foreground">Upgrade to Chambers</button>
              <button className="inline-flex h-10 items-center rounded-md border border-background/30 px-5 text-sm">Manage payment</button>
            </div>
          </div>

          <div className="hairline rounded-xl bg-card p-6">
            <div className="eyebrow">Next invoice</div>
            <div className="mt-2 font-serif text-3xl">₹4,128</div>
            <div className="text-xs text-muted-foreground">Includes 18% GST · UPI · 02/07/2026</div>
            <ul className="mt-6 space-y-2 text-sm">
              <li className="flex justify-between"><span>Advocate plan</span><span>₹3,499</span></li>
              <li className="flex justify-between text-muted-foreground"><span>GST @ 18%</span><span>₹629</span></li>
            </ul>
          </div>
        </div>

        <h3 className="mt-12 font-serif text-xl">Available plans</h3>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          {[
            { n: "Junior", p: "₹1,499", f: ["50 drafts / mo", "25 active matters", "Email support"] },
            { n: "Advocate", p: "₹3,499", f: ["Unlimited drafts", "200 matters", "eCourts sync", "Priority WhatsApp"], current: true },
            { n: "Chambers", p: "₹8,999", f: ["8 user seats", "Shared workspaces", "Fee dashboard", "Dedicated CSM"] },
          ].map((p) => (
            <div key={p.n} className={`hairline flex flex-col rounded-xl p-6 ${p.current ? "bg-sand" : "bg-card"}`}>
              <div className="eyebrow">{p.n}</div>
              <div className="mt-3 font-serif text-3xl">{p.p}<span className="text-base text-muted-foreground">/mo</span></div>
              <ul className="mt-5 flex-1 space-y-2 text-sm">
                {p.f.map((x) => <li key={x} className="flex gap-2"><Check className="mt-0.5 h-4 w-4" /> {x}</li>)}
              </ul>
              <button disabled={p.current} className={`mt-6 h-10 rounded-md text-sm font-medium ${p.current ? "bg-foreground/10 text-foreground cursor-default" : "bg-foreground text-background hover:opacity-90"}`}>
                {p.current ? "Current plan" : "Switch"}
              </button>
            </div>
          ))}
        </div>

        <h3 className="mt-12 font-serif text-xl">Billing history</h3>
        <div className="hairline mt-4 overflow-hidden rounded-xl bg-card">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-sand/50 text-left text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              <tr>
                <th className="px-5 py-3 font-medium">Date</th>
                <th className="py-3 font-medium">Invoice</th>
                <th className="py-3 font-medium">Method</th>
                <th className="py-3 font-medium text-right">Amount</th>
                <th className="px-5 py-3 font-medium text-right">Receipt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[
                ["02/06/2026", "INV-2026-0612", "UPI · HDFC", "₹4,128"],
                ["02/05/2026", "INV-2026-0518", "UPI · HDFC", "₹4,128"],
                ["02/04/2026", "INV-2026-0421", "UPI · HDFC", "₹4,128"],
                ["02/03/2026", "INV-2026-0327", "Card · Visa", "₹4,128"],
              ].map(([d, inv, m, a]) => (
                <tr key={inv}>
                  <td className="px-5 py-4 font-mono text-xs">{d}</td>
                  <td className="py-4">{inv}</td>
                  <td className="py-4 text-muted-foreground">{m}</td>
                  <td className="py-4 text-right">{a}</td>
                  <td className="px-5 py-4 text-right">
                    <button className="inline-flex items-center gap-1 text-xs text-foreground underline-offset-4 hover:underline"><Download className="h-3 w-3" /> PDF</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
