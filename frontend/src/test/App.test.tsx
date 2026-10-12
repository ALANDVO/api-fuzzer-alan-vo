import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import App from '../App';

// Mock fetch for all API calls in tests
(globalThis as any).fetch = vi.fn().mockImplementation((url: string) => {
  if (url.includes('/api/auth/login')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        access_token: 'mock-test-token',
        token_type: 'Bearer',
        expires_in_seconds: 7200,
        user_id: 'test-user',
        email: 'operator@example.com',
        roles: ['operator'],
      }),
    });
  }
  if (url.includes('/api/stats')) {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        total_specs: 3,
        total_jobs: 5,
        total_cases_fuzzed: 45,
        total_findings: 8,
        findings_by_severity: { critical: 2, moderate: 4, minor: 2, pass: 37 },
        findings_by_dimension: { injection_payloads: 2, boundary_values: 3 },
      }),
    });
  }
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve([]),
  });
}) as any;

describe('App Root and Navigation', () => {
  it('renders application branding and header elements', async () => {
    render(<App />);
    expect(await screen.findByText('api-fuzzer')).toBeDefined();
    const authorBadges = await screen.findAllByText(/Alan Vo/i);
    expect(authorBadges.length).toBeGreaterThan(0);
    expect(await screen.findByText('Dashboard')).toBeDefined();
    const specsButtons = await screen.findAllByText(/OpenAPI Specs/i);
    expect(specsButtons.length).toBeGreaterThan(0);
    expect(await screen.findByText('Fuzz Runner')).toBeDefined();
    expect(await screen.findByText('AI/ML Benchmark')).toBeDefined();
  });

  it('renders author metadata and footer copyright', async () => {
    render(<App />);
    const footerElement = await screen.findByText(/alanvo@gmail.com/i);
    expect(footerElement).toBeDefined();
  });
});
