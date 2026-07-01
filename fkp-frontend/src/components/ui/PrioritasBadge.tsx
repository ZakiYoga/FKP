const PRIORITAS_MAP: Record<string, { label: string; cls: string }> = {
    top_urgent: { label: 'Top Urgent', cls: 'bg-red-100 text-red-700 border-red-200' },
    urgent:     { label: 'Urgent',     cls: 'bg-orange-100 text-orange-700 border-orange-200' },
    reguler:    { label: 'Reguler',    cls: 'bg-blue-100 text-blue-700 border-blue-200' },
    low:        { label: 'Low',        cls: 'bg-gray-100 text-gray-600 border-gray-200' },
}

export function PrioritasBadge({ prioritas }: { prioritas: string }) {
    const { label, cls } = PRIORITAS_MAP[prioritas] ?? {
        label: prioritas,
        cls: 'bg-gray-100 text-gray-600 border-gray-200',
    }
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
            {label}
        </span>
    )
}
