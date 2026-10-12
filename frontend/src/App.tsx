import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { SpecManager } from './components/SpecManager';
import { FuzzJobRunner } from './components/FuzzJobRunner';
import { FindingsViewer } from './components/FindingsViewer';
import { EvaluationView } from './components/EvaluationView';

export const MainContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const handleViewJobFindings = (jobId: string) => {
    setSelectedJobId(jobId);
    setActiveTab('findings');
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && <Dashboard onNavigate={setActiveTab} />}
        {activeTab === 'specs' && <SpecManager />}
        {activeTab === 'runner' && <FuzzJobRunner onViewJobFindings={handleViewJobFindings} />}
        {activeTab === 'findings' && <FindingsViewer initialJobId={selectedJobId} />}
        {activeTab === 'evaluation' && <EvaluationView />}
      </main>

      <footer className="border-t border-slate-800 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            Built by <span className="font-semibold text-slate-300">Alan Vo</span> (alanvo@gmail.com) | AI & Machine Learning
          </div>
          <div>
            OpenAPI Adversarial Fuzzing & Security Intelligence &bull; MIT License
          </div>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainContent />
    </AuthProvider>
  );
};

export default App;
