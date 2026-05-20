import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend,
} from 'recharts'
import { FileText, AlertCircle, CheckCircle2, Clock, ArrowRight, TrendingUp } from 'lucide-react'
import { useFkpList } from '@/hooks/useFkp'
import { computeStats } from '@/api/dashboard'
import { useCurrentUser, useKodeRole } from '@/store/authStore'
import { PageLoader } from '@/components/ui/Spinner'
import { StatusBadge, PriorittasBadge } from '@/components/ui/Badge'
import { formatRelative } from '@/lib/utils'
import { FKP_STATUS_LABEL, FKP_PRIORITAS_LABEL } from '@/types'
import type { FkpStatusKey, FkpPrioritas } from '@/types'

// ── Warna chart ──────────────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  draft:           '#94a3b8',
  submitted:       '#3b82f6',
  apsm_review:     '#8b5cf6',
  in_review:       '#f59e0b',
  need_revision:   '#ef4444',
  investigation:   '#f97316',
  investigated:    '#06b6d4',
  rsm_review:      '#8b5cf6',
  direktur_review: '#a855f7',
  accepted:        '#10b981',
  rejected:        '#ef4444',
  resolved:        '#22c55e',
  closed:          '#64748b',
}
const PRIORITAS_COLORS: Record<string, string> = {
  top_urgent: '#dc2626',
  urgent:     '#ea580c',
  reguler:    '#16a34a',
  low:        '#2563eb',
}
const KEMASAN_COLORS = ['#6366f1', '#06b6d4', '#f59e0b']

