// src/layouts/PublicLayout.tsx
import { Outlet, useOutletContext } from 'react-router-dom'
import { useState, useEffect } from 'react'
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

export function useSetPublicPage(meta: PublicPageMeta) {
    // ✅ null guard — context bisa null jika dipakai di luar PublicLayout
    const ctx = useOutletContext<PublicPageContext | null>()

    useEffect(() => {
        ctx?.setPage(meta)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])
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