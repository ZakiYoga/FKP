import { useState, useRef, useCallback } from 'react'
import { Slider } from '@mantine/core'
import { motion, AnimatePresence } from 'framer-motion'
import { RATING_CONFIGS, getConfig, getTrackFillPercent } from './config'
import type { RatingSliderProps } from '@/types/slider'

export function RatingSlider({
  question = 'Seberapa puas Anda?',
  label = 'Pertanyaan 1',
  onSubmit,
  onChange,
  defaultValue = null,
  readonly = false,
}: RatingSliderProps) {
  const [value, setValue] = useState<number | null>(defaultValue)
  const [submitted, setSubmitted] = useState(false)
  const sliderRef = useRef<number | null>(value)

  const cfg = getConfig(value)

  const handlePick = useCallback(
    (v: number) => {
      if (readonly || submitted) return
      sliderRef.current = v
      setValue(v)
      onChange?.(v)
    },
    [readonly, submitted, onChange],
  )

  const handleSubmit = () => {
    if (!value) return
    setSubmitted(true)
    onSubmit?.(value)
  }

  // ── Tampilan setelah submit ────────────────────────────────────────────────
  if (submitted && cfg) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center gap-2 py-6 px-4 text-center"
      >
        <img
          src={cfg.image}
          alt={cfg.label}
          style={{ width: 48, height: 48, objectFit: 'contain' }}
        />
        <p className="text-[15px] font-medium text-gray-900 mt-1">
          Terima kasih atas penilaian Anda!
        </p>
        <p className="text-sm text-gray-400">
          Anda memberikan{' '}
          <span className="font-medium" style={{ color: cfg.color }}>
            {cfg.label}
          </span>{' '}
          ({value}/5)
        </p>
      </motion.div>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      {/* Header: label + pertanyaan + badge */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          {label && (
            <p className="text-[11px] font-medium uppercase tracking-wide text-gray-400 mb-1">
              {label}
            </p>
          )}
          {question && (
            <p className="text-[14px] font-medium text-gray-800 leading-snug">{question}</p>
          )}
        </div>

        {/* Score badge */}
        <AnimatePresence mode="wait">
          {value !== null && cfg ? (
            <motion.div
              key="badge"
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.85 }}
              transition={{ duration: 0.2 }}
              className="flex items-baseline gap-0.75 rounded-full px-3 py-1 border"
              style={{
                borderColor: cfg.color + '55',
                color: cfg.color,
                flexShrink: 0,
              }}
            >
              <motion.span
                key={value}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className="text-[18px] font-medium leading-none"
              >
                {value}
              </motion.span>
              <span className="text-[11px] text-gray-400">/5</span>
            </motion.div>
          ) : (
            <div className="w-13.5 h-7" />
          )}
        </AnimatePresence>
      </div>

      {/* Track + Nodes area */}
      <div className="relative" style={{ height: 90 }}>

        {/* Track line — z-index: 1 */}
        <div
          className="absolute left-6.5 right-6.5"
          style={{ top: 26, height: 4, background: '#DDDCD8', borderRadius: 2, zIndex: 1 }}
        >
          <motion.div
            animate={{ width: getTrackFillPercent(value) }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{
              height: '100%',
              borderRadius: 2,
              background: cfg?.color ?? '#DDDCD8',
              transition: 'background 0.3s',
            }}
          />
        </div>

        {/* Mantine Slider — drag layer, z-index: 15, di bawah emoji nodes */}
        {!readonly && (
          <div
            className="absolute"
            style={{
              top: 0,
              left: 0,
              right: 0,
              height: 56,
              zIndex: 15,
              pointerEvents: 'none', // container tidak block event emoji
            }}
          >
            <Slider
              min={1}
              max={5}
              step={1}
              value={value ?? 1}
              onChange={handlePick}
              style={{ position: 'absolute', left: 26, right: 26, top: 18 }}
              styles={{
                root: {
                  pointerEvents: 'all', // slider root tetap menerima drag
                  cursor: 'grab',
                },
                track: {
                  background: '#DDDCD8',
                  '&::before': { background: '#000' },
                },
                bar: { background: '#DDDCD8' },
                thumb: {
                  background: 'transparent',
                  border: 'none',
                  boxShadow: 'none',
                  width: 52,
                  height: 52,
                  cursor: 'grab',
                  '&:active': { cursor: 'grabbing' },
                },
              }}
            />
          </div>
        )}

        {/* Emoji nodes — z-index: 20, parent pointer-events: none agar drag tembus ke slider */}
        <div className="absolute inset-x-0 top-0 flex justify-between items-start pointer-events-none">
          {RATING_CONFIGS.map((r) => {
            const isActive = value === r.value
            return (
              <div
                key={r.value}
                className="flex flex-col items-center gap-1 bg-red-500"
                style={{
                  width: 70,
                  pointerEvents: 'auto', // tiap node tetap bisa diklik
                }}
                onClick={() => handlePick(r.value)}
              >
                <motion.div
                  animate={{
                    backgroundColor: isActive ? r.color : '#DDDCD8',
                    boxShadow: isActive
                      ? `0 0 0 4px ${r.glow}`
                      : '0 0 0 0px transparent',
                  }}
                  whileHover={!readonly && !isActive ? { scale: 1.1 } : {}}
                  transition={{ duration: 0.25 }}
                  className="flex items-center justify-center rounded-full cursor-pointer select-none overflow-hidden"
                  style={{ width: 70, height: 70, padding: 10 }}
                >
                  <AnimatePresence mode="wait">
                    {isActive ? (
                      <motion.img
                        key={`img-active-${r.value}`}
                        src={r.image}
                        alt={r.label}
                        initial={{ scale: 0.65, opacity: 0.6 }}
                        animate={{ scale: [0.65, 1.18, 0.94, 1.05, 1], opacity: 1 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                        style={{ width: '100%', height: '100%', objectFit: 'contain', filter: 'none' }}
                        draggable={false}
                      />
                    ) : (
                      <motion.img
                        key={`img-inactive-${r.value}`}
                        src={r.image}
                        alt={r.label}
                        loading="eager"
                        fetchPriority="high"
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'contain',
                          filter: 'grayscale(1) opacity(0.55)',
                        }}
                        draggable={false}
                      />
                    )}
                  </AnimatePresence>
                </motion.div>

                {/* Label */}
                <div style={{ height: 18, overflow: 'hidden' }}>
                  <AnimatePresence>
                    {isActive && (
                      <motion.span
                        key={`label-${r.value}`}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={{ duration: 0.25, ease: 'easeOut' }}
                        className="block text-center whitespace-nowrap"
                        style={{ fontSize: 11, fontWeight: 600, color: r.color, lineHeight: '18px' }}
                      >
                        {r.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            )
          })}
        </div>

      </div>

      {/* Submit button — hanya muncul jika onSubmit diberikan */}
      {!readonly && onSubmit && (
        <AnimatePresence>
          {value !== null && (
            <motion.div
              key="submit"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="flex justify-center mt-3"
            >
              <motion.button
                type="button"
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.97 }}
                onClick={handleSubmit}
                className="px-6 py-2 rounded-lg text-white text-sm font-medium border-0 outline-none cursor-pointer"
                style={{ background: cfg?.color ?? '#888', transition: 'background 0.3s' }}
              >
                Kirim Penilaian
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
      )}
    </div>
  )
}