import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { Dashboard } from '../components/Dashboard';

vi.mock('../api/client', () => ({
  api: {
    getStats: vi.fn().mockResolvedValue({
      total_specs: 4,
      total_jobs: 8,
      total_cases_fuzzed: 64,
      total_findings: 12,
      findings_by_severity: { critical: 3, moderate: 5, minor: 4, pass: 52 },
      findings_by_dimension: { injection_payloads: 3, boundary_values: 5, auth_bypass: 4 },
    }),
  },
}));

describe('Dashboard Component', () => {
  it('displays accurate telemetry metrics from API', async () => {
    const onNavigateMock = vi.fn();
    render(<Dashboard onNavigate={onNavigateMock} />);

    expect(await screen.findByText('API Security Fuzzing Center')).toBeDefined();
    expect(await screen.findByText(/3 critical vulnerabilities/i)).toBeDefined();
    expect(await screen.findByText('Severity Distribution')).toBeDefined();
    expect(await screen.findByText('Findings by Attack Dimension')).toBeDefined();
    expect(await screen.findByText('Mutated adversarial payloads')).toBeDefined();
  });
});
