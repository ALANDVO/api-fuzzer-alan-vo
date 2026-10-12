import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { FuzzJobRunner } from '../components/FuzzJobRunner';
import { AuthProvider } from '../context/AuthContext';

vi.mock('../api/client', () => ({
  api: {
    login: vi.fn().mockResolvedValue({
      access_token: 'mock-token',
      token_type: 'Bearer',
      expires_in_seconds: 7200,
      user_id: 'op-1',
      email: 'operator@example.com',
      roles: ['operator'],
    }),
    listSpecs: vi.fn().mockResolvedValue([
      {
        id: 'spec-01',
        name: 'Target Banking API',
        version: '1.0.0',
        format: 'json',
        endpoints_count: 5,
        endpoints: [],
        created_at: new Date().toISOString(),
        created_by: 'alanvo@gmail.com',
      },
    ]),
    listJobs: vi.fn().mockResolvedValue([]),
  },
  setAccessToken: vi.fn(),
}));

describe('FuzzJobRunner Component', () => {
  it('renders attack dimensions and configuration controls', async () => {
    const onViewJobFindingsMock = vi.fn();
    render(
      <AuthProvider>
        <FuzzJobRunner onViewJobFindings={onViewJobFindingsMock} />
      </AuthProvider>
    );

    expect(await screen.findByText('Adversarial Fuzz Execution')).toBeDefined();
    expect(await screen.findByText('Target Base URL')).toBeDefined();
    expect(await screen.findByText('Job Configuration')).toBeDefined();
    expect(await screen.findByText('Execution History')).toBeDefined();
    expect(await screen.findByRole('button', { name: /Execute Fuzz Suite/i })).toBeDefined();
  });
});
