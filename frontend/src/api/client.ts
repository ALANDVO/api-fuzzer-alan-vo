/**
 * Typed HTTP client with in-memory Bearer token authentication.
 * Per security contract: Access tokens are stored strictly in memory, never persisted to localStorage.
 */
import {
  AuthResponse,
  EvaluationMetrics,
  FuzzJob,
  FuzzJobDetail,
  Spec,
  StatsOverview,
  User
} from '../types';

let inMemoryAccessToken: string | null = null;

export const setAccessToken = (token: string | null): void => {
  inMemoryAccessToken = token;
};

export const getAccessToken = (): string | null => {
  return inMemoryAccessToken;
};

const getHeaders = (contentType: string = 'application/json'): HeadersInit => {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };
  if (contentType) {
    headers['Content-Type'] = contentType;
  }
  if (inMemoryAccessToken) {
    headers['Authorization'] = `Bearer ${inMemoryAccessToken}`;
  }
  return headers;
};

const handleResponse = async <T>(res: Response): Promise<T> => {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = data.detail;
      }
    } catch {
      // ignore json decode error on plain text response
    }
    throw new Error(errorDetail);
  }
  if (res.status === 204) {
    return {} as T;
  }
  return res.json() as Promise<T>;
};

export const api = {
  // Auth
  async login(email: string, role: string = 'operator'): Promise<AuthResponse> {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, role }),
    });
    const authData = await handleResponse<AuthResponse>(res);
    setAccessToken(authData.access_token);
    return authData;
  },

  async getMe(): Promise<User> {
    const res = await fetch('/api/auth/me', {
      headers: getHeaders(),
    });
    return handleResponse<User>(res);
  },

  async logout(): Promise<void> {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: getHeaders(),
      });
    } finally {
      setAccessToken(null);
    }
  },

  async getHealth(): Promise<{ status: string; version: string; env: string; demo_mode: string }> {
    const res = await fetch('/api/health');
    return handleResponse(res);
  },

  // Specs
  async listSpecs(search?: string): Promise<Spec[]> {
    const url = search ? `/api/specs?search=${encodeURIComponent(search)}` : '/api/specs';
    const res = await fetch(url, { headers: getHeaders() });
    return handleResponse<Spec[]>(res);
  },

  async getSpec(id: string): Promise<Spec> {
    const res = await fetch(`/api/specs/${id}`, { headers: getHeaders() });
    return handleResponse<Spec>(res);
  },

  async uploadSpec(name: string, raw_spec: string, version: string = '1.0.0'): Promise<Spec> {
    const res = await fetch('/api/specs', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ name, raw_spec, version }),
    });
    return handleResponse<Spec>(res);
  },

  async deleteSpec(id: string): Promise<void> {
    const res = await fetch(`/api/specs/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    return handleResponse<void>(res);
  },

  // Jobs
  async createJob(params: {
    spec_id: string;
    target_base_url: string;
    dimensions: string[];
    cases_per_endpoint: number;
    max_endpoints: number;
    enable_llm_advisory: boolean;
  }): Promise<FuzzJobDetail> {
    const res = await fetch('/api/jobs', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(params),
    });
    return handleResponse<FuzzJobDetail>(res);
  },

  async listJobs(): Promise<FuzzJob[]> {
    const res = await fetch('/api/jobs', { headers: getHeaders() });
    return handleResponse<FuzzJob[]>(res);
  },

  async getJobDetail(id: string, severity?: string): Promise<FuzzJobDetail> {
    const url = severity ? `/api/jobs/${id}?severity=${encodeURIComponent(severity)}` : `/api/jobs/${id}`;
    const res = await fetch(url, { headers: getHeaders() });
    return handleResponse<FuzzJobDetail>(res);
  },

  async downloadExport(id: string, format: 'json' | 'markdown' | 'sarif'): Promise<Blob> {
    const res = await fetch(`/api/jobs/${id}/export?format=${format}`, {
      headers: getHeaders(''),
    });
    if (!res.ok) {
      throw new Error(`Failed to export report in ${format} format`);
    }
    return res.blob();
  },

  // Stats & Evaluation
  async getStats(): Promise<StatsOverview> {
    const res = await fetch('/api/stats', { headers: getHeaders() });
    return handleResponse<StatsOverview>(res);
  },

  async getEvaluationBenchmark(): Promise<EvaluationMetrics> {
    const res = await fetch('/api/evaluation/benchmark', { headers: getHeaders() });
    return handleResponse<EvaluationMetrics>(res);
  },
};
