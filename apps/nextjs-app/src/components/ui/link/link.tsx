import NextLink, { LinkProps as NextLinkProps } from 'next/link';
import { MouseEvent } from 'react';

import { useNavigationLoading } from '@/components/ui/navigation-loading/navigation-loading';
import { cn } from '@/utils/cn';

export type LinkProps = {
  className?: string;
  children: React.ReactNode;
  target?: string;
} & NextLinkProps;

export const Link = ({ className, children, href, ...props }: LinkProps) => {
  const { startNavigation } = useNavigationLoading();

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    props.onClick?.(event);
    if (event.defaultPrevented) return;

    if (
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      props.target === '_blank'
    ) {
      return;
    }

    const hrefAsString =
      typeof href === 'string'
        ? href
        : `${href.pathname ?? ''}${href.search ?? ''}${href.hash ?? ''}`;

    if (!hrefAsString || hrefAsString.startsWith('#')) return;
    if (hrefAsString.startsWith('http://') || hrefAsString.startsWith('https://')) return;

    startNavigation(hrefAsString);
  };

  return (
    <NextLink
      href={href}
      className={cn('text-slate-600 hover:text-slate-900', className)}
      onClick={handleClick}
      {...props}
    >
      {children}
    </NextLink>
  );
};
