'use client';

import AppointmentTable from '@/components/AppointmentTable';

export default function AppointmentsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 animate-fade-in">Appointments</h1>
        <p className="text-slate-500 mt-1">Manage hospital appointments booked manually or by the AI agent.</p>
      </div>
      
      <AppointmentTable />
    </div>
  );
}
