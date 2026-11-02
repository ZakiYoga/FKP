// src/layouts/PublicLayout.tsx
import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import { PublicHeader } from '../PublicHeader'
import { PublicFooter } from '../PublicFooter'

export interface PublicPageContext {
    setPage: (ctx: PublicPageMeta) => void
}

export interface PublicPageMeta {
    pageTitle: string
    pageSubtitle?: string
    pageIcon?: string
}

export function PublicLayout() {
    const [meta, setMeta] = useState<PublicPageMeta>({
        pageTitle: 'FKP - PT SAKTI PANGAN PERKASA',
        pageSubtitle: 'Aplikasi untuk pengajuan form keluhan pelanggan',
        pageIcon: undefined,
    })

    return (
        <div className="min-h-screen flex flex-col">
            <PublicHeader meta={meta} />
            <main className="flex-1">
                <Outlet context={{ setPage: setMeta } satisfies PublicPageContext} />
            </main>
            <PublicFooter />
        </div>
    )
}