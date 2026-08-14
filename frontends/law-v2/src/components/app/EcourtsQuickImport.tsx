import { useState, useEffect, useRef } from 'react'
import { toast } from 'sonner'
import {
  X, Loader2, Scale, CheckSquare, Square, Download, MapPin, ChevronDown, Search,
} from 'lucide-react'
import { importCnrs, previewMyCases, searchCasesByName, getEcourtsStatus, type DiscoveredCase } from '@/api/ecourts'
import { useAuthStore } from '@/store/authStore'

interface Props {
  onClose: () => void
  onImported: (count: number) => void
}

export function EcourtsQuickImport({ onClose, onImported }: Props) {
  const user = useAuthStore((s) => s.user)
  const advocateName = user?.full_name ?? ''

  const [fetching, setFetching] = useState(false)
  const [cases, setCases] = useState<DiscoveredCase[]>([])
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  // True when a prior visit already checked the name and found nothing — we skip
  // the (billed) auto-check entirely and go straight to manual search.
  const [skippedAutoCheck, setSkippedAutoCheck] = useState(false)

  const [showCityFilter, setShowCityFilter] = useState(false)
  const [city, setCity] = useState(() => {
    try { return localStorage.getItem('sa-ecourts-city') ?? '' } catch { return '' }
  })

  // Manual fallback search — used when the identity-matched preview finds nothing.
  // Fires only on Enter, never on every keystroke — each call is a billed eCourts API hit.
  const [manualQuery, setManualQuery] = useState('')
  const [manualResults, setManualResults] = useState<DiscoveredCase[]>([])
  const [manualSearching, setManualSearching] = useState(false)
  const [manualError, setManualError] = useState<string | null>(null)
  const manualSearchIdRef = useRef(0)
  const manualLastFiredRef = useRef('')

  // "Check once" rule: after the first-ever name check, if nothing was found we
  // never re-attempt the (billed) name-based search again — go straight to
  // manual search every time the modal opens from then on.
  useEffect(() => {
    (async () => {
      setFetching(true)
      try {
        const res = await getEcourtsStatus()
        if (res.data.name_match_found === false) {
          setSkippedAutoCheck(true)
          setFetching(false)
          setCases([])
          return
        }
      } catch {
        // status check failed — fall through to the normal auto-fetch attempt
      }
      fetchCases(city || undefined)
    })()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const fetchCases = async (filterCity?: string) => {
    setFetching(true)
    setFetchError(null)
    try {
      const res = await previewMyCases(filterCity?.trim() || undefined)
      const fetched = (res.data.cases ?? []) as DiscoveredCase[]
      setCases(fetched)
      setSelected(new Set(fetched.map((c) => c.cnr)))
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFetchError(detail ?? 'Could not reach eCourts. Check your connection and try again.')
    } finally {
      setFetching(false)
    }
  }

  const applyCity = () => {
    const trimmed = city.trim()
    try { localStorage.setItem('sa-ecourts-city', trimmed) } catch {}
    fetchCases(trimmed || undefined)
  }

  const clearCity = () => {
    setCity('')
    try { localStorage.removeItem('sa-ecourts-city') } catch {}
    fetchCases(undefined)
  }

  const runManualSearch = async (raw: string) => {
    const trimmed = raw.trim()
    if (trimmed.length < 3 || trimmed === manualLastFiredRef.current) return
    manualLastFiredRef.current = trimmed

    const thisId = ++manualSearchIdRef.current
    setManualSearching(true)
    setManualError(null)
    try {
      const res = await searchCasesByName(trimmed)
      if (thisId !== manualSearchIdRef.current) return // stale response, ignore
      setManualResults(res.data.cases ?? [])
    } catch (err: unknown) {
      if (thisId !== manualSearchIdRef.current) return
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setManualError(detail ?? 'Search failed. Try again.')
      setManualResults([])
    } finally {
      if (thisId === manualSearchIdRef.current) setManualSearching(false)
    }
  }

  const handleManualKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      runManualSearch(manualQuery)
    }
  }

  const addManualCase = (c: DiscoveredCase) => {
    setCases((prev) => (prev.some((x) => x.cnr === c.cnr) ? prev : [...prev, c]))
    setSelected((prev) => new Set(prev).add(c.cnr))
    setManualQuery('')
    setManualResults([])
    manualLastFiredRef.current = ''
  }

  const toggleAll = () => {
    setSelected((prev) =>
      prev.size === cases.length ? new Set() : new Set(cases.map((c) => c.cnr))
    )
  }

  const toggle = (cnr: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(cnr) ? next.delete(cnr) : next.add(cnr)
      return next
    })
  }

  const handleImport = async () => {
    const toImport = cases.filter((c) => selected.has(c.cnr))
    if (!toImport.length) return

    onClose()

    const tid = toast.loading(
      `Importing ${toImport.length} case${toImport.length === 1 ? '' : 's'} from eCourts…`
    )
    try {
      const res = await importCnrs(toImport)
      const n = res.data.imported ?? toImport.length
      toast.success(
        `${n} case${n === 1 ? '' : 's'} imported. Hearing dates sync daily.`,
        { id: tid, duration: 7000 }
      )
      onImported(n)
    } catch {
      toast.error('Import failed. Try again from eCourts settings.', { id: tid, duration: 7000 })
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center bg-foreground/40 backdrop-blur-sm">
      <div className="w-full sm:max-w-lg max-h-[92vh] flex flex-col rounded-t-2xl sm:rounded-2xl bg-background shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-start justify-between border-b border-border px-6 py-5 shrink-0">
          <div>
            <h2 className="font-serif text-lg text-foreground leading-tight">Your eCourts cases</h2>
            {advocateName && (
              <p className="mt-1 text-xs text-muted-foreground">
                Showing pending cases for{' '}
                <span className="font-medium text-foreground">{advocateName}</span>
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto min-h-0">

          {/* Loading */}
          {fetching && (
            <div className="flex flex-col items-center justify-center gap-3 py-20">
              <Loader2 className="h-7 w-7 animate-spin text-amber-accent" />
              <p className="text-sm text-muted-foreground">Fetching your pending cases…</p>
            </div>
          )}

          {/* Error */}
          {!fetching && fetchError && (
            <div className="flex flex-col items-center justify-center gap-4 px-6 py-16 text-center">
              <Scale className="h-8 w-8 text-border" />
              <div>
                <p className="text-sm font-medium text-foreground">Could not fetch cases</p>
                <p className="mt-1.5 text-xs text-muted-foreground max-w-xs mx-auto">{fetchError}</p>
              </div>
              <button
                onClick={() => fetchCases(city || undefined)}
                className="text-xs font-medium text-amber-accent hover:opacity-80"
              >
                Try again
              </button>
            </div>
          )}

          {/* Results */}
          {!fetching && !fetchError && (
            <>
              {/* Toolbar */}
              <div className="flex items-center justify-between border-b border-border px-6 py-3 bg-muted/30 shrink-0">
                <div className="text-sm">
                  {cases.length > 0 ? (
                    <>
                      <span className="font-semibold text-foreground">{cases.length}</span>
                      <span className="text-muted-foreground"> pending case{cases.length !== 1 ? 's' : ''} found</span>
                    </>
                  ) : skippedAutoCheck ? (
                    <span className="text-muted-foreground">Search for your cases below</span>
                  ) : (
                    <span className="text-muted-foreground">No pending cases found</span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {cases.length > 0 && (
                    <button onClick={toggleAll} className="text-xs text-amber-accent hover:opacity-80">
                      {selected.size === cases.length ? 'Deselect all' : 'Select all'}
                    </button>
                  )}
                  {!skippedAutoCheck && (
                    <button
                      onClick={() => setShowCityFilter((f) => !f)}
                      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                      <MapPin className="h-3 w-3" />
                      Filter by city
                      <ChevronDown
                        className={`h-3 w-3 transition-transform ${showCityFilter ? 'rotate-180' : ''}`}
                      />
                    </button>
                  )}
                </div>
              </div>

              {/* City filter (collapsible) */}
              {showCityFilter && (
                <div className="flex items-center gap-2 border-b border-border bg-muted/20 px-6 py-3">
                  <input
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && applyCity()}
                    placeholder="e.g. Panchkula, Chandigarh, Ludhiana"
                    className="h-8 flex-1 rounded-md border border-border bg-background px-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                    autoFocus
                  />
                  <button
                    onClick={applyCity}
                    className="h-8 rounded-md bg-amber-accent px-3 text-xs font-medium text-amber-accent-fg hover:opacity-90"
                  >
                    Apply
                  </button>
                  {city && (
                    <button onClick={clearCity} className="text-xs text-muted-foreground hover:text-foreground">
                      Clear
                    </button>
                  )}
                </div>
              )}

              {/* Empty state — manual fallback search by case/party name */}
              {cases.length === 0 && (
                <div className="flex flex-col items-center gap-4 px-6 py-10 text-center">
                  <Scale className="h-8 w-8 text-border" />
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {skippedAutoCheck ? 'Search for your cases' : 'No pending cases found'}
                    </p>
                    <p className="mt-1.5 text-xs text-muted-foreground max-w-xs mx-auto">
                      {skippedAutoCheck
                        ? "We couldn't find your name on eCourts earlier, so we no longer check automatically. Search by case or party name below."
                        : 'Your name on eCourts may be spelled differently. Search by case or party name below, or filter by city.'}
                    </p>
                  </div>
                  {!skippedAutoCheck && (
                    <button
                      onClick={() => setShowCityFilter(true)}
                      className="text-xs font-medium text-amber-accent hover:opacity-80"
                    >
                      Filter by city →
                    </button>
                  )}

                  {/* Manual search box */}
                  <div className="w-full max-w-sm text-left">
                    <div className="relative">
                      <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                      <input
                        value={manualQuery}
                        onChange={(e) => setManualQuery(e.target.value)}
                        onKeyDown={handleManualKeyDown}
                        placeholder="Type a case or party name…"
                        className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-accent/40"
                      />
                      {manualSearching && (
                        <Loader2 className="absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 animate-spin text-muted-foreground" />
                      )}
                    </div>

                    {manualError && (
                      <p className="mt-2 text-xs text-red-600">{manualError}</p>
                    )}

                    {!manualError && manualResults.length > 0 && (
                      <ul className="mt-2 max-h-48 overflow-y-auto rounded-md border border-border divide-y divide-border">
                        {manualResults.map((c) => (
                          <li
                            key={c.cnr}
                            onClick={() => addManualCase(c)}
                            className="cursor-pointer px-3 py-2.5 hover:bg-muted/40"
                          >
                            <div className="flex items-center gap-1.5">
                              <div className="truncate text-xs font-medium text-foreground">
                                {c.case_name}
                              </div>
                              {c.case_type && (
                                <span className="shrink-0 rounded-full bg-muted px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground">
                                  {c.case_type}
                                </span>
                              )}
                            </div>
                            <div className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                              <span className="font-mono">{c.cnr}</span>
                              {c.court && (
                                <>
                                  <span>·</span>
                                  <span className="truncate">{c.court}</span>
                                </>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}

                    {!manualError && !manualSearching && manualLastFiredRef.current && manualResults.length === 0 && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        No cases matched "{manualLastFiredRef.current}".
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Case list */}
              {cases.length > 0 && (
                <ul className="divide-y divide-border">
                  {cases.map((c) => (
                    <li
                      key={c.cnr}
                      onClick={() => toggle(c.cnr)}
                      className="flex cursor-pointer items-start gap-3 px-6 py-3.5 hover:bg-muted/30 transition-colors"
                    >
                      <div className="mt-0.5 shrink-0">
                        {selected.has(c.cnr) ? (
                          <CheckSquare className="h-4 w-4 text-amber-accent" />
                        ) : (
                          <Square className="h-4 w-4 text-muted-foreground/40" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <div className="truncate text-sm font-medium text-foreground">
                            {c.case_name}
                          </div>
                          {c.case_type && (
                            <span className="shrink-0 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                              {c.case_type}
                            </span>
                          )}
                        </div>
                        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                          <span className="font-mono">{c.cnr}</span>
                          {c.court && (
                            <>
                              <span>·</span>
                              <span className="truncate">{c.court}</span>
                            </>
                          )}
                        </div>
                        {c.judges && c.judges.length > 0 && (
                          <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                            {c.judges.join(', ')}
                          </div>
                        )}
                      </div>
                      {c.next_hearing_date && (
                        <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
                          {c.next_hearing_date}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        {!fetching && !fetchError && cases.length > 0 && (
          <div className="shrink-0 border-t border-border bg-background px-6 py-4">
            <div className="flex items-center justify-between gap-4">
              <p className="text-xs text-muted-foreground">
                {selected.size} of {cases.length} selected
              </p>
              <button
                onClick={handleImport}
                disabled={selected.size === 0}
                className="inline-flex h-9 items-center gap-2 rounded-md bg-amber-accent px-5 text-sm font-medium text-amber-accent-fg hover:opacity-90 disabled:opacity-40 transition-opacity"
              >
                <Download className="h-4 w-4" />
                Import {selected.size} case{selected.size !== 1 ? 's' : ''}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
