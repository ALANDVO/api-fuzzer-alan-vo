import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatsOverview } from '../types';

export const Dashboard: React.FC<{ onNavigate: (tab: string) => void }> = ({ onNavigate }) => {
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      setStats(await api.getStats());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStats(); }, []);

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
        <span className="ml-3 text-slate-400">Loading fuzzer metrics...</span>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="p-6 bg-rose-950/30 border border-rose-800 rounded-xl m-6 text-rose-300">
        <h3 className="font-semibold text-lg mb-2">Metrics Error</h3>
        <p className="text-sm mb-4">{error}</p>
        <button onClick={fetchStats} className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm">Retry</button>
      </div>
    );
  }

  const sev = stats?.findings_by_severity || { critical: 0, moderate: 0, minor: 0, pass: 0 };
  const totalFindings = stats?.total_findings || 0;

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 border border-slate-700/60 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">API Security Fuzzing Center</h1>
          <p className="text-slate-400 text-sm mt-1">Automated OpenAPI adversarial testing, boundary verification, and deterministic severity scoring.</p>
        </div>
        <div className="flex space-x-3">
          <button onClick={() => onNavigate('specs')} className="px-4 py-2 bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-sm font-medium hover:bg-slate-700">Manage Specs</button>
          <button onClick={() => onNavigate('runner')} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium shadow-md">Launch Fuzz Run</button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'OpenAPI Specs', val: stats?.total_specs ?? 0, sub: 'Registered target schemas', color: 'text-white' },
          { label: 'Fuzz Jobs', val: stats?.total_jobs ?? 0, sub: 'Completed test suites', color: 'text-indigo-400' },
          { label: 'Test Cases Fuzzed', val: stats?.total_cases_fuzzed ?? 0, sub: 'Mutated adversarial payloads', color: 'text-cyan-400' },
          { label: 'Discovered Findings', val: totalFindings, sub: `${sev.critical} critical vulnerabilities`, color: 'text-amber-400' },
        ].map((c, i) => (
          <div key={i} className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-5 shadow-sm">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{c.label}</div>
            <div className={`mt-2 text-3xl font-extrabold ${c.color}`}>{c.val}</div>
            <div className="mt-1 text-xs text-slate-500">{c.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/70 border border-slate-700/80 rounded-xl p-6 shadow-sm">
          <h2 className="text-base font-semibold text-white mb-4">Severity Distribution</h2>
          <div className="space-y-4">
            {[
              { label: 'Critical (Crashes / Injection)', count: sev.critical, color: 'bg-rose-500', text: 'text-rose-400' },
              { label: 'Moderate (Status Mismatch)', count: sev.moderate, color: 'bg-amber-500', text: 'text-amber-400' },
              { label: 'Minor (Latency >2.5s)', count: sev.minor, color: 'bg-yellow-400', text: 'text-yellow-400' },
              { label: 'Conforming / Passed Tests', count: sev.pass, color: 'bg-emerald-500', text: 'text-emerald-400', denom: stats?.total_cases_fuzzed },
            ].map((s, idx) => (
              <div key={idx}>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className={s.text}>{s.label}</span>
                  <span className="text-slate-300">{s.count}</span>
                </div>
                <div className="w-full bg-slate-700/50 rounded-full h-2.5 overflow-hidden">
                  <div className={`${s.color} h-2.5 rounded-full transition-all duration-500`} style={{ width: `${(s.denom ? (s.count / s.denom) : (totalFindings ? (s.count / totalFindings) : 0)) * 100}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-800/70 border border-slate-700/80 rounded-xl p-6 shadow-sm">
          <h2 className="text-base font-semibold text-white mb-4">Findings by Attack Dimension</h2>
          {Object.keys(stats?.findings_by_dimension || {}).length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">No security findings recorded yet. Run a fuzz suite to populate telemetry.</div>
          ) : (
            <div className="space-y-3">
              {Object.entries(stats?.findings_by_dimension || {}).map(([dim, count]) => (
                <div key={dim} className="flex justify-between items-center p-2.5 rounded-lg bg-slate-900/40 border border-slate-800 text-xs">
                  <span className="text-slate-300 font-mono font-medium">{dim.replace('_', ' ')}</span>
                  <span className="px-2.5 py-0.5 rounded-full font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