export function DashboardPage() {
  const user = useCurrentUser()
  const kodeRole = useKodeRole()
  const navigate = useNavigate()

  const { data: fkpList = [], isLoading } = useFkpList()

  const stats = useMemo(
    () => computeStats(fkpList, kodeRole),
    [fkpList, kodeRole],
  )

  // Data untuk chart status (bar)
  const statusChartData = Object.entries(stats.by_status)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: FKP_STATUS_LABEL[key as FkpStatusKey] ?? key,
      value,
      fill: STATUS_COLORS[key] ?? '#94a3b8',
    }))
    .sort((a, b) => b.value - a.value)

  // Data untuk pie chart prioritas
  const prioritasChartData = Object.entries(stats.by_prioritas)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: FKP_PRIORITAS_LABEL[key as FkpPrioritas]?.replace(/^.\s/, '') ?? key,
      value,
      fill: PRIORITAS_COLORS[key] ?? '#94a3b8',
    }))

  // Data kemasan pie
  const kemasanChartData = Object.entries(stats.by_kemasan)
    .filter(([, v]) => v > 0)
    .map(([key, value], i) => ({
      name: key.charAt(0).toUpperCase() + key.slice(1),
      value,
      fill: KEMASAN_COLORS[i % KEMASAN_COLORS.length],
    }))

  // Tren 7 hari
  const trenData = stats.tren_7_hari.map((d) => ({
    tanggal: new Date(d.tanggal).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' }),
    jumlah: d.jumlah,
  }))

  // FKP terbaru (5)
  const recentFkp = [...fkpList]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Welcome banner ─────────────────────────────────── */}
      <div className="rounded-2xl bg-gradient-to-r from-brand-700 to-brand-600 p-6 text-white">
        <p className="text-brand-200 text-sm font-medium">Selamat datang kembali 👋</p>
        <h1 className="text-2xl font-bold mt-1">{user?.nama}</h1>
        <div className="flex items-center gap-1.5 mt-2 bg-white/15 rounded-full px-3 py-1 w-fit text-xs font-semibold">
          {user?.role?.nama_role}
        </div>
      </div>

      {/* ── Stat cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total FKP"
          value={stats.total_fkp}
          icon={FileText}
          color="brand"
        />
        <StatCard
          label="Perlu Tindakan"
          value={stats.perlu_tindakan}
          icon={AlertCircle}
          color="amber"
          onClick={() => navigate('/fkp')}
        />
        <StatCard
          label="Selesai Bulan Ini"
          value={stats.selesai_bulan_ini}
          icon={CheckCircle2}
          color="green"
        />
        <StatCard
          label="FKP Aktif"
          value={fkpList.filter((f) =>
            !['closed', 'rejected'].includes(f.status)
          ).length}
          icon={Clock}
          color="blue"
        />
      </div>

      {/* ── Charts row 1 ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Bar chart status */}
        <div className="lg:col-span-2 card">
          <div className="card-header flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-500" />
            <h2 className="font-semibold text-gray-900">Distribusi Status FKP</h2>
          </div>
          <div className="card-body">
            {statusChartData.length === 0 ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={statusChartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    tickLine={false}
                    axisLine={false}
                    interval={0}
                    angle={0}
                    textAnchor="end"
                    height={50}
                  />
                  <YAxis 
                  tick={{ fontSize: 11, fill: '#94a3b8' }} 
                  tickLine={false} 
                  axisLine={false} 
                  allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: 12 }}
                    cursor={{ fill: '#f8fafc' }}
                  />
                  <Bar dataKey="value" name="Jumlah" radius={[4, 4, 0, 0]}>
                    {statusChartData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Pie chart prioritas */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-gray-900">Prioritas FKP</h2>
          </div>
          <div className="card-body flex flex-col items-center">
            {prioritasChartData.length === 0 ? (
              <EmptyChart />
            ) : (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie
                      data={prioritasChartData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      paddingAngle={3}
                    >
                      {prioritasChartData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-1.5 w-full mt-2">
                  {prioritasChartData.map((d) => (
                    <div key={d.name} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ background: d.fill }} />
                        <span className="text-gray-600">{d.name}</span>
                      </div>
                      <span className="font-semibold text-gray-900">{d.value}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Charts row 2 ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Line chart tren 7 hari */}
        <div className="lg:col-span-2 card">
          <div className="card-header">
            <h2 className="font-semibold text-gray-900">Tren FKP — 7 Hari Terakhir</h2>
          </div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={trenData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="tanggal" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: 12 }}
                />
                <Line
                  type="monotone"
                  dataKey="jumlah"
                  name="FKP Masuk"
                  stroke="#6366f1"
                  strokeWidth={2.5}
                  dot={{ fill: '#6366f1', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie kemasan */}
        <div className="card">
          <div className="card-header">
            <h2 className="font-semibold text-gray-900">Jenis Kemasan</h2>
          </div>
          <div className="card-body flex flex-col items-center">
            {kemasanChartData.length === 0 ? (
              <EmptyChart />
            ) : (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie
                      data={kemasanChartData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={70}
                      paddingAngle={3}
                    >
                      {kemasanChartData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', fontSize: 12 }}
                    />
                    <Legend
                      iconType="circle"
                      iconSize={8}
                      wrapperStyle={{ fontSize: 11, color: '#64748b' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── FKP terbaru ─────────────────────────────────────── */}
      {recentFkp.length > 0 && (
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">FKP Terbaru</h2>
            <button
              onClick={() => navigate('/fkp')}
              className="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
            >
              Lihat semua <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-50 bg-gray-50/50">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Nomor FKP</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Keluhan</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Prioritas</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Dibuat</th>
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recentFkp.map((fkp) => (
                  <tr
                    key={fkp.id}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/fkp/${fkp.id}`)}
                  >
                    <td className="px-5 py-3.5 font-mono text-xs text-gray-500">{fkp.nomor_fkp}</td>
                    <td className="px-5 py-3.5 text-gray-800 font-medium truncate max-w-[200px]">{fkp.jenis_keluhan}</td>
                    <td className="px-5 py-3.5"><PriorittasBadge prioritas={fkp.prioritas} /></td>
                    <td className="px-5 py-3.5"><StatusBadge status={fkp.status} /></td>
                    <td className="px-5 py-3.5 text-gray-400 text-xs">{formatRelative(fkp.created_at)}</td>
                    <td className="px-5 py-3.5">
                      <ArrowRight className="w-4 h-4 text-gray-300" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Sub-komponen ──────────────────────────────────────────────────────────────

const STAT_COLORS: Record<string, { bg: string; icon: string; text: string }> = {
  brand: { bg: 'bg-brand-50', icon: 'text-brand-600', text: 'text-brand-700' },
  amber: { bg: 'bg-amber-50', icon: 'text-amber-600', text: 'text-amber-700' },
  green: { bg: 'bg-emerald-50', icon: 'text-emerald-600', text: 'text-emerald-700' },
  blue:  { bg: 'bg-blue-50',  icon: 'text-blue-600',  text: 'text-blue-700' },
}

function StatCard({
  label, value, icon: Icon, color, onClick,
}: {
  label: string
  value: number
  icon: React.ElementType
  color: string
  onClick?: () => void
}) {
  const c = STAT_COLORS[color]
  return (
    <div
      onClick={onClick}
      className={`card p-5 ${onClick ? 'cursor-pointer hover:shadow-card-hover hover:-translate-y-0.5 transition-all' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500">{label}</p>
          <p className={`text-3xl font-bold mt-1 ${c.text}`}>{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-xl ${c.bg} flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${c.icon}`} />
        </div>
      </div>
    </div>
  )
}

function EmptyChart() {
  return (
    <div className="flex items-center justify-center h-32 text-gray-300 text-sm">
      Belum ada data
    </div>
  )
}
