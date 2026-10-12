import React from 'react';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const { user, role, switchRole, logout } = useAuth();

  const tabs = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'specs', label: 'OpenAPI Specs' },
    { id: 'runner', label: 'Fuzz Runner' },
    { id: 'findings', label: 'Findings' },
    { id: 'evaluation', label: 'AI/ML Benchmark' },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-indigo-600 text-white font-bold text-xl shadow-lg shadow-indigo-500/20">
              ⚡
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight text-white">api-fuzzer</span>
                <span className="px-2 py-0.5 text-xs font-semibold rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Alan Vo
                </span>
              </div>
              <p className="text-xs text-slate-400">Adversarial OpenAPI Security & Robustness Fuzzer</p>
            </div>
          </div>

          <nav className="hidden md:flex space-x-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-slate-800 text-indigo-400 border border-slate-700'
                    : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center space-x-3">
            {/* Role Switcher */}
            <div className="flex items-center bg-slate-800 rounded-lg p-1 border border-slate-700 text-xs">
              <span className="text-slate-400 px-2 font-medium">Role:</span>
              {(['viewer', 'operator', 'admin'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => switchRole(r)}
                  className={`px-2.5 py-1 rounded text-xs font-semibold capitalize transition-all ${
                    role === r
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>

            <div className="text-right hidden sm:block">
              <div className="text-xs font-medium text-slate-300">{user?.email || 'Demo Operator'}</div>
              <div className="text-[10px] text-emerald-400 flex items-center justify-end space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>OIDC Demo Active</span>
              </div>
            </div>

            <button
              onClick={() => logout()}
              title="Logout"
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-md transition-colors text-xs border border-transparent hover:border-slate-700"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
