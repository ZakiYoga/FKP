"""
Tipe Pydantic yang dipakai bersama oleh beberapa schema.
Diletakkan di modul netral supaya auth.py, user.py, dan outlet_register.py
tidak saling mengimpor.
"""
from typing import Annotated
from pydantic import AfterValidator, BeforeValidator, EmailStr


def _strip(v):
    return v.strip() if isinstance(v, str) else v


# Email yang otomatis di-strip lalu di-lowercase saat divalidasi.
# Urutan: strip -> validasi format EmailStr -> lowercase.
NormalizedEmail = Annotated[
    EmailStr,
    BeforeValidator(_strip),
    AfterValidator(lambda v: v.lower()),
]