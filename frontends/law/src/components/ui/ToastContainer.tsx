import { useToastStore } from '@/store/toastStore'

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)

  if (!toasts.length) return null

  return (
    <div className="fixed bottom-[70px] md:bottom-[22px] left-1/2 md:left-auto -translate-x-1/2 md:translate-x-0 md:right-[22px] z-[999] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className="bg-ink text-white font-sans text-[12px] font-medium px-[15px] py-[7px] rounded-full md:rounded-sm shadow-lg whitespace-nowrap animate-[fadeUp_0.2s_ease_both]"
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
