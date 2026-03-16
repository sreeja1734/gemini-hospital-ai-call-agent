'use client';

import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

import Sidebar from '@/components/Sidebar';

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';

  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <>
      <Sidebar className="w-64 fixed h-full border-r border-slate-200 bg-white z-10 hidden md:block" />
      <div className="flex-1 md:ml-64 relative min-h-screen">
        <main className="p-4 md:p-8 max-w-7xl mx-auto pb-24">{children}</main>
      </div>
    </>
  );
}
