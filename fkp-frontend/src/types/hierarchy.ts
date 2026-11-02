export interface AreaBasicInfo {
  id: string
  kode_area: string
  nama_area: string
}

export interface ScSpvWithDistributors {
  sc_spv: UserBasicInfo
  area?: AreaBasicInfo | null
  distributors: DistributorBasicInfo[]
}

export interface UserBasicInfo {
  id: string
  nama: string
  email: string
  no_telepon?: string | null
  avatar_path: string | null
}

export interface DistributorBasicInfo {
  id: string
  kode_distributor: string
  nama_perusahaan: string
  status: string
}

export interface ScSpvWithDistributors {
  sc_spv: UserBasicInfo
  distributors: DistributorBasicInfo[]
}

export interface ApsmWithTeam {
  apsm: UserBasicInfo
  sc_spv_list: ScSpvWithDistributors[]
}

export interface RsmWithTeam {
  rsm: UserBasicInfo
  apsm_list: ApsmWithTeam[]
}