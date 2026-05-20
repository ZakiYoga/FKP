function InfoRow({ label, value, className, mono }: {
  label: string
  value: string | number | null | undefined
  className?: string
  mono?: boolean
}) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-400">{label}</dt>
      <dd className={`text-sm text-gray-900 mt-0.5 ${mono ? 'font-mono' : ''} ${className ?? ''}`}>
        {value ?? '—'}
      </dd>
    </div>
  )
}

export default InfoRow