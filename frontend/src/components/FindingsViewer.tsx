import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { FindingSeverity, FuzzJob, TestResult } from '../types';
import { ExportModal } from './ExportModal';

export const FindingsViewer: React.FC<{ initialJobId?: string | null }> = ({ initialJobId }) => {
  const [jobs, setJobs] = useState<FuzzJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>(initialJobId || '');
  const [results, setResults] = useState<TestResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedResult, setSelectedResult] = useState<TestResult | null>(null);
  const [copiedCurl, setCopiedCurl] = useState<boolean>(false);
  const [isExportOpen, setIsExportOpen] = useState<boolean>(false);

  useEffect(() => {
    api.listJobs().then((list) => {
      setJobs(list);
      if (list.length > 0 && !selectedJobId) setSelectedJobId(initialJobId || list[0].id);
    }).catch((e) => console.error(e));
  }, [initialJobId]);

  useEffect(() => {
    if (!selectedJobId) return;
    setLoading(true);
    api.getJobDetail(selectedJobId, severityFilter !== 'all' ? severityFilter : undefined)
      .then((d) => setResults(d.results))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedJobId, severityFilter]);

  const copyCurl = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCurl(true);
    setTimeout(() => setCopiedCurl(false), 2000);
  };

  const filtered = results.filter((r) => {
    if (!searchTerm) return true;
    const q = searchTerm.toLowerCase();
    return r.test_name.toLowerCase().includes(q) || r.endpoint.toLowerCase().includes(q) || r.dimension.toLowerCase().includes(q);
  });

  const badgeClass = (sev: FindingSeverity) => {
    const m: Record<FindingSeverity, string> = {
      critical: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
      moderate: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
      minor: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
      pass: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    };
    return `px-2 py-0.5 rounded text-[11px] font-bold uppercase border ${m[sev]}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Security Findings & Telemetry</h2>
          <p className="text-sm text-slate-400">Detailed test outcomes, curl reproduction commands, and advisory notes.</p>
        </div>
        {selectedJobId && (
          <button
            onClick={() => setIsExportOpen(true)}
            className="px-4 py-2 bg-slate-800 text-slate-200 border border-slate-700 rounded-lg text-sm font-medium hover:bg-slate-700"
          >
            Export Report (JSON / MD / SARIF)
          </button>
        )}
      </div>

      <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="flex items-center space-x-2 w-full md:w-auto">
          <label className="text-xs text-slate-400 font-medium">Job:</label>
          <select
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none"
          >
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>{j.id.slice(0, 8)} — {j.target_base_url} ({j.findings_count} findings)</option>
            ))}
          </select>
        </div>

        <div className="flex space-x-1.5 overflow-x-auto">
          {['all', 'critical', 'moderate', 'minor', 'pass'].map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition ${
                severityFilter === s ? 'bg-indigo-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-700'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        <input
          type="text"
          placeholder="Search findings..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 w-full md:w-56 focus:outline-none"
        />
      </div>

      {error && <div className="p-4 bg-rose-950/40 border border-rose-800 rounded-xl text-rose-300 text-sm">{error}</div>}

      {loading ? (
        <div className="p-12 text-center text-slate-400 text-sm">Loading test findings...</div>
      ) : filtered.length === 0 ? (
        <div className="p-12 text-center text-slate-500 text-sm bg-slate-800/40 rounded-xl border border-slate-700/60">
          No test results match the selected filter criteria.
        </div>
      ) : (
        <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/60 border-b border-slate-700 text-slate-400 uppercase font-semibold">
              <tr>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Test Name</th>
                <th className="py-3 px-4">Endpoint</th>
                <th className="py-3 px-4">Dimension</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Latency</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {filtered.map((r) => (
                <tr key={r.id} onClick={() => setSelectedResult(r)} className="hover:bg-slate-700/30 transition cursor-pointer">
                  <td className="py-3 px-4"><span className={badgeClass(r.severity)}>{r.severity}</span></td>
                  <td className="py-3 px-4 font-semibold text-white">{r.test_name}</td>
                  <td className="py-3 px-4 font-mono text-slate-300"><span className="text-indigo-400 font-bold mr-1">{r.method}</span>{r.endpoint}</td>
                  <td className="py-3 px-4 text-slate-400 text-[11px] font-mono">{r.dimension.replace('_', ' ')}</td>
                  <td className="py-3 px-4 font-mono font-bold text-slate-300">{r.status_code ?? 'ERR'}</td>
                  <td className="py-3 px-4 text-slate-400">{r.latency_ms.toFixed(1)}ms</td>
                  <td className="py-3 px-4 text-right">
                    <button className="px-2.5 py-1 bg-slate-700 hover:bg-indigo-600 text-slate-200 rounded text-xs">Inspect</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedResult && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <span className={badgeClass(selectedResult.severity)}>{selectedResult.severity}</span>
                <h3 className="font-bold text-sm text-white">{selectedResult.test_name}</h3>
              </div>
              <button onClick={() => setSelectedResult(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="grid grid-cols-4 gap-2 bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
              <div><span className="text-slate-500 block text-[10px]">Route</span><span className="font-mono text-slate-200">{selectedResult.method} {selectedResult.endpoint}</span></div>
              <div><span className="text-slate-500 block text-[10px]">Status</span><span className="font-mono font-bold text-slate-200">{selectedResult.status_code ?? 'CRASH'}</span></div>
              <div><span className="text-slate-500 block text-[10px]">Latency</span><span className="font-mono text-slate-200">{selectedResult.latency_ms.toFixed(1)}ms</span></div>
              <div><span className="text-slate-500 block text-[10px]">Dimension</span><span className="font-mono text-indigo-400">{selectedResult.dimension}</span></div>
            </div>

            <div>
              <span className="text-xs text-slate-400 font-semibold block mb-1">Reasoning</span>
              <p className="text-xs text-slate-200 bg-slate-800/60 p-2.5 rounded border border-slate-700/60">{selectedResult.reasoning}</p>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400 font-semibold">Reproduction curl</span>
                <button onClick={() => copyCurl(selectedResult.reproduction_curl)} className="text-indigo-400 hover:underline">
                  {copiedCurl ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <pre className="bg-slate-950 border border-slate-800 text-indigo-300 p-2.5 rounded text-xs font-mono overflow-x-auto whitespace-pre-wrap">{selectedResult.reproduction_curl}</pre>
            </div>

            {selectedResult.response_body && (
              <div>
                <span className="text-xs text-slate-400 font-semibold block mb-1">Response Body</span>
                <pre className="bg-slate-950 border border-slate-800 text-slate-300 p-2.5 rounded text-xs font-mono max-h-32 overflow-y-auto whitespace-pre-wrap">{selectedResult.response_body}</pre>
              </div>
            )}

            {selectedResult.advisory_notes && (
              <div className="bg-indigo-950/30 border border-indigo-800/50 rounded p-2.5 text-xs text-indigo-200">
                <span className="font-bold text-indigo-400 block mb-1">Advisory LLM Note</span>
                {selectedResult.advisory_notes}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button onClick={() => setSelectedResult(null)} className="px-4 py-1.5 bg-slate-800 text-slate-200 rounded text-xs">Close</button>
            </div>
          </div>
        </div>
      )}

      {isExportOpen && <ExportModal jobId={selectedJobId} onClose={() => setIsExportOpen(false)} />}
    </div>
  );
};
