import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { EvaluationMetrics } from '../types';

export const EvaluationView: React.FC = () => {
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBenchmark = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getEvaluationBenchmark();
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute evaluation benchmark');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBenchmark();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">AI/ML Security Evaluation Benchmark</h2>
          <p className="text-sm text-slate-400">
            Reproducible ground-truth evaluation across 24 curated API vulnerability scenarios and 6 attack dimensions.
          </p>
        </div>
        <button
          onClick={fetchBenchmark}
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition shadow-md shadow-indigo-600/20"
        >
          {loading ? 'Evaluating...' : 'Rerun Benchmark'}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-800 rounded-xl text-rose-300 text-sm">
          {error}
        </div>
      )}

      {loading && !metrics ? (
        <div className="p-12 text-center text-slate-400 text-sm">Executing benchmark suite...</div>
      ) : metrics ? (
        <div className="space-y-6">
          {/* Top Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Baseline Accuracy</div>
              <div className="mt-2 text-3xl font-extrabold text-slate-300">
                {(metrics.baseline_accuracy * 100).toFixed(1)}%
              </div>
              <div className="mt-1 text-xs text-slate-500">Naive HTTP status classifier</div>
            </div>

            <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Heuristic Classifier</div>
              <div className="mt-2 text-3xl font-extrabold text-indigo-400">
                {(metrics.heuristic_accuracy * 100).toFixed(1)}%
              </div>
              <div className="mt-1 text-xs text-emerald-400">
                +{((metrics.heuristic_accuracy - metrics.baseline_accuracy) * 100).toFixed(1)}% improvement
              </div>
            </div>

            <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Precision</div>
              <div className="mt-2 text-3xl font-extrabold text-emerald-400">
                {(metrics.precision_critical * 100).toFixed(1)}%
              </div>
              <div className="mt-1 text-xs text-slate-500">0 false positive critical alerts</div>
            </div>

            <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical F1-Score</div>
              <div className="mt-2 text-3xl font-extrabold text-cyan-400">
                {(metrics.f1_score * 100).toFixed(1)}%
              </div>
              <div className="mt-1 text-xs text-slate-500">
                Recall: {(metrics.recall_critical * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Dimension Breakdown Table */}
          <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-6">
            <h3 className="text-base font-semibold text-white mb-4">Dimension Performance Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-700 text-slate-400 uppercase font-semibold">
                    <th className="pb-3">Attack Dimension</th>
                    <th className="pb-3">Benchmark Cases</th>
                    <th className="pb-3">Accuracy</th>
                    <th className="pb-3">Evaluation Assessment</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {Object.entries(metrics.dimension_metrics).map(([dim, data]) => (
                    <tr key={dim} className="hover:bg-slate-700/20">
                      <td className="py-3 font-mono text-slate-200 font-semibold">{dim.replace('_', ' ')}</td>
                      <td className="py-3 text-slate-300">{data.cases}</td>
                      <td className="py-3 font-bold text-indigo-400">{(data.accuracy * 100).toFixed(1)}%</td>
                      <td className="py-3 text-slate-400">
                        {data.accuracy >= 1.0 ? (
                          <span className="text-emerald-400 font-medium">100% Deterministic match</span>
                        ) : (
                          <span className="text-amber-400 font-medium">Borderline validation boundary</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Methodology & Limitations */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-400 bg-slate-900/60 p-6 rounded-xl border border-slate-800">
            <div>
              <h4 className="font-bold text-slate-200 uppercase tracking-wider mb-2">Evaluation Methodology</h4>
              <p className="leading-relaxed">
                The benchmark evaluates classification accuracy across a curated dataset of 24 labeled API response
                scenarios. It measures the ability to detect SQL injections, traversal leaks, unhandled 500 exceptions,
                and unauthorized privilege escalation compared to a status-code-only baseline.
              </p>
            </div>
            <div>
              <h4 className="font-bold text-slate-200 uppercase tracking-wider mb-2">Failure Cases & Limitations</h4>
              <p className="leading-relaxed">
                Heuristic parsing may fail when custom API endpoints wrap database syntax errors inside 200 OK JSON envelopes
                without standard error keys. In these ambiguous cases, opt-in LLM advisory reasoning provides contextual
                disambiguation.
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
