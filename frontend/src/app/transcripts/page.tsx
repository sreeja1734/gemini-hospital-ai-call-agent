'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import TranscriptViewer from '@/components/TranscriptViewer';
import { getTranscripts, type Transcript } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';

export default function TranscriptsPage() {
  const router = useRouter();
  const { loading: authLoading } = useAuth();
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (authLoading) {
      return;
    }

    async function fetchTranscripts() {
      try {
        const data = await getTranscripts(50);
        setTranscripts(data.transcripts || []);
        setError('');
      } catch (caughtError) {
        console.error('Failed to fetch transcripts:', caughtError);
        const message =
          caughtError instanceof Error ? caughtError.message : 'Failed to fetch transcripts.';
        setError(message);
        if (message.toLowerCase().includes('401') || message.toLowerCase().includes('not authenticated')) {
          router.replace('/login');
        }
      } finally {
        setLoading(false);
      }
    }
    fetchTranscripts();
  }, [authLoading, router]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 animate-fade-in">Call Transcripts</h1>
        <p className="text-slate-500 mt-1">Review full conversation logs and Gemini AI post-call analysis.</p>
      </div>

      {authLoading || loading ? (
        <div className="flex items-center justify-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-hospital-500"></div>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : (
        <TranscriptViewer transcripts={transcripts} />
      )}
    </div>
  );
}
