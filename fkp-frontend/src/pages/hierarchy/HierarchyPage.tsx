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
import { Select } from '@/components/ui/Select'
import { PageLoader } from '@/components/ui/Spinner'
import { useKodeRole } from '@/store/authStore'

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

  if (loadingUsers) return <PageLoader />

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <GitBranch className="w-6 h-6 text-brand-600" /> Hierarki Tim Sales
        </h1>
        <p className="text-gray-500 text-sm mt-0.5">RSM → APSM → SC/SPV → Distributor</p>
      </div>

      {/* Pilih RSM */}
      <div className="card card-body">
        <div className="flex items-center gap-4 flex-wrap">
          <label className="text-sm font-medium text-gray-700">Tampilkan tim RSM:</label>
          <select
            value={selectedRsmId}
            onChange={(e) => setSelectedRsmId(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white
                       focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 min-w-[220px]"
          >
            <option value="">— Pilih RSM —</option>
            {rsmList.map((u) => <option key={u.id} value={u.id}>{u.nama}</option>)}
          </select>
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
            {team.apsm_list?.map((apsmNode: any) => (
              <div key={apsmNode.apsm.id} className="ml-6 space-y-3">
                <div className="card p-4 border-l-4 border-violet-500">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-violet-100 flex items-center justify-center">
                        <span className="text-violet-700 font-bold text-xs">{apsmNode.apsm.nama.charAt(0)}</span>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">{apsmNode.apsm.nama}</p>
                        <p className="text-xs text-gray-400">{apsmNode.apsm.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="badge bg-violet-100 text-violet-700">APSM</span>
                      {canManage && (
                        <>
                          <button
                            onClick={() => setModal({ type: 'apsm_sc', parentId: apsmNode.apsm.id, parentName: apsmNode.apsm.nama })}
                            className="btn-ghost btn-sm p-1.5 text-violet-600" title="Tambah SC/SPV">
                            <Plus className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => removeApsm({ rsmId: team.rsm.id, apsmId: apsmNode.apsm.id })}
                            className="btn-ghost btn-sm p-1.5 text-red-400 hover:text-red-600" title="Lepas dari RSM">
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* SC/SPV list */}
                {apsmNode.sc_spv_list?.map((scNode: any) => (
                  <div key={scNode.sc_spv.id} className="ml-6 space-y-2">
                    <div className="card p-4 border-l-4 border-emerald-500">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center">
                            <span className="text-emerald-700 font-bold text-xs">{scNode.sc_spv.nama.charAt(0)}</span>
                          </div>
                          <div>
                            <p className="font-semibold text-gray-900 text-sm">{scNode.sc_spv.nama}</p>
                            <p className="text-xs text-gray-400">{scNode.sc_spv.email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="badge bg-emerald-100 text-emerald-700 text-xs">SC/SPV</span>
                          {canManage && (
                            <>
                              <button
                                onClick={() => setModal({ type: 'sc_dist', parentId: scNode.sc_spv.id, parentName: scNode.sc_spv.nama })}
                                className="btn-ghost btn-sm p-1.5 text-emerald-600" title="Assign distributor">
                                <Plus className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => removeSc({ apsmId: apsmNode.apsm.id, scId: scNode.sc_spv.id })}
                                className="btn-ghost btn-sm p-1.5 text-red-400 hover:text-red-600" title="Lepas dari APSM">
                                <X className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Distributor list */}
                      {scNode.distributors?.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-50 flex flex-wrap gap-2">
                          {scNode.distributors.map((d: any) => (
                            <div key={d.id} className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1 text-xs">
                              <Building2 className="w-3 h-3 text-gray-400" />
                              <span className="text-gray-700">{d.nama_perusahaan}</span>
                              {canManage && (
                                <button
                                  onClick={() => removeDist({ scId: scNode.sc_spv.id, distId: d.id })}
                                  className="text-red-400 hover:text-red-600 ml-1">
                                  <X className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ))}

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
          <Select
            label={modal?.type === 'rsm_apsm' ? 'Pilih APSM' : modal?.type === 'apsm_sc' ? 'Pilih SC/SPV' : 'Pilih Distributor'}
            required
            value={selectValue}
            onChange={(e) => setSelectValue(e.target.value)}
            placeholder="— Pilih —"
          >
            {modal?.type === 'rsm_apsm' && apsmList.map((u) => <option key={u.id} value={u.id}>{u.nama} — {u.email}</option>)}
            {modal?.type === 'apsm_sc' && scList.map((u) => <option key={u.id} value={u.id}>{u.nama} — {u.email}</option>)}
            {modal?.type === 'sc_dist' && distributors.map((d) => <option key={d.id} value={d.id}>[{d.kode_distributor}] {d.nama_perusahaan}</option>)}
          </Select>
          <div className="flex justify-end gap-2">
            <button onClick={() => { setModal(null); setSelectValue('') }} className="btn-secondary">Batal</button>
            <button onClick={handleAssign} disabled={!selectValue} className="btn-primary">Assign</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
