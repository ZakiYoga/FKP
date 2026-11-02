import { useState } from 'react'
import type { ReactNode } from 'react'
import { ActionIcon, Paper, Text, Tooltip } from '@mantine/core'
import { Plus, X, Building2 } from 'lucide-react'
import {
  useUsersByRole,
  useHierarchyDistributors,
  useApsmAreas,
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
import { UserAvatar } from '@/components/UserAvatar'

const CAN_MANAGE = ['superadmin', 'admin_ho']

// ─── Bagian kecil yang dipakai berulang ─────────────────────────────────────

function NodeAction({
  label,
  onClick,
  color = 'gray',
  children,
}: {
  label: string
  onClick: () => void
  color?: string
  children: ReactNode
}) {
  return (
    <Tooltip label={label} withArrow position="top">
      <ActionIcon variant="subtle" color={color} size="sm" aria-label={label} onClick={onClick}>
        {children}
      </ActionIcon>
    </Tooltip>
  )
}

interface PersonNodeProps {
  nama: string
  email: string
  avatarPath?: string | null
  role: string
  /** Info tambahan di samping role, mis. "3 SC/SPV". */
  meta?: string
  avatarSize?: number
  actions?: ReactNode
  /** Konten di bawah identitas (mis. daftar distributor). */
  children?: ReactNode
}

function PersonNode({
  nama,
  email,
  avatarPath,
  role,
  meta,
  avatarSize = 40,
  actions,
  children,
}: PersonNodeProps) {
  return (
    <Paper withBorder radius="sm" p="sm" className="w-full">
      <div className="flex items-center gap-3">
        <UserAvatar user={{ full_name: nama, avatar_path: avatarPath }} size={avatarSize} />
        <div className="min-w-0 flex-1">
          <Text size="sm" fw={600} truncate>
            {nama}
          </Text>
          <Text size="xs" c="dimmed" truncate>
            {meta ? `${role} · ${meta}` : role}
          </Text>
          <Text size="xs" c="dimmed" truncate>
            {email}
          </Text>
        </div>
        {actions && <div className="flex shrink-0 items-center">{actions}</div>}
      </div>
      {children}
    </Paper>
  )
}

// ─── Halaman ────────────────────────────────────────────────────────────────

export function HierarchyPage() {
  const kodeRole = useKodeRole()
  const canManage = CAN_MANAGE.includes(kodeRole)

  const [selectedRsmId, setSelectedRsmId] = useState<string>('')
  const [modal, setModal] = useState<{
    type: 'rsm_apsm' | 'apsm_sc' | 'sc_dist'
    parentId: string
    parentName: string
    areaId?: string | null   // area SC/SPV, dipakai untuk 'sc_dist'
  } | null>(null)
  const [selectValue, setSelectValue] = useState('')
  const [areaValue, setAreaValue] = useState('')

  const { data: rsmList = [], isLoading: loadingUsers } = useUsersByRole('rsm')
  const { data: apsmList = [] } = useUsersByRole('apsm', { unassigned: true })
  const { data: scList = [] } = useUsersByRole('sc_spv', { unassigned: true })

  // Distributor hanya diambil saat modal 'sc_dist' terbuka, dan hanya di area SC/SPV tsb
  const { data: distributors = [], isLoading: loadingDists } = useHierarchyDistributors({
    unassigned: true,
    areaId: modal?.areaId ?? undefined,
    enabled: modal?.type === 'sc_dist' && !!modal.areaId,
  })

  // Area APSM hanya diambil saat modal 'apsm_sc' terbuka
  const { data: apsmAreas = [], isLoading: loadingAreas } = useApsmAreas(
    modal?.type === 'apsm_sc' ? modal.parentId : undefined,
  )

  // Jika APSM hanya punya 1 area, otomatis terpilih (tanpa useEffect)
  const effectiveArea = areaValue || (apsmAreas.length === 1 ? apsmAreas[0].id : '')

  const { data: team, isLoading: loadingTeam } = useRsmTeam(selectedRsmId || undefined)

  const { mutate: assignApsm } = useAssignApsmToRsm()
  const { mutate: assignSc } = useAssignScSpvToApsm()
  const { mutate: assignDist } = useAssignDistToScSpv()
  const { mutate: removeApsm } = useRemoveApsmFromRsm()
  const { mutate: removeSc } = useRemoveScSpvFromApsm()
  const { mutate: removeDist } = useRemoveDistFromScSpv()

  const closeModal = () => {
    setModal(null)
    setSelectValue('')
    setAreaValue('')
  }

  const handleAssign = () => {
    if (!modal || !selectValue) return
    if (modal.type === 'rsm_apsm') {
      assignApsm({ rsm_user_id: modal.parentId, apsm_user_id: selectValue }, { onSuccess: closeModal })
    } else if (modal.type === 'apsm_sc') {
      if (!effectiveArea) return
      assignSc(
        { apsm_user_id: modal.parentId, sc_spv_user_id: selectValue, area_id: effectiveArea },
        { onSuccess: closeModal },
      )
    } else {
      assignDist({ sc_spv_user_id: modal.parentId, distributor_id: selectValue }, { onSuccess: closeModal })
    }
  }

  const rsmOptions = rsmList.map((u) => ({ value: u.id, label: u.nama }))

  const areaOptions = apsmAreas.map((a) => ({ value: a.id, label: `[${a.kode_area}] ${a.nama_area}` }))

  const emptyMessage = (() => {
    if (!modal) return null
    if (modal.type === 'rsm_apsm') {
      return apsmList.length === 0 ? 'Semua APSM sudah memiliki RSM atasan.' : null
    }
    if (modal.type === 'apsm_sc') {
      if (loadingAreas) return null
      if (apsmAreas.length === 0) return 'APSM ini belum memegang area aktif. Atur PIC area terlebih dahulu.'
      return scList.length === 0 ? 'Semua SC/SPV sudah memiliki APSM atasan.' : null
    }
    if (!modal.areaId) return 'SC/SPV ini belum memiliki area. Hubungi admin untuk melengkapi data area.'
    if (loadingDists) return null
    return distributors.length === 0
      ? 'Tidak ada distributor aktif yang belum di-handle di area ini.'
      : null
  })()

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

  const apsmNodes = team?.apsm_list ?? []

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader title="Hierarki Tim" description="RSM → APSM → SC/SPV → Distributor" />

      {/* Pilih RSM */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Label membungkus select agar klik pada teks memfokuskan select */}
        <label className="flex flex-wrap items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Tampilkan tim RSM:</span>
          <FilterSelect
            value={selectedRsmId}
            onChange={setSelectedRsmId}
            placeholder="— Pilih RSM —"
            options={rsmOptions}
            className="min-w-55"
          />
        </label>
        {rsmList.length === 0 && <p className="text-sm text-amber-600">Belum ada user dengan role RSM.</p>}
      </div>

      {!selectedRsmId && rsmList.length > 0 && (
        <Text size="sm" c="dimmed">
          Pilih RSM untuk menampilkan peta hierarki timnya.
        </Text>
      )}

      {/* Peta hierarki. Lebar peta bisa melebihi layar, jadi digulir horizontal. */}
      {selectedRsmId &&
        (loadingTeam ? (
          <PageLoader />
        ) : team ? (
          <div className="overflow-x-auto pb-4">
            <div className="org-chart flex min-w-max flex-col items-center px-2">
              {/* RSM */}
              <div className="w-75">
                <PersonNode
                  nama={team.rsm.nama}
                  email={team.rsm.email}
                  avatarPath={team.rsm.avatar_path}
                  role="RSM"
                  meta={`${apsmNodes.length} APSM`}
                  actions={
                    canManage && (
                      <NodeAction
                        label="Tambah APSM"
                        onClick={() =>
                          setModal({ type: 'rsm_apsm', parentId: team.rsm.id, parentName: team.rsm.nama })
                        }
                      >
                        <Plus size={16} />
                      </NodeAction>
                    )
                  }
                />
              </div>

              {apsmNodes.length === 0 ? (
                <Text size="sm" c="dimmed" mt="md">
                  Belum ada APSM di bawah RSM ini.
                </Text>
              ) : (
                <ul className="org-children">
                  {apsmNodes.map((apsmNode) => {
                    const scNodes = apsmNode.sc_spv_list ?? []
                    return (
                      <li key={apsmNode.apsm.id} className="org-child">
                        <div className="w-75">
                          {/* APSM */}
                          <PersonNode
                            nama={apsmNode.apsm.nama}
                            email={apsmNode.apsm.email}
                            avatarPath={apsmNode.apsm.avatar_path}
                            role="APSM"
                            meta={`${scNodes.length} SC/SPV`}
                            actions={
                              canManage && (
                                <>
                                  <NodeAction
                                    label="Tambah SC/SPV"
                                    onClick={() =>
                                      setModal({
                                        type: 'apsm_sc',
                                        parentId: apsmNode.apsm.id,
                                        parentName: apsmNode.apsm.nama,
                                      })
                                    }
                                  >
                                    <Plus size={16} />
                                  </NodeAction>
                                  <NodeAction
                                    label="Lepas APSM dari RSM"
                                    color="red"
                                    onClick={() => removeApsm({ rsmId: team.rsm.id, apsmId: apsmNode.apsm.id })}
                                  >
                                    <X size={16} />
                                  </NodeAction>
                                </>
                              )
                            }
                          />

                          {/* SC/SPV */}
                          {scNodes.length === 0 ? (
                            <Text size="xs" c="dimmed" mt="sm" ml={20}>
                              Belum ada SC/SPV di bawah APSM ini.
                            </Text>
                          ) : (
                            <ul className="org-stack">
                              {scNodes.map((scNode) => {
                                const dists = scNode.distributors ?? []
                                return (
                                  <li key={scNode.sc_spv.id}>
                                    <PersonNode
                                      nama={scNode.sc_spv.nama}
                                      email={scNode.sc_spv.email}
                                      avatarPath={scNode.sc_spv.avatar_path}
                                      role="SC/SPV"
                                      meta={`${scNode.area?.nama_area ?? 'tanpa area'} · ${dists.length} distributor`}
                                      avatarSize={36}
                                      actions={
                                        canManage && (
                                          <>
                                            <NodeAction
                                              label="Assign distributor"
                                              onClick={() =>
                                                setModal({
                                                  type: 'sc_dist',
                                                  parentId: scNode.sc_spv.id,
                                                  parentName: scNode.sc_spv.nama,
                                                  areaId: scNode.area?.id ?? null,
                                                })
                                              }
                                            >
                                              <Plus size={16} />
                                            </NodeAction>
                                            <NodeAction
                                              label="Lepas SC/SPV dari APSM"
                                              color="red"
                                              onClick={() =>
                                                removeSc({ apsmId: apsmNode.apsm.id, scId: scNode.sc_spv.id })
                                              }
                                            >
                                              <X size={16} />
                                            </NodeAction>
                                          </>
                                        )
                                      }
                                    >
                                      {/* Distributor: daftar ringkas di dalam kartu SC/SPV */}
                                      <div className="mt-3 space-y-1">
                                        {dists.length === 0 ? (
                                          <Text size="xs" c="dimmed">
                                            Belum ada distributor.
                                          </Text>
                                        ) : (
                                          dists.map((dist) => (
                                            <div key={dist.id} className="flex items-center gap-2">
                                              <Building2 size={14} className="shrink-0 text-gray-400" />
                                              <Text size="xs" truncate className="min-w-0 flex-1">
                                                <span className="text-gray-500">[{dist.kode_distributor}]</span>{' '}
                                                {dist.nama_perusahaan}
                                                {dist.status !== 'aktif' && (
                                                  <span className="text-gray-400"> · {dist.status}</span>
                                                )}
                                              </Text>
                                              {canManage && (
                                                <NodeAction
                                                  label="Lepas distributor dari SC/SPV"
                                                  color="red"
                                                  onClick={() =>
                                                    removeDist({ scId: scNode.sc_spv.id, distId: dist.id })
                                                  }
                                                >
                                                  <X size={14} />
                                                </NodeAction>
                                              )}
                                            </div>
                                          ))
                                        )}
                                      </div>
                                    </PersonNode>
                                  </li>
                                )
                              })}
                            </ul>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        ) : null)}

      {/* Modal assign */}
      <Modal
        isOpen={!!modal}
        onClose={closeModal}
        title={
          modal?.type === 'rsm_apsm'
            ? `Tambah APSM ke ${modal.parentName}`
            : modal?.type === 'apsm_sc'
              ? `Tambah SC/SPV ke ${modal.parentName}`
              : `Assign Distributor ke ${modal?.parentName}`
        }
        size="sm"
      >
        <div className="space-y-4">
          {emptyMessage && (
            <Text size="sm" c="dimmed">
              {emptyMessage}
            </Text>
          )}

          {modal?.type === 'apsm_sc' && (
            <SearchableSelect
              label="Pilih Area"
              required
              value={effectiveArea || null}
              onChange={(v) => setAreaValue(v ?? '')}
              placeholder="Pilih area SC/SPV"
              options={areaOptions}
            />
          )}

          <SearchableSelect
            label={modalSelectLabel}
            required
            value={selectValue || null}
            onChange={(v) => setSelectValue(v ?? '')}
            placeholder="Cari atau pilih"
            options={modalOptions}
          />

          <div className="flex justify-end gap-2">
            <button onClick={closeModal} className="btn-secondary">
              Batal
            </button>
            <button
              onClick={handleAssign}
              disabled={!selectValue || (modal?.type === 'apsm_sc' && !effectiveArea)}
              className="btn-primary"
            >
              Assign
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}