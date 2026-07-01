import { Controller } from 'react-hook-form'
import { Star, Pencil, Loader2, MessageSquare, Users, Smartphone } from 'lucide-react'
import type { UseFormReturn } from 'react-hook-form'
import { RatingSliderField } from './RatingSliderField'
import type { TestimoniFormValues } from '@/schemas/testimoniSchema'

interface Props {
  form: UseFormReturn<TestimoniFormValues>
  nomorFkp: string
  isEditing: boolean
  isPending: boolean
  onCancel: () => void
  onSubmit: (values: TestimoniFormValues) => Promise<void>
}

export function TestimoniFormFields({
  form,
  nomorFkp,
  isEditing,
  isPending,
  onCancel,
  onSubmit,
}: Props) {
  const { control, register, handleSubmit, watch, formState: { errors } } = form

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-brand-500" />
              {isEditing ? 'Edit Testimoni' : 'Beri Testimoni'}
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Bantu kami meningkatkan layanan dengan penilaian Anda
            </p>
          </div>
          {isEditing && (
            <button onClick={onCancel} className="btn-ghost btn-sm text-xs text-gray-400">
              Batal
            </button>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="card-body space-y-6">

          {/* Bagian 1: Penanganan Keluhan */}
          <div>
            <div className="space-y-3">
              <Controller
                name="rating_keseluruhan"
                control={control}
                render={({ field }) => (
                  <RatingSliderField
                    label="Rating Keseluruhan"
                    question={`Seberapa puas Anda dengan penanganan FKP ${nomorFkp}?`}
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.rating_keseluruhan?.message}
                  />
                )}
              />
              <Controller
                name="rating_kecepatan"
                control={control}
                render={({ field }) => (
                  <RatingSliderField
                    label="Kecepatan Penanganan"
                    question="Seberapa cepat keluhan Anda ditangani?"
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.rating_kecepatan?.message}
                  />
                )}
              />
              <Controller
                name="rating_komunikasi"
                control={control}
                render={({ field }) => (
                  <RatingSliderField
                    label="Kualitas Komunikasi"
                    question="Apakah tim responsif dan informatif?"
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.rating_komunikasi?.message}
                  />
                )}
              />
              <Controller
                name="rating_solusi"
                control={control}
                render={({ field }) => (
                  <RatingSliderField
                    label="Kepuasan Solusi"
                    question="Apakah solusi yang diberikan memuaskan?"
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.rating_solusi?.message}
                  />
                )}
              />
            </div>

            <Controller
              name="rating_aplikasi"
              control={control}
              render={({ field }) => (
                <RatingSliderField
                  label="Rating Aplikasi"
                  question="Seberapa puas Anda menggunakan aplikasi FKP?"
                  value={field.value}
                  onChange={field.onChange}
                  error={errors.rating_aplikasi?.message}
                />
              )}
            />
            <TextareaField
              label="Kritik & Saran untuk Aplikasi"
              placeholder="Fitur apa yang perlu diperbaiki atau ditambahkan?"
              registration={register('kritik_saran_app')}
              error={errors.kritik_saran_app?.message}
              charCount={(watch('kritik_saran_app') ?? '').length}
              focusRing="focus:ring-violet-400"
            />

            <TextareaField
              label="Ulasan"
              placeholder="Bagikan pengalaman Anda secara keseluruhan..."
              registration={register('komentar')}
              error={errors.komentar?.message}
              charCount={(watch('komentar') ?? '').length}
            />
            <TextareaField
              label="Kritik & Saran untuk Tim"
              placeholder="Ada masukan spesifik untuk tim APSM, Admin HO, QC, atau RSM?"
              registration={register('kritik_saran_tim')}
              error={errors.kritik_saran_tim?.message}
              charCount={(watch('kritik_saran_tim') ?? '').length}
            />
          </div>

          {/* Visibilitas */}
          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              {...register('is_public')}
              className="w-4 h-4 rounded accent-brand-600"
            />
            <div>
              <p className="text-sm text-gray-700 group-hover:text-gray-900 transition-colors">
                Tampilkan testimoni ini secara internal
              </p>
              <p className="text-xs text-gray-400">
                Tim manajemen dapat melihat ulasan Anda untuk evaluasi layanan
              </p>
            </div>
          </label>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-100 px-6 py-4 flex items-center justify-end gap-3 bg-gray-50 rounded-b-xl">
          {isEditing && (
            <button
              type="button"
              onClick={onCancel}
              className="btn-secondary"
              disabled={isPending}
            >
              Batal
            </button>
          )}
          <button type="submit" disabled={isPending} className="btn-primary flex items-center gap-2">
            {isPending
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Menyimpan...</>
              : isEditing
                ? <><Pencil className="w-4 h-4" /> Simpan Perubahan</>
                : <><Star className="w-4 h-4" /> Kirim Testimoni</>
            }
          </button>
        </div>
      </form>
    </div>
  )
}

// ── Helper internal ────────────────────────────────────────────────────────────
function TextareaField({
  label,
  placeholder,
  registration,
  error,
  charCount,
  focusRing = 'focus:ring-brand-400',
}: {
  label: string
  placeholder: string
  registration: ReturnType<UseFormReturn<TestimoniFormValues>['register']>
  error?: string
  charCount: number
  focusRing?: string
}) {
  return (
    <div className="mt-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} <span className="text-gray-400 font-normal">(opsional)</span>
      </label>
      <textarea
        {...registration}
        rows={3}
        maxLength={1000}
        placeholder={placeholder}
        className={`w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm
                   placeholder:text-gray-300 focus:outline-none focus:ring-2
                   ${focusRing} focus:border-transparent resize-none transition-shadow`}
      />
      <div className="flex justify-between mt-1">
        {error ? <p className="text-xs text-red-500">{error}</p> : <span />}
        <p className="text-xs text-gray-300">{charCount}/1000</p>
      </div>
    </div>
  )
}