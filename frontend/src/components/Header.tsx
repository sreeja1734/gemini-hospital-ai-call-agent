'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  AlertTriangle,
  CalendarCheck,
  LayoutDashboard,
  PhoneCall,
  Settings,
  Stethoscope,
} from 'lucide-react';

const navLinks = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Live Calls', href: '/calls', icon: PhoneCall },
  { name: 'Appointments', href: '/appointments', icon: CalendarCheck },
  { name: 'Emergency Alerts', href: '/emergencies', icon: AlertTriangle, badge: true },
  { name: 'Transcripts', href: '/transcripts', icon: Stethoscope },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-gradient-to-r from-white via-teal-50 to-cyan-50 shadow-sm backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-4 md:px-8">
        <Link href="/" className="flex items-center gap-3 shrink-0 text-hospital-700">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-hospital-600 to-teal-500 text-white shadow-sm">
            <Stethoscope size={24} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight">Care Hospital</span>
            <span className="text-sm font-normal text-slate-400">AI</span>
          </div>
        </Link>

        <nav className="flex min-w-0 flex-1 items-center gap-2 overflow-x-auto pb-1">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            const Icon = link.icon;

            return (
              <Link
                key={link.name}
                href={link.href}
                className={`inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-white text-hospital-700 shadow-sm ring-1 ring-hospital-100'
                    : 'text-slate-600 hover:bg-white/80 hover:text-slate-900'
                }`}
              >
                <Icon size={16} className={isActive ? 'text-hospital-500' : 'text-slate-400'} />
                <span className="whitespace-nowrap">{link.name}</span>
                {link.badge ? (
                  <span className="ml-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-100 px-1.5 text-[11px] font-bold text-rose-600">
                    2
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
