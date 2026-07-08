import { Link } from "@tanstack/react-router";
import { Logo } from "@/components/brand/Logo";
import { Menu, X } from "lucide-react";
import { useState } from "react";

const NAV = [
  { to: "/features", label: "Features" },
  { to: "/pricing", label: "Pricing" },
  { to: "/contact", label: "Contact" },
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Logo />
        <nav className="hidden items-center gap-8 md:flex">
          {NAV.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              activeProps={{ className: "text-foreground" }}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          <Link to="/auth" search={{ mode: "login" }} className="text-sm text-foreground/80 hover:text-foreground">
            Sign in
          </Link>
          <Link
            to="/auth"
            search={{ mode: "signup" }}
            className="inline-flex h-9 items-center rounded-md bg-amber-accent px-4 text-sm font-medium text-amber-accent-fg transition-opacity hover:opacity-90"
          >
            Start free trial
          </Link>
        </div>
        <button className="md:hidden" onClick={() => setOpen((v) => !v)} aria-label="Menu">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {open && (
        <div className="border-t border-border bg-background md:hidden">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-6">
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} onClick={() => setOpen(false)} className="text-base">
                {n.label}
              </Link>
            ))}
            <Link to="/auth" search={{ mode: "login" }} onClick={() => setOpen(false)} className="text-base">
              Sign in
            </Link>
            <Link
              to="/auth"
              search={{ mode: "signup" }}
              onClick={() => setOpen(false)}
              className="inline-flex h-10 items-center justify-center rounded-md bg-amber-accent px-4 text-sm font-medium text-amber-accent-fg"
            >
              Start free trial
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
