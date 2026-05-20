function CatatanItem({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
      <p className="text-xs font-semibold text-gray-500 mb-1">{label}</p>
      <p className="text-sm text-gray-800 whitespace-pre-wrap">{value}</p>
    </div>
  )
}

export default CatatanItem