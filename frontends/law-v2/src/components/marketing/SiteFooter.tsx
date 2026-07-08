import { Link } from "@tanstack/react-router";
import { Logo } from "@/components/brand/Logo";

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-sand">
      <div className="mx-auto grid max-w-7xl gap-12 px-6 py-16 md:grid-cols-4">
        <div className="md:col-span-2">
          <Logo />
          <p className="mt-4 max-w-sm text-sm text-muted-foreground">
            Purpose-built AI for India's solo practitioners and small law firms. Draft, research,
            and run your practice from one quiet workspace.
          </p>
          <p className="mt-6 text-xs text-muted-foreground">
            © {new Date().getFullYear()} SuperAdvocate.Ai · Bengaluru, India
          </p>
        </div>
        <div>
          <div className="eyebrow mb-4">Product</div>
          <ul className="space-y-2 text-sm">
            <li><Link to="/features" className="hover:text-foreground">Features</Link></li>
            <li><Link to="/pricing" className="hover:text-foreground">Pricing</Link></li>
            <li><Link to="/auth" search={{ mode: "signup" }} className="hover:text-foreground">Free trial</Link></li>
          </ul>
        </div>
        <div>
          <div className="eyebrow mb-4">Firm</div>
          <ul className="space-y-2 text-sm">
            <li><Link to="/contact" className="hover:text-foreground">Contact</Link></li>
            <li><a className="hover:text-foreground" href="mailto:hello@superadvocate.ai">hello@superadvocate.ai</a></li>
            <li><span className="text-muted-foreground">+91 80 4718 2200</span></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-3 px-6 py-5 text-xs text-muted-foreground md:flex-row">
          <span>Information here does not constitute legal advice.</span>
          <span>Privacy · Terms · DPA</span>
        </div>
      </div>
    </footer>
  );
}
