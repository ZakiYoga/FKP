export const UUID_REGEX =
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export function isUuid(value: string): boolean {
    return UUID_REGEX.test(value.trim())
}

export function extractUuid(raw: string): string {
    const trimmed = raw.trim()
    const match = trimmed.match(
        /[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i,
    )
    return match ? match[0] : trimmed
}

export function formatDate(iso: string | null): string {
    if (!iso) return '-'
    return new Intl.DateTimeFormat('id-ID', {
        day: '2-digit', month: 'long', year: 'numeric',
    }).format(new Date(iso))
}