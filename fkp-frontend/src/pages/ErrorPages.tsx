import { useNavigate } from 'react-router-dom'
import { Home, ArrowLeft } from 'lucide-react'

export function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <p className="text-8xl font-black text-gray-200 leading-none">404</p>
        <h1 className="text-2xl font-bold text-gray-900 mt-4">Halaman Tidak Ditemukan</h1>
        <p className="text-gray-500 mt-2">
          Halaman yang kamu cari tidak ada atau sudah dipindahkan.
        </p>
        <div className="flex items-center justify-center gap-3 mt-6">
          <button onClick={() => navigate(-1)} className="btn-secondary">
            <ArrowLeft className="w-4 h-4" /> Kembali
          </button>
          <button onClick={() => navigate('/dashboard')} className="btn-primary">
            <Home className="w-4 h-4" /> Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}

export function ForbiddenPage() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <p className="text-8xl font-black text-red-100 leading-none">403</p>
        <h1 className="text-2xl font-bold text-gray-900 mt-4">Akses Ditolak</h1>
        <p className="text-gray-500 mt-2">
          Kamu tidak memiliki izin untuk mengakses halaman ini.
        </p>
        <button onClick={() => navigate('/dashboard')} className="btn-primary mt-6">
          <Home className="w-4 h-4" /> Kembali ke Dashboard
        </button>
      </div>
    </div>
  )
}
