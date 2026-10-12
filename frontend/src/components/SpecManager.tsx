import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { EndpointSummary, Spec } from '../types';
import sampleSpecJson from '../data/sample_spec.json';

const SAMPLE_SPEC = JSON.stringify(sampleSpecJson, null, 2);

export const SpecManager: React.FC = () => {
  const { role } = useAuth();
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>('');
  const [selectedSpec, setSelectedSpec] = useState<Spec | null>(null);

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [specName, setSpecName] = useState<string>('');
  const [specVersion, setSpecVersion] = useState<string>('1.0.0');
  const [rawSpec, setRawSpec] = useState<string>('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fetchSpecs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listSpecs(search);
      setSpecs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch specs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSpecs();
  }, [search]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!specName.trim() || !rawSpec.trim()) {
      setUploadError('Please provide a specification name and content.');
      return;
    }

    try {
      setIsSubmitting(true);
      setUploadError(null);
      await api.uploadSpec(specName.trim(), rawSpec.trim(), specVersion.trim());
      setIsModalOpen(false);
      setSpecName('');
      setRawSpec('');
      fetchSpecs();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (specId: string) => {
    if (!confirm('Are you sure you want to delete this specification?')) return;
    try {
      await api.deleteSpec(specId);
      if (selectedSpec?.id === specId) setSelectedSpec(null);
      fetchSpecs();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const methodClass = (m: string) => {
    const map: Record<string, string> = {
      GET: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      POST: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
      PUT: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      DELETE: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    };
    return map[m] || 'bg-slate-700 text-slate-300';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">OpenAPI Specifications</h2>
          <p className="text-sm text-slate-400">Manage target schemas, inspect endpoints, and configure fuzz boundaries.</p>
        </div>
        <div className="flex items-center space-x-3">
          <input
            type="text"
            placeholder="Search specs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500"
          />
          <button
            onClick={() => {
              setRawSpec(SAMPLE_SPEC);
              setSpecName('Sample PetStore Target');
              setIsModalOpen(true);
            }}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition shadow-md shadow-indigo-600/20"
          >
            Upload Spec
          </button>
        </div>
      </div>

      {error && <div className="p-4 bg-rose-950/30 border border-rose-800 rounded-lg text-rose-300 text-sm">{error}</div>}

      {loading && specs.length === 0 ? (
        <div className="p-12 text-center text-slate-400">Loading OpenAPI specs...</div>
      ) : specs.length === 0 ? (
        <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-12 text-center">
          <div className="text-3xl mb-3">📄</div>
          <h3 className="text-base font-semibold text-white">No specifications uploaded</h3>
          <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">Upload an OpenAPI schema or click below to load the PetStore sample.</p>
          <button
            onClick={() => {
              setRawSpec(SAMPLE_SPEC);
              setSpecName('Sample PetStore Target');
              setIsModalOpen(true);
            }}
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium"
          >
            Load Sample Target Spec
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-3">
            {specs.map((s) => (
              <div
                key={s.id}
                onClick={() => setSelectedSpec(s)}
                className={`p-4 rounded-xl border transition cursor-pointer ${
                  selectedSpec?.id === s.id
                    ? 'bg-indigo-950/20 border-indigo-500 shadow-md'
                    : 'bg-slate-800/60 border-slate-700/70 hover:bg-slate-800 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-sm text-white">{s.name}</h4>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-700 text-slate-300 uppercase font-mono">{s.format}</span>
                </div>
                <div className="text-xs text-slate-400 mt-1">Version: {s.version}</div>
                <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
                  <span>{s.endpoints_count} endpoints parsed</span>
                  {role === 'admin' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(s.id);
                      }}
                      className="text-rose-400 hover:text-rose-300 font-medium"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="lg:col-span-2 bg-slate-800/60 border border-slate-700/70 rounded-xl p-6">
            {selectedSpec ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-700">
                  <div>
                    <h3 className="font-bold text-lg text-white">{selectedSpec.name}</h3>
                    <p className="text-xs text-slate-400">Created by {selectedSpec.created_by}</p>
                  </div>
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    {selectedSpec.endpoints.length} Endpoints
                  </span>
                </div>
                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                  {selectedSpec.endpoints.map((ep: EndpointSummary, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1.5">
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold border font-mono ${methodClass(ep.method)}`}>
                          {ep.method}
                        </span>
                        <span className="text-sm font-mono text-slate-200 font-semibold">{ep.path}</span>
                      </div>
                      <p className="text-xs text-slate-400">{ep.summary || 'No description'}</p>
                      {ep.params.length > 0 && (
                        <div className="text-[11px] text-slate-500 flex flex-wrap gap-1">
                          <span className="text-slate-400">Params:</span>
                          {ep.params.map((p, pIdx) => (
                            <span key={pIdx} className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-300 font-mono">
                              {p.name} ({p.in})
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
                Select a specification on the left to inspect parsed routes and parameter schemas.
              </div>
            )}
          </div>
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-lg text-white">Upload OpenAPI Specification</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            {uploadError && <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg text-rose-300 text-xs">{uploadError}</div>}
            <form onSubmit={handleUpload} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Name</label>
                  <input
                    type="text"
                    value={specName}
                    onChange={(e) => setSpecName(e.target.value)}
                    required
                    className="w-full bg-slate-800 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Version</label>
                  <input
                    type="text"
                    value={specVersion}
                    onChange={(e) => setSpecVersion(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Specification (JSON/YAML)</label>
                  <button type="button" onClick={() => setRawSpec(SAMPLE_SPEC)} className="text-xs text-indigo-400">
                    Paste PetStore Sample
                  </button>
                </div>
                <textarea
                  rows={9}
                  value={rawSpec}
                  onChange={(e) => setRawSpec(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 font-mono text-xs text-slate-200 rounded-lg p-3 focus:outline-none"
                />
              </div>
              <div className="flex justify-end space-x-3 pt-2">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg text-sm">
                  Cancel
                </button>
                <button type="submit" disabled={isSubmitting} className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium">
                  {isSubmitting ? 'Parsing...' : 'Upload & Parse'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
