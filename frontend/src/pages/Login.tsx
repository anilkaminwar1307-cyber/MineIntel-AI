import React, { useState } from 'react';
import { Shield, KeyRound, User, Lock, AlertCircle, ArrowRight, CheckCircle2, Database, FileSpreadsheet, Sparkles, Building2 } from 'lucide-react';
import { api } from '../services/api';
import { TokenResponse } from '../types';

interface LoginProps {
  onLoginSuccess: (tokenData: TokenResponse) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password.');
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const data = await api.login(username.trim(), password);
      onLoginSuccess(data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please verify your credentials.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (demoUser: string, demoPass: string) => {
    setUsername(demoUser);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#080d1a] flex flex-col justify-center items-center px-4 py-8 text-slate-100 select-none">
      {/* Background ambient gradient glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-md">
        {/* App Branding Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-amber-600 to-amber-400 text-slate-950 font-black text-2xl shadow-lg shadow-amber-500/20 mb-3 border border-amber-300/40">
            <Building2 className="w-8 h-8 text-slate-950" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            MineIntel <span className="text-amber-400 font-normal">Evidence Intelligence</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            Ministry of Coal &bull; CMPDI &bull; Coal India Limited (SIH PS 26023)
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-[#0f172a]/90 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/60">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
            <div>
              <h2 className="text-base font-semibold text-white">Operator Sign In</h2>
              <p className="text-xs text-slate-400">Enter your credentials to access the ledger</p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
              RBAC PROTECTED
            </span>
          </div>

          {error && (
            <div className="mb-5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Username or Email
              </label>
              <div className="relative">
                <User className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="analyst_demo"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-colors"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-2.5 px-4 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-semibold text-xs transition-all duration-150 flex items-center justify-center space-x-2 shadow-lg shadow-amber-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Login Preset Buttons */}
          <div className="mt-6 pt-5 border-t border-slate-800">
            <p className="text-[11px] font-semibold text-slate-400 mb-2.5 uppercase tracking-wider">
              Quick Demo Logins (SIH Evaluator Mode)
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('analyst_demo', 'Analyst@Demo2026')}
                className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900 border border-slate-700/80 hover:border-amber-500/50 hover:bg-slate-800 text-left transition-all group"
              >
                <span className="text-[11px] font-bold text-slate-200 group-hover:text-amber-400">Analyst</span>
                <span className="text-[9px] text-slate-500">Upload & Query</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('reviewer_demo', 'Reviewer@Demo2026')}
                className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900 border border-slate-700/80 hover:border-amber-500/50 hover:bg-slate-800 text-left transition-all group"
              >
                <span className="text-[11px] font-bold text-slate-200 group-hover:text-amber-400">Reviewer</span>
                <span className="text-[9px] text-slate-500">Verify & Resolve</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('admin_demo', 'Admin@Demo2026!')}
                className="flex flex-col items-center justify-center p-2 rounded-lg bg-slate-900 border border-slate-700/80 hover:border-amber-500/50 hover:bg-slate-800 text-left transition-all group"
              >
                <span className="text-[11px] font-bold text-slate-200 group-hover:text-amber-400">Admin</span>
                <span className="text-[9px] text-slate-500">Full System</span>
              </button>
            </div>
          </div>
        </div>

        {/* Security & Provenance Badge Footer */}
        <div className="mt-6 text-center text-[11px] text-slate-500 space-y-1">
          <p className="flex items-center justify-center space-x-1.5">
            <Shield className="w-3.5 h-3.5 text-amber-500" />
            <span>NumberSafe Deterministic Ledger &bull; Immutable Provenance</span>
          </p>
          <p>JWT HMAC-SHA256 Authenticated Session</p>
        </div>
      </div>
    </div>
  );
};
