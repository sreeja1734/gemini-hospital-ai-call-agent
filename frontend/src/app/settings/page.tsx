'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, Globe2, RefreshCw, Settings2, Volume2, Database, Activity } from 'lucide-react';

import {
  getHealthStatus,
  getSystemInfo,
  type HealthStatus,
  type SystemInfo,
} from '@/lib/api';
import { useAuth } from '@/lib/useAuth';
import {
  DEFAULT_USER_SETTINGS,
  getUserSettings,
  saveUserSettings,
  type UserSettings,
} from '@/lib/userSettings';

function formatLanguageLabel(value: string) {
  const labels: Record<string, string> = {
    'en-US': 'English',
    'hi-IN': 'Hindi',
    'ta-IN': 'Tamil',
  };

  return labels[value] || value;
}

export default function SettingsPage() {
  const { loading: authLoading } = useAuth();
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_USER_SETTINGS);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [saveState, setSaveState] = useState<'idle' | 'saved'>('idle');

  useEffect(() => {
    setSettings(getUserSettings());

    async function fetchSystemData() {
      try {
        const [info, healthStatus] = await Promise.all([getSystemInfo(), getHealthStatus()]);
        setSystemInfo(info);
        setHealth(healthStatus);
      } catch (error) {
        console.error('Failed to load system settings context:', error);
      }
    }

    void fetchSystemData();
  }, []);

  function updateSetting<K extends keyof UserSettings>(key: K, value: UserSettings[K]) {
    setSettings((current) => ({
      ...current,
      [key]: value,
    }));
    setSaveState('idle');
  }

  function handleSave() {
    saveUserSettings(settings);
    setSaveState('saved');
    window.setTimeout(() => setSaveState('idle'), 2000);
  }

  const supportedLanguages = systemInfo?.supported_languages?.length
    ? systemInfo.supported_languages
    : ['en-US', 'hi-IN', 'ta-IN'];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Settings</h1>
          <p className="mt-2 max-w-3xl text-slate-500">
            Configure the frontend behavior for the hospital AI dashboard and review the live backend system status.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={authLoading}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {saveState === 'saved' ? <CheckCircle2 size={16} /> : <Settings2 size={16} />}
          {saveState === 'saved' ? 'Saved' : 'Save Preferences'}
        </button>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
        <section className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                <Volume2 size={20} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Voice Assistant Preferences</h2>
                <p className="text-sm text-slate-500">Applied to the browser voice-call experience.</p>
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Default Call Language</span>
                <select
                  value={settings.defaultLanguage}
                  onChange={(event) => updateSetting('defaultLanguage', event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
                >
                  {supportedLanguages.map((language) => (
                    <option key={language} value={language}>
                      {formatLanguageLabel(language)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Browser Speech Fallback</span>
                <button
                  type="button"
                  onClick={() =>
                    updateSetting('useBrowserSpeechFallback', !settings.useBrowserSpeechFallback)
                  }
                  className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-sm font-medium transition-colors ${
                    settings.useBrowserSpeechFallback
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-slate-200 bg-slate-50 text-slate-600'
                  }`}
                >
                  <span>
                    {settings.useBrowserSpeechFallback ? 'Enabled' : 'Disabled'}
                  </span>
                  <span className="text-xs">
                    {settings.useBrowserSpeechFallback ? 'Speak text when MP3 is unavailable' : 'Audio only'}
                  </span>
                </button>
              </label>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-teal-50 text-teal-600">
                <RefreshCw size={20} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Dashboard Preferences</h2>
                <p className="text-sm text-slate-500">Control how the dashboard refreshes and loads transcript data.</p>
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Dashboard Refresh Interval</span>
                <select
                  value={String(settings.dashboardRefreshSeconds)}
                  onChange={(event) => updateSetting('dashboardRefreshSeconds', Number(event.target.value))}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
                >
                  <option value="15">Every 15 seconds</option>
                  <option value="30">Every 30 seconds</option>
                  <option value="60">Every 60 seconds</option>
                  <option value="0">Manual refresh only</option>
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Transcript History Fetch Size</span>
                <select
                  value={String(settings.transcriptFetchLimit)}
                  onChange={(event) => updateSetting('transcriptFetchLimit', Number(event.target.value))}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
                >
                  <option value="20">20 transcripts</option>
                  <option value="50">50 transcripts</option>
                  <option value="100">100 transcripts</option>
                </select>
              </label>
            </div>
          </div>
        </section>

        <section className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                <Globe2 size={20} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900">System Status</h2>
                <p className="text-sm text-slate-500">Read-only details from the running FastAPI backend.</p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Service</div>
                <div className="mt-2 text-lg font-semibold text-slate-900">
                  {systemInfo?.service || 'Unavailable'}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Version</div>
                <div className="mt-2 text-lg font-semibold text-slate-900">
                  {systemInfo?.version || health?.version || 'Unavailable'}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Hospital</div>
                <div className="mt-2 text-lg font-semibold text-slate-900">
                  {systemInfo?.hospital || 'Unavailable'}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Supported Languages</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {supportedLanguages.map((language) => (
                    <span
                      key={language}
                      className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200"
                    >
                      {formatLanguageLabel(language)}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                <Database size={20} />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Runtime Health</h2>
                <p className="text-sm text-slate-500">Current health signals exposed by the backend.</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                <span className="text-sm font-medium text-slate-600">Application Status</span>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    health?.status === 'healthy'
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {health?.status || 'Unknown'}
                </span>
              </div>

              <div className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                <span className="text-sm font-medium text-slate-600">Database Connection</span>
                <span className="text-sm font-semibold text-slate-900">
                  {health?.database || 'Unknown'}
                </span>
              </div>

              <div className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                <span className="inline-flex items-center gap-2 text-sm font-medium text-slate-600">
                  <Activity size={16} />
                  Active Calls
                </span>
                <span className="text-sm font-semibold text-slate-900">
                  {health?.active_calls ?? 0}
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
