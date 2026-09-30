import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
  onRetry: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, onRetry }) => {
  return (
    <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-center max-w-md mx-auto my-8 space-y-3 shadow-xs">
      <div className="w-12 h-12 rounded-2xl bg-rose-100 flex items-center justify-center text-rose-600 mx-auto">
        <AlertTriangle className="w-6 h-6" />
      </div>

      <div>
        <h4 className="text-sm font-bold text-rose-900">Brief Generation Interrupted</h4>
        <p className="text-xs text-rose-700 mt-1 leading-relaxed">{message}</p>
      </div>

      <button
        onClick={onRetry}
        className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-rose-700 hover:bg-rose-800 text-white text-xs font-semibold shadow-2xs transition-colors"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        <span>Retry Brief Generation</span>
      </button>
    </div>
  );
};
