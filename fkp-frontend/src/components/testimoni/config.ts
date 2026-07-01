export interface RatingConfig {
  value: number
  image: string
  label: string
  color: string
  glow: string
}

export const RATING_CONFIGS: RatingConfig[] = [
  {
    value: 1,
    image: '/assets/icons/1.webp',
    label: 'Sangat Buruk',
    color: '#E24B4A',
    glow: 'rgba(226,75,74,0.28)',
  },
  {
    value: 2,
    image: '/assets/icons/2.webp',
    label: 'Buruk',
    color: '#EF9F27',
    glow: 'rgba(239,159,39,0.28)',
  },
  {
    value: 3,
    image: '/assets/icons/3.webp',
    label: 'Cukup',
    color: '#F5C842',
    glow: 'rgba(245,200,66,0.32)',
  },
  {
    value: 4,
    image: '/assets/icons/4.webp',
    label: 'Baik',
    color: '#7BC557',
    glow: 'rgba(99,153,34,0.28)',
  },
  {
    value: 5,
    image: '/assets/icons/5.webp',
    label: 'Luar Biasa',
    color: '#1D9E75',
    glow: 'rgba(29,158,117,0.28)',
  },
]

export const getConfig = (value: number | null): RatingConfig | null => {
  if (value === null) return null
  return RATING_CONFIGS.find((r) => r.value === value) ?? null
}

export const getTrackFillPercent = (value: number | null): string => {
  if (!value) return '0%'
  return `${((value - 1) / 4) * 100}%`
}