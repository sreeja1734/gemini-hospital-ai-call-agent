"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { getTranscripts } from "@/lib/api";
import { ArrowLeft, Phone, Clock, Shield, MessageSquare } from "lucide-react";

interface CallDetail {
    call_id: string;
    phone: string;
    status: string;
    risk_level: string;
    ai_handled: boolean;
    duration_seconds: number;
    transcript?: string;
    analysis?: any;
    started_at: string;
}

export default function CallDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { loading: authLoading } = useAuth();
    const [call, setCall] = useState<CallDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const callId = params.id as string;

    useEffect(() => {
        if (authLoading) return;

        async function fetchCall() {
            try {
                const data = await getTranscripts(100);
                const match = data.transcripts?.find(
                    (transcript) => transcript.call_id === callId
                );
                if (match) {
                    setCall({
                        call_id: match.call_id,
                        phone: match.phone || "Unknown",
                        status: String(match.analysis?.call_outcome || "unknown"),
                        risk_level: String(match.analysis?.emergency_risk || "low"),
                        ai_handled: true,
                        duration_seconds: 0,
                        transcript: match.content_preview,
                        analysis: match.analysis,
                        started_at: match.created_at,
                    });
                    setError("");
                } else {
                    setCall(null);
                    setError("No transcript was found for this call.");
                }
            } catch (caughtError) {
                console.error("Failed to fetch call", caughtError);
                const message =
                    caughtError instanceof Error ? caughtError.message : "Failed to fetch call details.";
                setError(message);
                if (message.toLowerCase().includes("401") || message.toLowerCase().includes("not authenticated")) {
                    router.replace("/login");
                }
            } finally {
                setLoading(false);
            }
        }

        fetchCall();
    }, [callId, authLoading, router]);

    if (authLoading || loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-slate-900">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500" />
            </div>
        );
    }

    const riskColors: Record<string, string> = {
        low: "bg-green-500/10 text-green-400 border-green-500/30",
        medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
        high: "bg-red-500/10 text-red-400 border-red-500/30",
    };

    return (
        <div className="min-h-screen bg-slate-900 text-white p-6">
            <div className="max-w-4xl mx-auto">
                {/* Back button */}
                <button
                    onClick={() => router.back()}
                    className="flex items-center gap-2 text-slate-400 hover:text-white mb-6 transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" /> Back to Dashboard
                </button>

                {!call ? (
                    <div className="text-center py-20 text-slate-500">
                        <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>{error || "Call not found or no transcript available."}</p>
                    </div>
                ) : (
                    <>
                        {/* Header */}
                        <div className="flex items-start justify-between mb-8">
                            <div>
                                <h1 className="text-2xl font-bold">Call Detail</h1>
                                <p className="text-slate-400 mt-1 font-mono text-sm">{call.call_id}</p>
                            </div>
                            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${riskColors[call.risk_level] || riskColors.low}`}>
                                {call.risk_level.toUpperCase()} RISK
                            </span>
                        </div>

                        {/* Info cards */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                                <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                                    <Phone className="w-4 h-4" /> Caller
                                </div>
                                <p className="font-semibold">{call.phone}</p>
                            </div>
                            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                                <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                                    <Clock className="w-4 h-4" /> Time
                                </div>
                                <p className="font-semibold">
                                    {call.started_at ? new Date(call.started_at).toLocaleString() : "Unknown"}
                                </p>
                            </div>
                            <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
                                <div className="flex items-center gap-2 text-slate-400 text-sm mb-1">
                                    <Shield className="w-4 h-4" /> Status
                                </div>
                                <p className="font-semibold capitalize">{call.status.replace("_", " ")}</p>
                            </div>
                        </div>

                        {/* Analysis */}
                        {call.analysis && (
                            <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50 mb-6">
                                <h2 className="text-lg font-semibold mb-4">AI Analysis</h2>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                    <div>
                                        <span className="text-slate-400">Intent</span>
                                        <p className="font-medium capitalize mt-1">{call.analysis.intent?.replace("_", " ")}</p>
                                    </div>
                                    <div>
                                        <span className="text-slate-400">Sentiment</span>
                                        <p className="font-medium capitalize mt-1">{call.analysis.sentiment}</p>
                                    </div>
                                    <div>
                                        <span className="text-slate-400">Follow-up</span>
                                        <p className="font-medium mt-1">{call.analysis.follow_up_required ? "Yes" : "No"}</p>
                                    </div>
                                    <div>
                                        <span className="text-slate-400">Language</span>
                                        <p className="font-medium mt-1">{call.analysis.language_detected}</p>
                                    </div>
                                </div>
                                {call.analysis.summary && (
                                    <div className="mt-4 pt-4 border-t border-slate-700/50">
                                        <span className="text-slate-400 text-sm">Summary</span>
                                        <p className="mt-1 text-slate-200">{call.analysis.summary}</p>
                                    </div>
                                )}
                                {call.analysis.key_topics?.length > 0 && (
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        {call.analysis.key_topics.map((topic: string, i: number) => (
                                            <span key={i} className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded-lg text-xs border border-blue-500/20">
                                                {topic}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Transcript */}
                        {call.transcript && (
                            <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                                <h2 className="text-lg font-semibold mb-4">Transcript Preview</h2>
                                <div className="bg-slate-900/50 rounded-lg p-4 font-mono text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                                    {call.transcript}
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
