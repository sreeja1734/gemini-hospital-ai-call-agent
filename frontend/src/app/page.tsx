'use client';

import { useEffect, useState } from 'react';
import { PhoneCall, CalendarCheck, Clock, ShieldAlert } from 'lucide-react';
import CallStats from '@/components/CallStats';
import EmergencyAlerts from '@/components/EmergencyAlerts';

export default function DashboardHome() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const res = await fetch('/api/get-dashboard-data');
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchDashboardData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-hospital-500"></div>
      </div>
    );
  }

  const stats = [
    { 
      name: 'Total Calls (Today)', 
      value: data?.calls?.today || 0, 
      icon: PhoneCall, 
      color: 'bg-blue-500' 
    },
    { 
      name: 'AI Handle Rate', 
      value: `${data?.calls?.ai_handle_rate || 0}%`, 
      icon: Clock, 
      color: 'bg-hospital-500' 
    },
    { 
      name: 'New Appointments', 
      value: data?.appointments?.today || 0, 
      icon: CalendarCheck, 
      color: 'bg-indigo-500' 
    },
    { 
      name: 'Active Emergencies', 
      value: data?.calls?.active_calls || 0, 
      icon: ShieldAlert, 
      color: 'bg-rose-500',
      urgent: true
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Hospital AI Overview</h1>
        <p className="text-slate-500 mt-1">Real-time metrics from the {data?.hospital || "Care Hospital"} AI voice agent.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className={`p-6 rounded-2xl bg-white border shadow-sm ${stat.urgent && stat.value > 0 ? 'border-rose-200 bg-rose-50/50' : 'border-slate-100'}`}>
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl text-white ${stat.color} ${stat.urgent && stat.value > 0 ? 'animate-pulse' : ''}`}>
                  <Icon size={24} />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">{stat.name}</p>
                  <p className={`text-2xl font-bold ${stat.urgent && stat.value > 0 ? 'text-rose-600' : 'text-slate-900'}`}>{stat.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <CallStats data={data?.hourly_volume || []} intents={data?.intents || []} />
        </div>
        <div>
          <EmergencyAlerts alerts={data?.emergency_alerts || []} />
        </div>
      </div>
    </div>
  );
}
