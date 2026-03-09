'use client';

import { useEffect, useState } from 'react';
import TranscriptViewer from '@/components/TranscriptViewer';

export default function TranscriptsPage() {
  const [transcripts, setTranscripts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTranscripts() {
      try {
        const res = await fetch('/api/transcripts?limit=50');
        if (res.ok) {
          const data = await res.json();
          setTranscripts(data.transcripts || []);
        }
      } catch (error) {
        console.error("Failed to fetch transcripts:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchTranscripts();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 animate-fade-in">Call Transcripts</h1>
        <p className="text-slate-500 mt-1">Review full conversation logs and Gemini AI post-call analysis.</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hospital-500"></div>
        </div>
      ) : (
        <TranscriptViewer transcripts={transcripts} />
      )}
    </div>
  );
}
