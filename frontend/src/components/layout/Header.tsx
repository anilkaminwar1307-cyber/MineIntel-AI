import React from 'react';
import { Shield, Sparkles, AlertTriangle } from 'lucide-react';
import { HealthInfo } from '../../types';

interface HeaderProps {
  title: string;
  subtitle: string;
  health: HealthInfo | null;
  onRefreshHealth?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle, health, onRefreshHealth }) => {
  const isHealthy = health?.status === 'ok';
  const isGeminiConfigured = health?.gemini === 'configured';

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between flex-shrink-0">
      {/* Title & Subtitle */}
      <div>
        <div className="flex items-center space-x-2">
          <h1 className="text-base font-semibold text-slate-900 tracking-tight">{title}</h1>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
            PS-26023
          </span>
        </div>
        <p className="text-xs text-slate-500">{subtitle}</p>
      </div>

      {/* Right side operational badges */}
      <div className="flex items-center space-x-3">
        {/* Ministry / CIL Badge */}
        <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-50 border border-slate-200 text-xs text-slate-700">
          <Shield className="w-3.5 h-3.5 text-amber-600" />
          <span className="font-medium">CMPDI / Coal India Limited</span>
        </div>

        {/* Gemini Status Badge */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-medium border ${
            isGeminiConfigured
              ? 'bg-purple-50 text-purple-700 border-purple-200'
              : 'bg-slate-100 text-slate-600 border-slate-200'
          }`}
          title={isGeminiConfigured ? 'Google Gemini AI Connected' : 'Gemini API key not configured yet'}
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-600" />
          <span>{isGeminiConfigured ? 'Gemini Active' : 'AI: Heuristic'}</span>
        </div>

        {/* Backend & DB Health Badge */}
        <div
          onClick={onRefreshHealth}
          className={`cursor-pointer flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
            isHealthy
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
              : 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100'
          }`}
          title="Click to recheck backend connectivity"
        >
          {isHealthy ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>DB Connected</span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
              <span>Backend Offline</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
