// Satu sumber untuk "siapa yang menangani FKP pcs".
// Dipakai oleh: useCanHandlePcs, NAV_ITEMS (roles), dan router (allowedRoles).
// Backend tetap otoritas lewat permission fkp.pcs.handle.
export const ROLE_PENANGAN_PCS: string[] = ['apsm', 'superadmin']