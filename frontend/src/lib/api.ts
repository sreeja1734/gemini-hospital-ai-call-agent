const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type ApiFetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
  headers?: HeadersInit;
};

export type DashboardData = {
  calls: {
    total: number;
    today: number;
    this_week: number;
    ai_handled: number;
    escalated: number;
    emergency: number;
    completed: number;
    avg_duration_seconds: number;
    ai_handle_rate: number;
  };
  appointments: {
    total: number;
    today: number;
    this_week: number;
    by_doctor: Array<{
      doctor: string;
      appointments: number;
    }>;
  };
  intents: Array<{
    intent: string;
    count: number;
  }>;
  hourly_volume: Array<{
    hour: string;
    count: number;
  }>;
  emergency_alerts: Array<{
    call_id: string;
    phone: string;
    risk_level: string;
    time: string;
    status: string;
    ai_handled?: boolean;
  }>;
  active_calls: number;
  generated_at: string;
  demo_mode?: boolean;
};

export type Appointment = {
  id: string;
  patient_name: string;
  patient_phone: string;
  doctor_name: string;
  department: string;
  appointment_slot: string | null;
  confirmed: boolean;
  notes: string | null;
  created_at: string | null;
};

export type Transcript = {
  id: string;
  call_id: string;
  phone: string;
  content_preview: string;
  analysis: Record<string, unknown> | null;
  turn_count: number;
  created_at: string;
};

function getToken() {
  if (typeof window === "undefined") {
    return "";
  }

  return window.localStorage.getItem("token") || "";
}

async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, headers } = options;
  const requestHeaders = new Headers(headers);

  if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = getToken();
    if (token) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const errorBody = await response.json();
      message = errorBody.detail || errorBody.error || message;
    } catch {
      // Ignore JSON parse failures for non-JSON error bodies.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function login(username: string, password: string) {
  return apiFetch<{
    access_token: string;
    token_type: string;
    username: string;
    role: string;
  }>("/auth/login", {
    method: "POST",
    auth: false,
    body: { username, password },
  });
}

export async function getDashboardData() {
  return apiFetch<DashboardData>("/dashboard-data");
}

export async function getAppointments(limit = 100) {
  return apiFetch<{
    appointments: Appointment[];
    count: number;
  }>(`/appointments?limit=${limit}`);
}

export async function getTranscripts(limit = 50) {
  return apiFetch<{
    transcripts: Transcript[];
  }>(`/transcripts?limit=${limit}`);
}
