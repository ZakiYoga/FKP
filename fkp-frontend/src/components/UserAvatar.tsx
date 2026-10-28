import { useState } from 'react'
import { getAvatarUrl } from '@/lib/avatar'
import type { UserMe } from '@/types'

type AvatarUser = Pick<UserMe, 'first_name' | 'last_name' | 'full_name' | 'avatar_path'>

// Satu sumber inisial untuk seluruh aplikasi (Profile, Sidebar, Navbar).
// Selalu 2 huruf bila memungkinkan:
// - 2 kata atau lebih  -> huruf pertama dari 2 kata pertama ("Budi Santoso" -> "BS")
// - 1 kata             -> 2 huruf pertama kata itu ("Budi" -> "BU")
export function getUserInitials(user?: Partial<AvatarUser> | null) {
  const source =
    [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim() ||
    user?.full_name?.trim() ||
    ''

  const words = source.split(/\s+/).filter(Boolean)
  if (words.length === 0) return '?'

  const initials =
    words.length >= 2 ? words[0][0] + words[1][0] : words[0].slice(0, 2)

  return initials.toUpperCase()
}

interface UserAvatarProps {
  user?: Partial<AvatarUser> | null
  /** Override sumber gambar, mis. object URL preview saat upload. */
  src?: string | null
  /** Ukuran dalam px (lebar = tinggi). */
  size?: number
  className?: string
}

// Menampilkan foto avatar jika ada; jika tidak ada atau gagal dimuat,
// menampilkan inisial.
export function UserAvatar({ user, src, size = 32, className = '' }: UserAvatarProps) {
  const url = src ?? (user?.avatar_path ? getAvatarUrl(user.avatar_path) : null)
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const showImage = Boolean(url) && url !== failedUrl

  return (
    <span
      style={{ width: size, height: size, fontSize: Math.round(size * 0.4) }}
      className={[
        'inline-flex shrink-0 select-none items-center justify-center overflow-hidden rounded-full bg-blue-500 font-semibold leading-none text-white',
        className,
      ].join(' ')}
    >
      {showImage ? (
        <img
          src={url ?? undefined}
          alt={user?.full_name ?? 'Avatar'}
          className="size-full object-cover"
          onError={() => setFailedUrl(url ?? null)}
        />
      ) : (
        getUserInitials(user)
      )}
    </span>
  )
}