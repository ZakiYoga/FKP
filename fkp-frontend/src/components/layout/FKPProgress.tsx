import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  FilePlus,
  Eye,
  Building2,
  Flag,
  Check,
  User,
  FlaskConical,
  Map,
  Crown,
  RefreshCw,
  Scissors,
  Trash2,
  Microscope,
  ReceiptText,
  FlameKindling,
} from "lucide-react"

// ─── Types ────────────────────────────────────────────────────────────────────

type StepStatus = 'done' | 'active' | 'pending'

interface SubBadge {
  icon: React.ReactNode
  label: string
}

interface FKPStep {
  icon: React.ReactNode
  title: string
  description: string
  subItems?: SubBadge[]
  outcomes?: SubBadge[]
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const FKP_STEPS: FKPStep[] = [
  {
    icon: <FilePlus size={14} />,
    title: 'Buat FKP',
    description: 'Distributor mengisi formulir keluhan produk dan melampirkan bukti',
  },
  {
    icon: <Eye size={14} />,
    title: 'Review APSM',
    description: 'Area Product Sales Manager memverifikasi dan meneruskan pengajuan',
  },
  {
    icon: <Building2 size={14} />,
    title: 'Review HO',
    description: 'Proses persetujuan bertahap di Head Office',
    subItems: [
      { icon: <User size={11} />,         label: 'Admin Marketing' },
      { icon: <Microscope size={11} />, label: 'QC'              },
      { icon: <Map size={11} />,          label: 'RSM'             },
      { icon: <Crown size={11} />,        label: 'Direktur'        },
    ],
  },
  {
    icon: <Flag size={14} />,
    title: 'Penyelesaian',
    description: 'Keputusan akhir berdasarkan hasil review',
    outcomes: [
      { icon: <RefreshCw size={11} />, label: 'Pergantian Barang' },
      { icon: <ReceiptText size={11} />, label: 'Potongan Tagihan'  },
      { icon: <FlameKindling size={11} />,   label: 'Dimusnahkan'       },
    ],
  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getStatus(stepIndex: number, activeIndex: number): StepStatus {
  if (stepIndex < activeIndex) return 'done'
  if (stepIndex === activeIndex) return 'active'
  return 'pending'
}

// ─── Status Config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<StepStatus, {
  dotClass: string
  lineFilledClass: string
  badgeClass: string
  label: string
  showCheck: boolean
}> = {
  done: {
    dotClass:        'bg-emerald-600 border-transparent',
    lineFilledClass: 'bg-emerald-600',
    badgeClass:      'text-emerald-300 bg-emerald-900/40 border-emerald-600/50',
    label:           'Selesai',
    showCheck:       true,
  },
  active: {
    dotClass:        'bg-amber-500 border-transparent',
    lineFilledClass: 'bg-amber-500',
    badgeClass:      'text-amber-300 bg-amber-900/40 border-amber-500/50',
    label:           'Dalam Proses',
    showCheck:       false,
  },
  pending: {
    dotClass:        'bg-white/5 border-white/20',
    lineFilledClass: 'bg-white/10',
    badgeClass:      'text-white/30 bg-white/5 border-white/10',
    label:           'Menunggu',
    showCheck:       false,
  },
}

// ─── Animated Line ────────────────────────────────────────────────────────────

function TimelineLine({
  status,
  isActive,
}: {
  status: StepStatus
  isActive: boolean
}) {
  const cfg = STATUS_CONFIG[status]

  return (
    <div className="flex-1 w-px my-0.5 relative overflow-hidden bg-white/10">
      <motion.div
        className={`absolute top-0 left-0 right-0 ${cfg.lineFilledClass}`}
        initial={{ height: '0%' }}
        animate={{
          height: status === 'done' ? '100%' : isActive ? '100%' : '0%',
        }}
        transition={{ duration: 0.6, ease: 'easeInOut' }}
      />
      {isActive && (
        <motion.div
          className="absolute left-0 right-0 h-6 bg-gradient-to-b from-amber-400/60 to-transparent"
          initial={{ top: '-20%' }}
          animate={{ top: '120%' }}
          transition={{
            duration: 0.8,
            ease: 'easeInOut',
            repeat: Infinity,
            repeatDelay: 0.2,
          }}
        />
      )}
    </div>
  )
}

// ─── Step Item ────────────────────────────────────────────────────────────────

function FKPStepItem({
  step,
  index,
  isLast,
  activeIndex,
}: {
  step: FKPStep
  index: number
  isLast: boolean
  activeIndex: number
}) {
  const status    = getStatus(index, activeIndex)
  const cfg       = STATUS_CONFIG[status]
  const isPending = status === 'pending'
  const isActive  = status === 'active'

  return (
    <motion.div
      className="flex items-stretch"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
    >
      {/* Timeline spine */}
      <div className="flex flex-col items-center w-8 flex-shrink-0">

        {/* Dot */}
        <motion.div
          className={`w-7 h-7 rounded-full border flex items-center justify-center flex-shrink-0 text-white ${cfg.dotClass}`}
          animate={isActive ? { scale: [1, 1.12, 1] } : { scale: 1 }}
          transition={isActive
            ? { duration: 1.2, repeat: Infinity, ease: 'easeInOut' }
            : {}
          }
        >
          {cfg.showCheck
            ? <Check size={13} strokeWidth={2.5} />
            : <span className={isPending ? 'text-white/30' : 'text-white'}>
                {step.icon}
              </span>
          }
        </motion.div>

        {/* Line */}
        {!isLast && (
          <TimelineLine status={status} isActive={isActive} />
        )}
      </div>

      {/* Content */}
      <div className={`pl-3 flex-1 ${!isLast ? 'pb-5' : ''}`}>

        {/* Title + badge */}
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-sm font-medium transition-colors duration-500 ${
            isPending ? 'text-white/40' : 'text-white'
          }`}>
            {step.title}
          </span>
          <motion.span
            key={status}
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className={`text-[10px] font-medium rounded-full px-2 py-0.5 border ${cfg.badgeClass}`}
          >
            {cfg.label}
          </motion.span>
        </div>

        {/* Description */}
        <p className={`text-xs leading-relaxed transition-colors duration-500 ${
          isPending ? 'text-white/25' : 'text-white/50'
        }`}>
          {step.description}
        </p>

        {/* Sub-approvers */}
        {step.subItems && (
          <motion.div
            className="flex flex-wrap gap-1.5 mt-2"
            animate={{ opacity: isPending ? 0.3 : 1 }}
            transition={{ duration: 0.4 }}
          >
            {step.subItems.map((sub) => (
              <div
                key={sub.label}
                className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-md px-2 py-1"
              >
                <span className="text-white/40">{sub.icon}</span>
                <span className="text-[11px] text-white/40">{sub.label}</span>
              </div>
            ))}
          </motion.div>
        )}

        {/* Outcomes */}
        {step.outcomes && (
          <motion.div
            className="flex flex-wrap gap-1.5 mt-2"
            animate={{ opacity: isPending ? 0.3 : 1 }}
            transition={{ duration: 0.4 }}
          >
            {step.outcomes.map((out) => (
              <div
                key={out.label}
                className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-md px-2 py-1"
              >
                <span className="text-white/40">{out.icon}</span>
                <span className="text-[11px] text-white/40">{out.label}</span>
              </div>
            ))}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

// ─── Main Export ──────────────────────────────────────────────────────────────

const STEP_DURATION = 2000

export function FKPProgress() {
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % FKP_STEPS.length)
    }, STEP_DURATION)

    return () => clearInterval(timer)
  }, [])

  return (
    <div className="pt-2">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-[10px] font-medium tracking-widest uppercase text-white/60">
          Alur Pengajuan
        </span>
        <span className="text-[10px] text-white/25 border border-white/10 rounded-full px-2 py-0.5">
          4 tahap
        </span>
      </div>

      {/* Steps */}
      {FKP_STEPS.map((step, i) => (
        <FKPStepItem
          key={step.title}
          step={step}
          index={i}
          isLast={i === FKP_STEPS.length - 1}
          activeIndex={activeIndex}
        />
      ))}

      {/* Loop indicator */}
      <div className="flex items-center gap-1.5 mt-4 justify-center">
        {FKP_STEPS.map((_, i) => (
          <motion.div
            key={i}
            className="h-1 rounded-full"
            animate={{
              width: i === activeIndex ? 20 : 6,
              backgroundColor: i === activeIndex
                ? 'rgba(251,191,36,0.7)'
                : i < activeIndex
                  ? 'rgba(52,211,153,0.5)'
                  : 'rgba(255,255,255,0.15)',
            }}
            transition={{ duration: 0.35 }}
          />
        ))}
      </div>

    </div>
  )
}