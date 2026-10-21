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
        pageTitle: 'SaktiFood',
        pageSubtitle: undefined,
        pageIcon: undefined,
    })

    return (
        <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50/30 to-white flex flex-col">
            <PublicHeader meta={meta} />
            <main className="flex-1">
                <Outlet context={{ setPage: setMeta } satisfies PublicPageContext} />
            </main>
            <PublicFooter />
        </div>
    )
}