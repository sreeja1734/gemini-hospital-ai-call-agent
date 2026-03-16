'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import Header from '@/components/Header';

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';

  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen w-full">
      <Header />
      <main className="mx-auto max-w-7xl p-4 md:p-8 pb-24">{children}</main>
    </div>
  );
}
