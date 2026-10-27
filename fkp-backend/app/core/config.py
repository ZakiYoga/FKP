from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # App
    APP_NAME: str = "FKP SaktiFood"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = True
    # "development" / "local" memasang router Debug dan membuka /docs, /redoc,
    # /openapi.json; selain itu dianggap production (fail-closed). Di .env
    # production isi APP_ENV=production (atau jangan diisi) bersama DEBUG=False.
    APP_ENV: str = "production"

    # File storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10

    # Superadmin seeder
    SUPERADMIN_EMAIL: str
    SUPERADMIN_PASSWORD: str
    SUPERADMIN_NAMA: str

    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "FKP SaktiFood"
    SMTP_FROM_EMAIL: str = ""
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # Token auth (verifikasi email & reset password)
    VERIFY_EMAIL_TOKEN_EXPIRE_HOURS: int = 24
    RESET_PASSWORD_TOKEN_EXPIRE_MINUTES: int = 30
    # Jeda minimum antar pengiriman ulang email (per user). Frontend memakai
    # angka yang sama untuk hitung mundur tombol "Kirim ulang".
    AUTH_EMAIL_RESEND_COOLDOWN_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    @model_validator(mode="after")
    def _validasi_url_production(self):
        """
        Cegah tautan localhost ikut terkirim di email verifikasi/reset
        password saat aplikasi berjalan di production (DEBUG=False).
        """
        url = self.FRONTEND_BASE_URL.lower()
        if not self.DEBUG and ("localhost" in url or "127.0.0.1" in url):
            raise ValueError(
                "FRONTEND_BASE_URL tidak boleh localhost ketika DEBUG=False "
                "(tautan di email verifikasi/reset akan salah)."
            )
        return self

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()