import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  ActionIcon, Anchor, Badge, Button, Center, Group, Loader, Menu, Modal, NumberInput,
  Pagination, SimpleGrid, Stack, Table, Text, Textarea,
  TextInput, Tooltip,
} from '@mantine/core'
import { Download, MoreHorizontal, RefreshCw } from 'lucide-react'
// PageHeader adalah default export (sama seperti di FkpListPage).
import PageHeader from '@/components/ui/PageHeader'
import { FilterBar } from '@/components/ui/FilterBar'
import {
  usePendingSjFkp, useSuratJalanInbox, useSuratJalanInboxAction, useSuratJalanSummary,
  warehouseKeys,
} from '@/hooks/useWarehouse'
import { warehouseApi } from '@/api/warehouse'
import { openAuthenticatedFile } from '@/hooks/useAuthenticatedImage'
import { useAuthStore, useKodeRole } from '@/store/authStore'
import { SURAT_JALAN_STATUS_LABEL } from '@/types'
import type {
  PendingSjFkp, SuratJalanCreatePayload, SuratJalanInboxItem, SuratJalanShipPayload,
  SuratJalanStatusKey,
} from '@/types'

// ─── Konstanta ───────────────────────────────────────────────────────────────

const PAGE_SIZE = 20

// Gate aksi mengikuti SEED PERMISSION (bukan bisaKelolaSj di FkpDetailPage):
// create / issue / ship = warehouse.surat_jalan.{create,issue,ship} → warehouse saja (+ superadmin bypass)
// confirm-delivery = warehouse.surat_jalan.confirm_delivery → warehouse, admin_ho (+ superadmin)
const ROLE_BUAT_PROSES = ['warehouse', 'superadmin']
const ROLE_KONFIRMASI = ['warehouse', 'admin_ho', 'superadmin']

type TabKey = 'pending' | SuratJalanStatusKey | 'all'

type ModalState =
  | null
  | { kind: 'create'; fkp: PendingSjFkp }
  | { kind: 'issue'; sj: SuratJalanInboxItem }
  | { kind: 'ship'; sj: SuratJalanInboxItem }
  | { kind: 'confirm'; sj: SuratJalanInboxItem }
  | { kind: 'detail'; sj: SuratJalanInboxItem }

type ActionMutate = ReturnType<typeof useSuratJalanInboxAction>['mutate']

// ─── Helper ──────────────────────────────────────────────────────────────────

