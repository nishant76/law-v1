import { Search } from "lucide-react";
import type { ReactNode } from "react";
import { NotificationBell } from "./NotificationBell";

export function AppTopbar({
  title,
  eyebrow,
  actions,
}: {
  title: string;
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="border-b border-border bg-background">
      <div className="flex h-16 items-center gap-4 px-6 lg:px-10">
        <div className="min-w-0">
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h1 className="font-serif text-lg leading-tight tracking-tight text-foreground">{title}</h1>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative hidden md:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              placeholder="Search cases, drafts, citations…"
              className="hairline h-9 w-72 rounded-md bg-card pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
            />
          </div>
          <NotificationBell />
          {actions}
        </div>
      </div>
    </header>
  );
}
