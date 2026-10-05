import { z } from 'zod'

export const registerOutletSchema = z
    .object({
        nama_toko: z.string().min(3, 'Nama toko minimal 3 karakter'),
        pemilik_toko: z.string().min(3, 'Nama pemilik minimal 3 karakter'),
        tipe_toko: z.enum([
            'retail_tradisional',
            'retail_modern',
            'grosir',
            'horeca',
            'umkm',
            'tobaku',
            'bakery',
            'catering',
            'reseller',
            'online_shop',
            'lainnya',
        ], { required_error: 'Pilih tipe toko' }),
        no_hp: z.string().min(1, 'No. HP wajib diisi')
            .pipe(
                z.string().regex(
                    /^628[1-9][0-9]{6,11}$/,
                    'Masukkan nomor HP/WhatsApp yang valid, tanpa angka 0 di depan (contoh: 81234567890).'
                )
            ),
        distributor_id: z.string().uuid('Pilih distributor terlebih dahulu'),
        alamat_lengkap: z.string().optional(),
        email: z.string().email('Format email tidak valid'),
        password: z.string().min(8, 'Password minimal 8 karakter'),
        retype_password: z.string(),
    })
    .refine((d) => d.password === d.retype_password, {
        message: 'Password tidak cocok',
        path: ['retype_password'],
    })

export type RegisterOutletFormValues = z.infer<typeof registerOutletSchema>