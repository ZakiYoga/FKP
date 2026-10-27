import type { ReactNode } from 'react'
import { Center, Loader, Paper, Tabs, Text } from '@mantine/core'
import { Building2, Lock, Store, User } from 'lucide-react'
import PageHeader from '@/components/ui/PageHeader'
import { useAuthStore } from '@/store/authStore'
import { useChangePassword } from '@/hooks/useAuth'
import {
  useDeleteAvatar,
  useMyProfile,
  useUpdateProfile,
  useUploadAvatar,
} from '@/hooks/useProfile'
import { ProfileSection } from '@/components/profile/ProfileSection'
import { SecuritySection } from '@/components/profile/SecuritySection'
import { OutletSection } from '@/components/profile/OutletSection'
import { DistributorSection } from '@/components/profile/DistributorSection'
import { useChangeEmail, useSendVerification } from '@/hooks/useAuthRecovery'

// Tab Outlet dan Distributor hanya tampil untuk role terkait.
// Siapa yang boleh mengedit ditentukan BE lewat can_edit, bukan di sini.
const ROLE_OUTLET = 'outlet'
const ROLE_DISTRIBUTOR = 'distributor'

function SectionPanel({ value, children }: { value: string; children: ReactNode }) {
  return (
    <Tabs.Panel value={value} pl="md">
      <Paper withBorder p="lg">
        {children}
      </Paper>
    </Tabs.Panel>
  )
}

// Penghubung hook -> props section (section sendiri murni presentasi).
function ProfileTab() {
  const { data, isLoading, isError } = useMyProfile()
  const update = useUpdateProfile()
  const upload = useUploadAvatar()
  const remove = useDeleteAvatar()
  const sendVerification = useSendVerification()
  const changeEmail = useChangeEmail()


  if (isLoading) {
    return (
      <Center py="xl">
        <Loader size="sm" />
      </Center>
    )
  }
  if (isError || !data) {
    return (
      <Text size="sm" c="red">
        Gagal memuat profil.
      </Text>
    )
  }

  return (
    <ProfileSection
      data={data}
      onSave={(values) => update.mutateAsync(values)}
      onUploadAvatar={(file) => upload.mutateAsync(file)}
      onDeleteAvatar={() => remove.mutateAsync()}
      onResendVerification={() => sendVerification.mutateAsync()}
      onChangeEmail={(values) => changeEmail.mutateAsync(values)}
    />
  )
}

function SecurityTab() {
  const { mutateAsync } = useChangePassword()

  return (
    <SecuritySection
      onSubmit={({ oldPassword, newPassword }) =>
        mutateAsync({
          password_lama: oldPassword,
          password_baru: newPassword,
          password_baru_konfirmasi: newPassword,
        })
      }
    />
  )
}

export default function Profile() {
  const roleCode = useAuthStore((s) => s.user?.role?.kode_role)
  const showOutlet = roleCode === ROLE_OUTLET
  const showDistributor = roleCode === ROLE_DISTRIBUTOR

  return (
    <div className="space-y-6 animate-fade-in">
      <PageHeader
        title="Account Settings"
        description="Kelola detail profil, informasi kontak, dan keamanan akun Anda."
      />

      {/* keepMounted=false: section (dan query-nya) baru jalan saat tab dibuka */}
      <Tabs
        defaultValue="profile"
        orientation="vertical"
        variant="pills"
        keepMounted={false}
      >
        <Paper withBorder p="xs" w={220} style={{ alignSelf: 'flex-start', flexShrink: 0 }}>
          <Tabs.List>
            <Tabs.Tab value="profile" leftSection={<User size={16} />}>
              Profile
            </Tabs.Tab>
            <Tabs.Tab value="security" leftSection={<Lock size={16} />}>
              Keamanan
            </Tabs.Tab>
            {showOutlet && (
              <Tabs.Tab value="outlet" leftSection={<Store size={16} />}>
                Outlet
              </Tabs.Tab>
            )}
            {showDistributor && (
              <Tabs.Tab value="distributor" leftSection={<Building2 size={16} />}>
                Distributor
              </Tabs.Tab>
            )}
          </Tabs.List>
        </Paper>

        <SectionPanel value="profile">
          <ProfileTab />
        </SectionPanel>
        <SectionPanel value="security">
          <SecurityTab />
        </SectionPanel>
        {showOutlet && (
          <SectionPanel value="outlet">
            <OutletSection />
          </SectionPanel>
        )}
        {showDistributor && (
          <SectionPanel value="distributor">
            <DistributorSection />
          </SectionPanel>
        )}
      </Tabs>
    </div>
  )
}