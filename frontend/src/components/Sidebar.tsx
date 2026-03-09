'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  PhoneCall,
  CalendarCheck,
  AlertTriangle,
  Stethoscope,
  Settings
} from 'lucide-react';

export default function Sidebar({ className = '' }: { className?: string }) {
  const pathname = usePathname();

  const navLinks = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Live Calls', href: '/calls', icon: PhoneCall },
    { name: 'Appointments', href: '/appointments', icon: CalendarCheck },
    { name: 'Emergency Alerts', href: '/emergencies', icon: AlertTriangle, badge: true },
    { name: 'Transcripts', href: '/transcripts', icon: Stethoscope },
  ];

  return (
    <div className={`${className} flex flex-col`}>
      <div className="p-6">
        <div className="flex items-center gap-3 text-hospital-600 font-bold text-xl tracking-tight">
          <div className="w-8 h-8 rounded-lg bg-hospital-600 text-white flex items-center justify-center">
            <Stethoscope size={20} />
          </div>
          Care Hospital <span className="text-slate-400 text-sm font-normal">AI</span>
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
        {navLinks.map((link) => {
          const isActive = pathname === link.href;
          const Icon = link.icon;

          return (
            <Link
              key={link.name}
              href={link.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive
                  ? 'bg-hospital-50 text-hospital-600'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
            >
              <Icon size={18} className={isActive ? 'text-hospital-500' : 'text-slate-400'} />
              {link.name}

              {link.badge && (
                <span className="ml-auto bg-rose-100 text-rose-600 py-0.5 px-2 rounded-full text-xs font-bold">
                  2
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-200">
        <button className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
          <Settings size={18} className="text-slate-400" />
          Settings
        </button>
      </div>
    </div>
  );
}
