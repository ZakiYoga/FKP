// Samakan dengan AUTH_EMAIL_RESEND_COOLDOWN_SECONDS di backend (config.py).
// Backend diam-diam tidak mengirim ulang selama cooldown, jadi tombol
// tidak boleh aktif lebih cepat dari ini.
export const AUTH_EMAIL_RESEND_COOLDOWN_SECONDS = 60
