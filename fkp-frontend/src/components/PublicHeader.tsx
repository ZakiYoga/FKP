// src/layouts/components/PublicHeader.tsx
import { Link } from 'react-router-dom'
import type { PublicPageMeta } from './layout/PublicLayout'
import { ThemeToggle } from './ThemeToggle'

interface PublicHeaderProps {
    meta: PublicPageMeta
}

export function PublicHeader({ meta }: PublicHeaderProps) {
    return (
        <header className="border-b bg-white dark:bg-gray-950 sticky top-0 z-40">
            <div className="mx-auto px-6 py-3 flex items-center justify-between">
                <img
                    src="/logo/logo.png"
                    alt="sakti-food"
                    className="h-6 lg:h-7 w-auto object-contain"
                />
                <div className="flex items-center gap-4">
                    {meta.pageTitle && (
                        <Link to="/" className="flex items-center gap-3">
                            {meta.pageIcon && (
                                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 p-1.5">
                                    <img
                                        src={meta.pageIcon}
                                        alt="icon"
                                        className="h-full w-full object-contain"
                                    />
                                </div>
                            )}
                            <div>
                                <p className="text-sm font-bold text-gray-900 dark:text-gray-100">
                                    {meta.pageTitle}
                                </p>
                                {meta.pageSubtitle && (
                                    <p className="text-[10px] leading-none text-gray-400 dark:text-gray-500">
                                        {meta.pageSubtitle}
                                    </p>
                                )}
                            </div>
                        </Link>
                    )}

                    <ThemeToggle
                        size={32}
                        className="text-gray-500 border-gray-300 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    />
                </div>
            </div>
        </header>
    )
}