import { useId } from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
    KEMASAN_COLOR,
    KEMASAN_LABEL,
    KEMASAN_OPTIONS,
    normalisasiKemasan,
    type KemasanValue,
} from '@/lib/kemasan'

interface KemasanPickerProps {
    value: string[]
    onChange: (next: string[]) => void
    error?: string | undefined
    disabled?: boolean | undefined
    label?: string | undefined
}

export function KemasanPicker({
    value,
    onChange,
    error,
    disabled,
    label = 'Kemasan',
}: KemasanPickerProps) {
    const uid = useId()
    const hintId = `${uid}-hint`
    const errorId = `${uid}-error`
    const terpilih = new Set(value)

    const toggle = (k: KemasanValue) => {
        const next = new Set(terpilih)
        if (next.has(k)) next.delete(k)
        else next.add(k)
        // Selalu keluar sesuai urutan KEMASAN_OPTIONS, bukan urutan klik.
        onChange(normalisasiKemasan([...next]))
    }

    return (
        <fieldset disabled={disabled} className="w-full min-w-0 m-0 p-0 border-0">
            <legend className="label label-required">{label}</legend>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {KEMASAN_OPTIONS.map((k) => {
                    const checked = terpilih.has(k)
                    return (
                        <label
                            key={k}
                            className={cn(
                                'flex items-center justify-center gap-1.5 rounded-lg border px-3 py-2.5',
                                'text-sm font-medium select-none cursor-pointer transition-colors duration-150',
                                'has-focus-visible:ring-2 has-focus-visible:ring-brand-500/40 has-focus-visible:ring-offset-1',
                                checked
                                    ? KEMASAN_COLOR[k]
                                    : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100',
                                error && !checked && 'border-red-300',
                                disabled && 'opacity-60 cursor-not-allowed',
                            )}
                        >
                            <input
                                type="checkbox"
                                className="sr-only"
                                checked={checked}
                                onChange={() => toggle(k)}
                                aria-invalid={error ? true : undefined}
                                aria-describedby={error ? `${hintId} ${errorId}` : hintId}
                            />
                            <Check
                                aria-hidden="true"
                                className={cn(
                                    'w-4 h-4 shrink-0 transition-all duration-150',
                                    checked ? 'opacity-100 scale-100' : 'opacity-0 scale-50',
                                )}
                            />
                            <span>{KEMASAN_LABEL[k]}</span>
                        </label>
                    )
                })}
            </div>

            <p id={hintId} className="mt-1.5 text-xs text-gray-500">
                Pilih semua kemasan yang tersedia untuk SKU ini. Minimal satu.
            </p>
            {error && (
                <p id={errorId} role="alert" className="mt-1 text-xs text-red-600">
                    {error}
                </p>
            )}
        </fieldset>
    )
}