function todayLocal(): string {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

// 'YYYY-MM-DD' dipecah manual (new Date() menganggapnya UTC → bisa geser hari di zona WIB).
function fmtTanggal(value: string | null | undefined): string {
  if (!value) return '-'
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [y, m, d] = value.split('-')
    return `${d}/${m}/${y}`
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('id-ID')
}

function statusBadge(status: SuratJalanStatusKey) {
  return (
    <Badge variant="light" radius="sm" color={status === 'delivered' ? 'green' : 'gray'}>
      {SURAT_JALAN_STATUS_LABEL[status]}
    </Badge>
  )
}

function orDash(value: ReactNode): ReactNode {
  return value === null || value === undefined || value === '' ? '-' : value
}

// ─── Halaman ─────────────────────────────────────────────────────────────────

export function SuratJalanPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const kodeRole = useKodeRole()
  const token = useAuthStore((s) => s.token)

  const canBuatProses = ROLE_BUAT_PROSES.includes(kodeRole)
  const canKonfirmasi = ROLE_KONFIRMASI.includes(kodeRole)

  const defaultTab: TabKey = canBuatProses ? 'pending' : 'all'
  const [tab, setTab] = useState<TabKey>(defaultTab)
  const [search, setSearch] = useState('')
  const [dari, setDari] = useState('')
  const [sampai, setSampai] = useState('')
  const [modal, setModal] = useState<ModalState>(null)
  // Debounce sudah ditangani FilterBar (300 ms), jadi `search` langsung dipakai sebagai kata kunci.
  const keyword = search.trim()

  const isPendingTab = tab === 'pending'
  const rangeInvalid = !isPendingTab && !!dari && !!sampai && dari > sampai

  // Halaman kembali ke 1 otomatis saat tab / pencarian / tanggal berubah:
  // nomor halaman disimpan bersama kunci filternya, tanpa useEffect.
  const filterKey = `${tab}|${keyword}|${dari}|${sampai}`
  const [pageState, setPageState] = useState({ key: filterKey, page: 1 })
  const page = pageState.key === filterKey ? pageState.page : 1
  const setPage = (p: number) => setPageState({ key: filterKey, page: p })

  const summaryQ = useSuratJalanSummary()
  const pendingQ = usePendingSjFkp(
    { page, page_size: PAGE_SIZE, search: keyword || undefined },
    isPendingTab,
  )
  const inboxQ = useSuratJalanInbox(
    {
      page,
      page_size: PAGE_SIZE,
      status: tab === 'all' || tab === 'pending' ? undefined : tab,
      search: keyword || undefined,
      tanggal_dari: dari || undefined,
      tanggal_sampai: sampai || undefined,
    },
    !isPendingTab && !rangeInvalid,
  )

  const action = useSuratJalanInboxAction()
  const busySjId =
    action.isPending && action.variables && 'sjId' in action.variables
      ? action.variables.sjId
      : null

  const pageData = isPendingTab ? pendingQ.data : inboxQ.data
  const isLoading = isPendingTab ? pendingQ.isLoading : inboxQ.isLoading
  const isError = isPendingTab ? pendingQ.isError : inboxQ.isError
  const isPlaceholder = isPendingTab ? pendingQ.isPlaceholderData : inboxQ.isPlaceholderData
  const isFetching = summaryQ.isFetching || pendingQ.isFetching || inboxQ.isFetching

  const refetchActive = () => {
    if (isPendingTab) void pendingQ.refetch()
    else void inboxQ.refetch()
  }
  const refreshAll = () => {
    void qc.invalidateQueries({ queryKey: warehouseKeys.all })
  }

  // Dipanggil FilterBar setelah search dikosongkan. Karena memakai onReset, semua field
  // (status/tab dan tanggal) harus dikembalikan di sini, termasuk tanggal yang sedang tersembunyi.
  const resetFilter = () => {
    setTab(defaultTab)
    setDari('')
    setSampai('')
  }

  const summary = summaryQ.data
  const withCount = (label: string, n: number | undefined) =>
    n === undefined ? label : `${label} (${n})`
  const tabData = [
    { value: 'pending', label: withCount('Perlu Dibuat', summary?.perlu_dibuat) },
    { value: 'draft', label: withCount('Draft', summary?.counts.draft) },
    { value: 'issued', label: withCount('Diterbitkan', summary?.counts.issued) },
    { value: 'shipped', label: withCount('Dikirim', summary?.counts.shipped) },
    { value: 'delivered', label: withCount('Diterima', summary?.counts.delivered) },
    { value: 'all', label: withCount('Semua', summary?.total) },
  ]

  const closeModal = () => setModal(null)
  const openPdf = (sj: SuratJalanInboxItem) =>
    void openAuthenticatedFile(warehouseApi.pdfPath(sj.fkp_id, sj.id), token)

  // ── Tombol aksi utama per baris SJ ────────────────────────────────────────
  const renderSjAction = (sj: SuratJalanInboxItem) => {
    const loading = busySjId === sj.id
    if (sj.status === 'draft' && canBuatProses) {
      return (
        <Button size="compact-sm" radius="sm" loading={loading}
          onClick={() => setModal({ kind: 'issue', sj })}>
          Terbitkan
        </Button>
      )
    }
    if (sj.status === 'issued' && canBuatProses) {
      return (
        <Button size="compact-sm" radius="sm" loading={loading}
          onClick={() => setModal({ kind: 'ship', sj })}>
          Tandai Dikirim
        </Button>
      )
    }
    if (sj.status === 'shipped' && canKonfirmasi) {
      return (
        <Button size="compact-sm" radius="sm" loading={loading}
          onClick={() => setModal({ kind: 'confirm', sj })}>
          Konfirmasi Diterima
        </Button>
      )
    }
    return null
  }

  // ── Tabel antrean "Perlu Dibuat" ──────────────────────────────────────────
  const renderPendingTable = (rows: PendingSjFkp[]) => (
    <Table.ScrollContainer minWidth={900}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>No. FKP</Table.Th>
            <Table.Th>Asal</Table.Th>
            <Table.Th>Diteruskan</Table.Th>
            <Table.Th>Item yang perlu dikirim</Table.Th>
            <Table.Th>Aksi</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((fkp) => (
            <Table.Tr key={fkp.fkp_id}>
              <Table.Td>
                <Anchor component="button" type="button" size="sm" ff="monospace"
                  onClick={() => navigate(`/fkp/${fkp.fkp_id}`)}>
                  {fkp.nomor_fkp}
                </Anchor>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{orDash(fkp.distributor_nama)}</Text>
                {fkp.outlet_nama && <Text size="xs" c="dimmed">{fkp.outlet_nama}</Text>}
              </Table.Td>
              <Table.Td>
                <Text size="sm">{fmtTanggal(fkp.tanggal_diteruskan_ke_warehouse)}</Text>
                {fkp.jumlah_sj_terbit > 0 && (
                  <Text size="xs" c="dimmed">{fkp.jumlah_sj_terbit} SJ sudah dibuat</Text>
                )}
              </Table.Td>
              <Table.Td>
                <Stack gap={2}>
                  {fkp.items.map((it) => (
                    <Text key={it.fkp_item_id} size="sm">
                      {it.nama_produk} — sisa {it.sisa_kuota} {it.satuan_default} dari {it.qty_disetujui}
                    </Text>
                  ))}
                </Stack>
              </Table.Td>
              <Table.Td>
                <Group gap="xs" wrap="nowrap">
                  {canBuatProses && (
                    <Button size="compact-sm" radius="sm"
                      onClick={() => setModal({ kind: 'create', fkp })}>
                      Buat Surat Jalan
                    </Button>
                  )}
                  <Menu position="bottom-end" radius="sm" withinPortal>
                    <Menu.Target>
                      <ActionIcon variant="subtle" color="gray" aria-label="Menu lainnya">
                        <MoreHorizontal size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item onClick={() => navigate(`/fkp/${fkp.fkp_id}`)}>Buka FKP</Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )

  // ── Tabel surat jalan ─────────────────────────────────────────────────────
  const renderSjTable = (rows: SuratJalanInboxItem[]) => (
    <Table.ScrollContainer minWidth={1000}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>No. SJ</Table.Th>
            <Table.Th>FKP</Table.Th>
            <Table.Th>Penerima</Table.Th>
            <Table.Th>Item</Table.Th>
            <Table.Th>Pengiriman</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Aksi</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((sj) => (
            <Table.Tr key={sj.id}>
              <Table.Td>
                <Text size="sm" ff="monospace">{sj.nomor_surat_jalan}</Text>
                <Text size="xs" c="dimmed">{fmtTanggal(sj.tanggal_surat_jalan)}</Text>
              </Table.Td>
              <Table.Td>
                <Anchor component="button" type="button" size="sm" ff="monospace"
                  onClick={() => navigate(`/fkp/${sj.fkp_id}`)}>
                  {sj.nomor_fkp}
                </Anchor>
                <Text size="xs" c="dimmed">
                  {[sj.distributor_nama, sj.outlet_nama].filter(Boolean).join(' / ') || '-'}
                </Text>
              </Table.Td>
              <Table.Td><Text size="sm">{sj.nama_penerima}</Text></Table.Td>
              <Table.Td>
                <Tooltip withArrow multiline w={260} radius="sm" label={
                  <Stack gap={2}>
                    {sj.items.map((it) => (
                      <Text key={it.id} size="xs">{it.nama_produk} — {it.qty} {it.satuan}</Text>
                    ))}
                  </Stack>
                }>
                  <Text size="sm">{sj.jumlah_item} item · {sj.total_qty} qty</Text>
                </Tooltip>
              </Table.Td>
              <Table.Td>
                <Text size="sm">
                  {[sj.ekspedisi, sj.nomor_resi].filter(Boolean).join(' · ') || '-'}
                </Text>
                {sj.tanggal_kirim && (
                  <Text size="xs" c="dimmed">Kirim {fmtTanggal(sj.tanggal_kirim)}</Text>
                )}
              </Table.Td>
              <Table.Td>{statusBadge(sj.status)}</Table.Td>
              <Table.Td>
                <Group gap="xs" wrap="nowrap">
                  {renderSjAction(sj)}
                  {sj.url_pdf ? (
                    <ActionIcon variant="subtle" color="gray" aria-label="Unduh PDF"
                      onClick={() => openPdf(sj)}>
                      <Download size={16} />
                    </ActionIcon>
                  ) : (
                    <Tooltip label="PDF tersedia setelah surat jalan diterbitkan" withArrow radius="sm">
                      <ActionIcon variant="subtle" color="gray" aria-label="Unduh PDF" disabled>
                        <Download size={16} />
                      </ActionIcon>
                    </Tooltip>
                  )}
                  <Menu position="bottom-end" radius="sm" withinPortal>
                    <Menu.Target>
                      <ActionIcon variant="subtle" color="gray" aria-label="Menu lainnya">
                        <MoreHorizontal size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item onClick={() => setModal({ kind: 'detail', sj })}>Detail</Menu.Item>
                      <Menu.Item onClick={() => navigate(`/fkp/${sj.fkp_id}`)}>Buka FKP</Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  )

  // ── Isi utama (loading / error / kosong / tabel) ──────────────────────────
  const renderBody = () => {
    if (rangeInvalid) {
      return <Text c="dimmed" ta="center" py="xl">Rentang tanggal tidak valid.</Text>
    }
    if (isLoading) {
      return <Center py="xl"><Loader size="sm" /></Center>
    }
    if (isError) {
      return (
        <Center py="xl">
          <Stack align="center" gap="xs">
            <Text c="red" size="sm">Gagal memuat data.</Text>
            <Button variant="default" radius="sm" size="compact-sm" onClick={refetchActive}>
              Coba Lagi
            </Button>
          </Stack>
        </Center>
      )
    }
    if (!pageData || pageData.items.length === 0) {
      return (
        <Text c="dimmed" ta="center" py="xl">
          {isPendingTab
            ? 'Tidak ada FKP yang menunggu dibuatkan surat jalan.'
            : 'Tidak ada surat jalan pada filter ini.'}
        </Text>
      )
    }
    return (
      <div style={{ opacity: isPlaceholder ? 0.6 : 1 }}>
        {isPendingTab
          ? renderPendingTable(pendingQ.data?.items ?? [])
          : renderSjTable(inboxQ.data?.items ?? [])}
      </div>
    )
  }

  const showPagination = !rangeInvalid && !!pageData && pageData.total > 0
  const from = pageData ? (pageData.page - 1) * pageData.page_size + 1 : 0
  const to = pageData ? Math.min(pageData.page * pageData.page_size, pageData.total) : 0

  return (
    <Stack gap="md">
      <PageHeader
        title="Surat Jalan"
        description="Buat, pantau, dan unduh surat jalan barang pengganti"
        actions={
          <Button variant="default" radius="sm" leftSection={<RefreshCw size={14} />}
            loading={isFetching} onClick={refreshAll}>
            Muat Ulang
          </Button>
        }
      />

      <FilterBar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder={isPendingTab
          ? 'Cari no. FKP, distributor, toko...'
          : 'Cari no. SJ, no. FKP, penerima, resi...'}
        fields={[
          {
            // Pengganti tab: nilai bawaan tidak dihitung sebagai filter aktif
            key: 'tab',
            type: 'select',
            label: 'Status',
            value: tab,
            defaultValue: defaultTab,
            onChange: (v) => setTab((v || defaultTab) as TabKey),
            options: tabData,
            placeholder: 'Pilih status',
          },
          {
            // Tab "Perlu Dibuat" tidak memakai filter tanggal, jadi field ini disembunyikan
            key: 'tanggal',
            type: 'date-range',
            hidden: isPendingTab,
            from: dari,
            to: sampai,
            onFromChange: setDari,
            onToChange: setSampai,
            fromLabel: 'Tanggal SJ dari',
            toLabel: 'Tanggal SJ sampai',
          },
        ]}
        onReset={resetFilter}
      />

      {renderBody()}

      {showPagination && pageData && (
        <Group justify="space-between">
          <Text size="xs" c="dimmed">Menampilkan {from}–{to} dari {pageData.total}</Text>
          {pageData.total_pages > 1 && (
            <Pagination size="sm" radius="sm" total={pageData.total_pages} value={page}
              onChange={setPage} />
          )}
        </Group>
      )}

      {modal?.kind === 'create' && (
        <CreateSjModal key={modal.fkp.fkp_id} fkp={modal.fkp} onClose={closeModal}
          mutate={action.mutate} isPending={action.isPending} />
      )}
      {modal?.kind === 'ship' && (
        <ShipSjModal key={modal.sj.id} sj={modal.sj} onClose={closeModal}
          mutate={action.mutate} isPending={action.isPending} />
      )}
      {modal?.kind === 'issue' && (
        <ConfirmModal
          title="Terbitkan Surat Jalan"
          message={`Surat jalan ${modal.sj.nomor_surat_jalan} akan diterbitkan dan PDF dibuat. Data tidak bisa diubah lagi setelah ini.`}
          confirmLabel="Terbitkan"
          isPending={action.isPending}
          onClose={closeModal}
          onConfirm={() => action.mutate(
            { kind: 'issue', fkpId: modal.sj.fkp_id, sjId: modal.sj.id },
            { onSuccess: closeModal },
          )}
        />
      )}
      {modal?.kind === 'confirm' && (
        <ConfirmModal
          title="Konfirmasi Diterima"
          message={`Konfirmasi barang pengganti pada surat jalan ${modal.sj.nomor_surat_jalan} sudah diterima penerima?`}
          confirmLabel="Lanjut"
          isPending={action.isPending}
          onClose={closeModal}
          onConfirm={() => action.mutate(
            { kind: 'confirm_delivery', fkpId: modal.sj.fkp_id, sjId: modal.sj.id },
            { onSuccess: closeModal },
          )}
        />
      )}
      {modal?.kind === 'detail' && (
        <DetailModal sj={modal.sj} onClose={closeModal}
          onPdf={() => openPdf(modal.sj)}
          onOpenFkp={() => navigate(`/fkp/${modal.sj.fkp_id}`)} />
      )}
    </Stack>
  )
}

// ─── Modal: Buat Surat Jalan ─────────────────────────────────────────────────

interface CreateForm {
  nomor_surat_jalan: string
  tanggal_surat_jalan: string
  nama_penerima: string
  alamat_penerima: string
  telepon_penerima: string
  ekspedisi: string
  nomor_resi: string
  tanggal_kirim: string
  catatan: string
}

function CreateSjModal({ fkp, onClose, mutate, isPending }: {
  fkp: PendingSjFkp
  onClose: () => void
  mutate: ActionMutate
  isPending: boolean
}) {
  // Qty default = sisa kuota; nilai 0 berarti item tidak dikirim di SJ ini.
  const [qty, setQty] = useState<Record<string, number | string>>(() =>
    Object.fromEntries(fkp.items.map((it) => [it.fkp_item_id, it.sisa_kuota])),
  )
  const [form, setForm] = useState<CreateForm>({
    nomor_surat_jalan: '',
    tanggal_surat_jalan: todayLocal(),
    nama_penerima: fkp.penerima_default.nama ?? '',
    alamat_penerima: fkp.penerima_default.alamat ?? '',
    telepon_penerima: fkp.penerima_default.telepon ?? '',
    ekspedisi: '',
    nomor_resi: '',
    tanggal_kirim: '',
    catatan: '',
  })

  const bind = (key: keyof CreateForm) => ({
    value: form[key],
    onChange: (e: { currentTarget: { value: string } }) => {
      const value = e.currentTarget.value
      setForm((prev) => ({ ...prev, [key]: value }))
    },
  })

  const qtyOf = (id: string): number => {
    const v = qty[id]
    return typeof v === 'number' ? v : Number(v) || 0
  }
  const selected = fkp.items.filter((it) => qtyOf(it.fkp_item_id) > 0)
  const overLimit = fkp.items.some((it) => qtyOf(it.fkp_item_id) > it.sisa_kuota)
  const wajibKosong = [
    form.nomor_surat_jalan, form.tanggal_surat_jalan, form.nama_penerima,
    form.alamat_penerima, form.telepon_penerima, form.ekspedisi,
  ].some((v) => v.trim() === '')
  const disabled = wajibKosong || selected.length === 0 || overLimit

  const submit = () => {
    const data: SuratJalanCreatePayload = {
      nomor_surat_jalan: form.nomor_surat_jalan.trim(),
      tanggal_surat_jalan: form.tanggal_surat_jalan,
      nama_penerima: form.nama_penerima.trim(),
      alamat_penerima: form.alamat_penerima.trim(),
      telepon_penerima: form.telepon_penerima.trim(),
      ekspedisi: form.ekspedisi.trim(),
      nomor_resi: form.nomor_resi.trim() || null,
      tanggal_kirim: form.tanggal_kirim || null,
      catatan: form.catatan.trim() || null,
      items: selected.map((it) => ({
        fkp_item_id: it.fkp_item_id,
        nama_produk: it.nama_produk,
        qty: qtyOf(it.fkp_item_id),
        satuan: it.satuan_default,
      })),
    }
    mutate({ kind: 'create', fkpId: fkp.fkp_id, data }, { onSuccess: onClose })
  }

  return (
    <Modal opened onClose={onClose} centered radius="sm" size="lg" title="Buat Surat Jalan">
      <Stack gap="md">
        <Text size="sm">
          FKP <Text span ff="monospace" fw={500}>{fkp.nomor_fkp}</Text>
          {' — '}{[fkp.distributor_nama, fkp.outlet_nama].filter(Boolean).join(' / ') || '-'}
        </Text>

        <Stack gap="xs">
          <Text size="sm" fw={500}>Qty yang dikirim di SJ ini</Text>
          {fkp.items.map((it) => (
            <NumberInput
              key={it.fkp_item_id}
              radius="sm"
              label={it.nama_produk}
              description={`Sisa kuota ${it.sisa_kuota} dari ${it.qty_disetujui} disetujui`}
              min={0}
              max={it.sisa_kuota}
              allowDecimal={false}
              allowNegative={false}
              clampBehavior="strict"
              suffix={` ${it.satuan_default}`}
              value={qty[it.fkp_item_id]}
              onChange={(v) => setQty((prev) => ({ ...prev, [it.fkp_item_id]: v }))}
            />
          ))}
        </Stack>

        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput radius="sm" label="Nomor SJ" required {...bind('nomor_surat_jalan')} />
          <TextInput radius="sm" type="date" label="Tanggal SJ" required {...bind('tanggal_surat_jalan')} />
        </SimpleGrid>
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput radius="sm" label="Nama Penerima" required {...bind('nama_penerima')} />
          <TextInput radius="sm" label="Telepon Penerima" required {...bind('telepon_penerima')} />
        </SimpleGrid>
        <Textarea radius="sm" label="Alamat Penerima" required autosize minRows={2}
          {...bind('alamat_penerima')} />
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput radius="sm" label="Ekspedisi" required {...bind('ekspedisi')} />
          <TextInput radius="sm" label="No. Resi" {...bind('nomor_resi')} />
        </SimpleGrid>
        <TextInput radius="sm" type="date" label="Tanggal Kirim" {...bind('tanggal_kirim')} />
        <Textarea radius="sm" label="Catatan" autosize minRows={2} {...bind('catatan')} />

        <Text size="xs" c="dimmed">SJ pertama otomatis memindahkan FKP ke status Diproses.</Text>

        <Group justify="flex-end">
          <Button variant="default" radius="sm" onClick={onClose} disabled={isPending}>Batal</Button>
          <Button radius="sm" loading={isPending} disabled={disabled} onClick={submit}>
            Buat Surat Jalan
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}

// ─── Modal: Tandai Dikirim ───────────────────────────────────────────────────

function ShipSjModal({ sj, onClose, mutate, isPending }: {
  sj: SuratJalanInboxItem
  onClose: () => void
  mutate: ActionMutate
  isPending: boolean
}) {
  const [ekspedisi, setEkspedisi] = useState(sj.ekspedisi ?? '')
  const [resi, setResi] = useState(sj.nomor_resi ?? '')
  const [tanggal, setTanggal] = useState(sj.tanggal_kirim ?? '')

  const submit = () => {
    const data: SuratJalanShipPayload = {
      ekspedisi: ekspedisi.trim() || null,
      nomor_resi: resi.trim() || null,
      tanggal_kirim: tanggal || null,
    }
    mutate({ kind: 'ship', fkpId: sj.fkp_id, sjId: sj.id, data }, { onSuccess: onClose })
  }

  return (
    <Modal opened onClose={onClose} centered radius="sm" title="Tandai Dikirim">
      <Stack gap="md">
        <Text size="sm">
          Surat jalan <Text span ff="monospace" fw={500}>{sj.nomor_surat_jalan}</Text>
        </Text>
        <TextInput radius="sm" label="Ekspedisi" value={ekspedisi}
          onChange={(e) => setEkspedisi(e.currentTarget.value)} />
        <TextInput radius="sm" label="No. Resi" value={resi}
          onChange={(e) => setResi(e.currentTarget.value)} />
        <TextInput radius="sm" type="date" label="Tanggal Kirim" value={tanggal}
          onChange={(e) => setTanggal(e.currentTarget.value)} />
        <Group justify="flex-end">
          <Button variant="default" radius="sm" onClick={onClose} disabled={isPending}>Batal</Button>
          <Button radius="sm" loading={isPending} onClick={submit}>Tandai Dikirim</Button>
        </Group>
      </Stack>
    </Modal>
  )
}

// ─── Modal: Konfirmasi (Terbitkan dan Konfirmasi Diterima) ───────────────────

function ConfirmModal({ title, message, confirmLabel, isPending, onClose, onConfirm }: {
  title: string
  message: string
  confirmLabel: string
  isPending: boolean
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <Modal opened onClose={onClose} centered radius="sm" size="sm" title={title}>
      <Stack gap="md">
        <Text size="sm">{message}</Text>
        <Group justify="flex-end">
          <Button variant="default" radius="sm" onClick={onClose} disabled={isPending}>Batal</Button>
          <Button radius="sm" loading={isPending} onClick={onConfirm}>{confirmLabel}</Button>
        </Group>
      </Stack>
    </Modal>
  )
}

// ─── Modal: Detail (read-only) ───────────────────────────────────────────────

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Group gap="sm" align="flex-start" wrap="nowrap">
      <Text size="sm" c="dimmed" w={150} style={{ flexShrink: 0 }}>{label}</Text>
      <Text size="sm" component="div" style={{ flex: 1 }}>{orDash(value)}</Text>
    </Group>
  )
}

function DetailModal({ sj, onClose, onPdf, onOpenFkp }: {
  sj: SuratJalanInboxItem
  onClose: () => void
  onPdf: () => void
  onOpenFkp: () => void
}) {
  return (
    <Modal opened onClose={onClose} centered radius="sm" size="lg"
      title={`Surat Jalan ${sj.nomor_surat_jalan}`}>
      <Stack gap="xs">
        <DetailRow label="Status" value={statusBadge(sj.status)} />
        <DetailRow label="Tanggal SJ" value={fmtTanggal(sj.tanggal_surat_jalan)} />
        <DetailRow label="FKP" value={sj.nomor_fkp} />
        <DetailRow label="Asal"
          value={[sj.distributor_nama, sj.outlet_nama].filter(Boolean).join(' / ')} />
        <DetailRow label="Penerima" value={sj.nama_penerima} />
        <DetailRow label="Alamat" value={sj.alamat_penerima} />
        <DetailRow label="Telepon" value={sj.telepon_penerima} />
        <DetailRow label="Ekspedisi" value={sj.ekspedisi} />
        <DetailRow label="No. Resi" value={sj.nomor_resi} />
        <DetailRow label="Tanggal Kirim" value={sj.tanggal_kirim ? fmtTanggal(sj.tanggal_kirim) : null} />
        <DetailRow label="Tanggal Diterima"
          value={sj.tanggal_delivered ? fmtTanggal(sj.tanggal_delivered) : null} />
        <DetailRow label="Catatan" value={sj.catatan} />

        <Text size="sm" fw={500} mt="xs">Item</Text>
        <Stack gap={2}>
          {sj.items.map((it) => (
            <Text key={it.id} size="sm">
              {it.nama_produk} — {it.qty} {it.satuan}{it.keterangan ? ` (${it.keterangan})` : ''}
            </Text>
          ))}
        </Stack>

        <Group justify="flex-end" mt="md">
          <Button variant="default" radius="sm" onClick={onOpenFkp}>Buka FKP</Button>
          {sj.url_pdf ? (
            <Button radius="sm" leftSection={<Download size={14} />} onClick={onPdf}>Unduh PDF</Button>
          ) : (
            <Tooltip label="PDF tersedia setelah surat jalan diterbitkan" withArrow radius="sm">
              <Button radius="sm" leftSection={<Download size={14} />} disabled>Unduh PDF</Button>
            </Tooltip>
          )}
        </Group>
      </Stack>
    </Modal>
  )
}