import React, { useState } from 'react';
import { api } from '../api/client';

interface ExportModalProps {
  jobId: string;
  onClose: () => void;
}

export const ExportModal: React.FC<ExportModalProps> = ({ jobId, onClose }) => {
  const [selectedFormat, setSelectedFormat] = useState<'json' | 'markdown' | 'sarif'>('json');
  const [downloading, setDownloading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    try {
      setDownloading(true);
      setError(null);
      const blob = await api.downloadExport(jobId, selectedFormat);
      const ext = selectedFormat === 'markdown' ? 'md' : selectedFormat;
      const filename = `api-fuzz-report-${jobId.slice(0, 8)}.${ext}`;

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h3 className="font-bold text-base text-white">Export Security Audit Report</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white font-bold">✕</button>
        </div>

        {error && (
          <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg text-rose-300 text-xs">
            {error}
          </div>
        )}

        <div className="space-y-3">
          <p className="text-xs text-slate-400">Select export format for Job <span className="font-mono text-slate-200">{jobId.slice(0, 8)}</span>:</p>

          {[
            {
              id: 'json',
              title: 'Structured JSON Document',
              desc: 'Complete machine-readable telemetry, findings, and reproduction curls.',
            },
            {
              id: 'markdown',
              title: 'GitHub-Flavored Markdown',
              desc: 'Human-readable security audit report with vulnerability tables and curl blocks.',
            },
            {
              id: 'sarif',
              title: 'SARIF 2.1.0 Interchange Format',
              desc: 'OASIS standard static analysis results for GitHub Security & CodeQL ingestion.',
            },
          ].map((fmt) => (
            <div
              key={fmt.id}
              onClick={() => setSelectedFormat(fmt.id as any)}
              className={`p-3 rounded-xl border cursor-pointer transition ${
                selectedFormat === fmt.id
                  ? 'bg-indigo-950/30 border-indigo-500 shadow-sm'
                  : 'bg-slate-800/50 border-slate-700/60 hover:bg-slate-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-white">{fmt.title}</span>
                <span className="text-[10px] font-mono uppercase text-indigo-400 font-bold">{fmt.id}</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1">{fmt.desc}</p>
            </div>
          ))}
        </div>

        <div className="flex justify-end space-x-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs"
          >
            Cancel
          </button>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/20"
          >
            {downloading ? 'Exporting...' : 'Download Report'}
          </button>
        </div>
      </div>
    </div>
  );
};
