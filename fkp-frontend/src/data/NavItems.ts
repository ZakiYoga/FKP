import { NavItem } from "@/types/navItems";
import { Bell, Building2, ClipboardList, FileText, GitBranch, LayoutDashboard, MapPin, MessageSquareQuote, Package, Route, Settings, Store, Users, } from "lucide-react";


export const NAV_ITEMS: NavItem[] = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'FKP', href: '/fkp', icon: FileText },
    {
        label: 'Outlet', href: '/outlets', icon: Store,
        roles: ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'distributor']
    },
    {
        label: 'Distributor', href: '/distributors', icon: Building2,
        roles: ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'rsm', 'direktur', 'qc']
    },
    {
        label: 'Area', href: '/areas', icon: MapPin,
        roles: ['superadmin', 'admin_ho', 'rsm', 'direktur']
    },
    {
        label: 'Produk', href: '/products', icon: Package,
        roles: ['superadmin', 'admin_ho', 'qc']
    },
    {
        label: 'Hierarki Tim', href: '/hierarchy', icon: GitBranch,
        roles: ['superadmin', 'admin_ho', 'rsm', 'direktur']
    },
    {
        label: 'Pengguna', href: '/users', icon: Users,
        roles: ['superadmin']
    },
    {
        label: 'Registrasi Outlet', href: '/outlet-registrations', icon: ClipboardList,
        roles: ['superadmin', 'admin_ho', 'apsm', 'sc_spv', 'distributor']
    },
    {
        label: 'Testimoni', href: '/testimoni', icon: MessageSquareQuote
    },
    {
        label: 'Track FKP', href: '/track', icon: Route
    },
    {
        label: 'Notifikasi', href: '/notifications', icon: Bell
    },
    {
        label: 'Ubah Password', href: '/change-password', icon: Settings
    },
]