import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { FuzzJob, Spec } from '../types';

export const FuzzJobRunner: React.FC<{ onViewJobFindings: (jobId: string) => void }> = ({ onViewJobFindings }) => {
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [jobs, setJobs] = useState<FuzzJob[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedSpecId, setSelectedSpecId] = useState<string>('');
  const [targetBaseUrl, setTargetBaseUrl] = useState<string>('http://127.0.0.1:8000');
  const [casesPerEndpoint, setCasesPerEndpoint] = useState<number>(4);
  const [maxEndpoints, setMaxEndpoints] = useState<number>(5);
  const [enableLlm, setEnableLlm] = useState<boolean>(false);

  const [dimensions, setDimensions] = useState<Record<string, boolean>>({
    boundary_values: true,
    type_coercion: true,
    injection_payloads: true,
    auth_bypass: true,
    idempotency_race: true,
    unicode_locale: true,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [specList, jobList] = await Promise.all([api.listSpecs(), api.listJobs()]);
      setSpecs(specList);
      setJobs(jobList);
      if (specList.length > 0 && !selectedSpecId) setSelectedSpecId(specList[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load test runner data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSpecId) return setError('Please select an OpenAPI specification to fuzz.');

    const active = Object.entries(dimensions).filter(([_, v]) => v).map(([k]) => k);
    if (active.length === 0) return setError('Select at least one attack dimension.');

    try {
      setRunning(true);
      setError(null);
      const result = await api.createJob({
        spec_id: selectedSpecId,
        target_base_url: targetBaseUrl.trim(),
        dimensions: active,
        cases_per_endpoint: casesPerEndpoint,
        max_endpoints: maxEndpoints,
        enable_llm_advisory: enableLlm,
      });
      await loadData();
      onViewJobFindings(result.job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Job execution failed');
    } finally {
      setRunning(false);
    }
  };

  const dimLabels: Record<string, string> = {
    boundary_values: 'Boundary Values (Min/Max/Empty/Oversized)',
    type_coercion: 'Type Coercion (String/Int/Null Mismatch)',
    injection_payloads: 'Injection Payloads (SQLi/XSS/Traversal)',
    auth_bypass: 'Auth Bypass (Missing/Forged Tokens)',
    idempotency_race: 'Idempotency & Concurrent Duplication',
    unicode_locale: 'Unicode & Locale Boundary Exploits',
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Adversarial Fuzz Execution</h2>
        <p className="text-sm text-slate-400">Synthesize boundary and injection payloads, execute against endpoints, and isolate vulnerabilities.</p>
      </div>

      {error && <div className="p-4 bg-rose-950/40 border border-rose-800 rounded-xl text-rose-300 text-sm">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-slate-800/80 border border-slate-700/80 rounded-xl p-6 shadow-sm">
          <h3 className="text-base font-semibold text-white mb-4">Job Configuration</h3>
          <form onSubmit={handleLaunch} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Target Specification</label>
              {specs.length === 0 ? (
                <div className="text-xs text-amber-400 p-2 bg-amber-950/30 rounded border border-amber-800">
                  No specs available. Upload one in the Specs tab first.
                </div>
              ) : (
                <select
                  value={selectedSpecId}
                  onChange={(e) => setSelectedSpecId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none"
                >
                  {specs.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.endpoints_count} endpoints)</option>)}
                </select>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Target Base URL</label>
              <input
                type="text"
                value={targetBaseUrl}
                onChange={(e) => setTargetBaseUrl(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700 text-slate-100 font-mono rounded-lg px-3 py-2 text-sm focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2">Attack Dimensions</label>
              <div className="space-y-1.5">
                {Object.keys(dimLabels).map((d) => (
                  <label key={d} className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={dimensions[d]}
                      onChange={() => setDimensions((p) => ({ ...p, [d]: !p[d] }))}
                      className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                    />
                    <span>{dimLabels[d]}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">Cases/Route ({casesPerEndpoint})</label>
                <input type="range" min="1" max="10" value={casesPerEndpoint} onChange={(e) => setCasesPerEndpoint(parseInt(e.target.value))} className="w-full" />
              </div>
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">Max Routes ({maxEndpoints})</label>
                <input type="range" min="1" max="10" value={maxEndpoints} onChange={(e) => setMaxEndpoints(parseInt(e.target.value))} className="w-full" />
              </div>
            </div>

            <div className="pt-2 border-t border-slate-700/60">
              <label className="flex items-start space-x-2 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" checked={enableLlm} onChange={(e) => setEnableLlm(e.target.checked)} className="mt-0.5 rounded bg-slate-900 border-slate-700 text-indigo-600" />
                <div>
                  <span className="font-semibold text-indigo-400">Opt-in LLM Advisory Analysis</span>
                  <p className="text-[10px] text-slate-500 mt-0.5">Advisory remediation notes grounded in actual records. Deterministic offline core runs without keys.</p>
                </div>
              </label>
            </div>

            <button
              type="submit"
              disabled={running || specs.length === 0}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition shadow-md shadow-indigo-600/30"
            >
              {running ? 'Fuzzing Live Endpoints...' : 'Execute Fuzz Suite'}
            </button>
          </form>
        </div>

        <div className="lg:col-span-2 bg-slate-800/80 border border-slate-700/80 rounded-xl p-6 shadow-sm">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-base font-semibold text-white">Execution History</h3>
            <button onClick={loadData} className="text-xs text-slate-400 hover:text-white">Refresh</button>
          </div>

          {loading && jobs.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">Loading job records...</div>
          ) : jobs.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-sm bg-slate-900/40 rounded-lg border border-slate-800">
              No fuzz runs recorded yet. Configure parameters on the left and launch a run.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-700 text-slate-400 uppercase font-semibold">
                    <th className="pb-3">Job ID</th>
                    <th className="pb-3">Target Base URL</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">Cases</th>
                    <th className="pb-3">Findings</th>
                    <th className="pb-3">Timestamp</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {jobs.map((j) => (
                    <tr key={j.id} className="hover:bg-slate-700/30 transition">
                      <td className="py-3 font-mono text-slate-300">{j.id.slice(0, 8)}</td>
                      <td className="py-3 font-mono text-slate-200">{j.target_base_url}</td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          j.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                        }`}>{j.status}</span>
                      </td>
                      <td className="py-3 text-slate-300">{j.total_cases}</td>
                      <td className="py-3"><span className={`font-semibold ${j.findings_count > 0 ? 'text-amber-400' : 'text-slate-400'}`}>{j.findings_count}</span></td>
                      <td className="py-3 text-slate-400">{new Date(j.created_at).toLocaleTimeString()}</td>
                      <td className="py-3 text-right">
                        <button onClick={() => onViewJobFindings(j.id)} className="px-2.5 py-1 bg-slate-700 hover:bg-indigo-600 text-slate-200 rounded text-xs">View Results</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
