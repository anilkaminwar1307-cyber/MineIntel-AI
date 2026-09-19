import React from 'react';
import { HelpCircle, LayoutDashboard, ArrowLeft } from 'lucide-react';

interface NotFoundProps {
  onNavigate: (tab: string) => void;
  requestedRoute?: string;
}

export const NotFound: React.FC<NotFoundProps> = ({ onNavigate, requestedRoute }) => {
  return (
    <div className="min-h-[450px] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-xl border border-slate-200 shadow-sm p-8 text-center space-y-4">
        <div className="w-14 h-14 bg-slate-100 border border-slate-200 rounded-full flex items-center justify-center mx-auto text-slate-500">
          <HelpCircle className="w-7 h-7 text-amber-600" />
        </div>

        <div className="space-y-1.5">
          <div className="inline-block px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200 uppercase">
            404 — Route Not Found
          </div>
          <h3 className="text-lg font-bold text-slate-900">Page Not Found</h3>
          <p className="text-xs text-slate-500 leading-relaxed">
            The requested section {requestedRoute ? <code className="text-slate-800 font-mono">"{requestedRoute}"</code> : ''} does not exist in the MineIntel navigation index.
          </p>
        </div>

        <div className="pt-2 flex items-center justify-center space-x-3">
          <button
            type="button"
            onClick={() => onNavigate('overview')}
            className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
          >
            <LayoutDashboard className="w-3.5 h-3.5 text-amber-400" />
            <span>Return to Overview</span>
          </button>
        </div>
      </div>
    </div>
  );
};
