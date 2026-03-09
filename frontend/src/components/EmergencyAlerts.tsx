'use client';

import { ShieldAlert, Clock, PhoneForwarded, CheckCircle2 } from 'lucide-react';
import { formatDistanceToNow, parseISO } from 'date-fns';

export default function EmergencyAlerts({ alerts }: { alerts: any[] }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm h-full flex flex-col items-center justify-center min-h-[400px]">
        <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4">
          <CheckCircle2 size={32} className="text-emerald-500" />
        </div>
        <h3 className="text-lg font-bold text-slate-900">No Active Emergencies</h3>
        <p className="text-slate-500 text-sm mt-2 text-center max-w-[200px]">
          The AI agent is monitoring all calls for critical keywords.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-rose-100 shadow-sm overflow-hidden h-full flex flex-col">
      <div className="p-6 bg-rose-50 border-b border-rose-100 flex items-center justify-between">
        <h3 className="text-lg font-bold text-rose-900 flex items-center gap-2">
          <ShieldAlert size={20} className="text-rose-600" />
          Emergency Alerts
        </h3>
        <span className="bg-rose-600 text-white text-xs font-bold px-2 py-1 rounded-full">
          {alerts.length} Escalarions
        </span>
      </div>
      
      <div className="p-2 flex-1 overflow-y-auto max-h-[600px]">
        <div className="space-y-2">
          {alerts.map((alert, i) => (
            <div key={i} className="p-4 rounded-xl border border-slate-100 hover:border-rose-200 hover:bg-rose-50/30 transition-colors group cursor-pointer">
              <div className="flex justify-between items-start mb-2">
                <div className="font-bold text-slate-900">{alert.phone}</div>
                <div className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-md bg-rose-100 text-rose-700">
                  {alert.risk_level.toUpperCase()} RISK
                </div>
              </div>
              
              <div className="flex items-center gap-4 text-xs text-slate-500 mt-3">
                <div className="flex items-center gap-1">
                  <Clock size={14} />
                  {alert.time ? formatDistanceToNow(parseISO(alert.time), { addSuffix: true }) : 'Just now'}
                </div>
                <div className="flex items-center gap-1 flex-1">
                  <PhoneForwarded size={14} />
                  {alert.status === 'escalated' ? (
                    <span className="text-orange-600 font-medium">Escalated to human</span>
                  ) : (
                    <span>Status: {alert.status}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
