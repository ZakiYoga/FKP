import { formatDateTime } from "@/lib/utils"
import { TrackingStage } from "@/types/trackFkp"
import { CheckCircle2, Clock } from "lucide-react"

function TimelineItem({
    stage,
    isLast,
}: {
    stage: TrackingStage
    isLast: boolean
}) {
    return (
        <div className="flex gap-4">
            {/* Indicator kolom kiri */}
            <div className="flex flex-col items-center shrink-0">
                <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all z-10
            ${stage.is_current
                            ? 'bg-amber-500 border-amber-500 shadow-md'
                            : stage.is_completed
                                ? 'bg-emerald-500 border-emerald-500'
                                : 'bg-white border-gray-200'
                        }`}
                >
                    {stage.is_completed ? (
                        <CheckCircle2 className="w-4 h-4 text-white" />
                    ) : stage.is_current ? (
                        <Clock className="w-4 h-4 text-white animate-pulse" />
                    ) : (
                        <div className="w-2 h-2 rounded-full bg-gray-300" />
                    )}
                </div>
                {/* Garis vertikal */}
                {!isLast && (
                    <div
                        className={`w-0.5 flex-1 mt-1 min-h-8 ${stage.is_completed ? 'bg-emerald-300' : 'bg-gray-200'
                            }`}
                    />
                )}
            </div>

            {/* Konten kanan */}
            <div
                className={`
          pb-6 flex-1 min-w-0
          ${isLast ? 'pb-0' : ''}
        `}
            >
                <p
                    className={`
            text-sm font-semibold leading-snug
            ${stage.is_current
                            ? 'text-brand-700'
                            : stage.is_completed
                                ? 'text-gray-800'
                                : 'text-gray-400'
                        }
          `}
                >
                    {stage.label}
                    {stage.is_current && (
                        <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-brand-100 text-brand-600 uppercase tracking-wide">
                            Saat ini
                        </span>
                    )}
                </p>
                {(stage.is_completed || stage.is_current) && stage.timestamp && (
                    <p className="text-xs text-gray-400 mt-0.5">
                        {formatDateTime(stage.timestamp)}
                    </p>
                )}
                {!stage.is_completed && !stage.is_current && (
                    <p className="text-xs text-gray-300 mt-0.5">Menunggu diproses</p>
                )}
            </div>
        </div>
    )
}

export default TimelineItem;