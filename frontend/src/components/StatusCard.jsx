/**
 * StatusCard.jsx — Reusable service-status indicator
 *
 * Props:
 *   title    {string}  — service display name
 *   status   {string}  — 'ok' | 'error' | 'loading'
 *   detail   {string=} — optional sub-status line (e.g. database status)
 *   id       {string}  — unique element ID for browser testing
 */

export default function StatusCard({ title, status, detail, id }) {
  const colours = {
    ok:      { ring: 'ring-emerald-500/40', dot: 'bg-emerald-400', label: 'text-emerald-400', text: 'Operational' },
    error:   { ring: 'ring-red-500/40',     dot: 'bg-red-400',     label: 'text-red-400',     text: 'Unreachable'  },
    loading: { ring: 'ring-slate-500/40',   dot: 'bg-slate-400',   label: 'text-slate-400',   text: 'Checking…'   },
  }

  const c = colours[status] ?? colours.loading

  return (
    <div
      id={id}
      className={`rounded-2xl bg-slate-800/60 backdrop-blur-sm ring-1 ${c.ring} p-6 flex flex-col gap-3 transition-all duration-500`}
    >
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">{title}</p>

      <div className="flex items-center gap-2">
        {/* Animated pulse dot */}
        <span className="relative flex h-2.5 w-2.5">
          {status === 'loading' && (
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${c.dot} opacity-75`} />
          )}
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${c.dot}`} />
        </span>
        <span className={`text-sm font-medium ${c.label}`}>{c.text}</span>
      </div>

      {detail && (
        <p className="text-xs text-slate-500 leading-relaxed">{detail}</p>
      )}
    </div>
  )
}
