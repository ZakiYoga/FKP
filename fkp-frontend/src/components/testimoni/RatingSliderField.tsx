import { RatingSlider } from './RatingSlider'

interface RatingSliderFieldProps {
  label: string
  question: string
  value: number | undefined
  onChange: (v: number) => void
  error?: string
}

export function RatingSliderField({
  label,
  question,
  value,
  onChange,
  error,
}: RatingSliderFieldProps) {
  return (
    <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
      <RatingSlider
        label={label}
        question={question}
        defaultValue={value ?? null}
        onChange={onChange}
      />
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </div>
  )
}