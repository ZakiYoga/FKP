export interface RatingSliderProps {
  /** Teks pertanyaan */
  question?: string
  /** Label di atas pertanyaan */
  label?: string
  /** Callback saat user klik tombol "Kirim" — jika tidak diberikan, tombol tidak muncul */
  onSubmit?: (value: number) => void
  /** Callback setiap kali nilai berubah (tanpa perlu tombol submit) */
  onChange?: (value: number) => void
  /** Nilai awal (untuk mode edit) */
  defaultValue?: number | null
  /** Readonly mode */
  readonly?: boolean
}