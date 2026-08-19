import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, X } from "lucide-react";

import {
  recordHearingOutcome,
  type HearingEntry,
  type HearingEntryStatus,
} from "@/api/diary";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

/**
 * Plain <label>, not components/ui/label — that wraps @radix-ui/react-label, and
 * no Radix primitive resolves correctly under this project's TanStack Start /
 * Vite setup (importing one yields a second React instance and an "Invalid hook
 * call"). Same reason this dialog is hand-rolled instead of using ui/dialog.
 */
function Label({ htmlFor, children }: { htmlFor?: string; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs font-medium text-foreground">
      {children}
    </label>
  );
}

const STATUS_OPTIONS: { value: HearingEntryStatus; label: string; hint: string }[] = [
  { value: "adjourned", label: "Adjourned", hint: "Taken up and put off to a new date" },
  { value: "held", label: "Heard", hint: "Proceeded — arguments, evidence, order" },
  { value: "not_taken_up", label: "Not taken up", hint: "Not reached, or judge on leave" },
  { value: "disposed", label: "Disposed", hint: "Matter finished on this date" },
];

/**
 * Records what happened on a court date.
 *
 * Supplying a next date is what makes the diary self-maintaining: the backend
 * creates the next listing, rolls the matter's next_hearing_date forward, and
 * arms a fresh 30/7/1 reminder set.
 */
export function RecordOutcomeDialog({
  entry,
  onClose,
  onSaved,
}: {
  entry: HearingEntry | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [status, setStatus] = useState<HearingEntryStatus>("adjourned");
  const [outcome, setOutcome] = useState("");
  const [nextDate, setNextDate] = useState("");
  const [actionRequired, setActionRequired] = useState("");
  const [boardNumber, setBoardNumber] = useState("");
  const [appearedBy, setAppearedBy] = useState("");
  const [saving, setSaving] = useState(false);

  // Re-seed the form whenever a different entry is opened.
  useEffect(() => {
    if (!entry) return;
    setStatus(entry.status === "scheduled" ? "adjourned" : entry.status);
    setOutcome(entry.outcome ?? "");
    setNextDate(entry.next_date ? entry.next_date.slice(0, 10) : "");
    setActionRequired(entry.action_required ?? "");
    setBoardNumber(entry.board_number ?? "");
    setAppearedBy(entry.appeared_by ?? "");
  }, [entry]);

  if (!entry) return null;

  const needsNextDate = status === "adjourned" || status === "not_taken_up";

  const handleSave = async () => {
    if (saving) return;
    if (needsNextDate && !nextDate) {
      toast.error("Please enter the next date of hearing.");
      return;
    }
    setSaving(true);
    try {
      await recordHearingOutcome(entry.id, {
        status,
        outcome: outcome.trim() || undefined,
        // Hearings are listed for the day; 10:30 IST (05:00 UTC) is the
        // conventional court hour and keeps the date on the right IST day.
        next_date: nextDate ? `${nextDate}T05:00:00Z` : undefined,
        action_required: actionRequired.trim() || undefined,
        board_number: boardNumber.trim() || undefined,
        appeared_by: appearedBy.trim() || undefined,
      });
      toast.success(
        nextDate ? "Recorded. Next date added and reminders set." : "Recorded.",
      );
      onSaved();
    } catch {
      toast.error("Could not save. Please try again.");
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
        aria-label={`Record outcome — ${entry.case_name}`}
        className="hairline max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5">
          <div className="flex items-start justify-between gap-3">
            <h2 className="font-serif text-lg leading-snug">{entry.case_name}</h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="shrink-0 rounded p-1 text-muted-foreground hover:bg-muted"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {new Date(entry.hearing_date).toLocaleDateString("en-IN", {
              timeZone: "Asia/Kolkata",
              weekday: "short",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
            {entry.court ? ` · ${entry.court}` : ""}
          </p>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>What happened</Label>
            <div className="grid grid-cols-2 gap-2">
              {STATUS_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => setStatus(o.value)}
                  className={`rounded-md border p-3 text-left text-sm transition ${
                    status === o.value
                      ? "border-foreground bg-sand/60"
                      : "border-border bg-card hover:bg-sand/30"
                  }`}
                >
                  <div className="font-medium">{o.label}</div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground">{o.hint}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="outcome">Note</Label>
            <Textarea
              id="outcome"
              rows={3}
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
              placeholder="What the court said, orders passed, reason for adjournment…"
            />
          </div>

          {status !== "disposed" && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="next-date">
                  Next date {needsNextDate && <span className="text-destructive">*</span>}
                </Label>
                <Input
                  id="next-date"
                  type="date"
                  value={nextDate}
                  onChange={(e) => setNextDate(e.target.value)}
                />
                <p className="text-[11px] text-muted-foreground">
                  Sets the matter's next hearing and re-arms 30/7/1 reminders.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="action">To do before next date</Label>
                <Input
                  id="action"
                  value={actionRequired}
                  onChange={(e) => setActionRequired(e.target.value)}
                  placeholder="File reply, produce witness…"
                />
              </div>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="board">Item / board no.</Label>
              <Input
                id="board"
                value={boardNumber}
                onChange={(e) => setBoardNumber(e.target.value)}
                placeholder="37"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="appeared">Appeared by</Label>
              <Input
                id="appeared"
                value={appearedBy}
                onChange={(e) => setAppearedBy(e.target.value)}
                placeholder="Self / proxy counsel"
              />
            </div>
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
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
