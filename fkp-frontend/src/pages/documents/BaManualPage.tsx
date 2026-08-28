import { useState } from 'react'
import { Flame, ClipboardCheck } from 'lucide-react'
import { PemusnahanTukarBarangTab } from '@/pages/documents/PemusnahanTukarBarangTab'
import { BapkpTab } from '@/pages/documents/BapkpTab'

type BaTabKey = 'pemusnahan' | 'bapkp'

const TABS: { key: BaTabKey; label: string; icon: typeof Flame }[] = [
  { key: 'pemusnahan', label: 'Pemusnahan & Tukar Barang', icon: Flame },
  { key: 'bapkp', label: 'Pemeriksaan Keluhan Pelanggan (QC)', icon: ClipboardCheck },
]

export function BaManualPage() {
  const [activeTab, setActiveTab] = useState<BaTabKey>('pemusnahan')

  return (
    <div className="mx-auto space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Buat Berita Acara</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Pilih jenis Berita Acara yang ingin diterbitkan
          </p>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2 border-b border-gray-200">
        {TABS.map((tab) => {
          const Icon = tab.icon
          const active = activeTab === tab.key
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${active
                  ? 'border-brand-500 text-brand-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Konten tab aktif */}
      {activeTab === 'pemusnahan' && <PemusnahanTukarBarangTab />}
      {activeTab === 'bapkp' && <BapkpTab />}
    </div>
  )
}