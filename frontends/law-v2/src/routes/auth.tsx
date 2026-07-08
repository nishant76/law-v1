import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Logo } from "@/components/brand/Logo";
import { z } from "zod";
import { useState } from "react";
import { login } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";

const search = z.object({
  mode: z.enum(["login", "signup"]).catch("login"),
});

export const Route = createFileRoute("/auth")({
  validateSearch: search,
  head: () => ({
    meta: [
      { title: "Sign in — SuperAdvocate.Ai" },
      { name: "description", content: "Sign in or start a free trial of SuperAdvocate.Ai." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const { mode } = Route.useSearch();
  const isSignup = mode === "signup";
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await login(email, password);
      const { access_token, user } = res.data.data;
      setAuth(user, access_token);
      navigate({ to: "/app" });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: { message?: string } } } })
          ?.response?.data?.error?.message ?? "Invalid email or password.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_1.05fr]">
      {/* Left visual */}
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-foreground p-12 text-background lg:flex">
        <Logo to="/" className="[&_*]:!text-background" />
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-amber-accent">From a Senior Advocate</div>
          <blockquote className="mt-4 font-serif text-3xl leading-snug">
            "SuperAdvocate.Ai has the rare quality of being quiet — it gets out of the way, and
            simply makes the work better."
          </blockquote>
          <div className="mt-6 text-sm text-background/60">— Sr. Adv. Kavita Menon, Supreme Court of India</div>
        </div>
        <div className="pointer-events-none absolute inset-0 opacity-[0.06]" style={{
          backgroundImage: "linear-gradient(var(--color-background) 1px, transparent 1px), linear-gradient(90deg, var(--color-background) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }} />
      </aside>

      {/* Form */}
      <main className="flex flex-col bg-paper p-6 sm:p-12">
        <div className="lg:hidden">
          <Logo />
        </div>
        <div className="flex flex-1 items-center">
          <div className="mx-auto w-full max-w-md">
            <div className="eyebrow">{isSignup ? "Create your chamber" : "Welcome back"}</div>
            <h1 className="serif-display mt-3 text-4xl text-foreground">
              {isSignup ? "Start your 14-day free trial." : "Sign in to continue."}
            </h1>
            <p className="mt-3 text-sm text-muted-foreground">
              {isSignup
                ? "No credit card required. Cancel anytime."
                : "Use the email associated with your practice."}
            </p>

            <form className="mt-10 space-y-5" onSubmit={handleLogin}>
              {isSignup && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Full name" placeholder="Ananya Rao" />
                  <Field label="Bar Council No." placeholder="KAR/2847/2018" />
                </div>
              )}
              <div>
                <label className="eyebrow mb-2 block">Email</label>
                <input
                  type="email"
                  placeholder="you@chambers.in"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="hairline h-11 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
                />
              </div>
              <div>
                <label className="eyebrow mb-2 block">Password</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="hairline h-11 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
                />
              </div>
              {isSignup && (
                <Field label="Mobile (for WhatsApp)" placeholder="+91 98000 00000" />
              )}

              {error && (
                <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="inline-flex h-11 w-full items-center justify-center rounded-md bg-amber-accent text-sm font-medium text-amber-accent-fg hover:opacity-90 disabled:opacity-50"
              >
                {loading ? "Signing in…" : isSignup ? "Create account" : "Sign in"}
              </button>

              <div className="relative py-2 text-center text-xs text-muted-foreground">
                <span className="relative z-10 bg-paper px-3">or continue with</span>
                <span className="absolute left-0 top-1/2 h-px w-full -translate-y-1/2 bg-border" />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <button type="button" className="hairline h-11 rounded-md bg-card text-sm">Google</button>
                <button type="button" className="hairline h-11 rounded-md bg-card text-sm">Mobile OTP</button>
              </div>
            </form>

            <div className="mt-8 flex items-center justify-between text-sm">
              <Link
                to="/auth"
                search={{ mode: isSignup ? "login" : "signup" }}
                className="text-foreground underline-offset-4 hover:underline"
              >
                {isSignup ? "I already have an account" : "Create an account"}
              </Link>
              {!isSignup && (
                <a href="#" className="text-muted-foreground hover:text-foreground">Forgot password?</a>
              )}
            </div>

            <div className="mt-12 text-xs text-muted-foreground">
              By continuing you agree to our Terms and Privacy Policy. Your matters stay in India.
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function Field({ label, type = "text", placeholder }: { label: string; type?: string; placeholder?: string }) {
  return (
    <div>
      <label className="eyebrow mb-2 block">{label}</label>
      <input
        type={type}
        placeholder={placeholder}
        className="hairline h-11 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
      />
    </div>
  );
}
