import { useState } from 'react'
import { Plus, X, GitBranch, Building2 } from 'lucide-react'
import {
  useUsersByRole,
  useHierarchyDistributors,
  useRsmTeam,
  useAssignApsmToRsm,
  useAssignScSpvToApsm,
  useAssignDistToScSpv,
  useRemoveApsmFromRsm,
  useRemoveScSpvFromApsm,
  useRemoveDistFromScSpv,
} from '@/hooks/useHierarchy'
import { Modal } from '@/components/ui/Modal'
import { FilterSelect } from '@/components/fkp/FilterSelect'
import { SearchableSelect } from '@/components/ui/SearchableSelect'
import { PageLoader } from '@/components/ui/Spinner'
import { useKodeRole } from '@/store/authStore'
import PageHeader from '@/components/ui/PageHeader'

const CAN_MANAGE = ['superadmin', 'admin_ho']

export function HierarchyPage() {
  const kodeRole = useKodeRole()
  const canManage = CAN_MANAGE.includes(kodeRole)

  const { data: rsmList = [], isLoading: loadingUsers } = useUsersByRole('rsm')
  const { data: apsmList = [] } = useUsersByRole('apsm')
  const { data: scList = [] } = useUsersByRole('sc_spv')
  const { data: distributors = [] } = useHierarchyDistributors()

  const [selectedRsmId, setSelectedRsmId] = useState<string>('')
  const [modal, setModal] = useState<{
    type: 'rsm_apsm' | 'apsm_sc' | 'sc_dist'
    parentId: string
    parentName: string
  } | null>(null)
  const [selectValue, setSelectValue] = useState('')

  const { data: team, isLoading: loadingTeam } = useRsmTeam(selectedRsmId || undefined)

  const { mutate: assignApsm } = useAssignApsmToRsm()
  const { mutate: assignSc } = useAssignScSpvToApsm()
  const { mutate: assignDist } = useAssignDistToScSpv()
  const { mutate: removeApsm } = useRemoveApsmFromRsm()
  const { mutate: removeSc } = useRemoveScSpvFromApsm()
  const { mutate: removeDist } = useRemoveDistFromScSpv()

  const handleAssign = () => {
    if (!modal || !selectValue) return
    if (modal.type === 'rsm_apsm') {
      assignApsm({ rsm_user_id: modal.parentId, apsm_user_id: selectValue },
        { onSuccess: () => { setModal(null); setSelectValue('') } })
    } else if (modal.type === 'apsm_sc') {
      assignSc({ apsm_user_id: modal.parentId, sc_spv_user_id: selectValue },
        { onSuccess: () => { setModal(null); setSelectValue('') } })
    } else {
      assignDist({ sc_spv_user_id: modal.parentId, distributor_id: selectValue },
        { onSuccess: () => { setModal(null); setSelectValue('') } })
    }
  }

  const rsmOptions = rsmList.map((u) => ({ value: u.id, label: u.nama }))

  // Opsi select di modal mengikuti tipe assign yang sedang dibuka
  const modalOptions =
    modal?.type === 'rsm_apsm'
      ? apsmList.map((u) => ({ value: u.id, label: `${u.nama} — ${u.email}` }))
      : modal?.type === 'apsm_sc'
        ? scList.map((u) => ({ value: u.id, label: `${u.nama} — ${u.email}` }))
        : modal?.type === 'sc_dist'
          ? distributors.map((d) => ({ value: d.id, label: `[${d.kode_distributor}] ${d.nama_perusahaan}` }))
          : []

  const modalSelectLabel =
    modal?.type === 'rsm_apsm' ? 'Pilih APSM' : modal?.type === 'apsm_sc' ? 'Pilih SC/SPV' : 'Pilih Distributor'

  if (loadingUsers) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <PageHeader title="Hierarki Tim" description="RSM → APSM → SC/SPV → Distributor" />

      {/* Pilih RSM */}
      <div className="card card-body">
        <div className="flex items-center gap-4 flex-wrap">
          {/* Label membungkus select agar klik pada teks memfokuskan select */}
          <label className="flex items-center gap-4 flex-wrap">
            <span className="text-sm font-medium text-gray-700">Tampilkan tim RSM:</span>
            <FilterSelect
              value={selectedRsmId}
              onChange={setSelectedRsmId}
              placeholder="— Pilih RSM —"
              options={rsmOptions}
              className="min-w-55"
            />
          </label>
          {rsmList.length === 0 && (
            <p className="text-sm text-amber-600">Belum ada user dengan role RSM.</p>
          )}
        </div>
      </div>

      {/* Tree hierarki */}
      {selectedRsmId && (
        loadingTeam ? <PageLoader /> : team ? (
          <div className="space-y-4">
            {/* RSM Node */}
            <div className="card p-4 border-l-4 border-brand-600">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-brand-100 flex items-center justify-center">
                    <span className="text-brand-700 font-bold text-sm">{team.rsm.nama.charAt(0)}</span>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{team.rsm.nama}</p>
                    <p className="text-xs text-gray-400">{team.rsm.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge bg-brand-100 text-brand-700">RSM</span>
                  {canManage && (
                    <button
                      onClick={() => setModal({ type: 'rsm_apsm', parentId: team.rsm.id, parentName: team.rsm.nama })}
                      className="btn-ghost btn-sm p-1.5 text-brand-600"
                      title="Tambah APSM"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* APSM list */}
            <div className="ml-6 space-y-3">
              {team.apsm_list?.map((apsmNode) => (
                <div key={apsmNode.apsm.id} className="space-y-3">
                  {/* APSM Node */}
                  <div className="card p-4 border-l-4 border-emerald-500">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                          <span className="text-emerald-700 font-bold text-xs">
                            {apsmNode.apsm.nama.charAt(0)}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 text-sm">{apsmNode.apsm.nama}</p>
                          <p className="text-xs text-gray-400">{apsmNode.apsm.email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="badge bg-emerald-100 text-emerald-700">APSM</span>
                        {canManage && (
                          <>
                            <button
                              onClick={() => setModal({ type: 'apsm_sc', parentId: apsmNode.apsm.id, parentName: apsmNode.apsm.nama })}
                              className="btn-ghost btn-sm p-1.5 text-emerald-600"
                              title="Tambah SC/SPV"
                            >
                              <Plus className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => removeApsm({ rsmId: team.rsm.id, apsmId: apsmNode.apsm.id })}
                              className="btn-ghost btn-sm p-1.5 text-red-500"
                              title="Lepas APSM dari RSM"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* SC/SPV list di bawah APSM ini */}
                  <div className="ml-6 space-y-3">
                    {(!apsmNode.sc_spv_list || apsmNode.sc_spv_list.length === 0) && (
                      <div className="card card-body text-center py-6 text-gray-400 text-xs">
                        Belum ada SC/SPV di bawah APSM ini.
                      </div>
                    )}
                    {apsmNode.sc_spv_list?.map((scNode) => (
                      <div key={scNode.sc_spv.id} className="space-y-3">
                        {/* SC/SPV Node */}
                        <div className="card p-3 border-l-4 border-amber-500">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center">
                                <span className="text-amber-700 font-bold text-xs">
                                  {scNode.sc_spv.nama.charAt(0)}
                                </span>
                              </div>
                              <div>
                                <p className="font-medium text-gray-900 text-sm">{scNode.sc_spv.nama}</p>
                                <p className="text-xs text-gray-400">{scNode.sc_spv.email}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="badge bg-amber-100 text-amber-700">SC/SPV</span>
                              {canManage && (
                                <>
                                  <button
                                    onClick={() => setModal({ type: 'sc_dist', parentId: scNode.sc_spv.id, parentName: scNode.sc_spv.nama })}
                                    className="btn-ghost btn-sm p-1.5 text-amber-600"
                                    title="Assign Distributor"
                                  >
                                    <Plus className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => removeSc({ apsmId: apsmNode.apsm.id, scId: scNode.sc_spv.id })}
                                    className="btn-ghost btn-sm p-1.5 text-red-500"
                                    title="Lepas SC/SPV dari APSM"
                                  >
                                    <X className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Distributor list di bawah SC/SPV ini */}
                        <div className="ml-6 space-y-2">
                          {(!scNode.distributors || scNode.distributors.length === 0) && (
                            <div className="card card-body text-center py-4 text-gray-400 text-xs">
                              Belum ada distributor untuk SC/SPV ini.
                            </div>
                          )}
                          {scNode.distributors?.map((dist) => (
                            <div
                              key={dist.id}
                              className="card p-3 flex items-center justify-between border-l-4 border-gray-300"
                            >
                              <div className="flex items-center gap-2">
                                <Building2 className="w-4 h-4 text-gray-400" />
                                <div>
                                  <p className="text-sm font-medium text-gray-800">
                                    [{dist.kode_distributor}] {dist.nama_perusahaan}
                                  </p>
                                  <p className="text-xs text-gray-400">{dist.status}</p>
                                </div>
                              </div>
                              {canManage && (
                                <button
                                  onClick={() => removeDist({ scId: scNode.sc_spv.id, distId: dist.id })}
                                  className="btn-ghost btn-sm p-1.5 text-red-500"
                                  title="Lepas Distributor dari SC/SPV"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {(!team.apsm_list || team.apsm_list.length === 0) && (
              <div className="ml-6 card card-body text-center py-8 text-gray-400 text-sm">
                Belum ada APSM di bawah RSM ini.
              </div>
            )}

          </div>
        ) : null
      )}

      {/* Modal assign */}
      <Modal
        isOpen={!!modal}
        onClose={() => { setModal(null); setSelectValue('') }}
        title={
          modal?.type === 'rsm_apsm' ? `Tambah APSM ke ${modal.parentName}` :
            modal?.type === 'apsm_sc' ? `Tambah SC/SPV ke ${modal.parentName}` :
              `Assign Distributor ke ${modal?.parentName}`
        }
        size="sm"
      >
        <div className="space-y-4">
          <SearchableSelect
            label={modalSelectLabel}
            required
            value={selectValue || null}
            onChange={(v) => setSelectValue(v ?? '')}
            placeholder="Cari atau pilih"
            options={modalOptions}
          />
          <div className="flex justify-end gap-2">
            <button onClick={() => { setModal(null); setSelectValue('') }} className="btn-secondary">Batal</button>
            <button onClick={handleAssign} disabled={!selectValue} className="btn-primary">Assign</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}