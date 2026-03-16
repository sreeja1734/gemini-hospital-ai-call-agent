export type UserSettings = {
  defaultLanguage: string;
  dashboardRefreshSeconds: number;
  transcriptFetchLimit: number;
  useBrowserSpeechFallback: boolean;
};

export const DEFAULT_USER_SETTINGS: UserSettings = {
  defaultLanguage: 'en-US',
  dashboardRefreshSeconds: 30,
  transcriptFetchLimit: 50,
  useBrowserSpeechFallback: true,
};

const STORAGE_KEY = 'hospital-ai-user-settings';

export function getUserSettings(): UserSettings {
  if (typeof window === 'undefined') {
    return DEFAULT_USER_SETTINGS;
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return DEFAULT_USER_SETTINGS;
    }

    const parsed = JSON.parse(stored) as Partial<UserSettings>;
    return {
      ...DEFAULT_USER_SETTINGS,
      ...parsed,
    };
  } catch {
    return DEFAULT_USER_SETTINGS;
  }
}

export function saveUserSettings(settings: UserSettings) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}
