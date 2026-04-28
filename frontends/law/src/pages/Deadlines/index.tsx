import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listDeadlines, deleteDeadline, generateCondonation } from '@/api/deadlines'
import Button from '@/components/ui/Button'
import { toast } from '@/store/toastStore'
import type { Deadline } from '@/types'
import dayjs from 'dayjs'

type UrgencyVariant = 'urgent' | 'soon' | 'ok'

function urgencyFromDate(due: string): UrgencyVariant {
  const diff = dayjs(due).diff(dayjs(), 'day')
  if (diff < 0) return 'urgent'
  if (diff <= 7) return 'urgent'
  if (diff <= 14) return 'soon'
  return 'ok'
}

function urgencyLabel(due: string): string {
  const diff = dayjs(due).diff(dayjs(), 'day')
  if (diff < 0) return 'Missed'
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  return `${diff} days`
}

const urgencyCls: Record<UrgencyVariant, string> = {
  urgent: 'bg-red-bg text-red border-red/15',
  soon: 'bg-amber-bg text-amber border-amber/15',
  ok: 'bg-green-bg text-green border-green/15',
}

function DeadlineRow({ deadline, onDelete, onCondonation }: {
  deadline: Deadline
  onDelete: (id: string) => void
  onCondonation: (id: string) => void
}) {
  const urgency = urgencyFromDate(deadline.due_date)
  const isMissed = dayjs(deadline.due_date).isBefore(dayjs(), 'day')
  const day = dayjs(deadline.due_date).format('D')
  const mon = dayjs(deadline.due_date).format('MMM').toUpperCase()

  return (
    <div className="bg-white border border-border-1 rounded-DEFAULT px-[15px] py-3 flex items-center gap-[13px] mb-[7px] cursor-pointer transition-all hover:border-border-2 hover:shadow-[0_2px_8px_rgba(0,0,0,0.05)] group">
      <div className="w-[38px] text-center flex-shrink-0">
        <div className="font-serif text-[21px] text-text-1 leading-none">{day}</div>
        <div className="text-[9px] font-bold tracking-[0.5px] uppercase text-text-3">{mon}</div>
      </div>
      <div className="w-px h-8 bg-border-1 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-[12.5px] font-semibold text-text-1 truncate">{deadline.matter_title}</div>
        <div className="text-[11px] text-text-3 mt-[1px]">
          {deadline.court}{deadline.case_number ? ` · ${deadline.case_number}` : ''}
        </div>
      </div>
      <span className={`text-[10px] font-bold px-[9px] py-[3px] rounded-full border flex-shrink-0 ${urgencyCls[urgency]}`}>
        {urgencyLabel(deadline.due_date)}
      </span>
      {isMissed && (
        <button
          onClick={(e) => { e.stopPropagation(); onCondonation(deadline.id) }}
          className="hidden group-hover:block text-[11px] font-semibold px-[11px] py-[5px] rounded-sm bg-ink text-white border border-ink hover:bg-[#2e2b27] transition-colors flex-shrink-0"
        >
          Draft Condonation →
        </button>
      )}
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(deadline.id) }}
        className="hidden group-hover:block text-[11px] text-text-3 hover:text-red transition-colors flex-shrink-0 px-1"
      >
        ✕
      </button>
    </div>
  )
}

export default function DeadlinesPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['deadlines'],
    queryFn: () => listDeadlines().then((r) => r.data.data),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDeadline(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['deadlines'] }); toast('Deadline removed') },
  })

  const condonationMutation = useMutation({
    mutationFn: (id: string) => generateCondonation(id),
    onSuccess: ({ data }) => {
      toast('Drafting condonation application…')
      navigate(`/draft?id=${data.data.draft_id}`)
    },
    onError: () => toast('Could not generate condonation draft.'),
  })

  const deadlines = data ?? []
  const missed = deadlines.filter((d) => dayjs(d.due_date).isBefore(dayjs(), 'day'))
  const urgent = deadlines.filter((d) => {
    const diff = dayjs(d.due_date).diff(dayjs(), 'day')
    return diff >= 0 && diff <= 7
  })
  const upcoming = deadlines.filter((d) => {
    const diff = dayjs(d.due_date).diff(dayjs(), 'day')
    return diff > 7
  })

  return (
    <div className="max-w-[860px]">
      <div className="flex gap-[7px] mb-[18px] flex-wrap">
        <Button variant="primary" onClick={() => toast('Add deadline — coming soon')}>+ Add Deadline</Button>
        <Button onClick={() => toast('WhatsApp configured')}>📱 WhatsApp Reminders</Button>
      </div>

      {/* Missed alerts */}
      {missed.map((d) => (
        <div key={d.id} className="bg-red-bg border border-red/20 rounded-DEFAULT px-[15px] py-[14px] flex items-start gap-3 mb-4">
          <span className="text-[18px]">⚠️</span>
          <div className="flex-1">
            <div className="text-[11px] font-bold text-red uppercase tracking-[0.5px] mb-[3px]">Missed Deadline</div>
            <div className="text-[12.5px] text-text-2">
              Limitation for <strong>{d.matter_title}</strong> may have lapsed on {dayjs(d.due_date).format('D MMMM YYYY')}.
            </div>
          </div>
          <button
            onClick={() => condonationMutation.mutate(d.id)}
            disabled={condonationMutation.isPending}
            className="text-[11px] font-semibold px-[11px] py-[5px] rounded-sm bg-ink text-white border border-ink hover:bg-[#2e2b27] transition-colors flex-shrink-0 disabled:opacity-50"
          >
            Draft Condonation →
          </button>
        </div>
      ))}

      {isLoading && (
        <div className="text-[12px] text-text-3 text-center py-12">Loading deadlines…</div>
      )}

      {/* Urgent */}
      {urgent.length > 0 && (
        <div className="mb-4">
          <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-red mb-2">Urgent — This Week</div>
          {urgent.map((d) => (
            <DeadlineRow
              key={d.id}
              deadline={d}
              onDelete={(id) => deleteMutation.mutate(id)}
              onCondonation={(id) => condonationMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      {/* Upcoming */}
      {upcoming.length > 0 && (
        <div>
          <div className="text-[10px] font-bold tracking-[0.7px] uppercase text-text-3 mb-2">Upcoming</div>
          {upcoming.map((d) => (
            <DeadlineRow
              key={d.id}
              deadline={d}
              onDelete={(id) => deleteMutation.mutate(id)}
              onCondonation={(id) => condonationMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && deadlines.length === 0 && (
        <div className="text-center py-16">
          <div className="text-[30px] mb-3">📅</div>
          <p className="font-serif text-[16px] text-text-2 mb-1">No deadlines yet</p>
          <p className="text-[12px] text-text-3">Add a matter to start tracking hearings and limitations.</p>
        </div>
      )}
    </div>
  )
}
