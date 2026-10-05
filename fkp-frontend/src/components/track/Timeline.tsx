import { useState } from 'react'
import { CheckCircle2, ChevronDown, Clock, XCircle } from 'lucide-react'

import { formatDateTime } from '@/lib/utils'
import type { StepState, TrackingPhase, TrackingStep } from '@/types/trackFkp'

const STYLE: Record<StepState, { circle: string; title: string; badge: string }> = {
    done:     { circle: 'bg-emerald-500 border-emerald-500', title: 'text-gray-800', badge: '' },
    current:  { circle: 'bg-amber-500 border-amber-500 shadow-md', title: 'text-amber-700', badge: 'bg-amber-100 text-amber-700' },
    rejected: { circle: 'bg-red-500 border-red-500', title: 'text-red-700', badge: 'bg-red-100 text-red-700' },
    pending:  { circle: 'bg-white border-gray-200', title: 'text-gray-400', badge: '' },
}

function StateIcon({ state, small = false }: { state: StepState; small?: boolean }) {
    const size = small ? 'w-2.5 h-2.5' : 'w-4 h-4'
    if (state === 'done') return <CheckCircle2 className={`${size} text-white`} />
    if (state === 'current') return <Clock className={`${size} text-white animate-pulse`} />
    if (state === 'rejected') return <XCircle className={`${size} text-white`} />
    return <div className={`${small ? 'w-1 h-1' : 'w-2 h-2'} rounded-full bg-gray-300`} />
}

function timeText(state: StepState, ts: string | null) {
    if (!ts || state === 'pending') return null
    return state === 'current' ? `Sejak ${formatDateTime(ts)}` : formatDateTime(ts)
}

function StepRow({ step }: { step: TrackingStep }) {
    const style = STYLE[step.state]
    const time = timeText(step.state, step.timestamp)
    return (
        <li className="flex items-start gap-3">
            <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${style.circle}`}>
                <StateIcon state={step.state} small />
            </div>
            <div className="min-w-0">
                <p className={`text-xs font-medium leading-snug ${style.title}`}>{step.label}</p>
                {time && <p className="text-[11px] text-gray-400 mt-0.5">{time}</p>}
            </div>
        </li>
    )
}

function PhaseItem({ phase, isLast }: { phase: TrackingPhase; isLast: boolean }) {
    const expandable = phase.steps.length > 1
    const [open, setOpen] = useState(phase.state === 'current' || phase.state === 'rejected')

    const style = STYLE[phase.state]
    const active = phase.steps.find(s => s.state === 'current' || s.state === 'rejected')
    const subtitle = phase.state === 'pending' ? 'Menunggu diproses' : active?.label ?? null
    const time = timeText(phase.state, phase.timestamp)
    const badge =
        phase.state === 'current' ? 'Saat ini' : phase.state === 'rejected' ? 'Ditolak' : null

    return (
        <div className="flex gap-4">
            {/* Indikator kiri */}
            <div className="flex flex-col items-center shrink-0">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center border-2 z-10 ${style.circle}`}>
                    <StateIcon state={phase.state} />
                </div>
                {!isLast && (
                    <div className={`w-0.5 flex-1 mt-1 min-h-8 ${phase.state === 'done' ? 'bg-emerald-300' : 'bg-gray-200'}`} />
                )}
            </div>

            {/* Konten kanan */}
            <div className={`flex-1 min-w-0 ${isLast ? '' : 'pb-6'}`}>
                <button
                    type="button"
                    onClick={() => expandable && setOpen(o => !o)}
                    disabled={!expandable}
                    aria-expanded={expandable ? open : undefined}
                    className="w-full flex items-start justify-between gap-2 text-left disabled:cursor-default"
                >
                    <div className="min-w-0">
                        <p className={`text-sm font-semibold leading-snug ${style.title}`}>
                            {phase.label}
                            {badge && (
                                <span className={`ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide ${style.badge}`}>
                                    {badge}
                                </span>
                            )}
                        </p>
                        {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
                        {time && <p className="text-xs text-gray-400 mt-0.5">{time}</p>}
                    </div>
                    {expandable && (
                        <ChevronDown
                            className={`w-4 h-4 text-gray-400 shrink-0 mt-0.5 transition-transform ${open ? 'rotate-180' : ''}`}
                        />
                    )}
                </button>

                {expandable && open && (
                    <ol className="mt-3 ml-1 space-y-3 border-l border-gray-100 pl-4">
                        {phase.steps.map(step => <StepRow key={step.key} step={step} />)}
                    </ol>
                )}
            </div>
        </div>
    )
}

export function PhaseTimeline({ phases }: { phases: TrackingPhase[] }) {
    return (
        <div>
            {phases.map((phase, idx) => (
                <PhaseItem key={phase.key} phase={phase} isLast={idx === phases.length - 1} />
            ))}
        </div>
    )
}