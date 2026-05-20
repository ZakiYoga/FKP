import { cn } from '@/lib/utils'

export function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin',
        className,
      )}
    />
  )
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[300px]">
      <div className="text-center space-y-3">
        <Spinner className="w-8 h-8 text-brand-500 mx-auto" />
        <p className="text-sm text-gray-400">Memuat data...</p>
      </div>
    </div>
  )
}
