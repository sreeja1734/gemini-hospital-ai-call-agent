'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { LoaderCircle, Mic, Phone, PhoneOff, Volume2 } from 'lucide-react';

type CallState = 'idle' | 'connecting' | 'listening' | 'ai-speaking';

type Message = {
  role: 'patient' | 'assistant';
  text: string;
};

const SILENCE_THRESHOLD = 0.035;
const SILENCE_DURATION_MS = 1200;

function getVoiceSocketUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_VOICE_WS_URL;
  if (configuredUrl) {
    return configuredUrl;
  }

  if (typeof window === 'undefined') {
    return 'ws://localhost:8000/ws/voice-call';
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.hostname}:8000/ws/voice-call`;
}

function pickRecorderMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm'];
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) ?? '';
}

export default function VoiceCall() {
  const [callState, setCallState] = useState<CallState>('idle');
  const [callId, setCallId] = useState('');
  const [error, setError] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [language, setLanguage] = useState('en-US');

  const wsRef = useRef<WebSocket | null>(null);
  const callIdRef = useRef('');
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const rafRef = useRef<number | null>(null);
  const isCommittingRef = useRef(false);
  const speechDetectedRef = useRef(false);
  const lastSpeechAtRef = useRef(0);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      void stopCall();
    };
  }, []);

  async function startCall() {
    setError('');
    setMessages([]);
    setCallState('connecting');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const websocket = new WebSocket(getVoiceSocketUrl());
      wsRef.current = websocket;

      websocket.onopen = () => {
        websocket.send(
          JSON.stringify({
            type: 'session.start',
            callerPhone: 'web-demo-user',
            language,
          }),
        );
      };

      websocket.onmessage = async (event) => {
        const payload = JSON.parse(event.data);

        if (payload.type === 'state') {
          setCallState(payload.state);
          return;
        }

        if (payload.type === 'session.ready') {
          callIdRef.current = payload.callId;
          setCallId(payload.callId);
          setMessages([{ role: 'assistant', text: payload.greetingText }]);
          await playAssistantResponse(payload.greetingText, payload.greetingAudioBase64, payload.callId);
          return;
        }

        if (payload.type === 'assistant.response') {
          setMessages((current) => [
            ...current,
            { role: 'patient', text: payload.transcript },
            { role: 'assistant', text: payload.responseText },
          ]);
          await playAssistantResponse(payload.responseText, payload.responseAudioBase64, payload.callId);
          return;
        }

        if (payload.type === 'error') {
          setError(payload.message);
          await stopCall(false);
        }
      };

      websocket.onclose = () => {
        wsRef.current = null;
        setCallState('idle');
      };
    } catch (caughtError) {
      console.error(caughtError);
      setError('Unable to access the microphone or connect to the voice service.');
      await stopCall(false);
    }
  }

  async function beginListening(nextCallId?: string) {
    const activeCallId = nextCallId ?? callIdRef.current;
    if (!streamRef.current || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !activeCallId) {
      return;
    }

    const mimeType = pickRecorderMimeType();
    if (!mimeType) {
      setError('This browser does not support WebM audio recording for the demo.');
      await stopCall(false);
      return;
    }

    speechDetectedRef.current = false;
    lastSpeechAtRef.current = Date.now();
    isCommittingRef.current = false;

    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    recorderRef.current = recorder;
    recorder.ondataavailable = async (mediaEvent) => {
      if (!mediaEvent.data.size || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !activeCallId) {
        return;
      }

      const buffer = await mediaEvent.data.arrayBuffer();
      wsRef.current.send(
        JSON.stringify({
          type: 'audio.chunk',
          callId: activeCallId,
          audio: arrayBufferToBase64(buffer),
        }),
      );
    };

    recorder.start(300);
    setCallState('listening');
    setupSilenceDetection(streamRef.current);
  }

  function setupSilenceDetection(stream: MediaStream) {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
    }

    sourceNodeRef.current?.disconnect();
    const source = audioContextRef.current.createMediaStreamSource(stream);
    sourceNodeRef.current = source;
    const analyser = audioContextRef.current.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    analyserRef.current = analyser;

    const data = new Float32Array(analyser.fftSize);
    const checkLevel = () => {
      if (!analyserRef.current) {
        return;
      }

      analyserRef.current.getFloatTimeDomainData(data);
      let sum = 0;
      for (const sample of data) {
        sum += sample * sample;
      }
      const rms = Math.sqrt(sum / data.length);

      if (rms > SILENCE_THRESHOLD) {
        speechDetectedRef.current = true;
        lastSpeechAtRef.current = Date.now();
      }

      if (
        speechDetectedRef.current &&
        !isCommittingRef.current &&
        Date.now() - lastSpeechAtRef.current > SILENCE_DURATION_MS
      ) {
        void commitCurrentTurn();
        return;
      }

      rafRef.current = window.requestAnimationFrame(checkLevel);
    };

    cancelSilenceDetection();
    rafRef.current = window.requestAnimationFrame(checkLevel);
  }

  async function commitCurrentTurn() {
    if (!recorderRef.current || !wsRef.current || !callIdRef.current || isCommittingRef.current) {
      return;
    }

    isCommittingRef.current = true;
    cancelSilenceDetection();
    setCallState('connecting');

    const recorder = recorderRef.current;
    await new Promise<void>((resolve) => {
      recorder.addEventListener(
        'stop',
        () => {
          wsRef.current?.send(JSON.stringify({ type: 'audio.commit', callId: callIdRef.current }));
          recorderRef.current = null;
          resolve();
        },
        { once: true },
      );
      recorder.stop();
    });
  }

  async function playAssistantResponse(text: string, audioBase64?: string, nextCallId?: string) {
    setCallState('ai-speaking');

    if (audioBase64) {
      await new Promise<void>((resolve) => {
        const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
        currentAudioRef.current = audio;
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
        void audio.play().catch(() => resolve());
      });
    } else if ('speechSynthesis' in window) {
      await new Promise<void>((resolve) => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.onend = () => resolve();
        utterance.onerror = () => resolve();
        window.speechSynthesis.speak(utterance);
      });
    }

    currentAudioRef.current = null;
    await beginListening(nextCallId);
  }

  async function stopCall(notifyServer = true) {
    cancelSilenceDetection();

    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop();
    }
    recorderRef.current = null;

    currentAudioRef.current?.pause();
    currentAudioRef.current = null;
    window.speechSynthesis?.cancel();

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (notifyServer && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'session.stop', callId: callIdRef.current }));
      wsRef.current.close();
    } else {
      wsRef.current?.close();
    }
    wsRef.current = null;

    analyserRef.current = null;
    sourceNodeRef.current?.disconnect();
    sourceNodeRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      await audioContextRef.current.close();
    }
    audioContextRef.current = null;

    callIdRef.current = '';
    setCallId('');
    setCallState('idle');
  }

  function cancelSilenceDetection() {
    if (rafRef.current !== null) {
      window.cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }

  function arrayBufferToBase64(buffer: ArrayBuffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    bytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return window.btoa(binary);
  }

  const statusConfig: Record<CallState, { label: string; tone: string; icon: ReactNode }> = {
    idle: {
      label: 'Idle',
      tone: 'bg-slate-100 text-slate-700',
      icon: <Phone size={16} />,
    },
    connecting: {
      label: 'Connecting',
      tone: 'bg-amber-100 text-amber-700',
      icon: <LoaderCircle size={16} className="animate-spin" />,
    },
    listening: {
      label: 'Listening',
      tone: 'bg-emerald-100 text-emerald-700',
      icon: <Mic size={16} />,
    },
    'ai-speaking': {
      label: 'AI Speaking',
      tone: 'bg-blue-100 text-blue-700',
      icon: <Volume2 size={16} />,
    },
  };

  const status = statusConfig[callState];

  return (
    <section className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">WebRTC Voice Call with AI Assistant</h2>
          <p className="text-sm text-slate-500 mt-1">
            Browser microphone streaming over WebSocket into the Gemini ADK voice pipeline.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            disabled={callState !== 'idle'}
            className="min-w-[156px] rounded-xl border border-slate-200 pl-4 pr-10 py-2 text-sm text-slate-700 whitespace-nowrap"
          >
            <option value="en-US">English</option>
            <option value="hi-IN">Hindi</option>
            <option value="ta-IN">Tamil</option>
          </select>

          {callState === 'idle' ? (
            <button
              onClick={startCall}
              className="inline-flex min-w-[136px] items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
            >
              <PhoneCallIcon />
              Start Call
            </button>
          ) : (
            <button
              onClick={() => void stopCall()}
              className="inline-flex min-w-[136px] items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-rose-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-rose-500"
            >
              <PhoneOff size={16} />
              End Call
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${status.tone}`}>
          {status.icon}
          {status.label}
        </div>
        {callId ? <span className="text-xs text-slate-400">Session: {callId}</span> : null}
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
        <div className="rounded-2xl bg-slate-50 border border-slate-200 p-4 min-h-[280px]">
          <div className="text-sm font-semibold text-slate-900 mb-3">Conversation</div>
          <div className="space-y-3">
            {messages.length === 0 ? (
              <p className="text-sm text-slate-500">
                Start a call, speak naturally, and pause for a moment after each turn so the demo can commit audio.
              </p>
            ) : (
              messages.slice(-6).map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`rounded-2xl px-4 py-3 text-sm ${
                    message.role === 'assistant'
                      ? 'bg-blue-50 text-blue-900 border border-blue-100'
                      : 'bg-white text-slate-700 border border-slate-200'
                  }`}
                >
                  <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    {message.role === 'assistant' ? 'AI Assistant' : 'Patient'}
                  </div>
                  {message.text}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl bg-slate-900 text-white p-5 space-y-4">
          <div>
            <div className="text-sm uppercase tracking-[0.2em] text-slate-400">Call Flow</div>
            <h3 className="text-lg font-semibold mt-1">Real-time Voice Loop</h3>
          </div>
          <ol className="space-y-3 text-sm text-slate-200">
            <li>1. Browser captures microphone audio with `getUserMedia`.</li>
            <li>2. Audio chunks stream to FastAPI over WebSocket.</li>
            <li>3. The backend transcribes speech, calls the Gemini ADK agent, then synthesizes MP3 audio.</li>
            <li>4. The browser plays the AI reply and resumes listening for the next turn.</li>
          </ol>
          <p className="text-xs text-slate-400">
            This demo uses silence detection for turn-taking to keep the implementation small and modular.
          </p>
        </div>
      </div>
    </section>
  );
}

function PhoneCallIcon() {
  return <Phone size={16} />;
}
