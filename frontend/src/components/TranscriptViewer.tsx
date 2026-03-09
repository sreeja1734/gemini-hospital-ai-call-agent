'use client';

import { useState } from 'react';
import { format, parseISO } from 'date-fns';
import { FileText, Clock, ChevronDown, ChevronUp, Bot, User, Activity } from 'lucide-react';

export default function TranscriptViewer({ transcripts }: { transcripts: any[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!transcripts || transcripts.length === 0) {
    return (
      <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm text-center text-slate-500">
        No transcripts available yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {transcripts.map((tr) => {
        const isExpanded = expandedId === tr.id;
        const analysis = tr.analysis || {};

        // Define badge color based on intent/risk
        let intentColor = "bg-slate-100 text-slate-700";
        if (analysis.intent === "appointment_booking") intentColor = "bg-blue-100 text-blue-700";
        else if (analysis.intent === "emergency") intentColor = "bg-rose-100 text-rose-700";
        else if (analysis.intent === "doctor_availability") intentColor = "bg-emerald-100 text-emerald-700";

        // Parse lines for display
        const lines = (tr.content_preview || "").split('\n').filter(Boolean);

        return (
          <div key={tr.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden transition-all duration-200 hover:shadow-md">
            {/* Header (Always visible) */}
            <div
              className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-slate-50/50"
              onClick={() => setExpandedId(isExpanded ? null : tr.id)}
            >
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-xl flex-shrink-0 ${analysis.intent === 'emergency' ? 'bg-rose-100 text-rose-600' : 'bg-hospital-50 text-hospital-600'}`}>
                  <FileText size={20} />
                </div>
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-bold text-slate-900">{tr.phone}</h3>
                    <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${intentColor}`}>
                      {analysis.intent?.replace(/_/g, ' ').toUpperCase() || 'UNKNOWN'}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-medium text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock size={14} />
                      {tr.created_at ? format(parseISO(tr.created_at), 'MMM d, h:mm a') : ''}
                    </span>
                    <span className="flex items-center gap-1">
                      <Activity size={14} />
                      Risk: {analysis.emergency_risk?.toUpperCase() || 'LOW'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4">
                {analysis.summary && (
                  <p className="text-sm text-slate-600 hidden lg:block max-w-sm truncate">
                    {analysis.summary}
                  </p>
                )}
                <div className="text-slate-400">
                  {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
              </div>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
              <div className="p-5 border-t border-slate-100 bg-slate-50/50">

                {/* Analysis Box */}
                {analysis.summary && (
                  <div className="mb-6 bg-white p-4 rounded-xl border border-hospital-100 shadow-sm">
                    <h4 className="text-sm font-bold text-hospital-800 mb-2 flex items-center gap-2">
                      <Bot size={16} /> Gemini AI Analysis
                    </h4>
                    <p className="text-sm text-slate-700 leading-relaxed mb-3">
                      {analysis.summary}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {analysis.key_topics?.map((topic: string, i: number) => (
                        <span key={i} className="text-xs font-medium bg-hospital-50 text-hospital-700 px-2 py-1 rounded-md">
                          #{topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Transcript Dialog */}
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 ml-1">Call Transcript ({tr.turn_count} turns)</h4>
                <div className="space-y-3 font-mono text-sm">
                  {lines.length > 0 ? lines.map((line: string, i: number) => {
                    const isUser = line.includes('Patient:');
                    return (
                      <div key={i} className={`flex gap-3 p-3 rounded-lg ${isUser ? 'bg-white border border-slate-200' : 'bg-hospital-50/50 border border-hospital-100 ml-4'}`}>
                        <div className={`mt-0.5 ${isUser ? 'text-slate-400' : 'text-hospital-500'}`}>
                          {isUser ? <User size={16} /> : <Bot size={16} />}
                        </div>
                        <div className="text-slate-700">
                          {line.replace(/\[.*?\]\s*(Patient|AI Assistant):\s*/, '')}
                        </div>
                      </div>
                    );
                  }) : (
                    <div className="text-slate-500 italic p-4 text-center">Transcript content unavailable.</div>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
