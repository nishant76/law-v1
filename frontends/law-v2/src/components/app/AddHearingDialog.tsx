import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Loader2, Search, X } from "lucide-react";

import { createDiaryEntry } from "@/api/diary";
import { listMatters, type Matter } from "@/api/matters";
import { Input } from "@/components/ui/input";

/**
 * Add a court date to the diary by hand.
 *
 * Needed for every matter that did not come from eCourts, and for dates the
 * lawyer learns in court before the portal catches up. Plain markup rather
 * than components/ui/dialog — Radix does not resolve under this project's
 * Vite setup (see NotificationBell).
 */
export function AddHearingDialog({
  open,
  defaultDate,
  onClose,
  onSaved,
}: {
  open: boolean;
  /** Local (IST) yyyy-mm-dd the diary is currently showing. */
  defaultDate: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [matters, setMatters] = useState<Matter[]>([]);
  const [query, setQuery] = useState("");
  const [matterId, setMatterId] = useState("");
  const [date, setDate] = useState(defaultDate);
  const [board, setBoard] = useState("");
  const [purpose, setPurpose] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadingMatters, setLoadingMatters] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDate(defaultDate);
    setQuery("");
    setMatterId("");
    setBoard("");
    setPurpose("");
    setLoadingMatters(true);
    // Plain async/await, never useMutation (CLAUDE.md, GAP-050).
    listMatters()
      .then((res) => setMatters(res.data.matters))
      .catch(() => toast.error("Could not load your matters."))
      .finally(() => setLoadingMatters(false));
  }, [open, defaultDate]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Search by client as well as case name — a lawyer looking for "which matter"
  // often remembers the client, not the cause title.
  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const pool = q
      ? matters.filter(
          (m) =>
            m.case_name.toLowerCase().includes(q) ||
            m.client_name?.toLowerCase().includes(q) ||
            m.cnr_number?.toLowerCase().includes(q),
        )
      : matters;
    return pool.slice(0, 40);
  }, [matters, query]);

  if (!open) return null;

  const selected = matters.find((m) => m.id === matterId);

  const handleSave = async () => {
    if (saving) return;
    if (!matterId) return toast.error("Pick the matter this date belongs to.");
    if (!date) return toast.error("Pick the date of hearing.");
    setSaving(true);
    try {
      await createDiaryEntry({
        matter_id: matterId,
        // 10:30 IST is the conventional court hour; storing 05:00Z keeps the
        // entry on the correct IST calendar day.
        hearing_date: `${date}T05:00:00Z`,
        board_number: board.trim() || undefined,
        purpose: purpose.trim() || undefined,
      });
      toast.success("Hearing added to your diary.");
      onSaved();
    } catch {
      toast.error("Could not add the hearing. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 lg:p-10"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Add a hearing"
        className="hairline max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between gap-3">
          <h2 className="font-serif text-lg">Add a hearing</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 rounded p-1 text-muted-foreground hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="block text-xs font-medium">Matter</label>
            {selected ? (
              <div className="flex items-center justify-between gap-2 rounded-md bg-sand/60 p-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{selected.case_name}</div>
                  <div className="truncate text-[11px] text-muted-foreground">
                    {selected.client_name ? `${selected.client_name} · ` : ""}
                    {selected.court ?? ""}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setMatterId("")}
                  className="shrink-0 text-xs text-muted-foreground underline"
                >
                  Change
                </button>
              </div>
            ) : (
              <>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    autoFocus
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search by client, case name or CNR…"
                    className="pl-9"
                  />
                </div>
                <div className="hairline max-h-52 overflow-y-auto rounded-md">
                  {loadingMatters ? (
                    <div className="flex justify-center py-6">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  ) : results.length === 0 ? (
                    <p className="px-3 py-6 text-center text-xs text-muted-foreground">
                      No matter matches that search.
                    </p>
                  ) : (
                    <ul className="divide-y divide-border">
                      {results.map((m) => (
                        <li key={m.id}>
                          <button
                            type="button"
                            onClick={() => setMatterId(m.id)}
                            className="w-full px-3 py-2 text-left hover:bg-sand/50"
                          >
                            <div className="truncate text-xs font-medium">{m.case_name}</div>
                            <div className="truncate text-[11px] text-muted-foreground">
                              {m.client_name ? `${m.client_name} · ` : ""}
                              {m.court ?? ""}
                            </div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="hearing-date" className="block text-xs font-medium">
                Date of hearing
              </label>
              <Input
                id="hearing-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="hearing-board" className="block text-xs font-medium">
                Item / board no.
              </label>
              <Input
                id="hearing-board"
                value={board}
                onChange={(e) => setBoard(e.target.value)}
                placeholder="37"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="hearing-purpose" className="block text-xs font-medium">
              For (stage)
            </label>
            <Input
              id="hearing-purpose"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="Arguments, evidence, framing of issues…"
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="hairline h-9 rounded-md bg-card px-4 text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="inline-flex h-9 items-center gap-2 rounded-md bg-foreground px-4 text-sm text-background disabled:opacity-50"
          >
            {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Add hearing
          </button>
        </div>
      </div>
    </div>
  );
}
