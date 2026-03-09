'use client';

import { useEffect, useState } from 'react';
import { format, parseISO } from 'date-fns';
import { Calendar, Search, Filter, MoreHorizontal } from 'lucide-react';

export default function AppointmentTable() {
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    async function fetchAppointments() {
      try {
        const res = await fetch('/api/appointments?limit=100');
        if (res.ok) {
          const data = await res.json();
          setAppointments(data.appointments || []);
        }
      } catch (error) {
        console.error("Failed to fetch appointments:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchAppointments();
  }, []);

  const filteredAppointments = appointments.filter(apt => 
    apt.patient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    apt.doctor_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    apt.department?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-6 border-b border-slate-200 bg-white">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Calendar className="text-hospital-500" />
            Upcoming Appointments
          </h2>
          
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute text-slate-400 left-3 top-1/2 -translate-y-1/2" size={16} />
              <input 
                type="text" 
                placeholder="Search patients, doctors..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-hospital-500 w-full sm:w-64"
              />
            </div>
            <button className="flex items-center gap-2 px-3 py-2 border border-slate-200 rounded-lg text-sm font-medium hover:bg-slate-50 text-slate-600 transition-colors">
              <Filter size={16} />
              Filter
            </button>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-slate-900 font-medium">
            <tr>
              <th className="px-6 py-4">Patient</th>
              <th className="px-6 py-4">Date & Time</th>
              <th className="px-6 py-4">Doctor</th>
              <th className="px-6 py-4">Department</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 rounded-full border-2 border-slate-200 border-t-hospital-500 animate-spin"></div>
                    Loading appointments...
                  </div>
                </td>
              </tr>
            ) : filteredAppointments.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                  No appointments found.
                </td>
              </tr>
            ) : (
              filteredAppointments.map((apt) => (
                <tr key={apt.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-6 py-4">
                    <p className="font-bold text-slate-900">{apt.patient_name}</p>
                    <p className="text-xs text-slate-500">{apt.patient_phone || 'No phone'}</p>
                  </td>
                  <td className="px-6 py-4 font-medium">
                    {apt.appointment_slot ? format(parseISO(apt.appointment_slot), 'MMM d, yyyy h:mm a') : 'Unscheduled'}
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                      {apt.doctor_name}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-500">{apt.department}</td>
                  <td className="px-6 py-4">
                    {apt.confirmed ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-50 text-emerald-700">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        Confirmed
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-amber-50 text-amber-700">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                        Pending
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-slate-400 hover:text-hospital-600 transition-colors">
                      <MoreHorizontal size={20} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
