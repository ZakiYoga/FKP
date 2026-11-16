import type { ElementType } from 'react';
import { Anchor, Breadcrumbs } from '@mantine/core';
import { ChevronRight, Home, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';

export interface BreadcrumbItem {
    title: string;
    /** Kosongkan untuk halaman aktif (item terakhir). */
    href?: string;
    /** Icon lucide (opsional). */
    icon?: LucideIcon;
}

interface PageBreadcrumbProps {
    items: BreadcrumbItem[];
    /** Tampilkan tombol home di awal. Default: true */
    showHome?: boolean;
    /** Tujuan tombol home. Default: '/' */
    homeHref?: string;
    /** Teks di samping icon home, mis. "Dashboard". Kosongkan = icon saja. */
    homeLabel?: string;
    /**
     * Komponen link router. Default: <a>.
     * Next.js: `linkComponent={Link}` (pakai prop href).
     */
    linkComponent?: ElementType;
    className?: string;
}

const itemBase =
    'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs leading-none';

const linkStyle = cn(
    itemBase,
    'text-gray-500 dark:text-gray-400 no-underline transition-colors',
    'hover:text-primary-500 hover:bg-secondary-500',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500'
);

const currentStyle = cn(itemBase, 'font-medium text-gray-900 dark:text-gray-100');

export function PageBreadcrumb({
    items,
    showHome = true,
    homeHref = '/dashboard',
    homeLabel,
    linkComponent,
    className,
}: PageBreadcrumbProps) {
    const all: BreadcrumbItem[] = showHome
        ? [{ title: homeLabel ?? '', href: homeHref, icon: Home }, ...items]
        : items;

    const crumbs = all.map((item, index) => {
        const Icon = item.icon;
        const isLast = index === all.length - 1;
        const isHome = showHome && index === 0;

        const content = (
            <>
                {Icon && <Icon size={isHome ? 14 : 12} aria-hidden="true" />}
                {item.title && <span>{item.title}</span>}
            </>
        );

        // Halaman aktif -> bukan link
        if (isLast || !item.href) {
            return (
                <span
                    key={index}
                    aria-current={isLast ? 'page' : undefined}
                    className={isLast ? currentStyle : cn(itemBase, 'text-gray-400 dark:text-gray-500')}
                >
                    {content}
                </span>
            )
        }

        return (
            <Anchor
                key={index}
                component={Link}
                to={item.href}
                underline="never"
                className={linkStyle}
                aria-label={isHome && !homeLabel ? 'Dashboard' : undefined}
            >
                {content}
            </Anchor>
        );
    });

    return (
        <Breadcrumbs
            className={className}
            separator={
                <ChevronRight size={14} className="text-gray-400" aria-hidden="true" />
            }
            separatorMargin={2}
            aria-label="Breadcrumb"
        >
            {crumbs}
        </Breadcrumbs>
    );
}

export default PageBreadcrumb;