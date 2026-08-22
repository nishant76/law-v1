import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Logo } from "@/components/brand/Logo";
import { z } from "zod";
import { useState } from "react";
import { login, register } from "@/api/auth";
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

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registered, setRegistered] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isSignup) {
        const name = fullName.trim() || email.split("@")[0];
        await register(name, email, password);
        // Registration doesn't return a token — auto-login after signup
        const loginRes = await login(email, password);
        const { access_token, user } = loginRes.data.data;
        setAuth(user, access_token);
        setRegistered(true);
        navigate({ to: "/app" });
      } else {
        const res = await login(email, password);
        const { access_token, user } = res.data.data;
        setAuth(user, access_token);
        navigate({ to: "/app" });
      }
    } catch (err: unknown) {
      const resp = err as { response?: { data?: { detail?: string; message?: string; error?: { message?: string } } } };
      const msg =
        resp?.response?.data?.detail ??
        resp?.response?.data?.message ??
        resp?.response?.data?.error?.message ??
        (isSignup ? "Registration failed. Please try again." : "Invalid email or password.");
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

            <form className="mt-10 space-y-5" onSubmit={handleSubmit}>
              {isSignup && (
                <div>
                  <label className="eyebrow mb-2 block">Full name</label>
                  <input
                    type="text"
                    placeholder="Ananya Rao"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    className="hairline h-11 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
                  />
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
                  minLength={8}
                  className="hairline h-11 w-full rounded-md bg-card px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
                />
                {isSignup && (
                  <p className="mt-1.5 text-[11px] text-muted-foreground">At least 8 characters.</p>
                )}
              </div>

              {error && (
                <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              )}

              {registered && (
                <p className="rounded-md bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700">
                  Account created. Signing you in…
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="inline-flex h-11 w-full items-center justify-center rounded-md bg-amber-accent text-sm font-medium text-amber-accent-fg hover:opacity-90 disabled:opacity-50"
              >
                {loading
                  ? (isSignup ? "Creating account…" : "Signing in…")
                  : (isSignup ? "Create account" : "Sign in")}
              </button>

              <div className="relative py-2 text-center text-xs text-muted-foreground">
                <span className="relative z-10 bg-paper px-3">or continue with</span>
                <span className="absolute left-0 top-1/2 h-px w-full -translate-y-1/2 bg-border" />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <button type="button" disabled className="hairline h-11 rounded-md bg-card text-sm text-muted-foreground">Google</button>
                <button type="button" disabled className="hairline h-11 rounded-md bg-card text-sm text-muted-foreground">Mobile OTP</button>
              </div>
              <p className="text-center text-[11px] text-muted-foreground">Google and OTP sign-in coming soon.</p>
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
                <span className="text-muted-foreground text-xs">
                  Forgot password? Contact support.
                </span>
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
