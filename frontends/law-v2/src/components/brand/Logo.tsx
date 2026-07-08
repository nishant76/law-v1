import { Link } from "@tanstack/react-router";

export function Logo({ className = "", to = "/" }: { className?: string; to?: string }) {
  return (
    <Link to={to} className={`inline-flex items-baseline gap-0 font-serif text-foreground ${className}`}>
      <span className="text-[1.05em] font-bold tracking-tight">Super</span>
      <span className="text-[1.05em] font-normal tracking-tight">Advocate</span>
      <span className="ml-1 text-[0.7em] font-normal text-muted-foreground">.Ai</span>
    </Link>
  );
}
