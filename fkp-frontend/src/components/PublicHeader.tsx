// src/layouts/components/PublicHeader.tsx
import { Link } from 'react-router-dom'
import type { PublicPageMeta } from './layout/PublicLayout'

interface PublicHeaderProps {
    meta: PublicPageMeta
}

export function PublicHeader({ meta }: PublicHeaderProps) {
    return (
        <header className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-40">
            <div className="mx-auto px-6 py-3 flex items-center justify-between">
                <Link to="https://saktipangan.co.id">
                    <img
                        src="/logo/logo.png"
                        alt="sakti-food"
                        className="h-6 lg:h-7 w-auto object-contain"
                    />
                </Link>
                {meta.pageTitle && (
                    <Link to="/" className="flex items-center gap-3">
                        {meta.pageIcon && (
                            <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center p-1.5">
                                <img
                                    src={meta.pageIcon}
                                    alt="icon"
                                    className="w-full h-full object-contain"
                                />
                            </div>
                        )}
                        <div>
                            <p className="text-sm font-bold text-gray-900">{meta.pageTitle}</p>
                            {meta.pageSubtitle && (
                                <p className="text-[10px] text-gray-400 leading-none">{meta.pageSubtitle}</p>
                            )}
                        </div>
                    </Link>
                )}
            </div>
        </header>
    )
}