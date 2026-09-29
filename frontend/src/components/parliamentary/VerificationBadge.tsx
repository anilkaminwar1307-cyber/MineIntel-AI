import React from 'react';
import { Shield, CheckCircle2, AlertTriangle, AlertCircle, HelpCircle } from 'lucide-react';

interface VerificationBadgeProps {
  status?: string | null;
  confidence?: number;
  recordsUsed?: number;
  compact?: boolean;
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({
  status,
  confidence = 0.95,
  recordsUsed,
  compact = false,
}) => {
  const normStatus = (status || '').toUpperCase();

  // Certified / Supported / 100% Verified
  if (
    normStatus === 'SUCCESS' ||
    normStatus === 'SUPPORTED' ||
    normStatus.includes('VERIFIED') ||
    normStatus.includes('CERTIFIED') ||
    normStatus.includes('CLEAN')
  ) {
    if (compact) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>NumberSafe Certified</span>
        </span>
      );
    }

    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200/80 text-emerald-800">
        <Shield className="w-4 h-4 text-emerald-600 flex-shrink-0" />
        <div className="text-xs">
          <span className="font-bold">NumberSafe 2.0 Certified</span>
          <span className="text-emerald-700/80 ml-1.5">
            · Deterministic SQL ({Math.round(confidence * 100)}% conf
            {recordsUsed ? `, ${recordsUsed} records` : ''})
          </span>
        </div>
      </div>
    );
  }

  // Conflicting evidence
  if (normStatus.includes('CONFLICT') || normStatus.includes('DISCREPANCY')) {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-rose-50 border border-rose-200/80 text-rose-800">
        <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
        <div className="text-xs">
          <span className="font-bold">Conflict Detected</span>
          <span className="text-rose-700/80 ml-1.5">
            · Discrepancy logged for analyst review
          </span>
        </div>
      </div>
    );
  }

  // Partial support
  if (normStatus.includes('PARTIAL') || normStatus.includes('NEEDS_REVIEW')) {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200/80 text-amber-800">
        <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
        <div className="text-xs">
          <span className="font-bold">Partial Evidence Coverage</span>
          <span className="text-amber-700/80 ml-1.5">
            · Manual analyst review advised ({Math.round(confidence * 100)}% conf)
          </span>
        </div>
      </div>
    );
  }

  // Insufficient evidence
  return (
    <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-700">
      <HelpCircle className="w-4 h-4 text-slate-500 flex-shrink-0" />
      <div className="text-xs">
        <span className="font-bold">Limited Operational Evidence</span>
        <span className="text-slate-500 ml-1.5">· Additional filing documents required</span>
      </div>
    </div>
  );
};
