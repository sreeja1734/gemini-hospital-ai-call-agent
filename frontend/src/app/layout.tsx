import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Sidebar from '@/components/Sidebar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Care Hospital | AI Agent Dashboard',
  description: 'Manage calls, appointments, and emergency alerts from the AI phone agent.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 text-slate-900 min-h-screen flex`}>
        <Sidebar className="w-64 fixed h-full border-r border-slate-200 bg-white z-10 hidden md:block" />
        <div className="flex-1 md:ml-64 relative min-h-screen">
          <main className="p-4 md:p-8 max-w-7xl mx-auto pb-24">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
