/**
 * EcourtsOnboarding — first-login wizard that imports a lawyer's cases from
 * ecourtsindia.com so the dashboard is populated from day one.
 *
 * Step 1 · Type your name → search profiles
 * Step 2 · Pick your profile from the list
 * Step 3 · Review your cases → confirm import
 * Step 4 · Done — cases imported and hearing dates synced
 */
import { useState, useRef } from 'react'
import {
  searchLawyerProfiles,
  getLawyerCases,
  importCnrs,
  type LawyerProfile,
  type DiscoveredCase,
} from '@/api/ecourts'
import { useAuthStore } from '@/store/authStore'
import { Search, ChevronRight, Check, Loader2, X, Building2, Scale } from 'lucide-react'

type Step = 'search' | 'pick' | 'review' | 'done'

interface Props {
  onClose: () => void
  onImported: (count: number) => void
}

export function EcourtsOnboarding({ onClose, onImported }: Props) {
  const authUser = useAuthStore((s) => s.user)
  const [step, setStep] = useState<Step>('search')
  const [query, setQuery] = useState(authUser?.full_name ?? '')
  const [city, setCity] = useState('')
  const [searching, setSearching] = useState(false)
  const [profiles, setProfiles] = useState<LawyerProfile[]>([])
  const [selectedProfile, setSelectedProfile] = useState<LawyerProfile | null>(null)
  const [loadingCases, setLoadingCases] = useState(false)
  const [cases, setCases] = useState<DiscoveredCase[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<{ imported: number; refreshed: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showDisposed, setShowDisposed] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // ── Step 1: search ───────────────────────────────────────────────────────

  const handleSearch = async () => {
    const q = query.trim()
    if (!q || searching) return
    setSearching(true)
    setError(null)
    setProfiles([])
    try {
      const res = await searchLawyerProfiles(q)
      setProfiles(res.data.profiles)
      setStep('pick')
      if (res.data.profiles.length === 0) setError('No matching advocates found. Try a different spelling.')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg || 'Could not reach eCourtsIndia. Check the backend is running and try again.')
    } finally {
      setSearching(false)
    }
  }

  // ── Step 2: pick profile ─────────────────────────────────────────────────

  const handlePickProfile = async (profile: LawyerProfile) => {
    setSelectedProfile(profile)
    setLoadingCases(true)
    setError(null)
    setCases([])
    setStep('review')
    try {
      const res = await getLawyerCases(profile.slug, city.trim() || undefined)
      setCases(res.data.cases)
      // Pre-select only Pending cases — disposed cases are old and not useful
      setSelected(new Set(
        res.data.cases
          .filter(c => !c.status || c.status.toLowerCase() === 'pending')
          .map(c => c.cnr)
      ))
    } catch {
      setError('Could not fetch cases. Please try again.')
    } finally {
      setLoadingCases(false)
    }
  }

  // ── Step 3: import ───────────────────────────────────────────────────────

  const handleImport = async () => {
    if (importing || selected.size === 0) return
    setImporting(true)
    setError(null)
    try {
      const selectedCases = cases.filter((c) => selected.has(c.cnr))
      const res = await importCnrs(selectedCases)
      setImportResult({ imported: res.data.imported, refreshed: res.data.refreshed })
      setStep('done')
      onImported(res.data.imported)
    } catch {
      setError('Import failed. Please try again.')
    } finally {
      setImporting(false)
    }
  }

  const toggleAll = () => {
    const pending = cases.filter(c => !c.status || c.status.toLowerCase() === 'pending')
    if (selected.size === pending.length) setSelected(new Set())
    else setSelected(new Set(pending.map(c => c.cnr)))
  }

  const toggleOne = (cnr: string) => {
    const next = new Set(selected)
    next.has(cnr) ? next.delete(cnr) : next.add(cnr)
    setSelected(next)
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="relative flex w-full max-w-2xl flex-col rounded-xl bg-background shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <div className="eyebrow">eCourts · First setup</div>
            <h2 className="mt-0.5 font-serif text-lg">Import your cases</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1.5 text-muted-foreground hover:bg-sand/60">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-0 border-b border-border px-6 py-3 text-xs">
          {(['search', 'pick', 'review', 'done'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center gap-0">
              <div className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${step === s ? 'bg-amber-accent text-amber-accent-fg' : ['done', 'review', 'pick'].slice(0, ['search','pick','review','done'].indexOf(step)).includes(s) || s < step ? 'bg-foreground text-background' : 'bg-sand text-muted-foreground'}`}>
                {i + 1}
              </div>
              <span className={`mx-2 capitalize ${step === s ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                {s === 'search' ? 'Enter name' : s === 'pick' ? 'Pick profile' : s === 'review' ? 'Review cases' : 'Done'}
              </span>
              {i < 3 && <ChevronRight className="h-3 w-3 text-border mr-2" />}
            </div>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6" style={{ maxHeight: '60vh' }}>

          {/* Step 1: search */}
          {step === 'search' && (
            <div className="mx-auto max-w-md">
              <p className="text-sm text-muted-foreground">
                Enter your name as registered on eCourts. We'll find your pending cases and import them so your dashboard is ready from day one.
              </p>
              <div className="mt-6 space-y-2">
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                      ref={inputRef}
                      value={query}
                      onChange={e => setQuery(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleSearch()}
                      placeholder="Advocate name, e.g. Neera Rani"
                      className="hairline h-11 w-full rounded-md bg-card pl-9 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                      autoFocus
                    />
                  </div>
                  <div className="relative w-36">
                    <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                      value={city}
                      onChange={e => setCity(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleSearch()}
                      placeholder="City (optional)"
                      className="hairline h-11 w-full rounded-md bg-card pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                    />
                  </div>
                  <button
                    onClick={handleSearch}
                    disabled={!query.trim() || searching}
                    className="inline-flex h-11 items-center gap-2 rounded-md bg-amber-accent px-5 text-sm font-medium text-amber-accent-fg disabled:opacity-50"
                  >
                    {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
                  </button>
                </div>
              </div>
              {error && <p className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
            </div>
          )}

          {/* Step 2: pick profile */}
          {step === 'pick' && (
            <div>
              {(() => {
                const visible = profiles
                return (
                  <>
                    <p className="mb-4 text-sm text-muted-foreground">
                      {visible.length} advocate{visible.length !== 1 ? 's' : ''} matching <strong>"{query}"</strong>.
                      {city.trim() && <> After you pick your profile, we'll show only your <strong>{city.trim()}</strong> cases.</>}
                      {' '}<button className="text-amber-accent underline underline-offset-4 text-xs" onClick={() => setStep('search')}>Search again</button>
                    </p>
                    {visible.length === 0 && (
                      <div className="rounded-lg bg-sand/60 px-4 py-8 text-center text-sm text-muted-foreground">
                        No profiles found. <button className="text-amber-accent underline underline-offset-4" onClick={() => setStep('search')}>Try again</button>
                      </div>
                    )}
                    <div className="grid gap-2">
                      {visible.map(p => (
                  <button
                    key={p.slug}
                    onClick={() => handlePickProfile(p)}
                    className="hairline flex w-full items-center gap-4 rounded-lg bg-card p-4 text-left hover:bg-sand/60"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-accent/15 font-bold text-amber-accent text-sm">
                      {p.display_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm">{p.display_name}</div>
                      <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground truncate">
                        <Building2 className="h-3 w-3 shrink-0" />
                        {p.court}
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  </button>
                      ))}
                    </div>
                    {error && <p className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
                  </>
                )
              })()}
            </div>
          )}

          {/* Step 3: review cases */}
          {step === 'review' && (
            <div>
              {loadingCases ? (
                <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                  <Loader2 className="h-8 w-8 animate-spin" />
                  <p className="mt-4 text-sm">Fetching your cases from eCourtsIndia…</p>
                  <p className="mt-1 text-xs opacity-60">
                    {city.trim() ? `Filtering to ${city.trim()} courts — usually under 1 minute` : 'Scraping all pages — may take 1–3 minutes for lawyers with many cases'}
                  </p>
                </div>
              ) : (
                <>
                  {(() => {
                    const pending = cases.filter(c => !c.status || c.status.toLowerCase() === 'pending')
                    const disposed = cases.filter(c => c.status?.toLowerCase() === 'disposed')
                    const visible = showDisposed ? cases : pending
                    return (
                      <>
                        <div className="mb-4 flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium">
                              <span className="text-amber-accent">{pending.length} pending</span>
                              {disposed.length > 0 && (
                                <button
                                  onClick={() => setShowDisposed(v => !v)}
                                  className="ml-2 text-muted-foreground underline underline-offset-4 hover:text-foreground"
                                >
                                  {showDisposed ? `hide ${disposed.length} disposed` : `+ ${disposed.length} disposed`}
                                </button>
                              )}
                            </p>
                            <p className="text-xs text-muted-foreground">{selectedProfile?.display_name} · {selectedProfile?.court}</p>
                          </div>
                          <button onClick={toggleAll} className="text-xs text-amber-accent underline underline-offset-4">
                            {selected.size === pending.length ? 'Deselect all' : 'Select all pending'}
                          </button>
                        </div>

                        {pending.length === 0 && (
                          <div className="rounded-lg bg-sand/60 px-4 py-8 text-center text-sm text-muted-foreground">
                            No pending cases found. <button className="text-amber-accent underline underline-offset-4" onClick={() => setStep('pick')}>Try a different profile</button>
                          </div>
                        )}

                        <div className="grid gap-1.5">
                          {visible.map(c => {
                            const isDisposed = c.status?.toLowerCase() === 'disposed'
                            return (
                              <label key={c.cnr} className={`flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 transition-colors ${isDisposed ? 'border-border/50 bg-card opacity-40' : selected.has(c.cnr) ? 'border-amber-accent/40 bg-amber-accent/5' : 'border-border bg-card hover:bg-sand/40'}`}>
                                <div className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border ${selected.has(c.cnr) ? 'border-amber-accent bg-amber-accent' : 'border-border'}`}>
                                  {selected.has(c.cnr) && <Check className="h-2.5 w-2.5 text-amber-accent-fg" />}
                                </div>
                                <input type="checkbox" className="sr-only" checked={selected.has(c.cnr)} onChange={() => toggleOne(c.cnr)} />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="font-mono text-[11px] text-muted-foreground">{c.cnr}</span>
                                    {c.status && (
                                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${isDisposed ? 'bg-sand text-muted-foreground' : 'bg-amber-accent/15 text-amber-accent'}`}>
                                        {c.status}
                                      </span>
                                    )}
                                  </div>
                                  <div className="mt-0.5 text-sm font-medium leading-snug">{c.case_name}</div>
                                  {c.court && (
                                    <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                                      <Scale className="h-3 w-3 shrink-0" />
                                      {c.court}
                                    </div>
                                  )}
                                </div>
                              </label>
                            )
                          })}
                        </div>
                      </>
                    )
                  })()}

                  {error && <p className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
                </>
              )}
            </div>
          )}

          {/* Step 4: done */}
          {step === 'done' && importResult && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10">
                <Check className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="mt-4 font-serif text-xl">Cases imported</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                <strong>{importResult.imported}</strong> cases added to your dashboard.
                {importResult.refreshed > 0 && <> Hearing dates fetched for <strong>{importResult.refreshed}</strong> cases.</>}
              </p>
              <p className="mt-4 text-xs text-muted-foreground max-w-sm">
                SuperAdvocate will automatically refresh hearing dates from eCourts daily. You can add more cases anytime from the Hearings page.
              </p>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4">
          <button onClick={onClose} className="text-sm text-muted-foreground hover:text-foreground">
            {step === 'done' ? 'Close' : 'Skip for now'}
          </button>
          {step === 'review' && !loadingCases && cases.length > 0 && (
            <button
              onClick={handleImport}
              disabled={selected.size === 0 || importing}
              className="inline-flex h-10 items-center gap-2 rounded-md bg-amber-accent px-6 text-sm font-medium text-amber-accent-fg disabled:opacity-50"
            >
              {importing ? <><Loader2 className="h-4 w-4 animate-spin" /> Importing…</> : <>Import {selected.size} case{selected.size !== 1 ? 's' : ''}</>}
            </button>
          )}
          {step === 'done' && (
            <button onClick={onClose} className="inline-flex h-10 items-center gap-2 rounded-md bg-amber-accent px-6 text-sm font-medium text-amber-accent-fg">
              Go to dashboard
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
