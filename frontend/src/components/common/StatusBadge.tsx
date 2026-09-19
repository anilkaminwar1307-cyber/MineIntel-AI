import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  const normalized = (status || '').toUpperCase();
  const px = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';

  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-200';

  if (['VERIFIED', 'READY', 'OPERATIONAL', 'CONNECTED', 'OK'].includes(normalized)) {
    colorClasses = 'bg-emerald-50 text-emerald-800 border-emerald-200';
  } else if (['UPLOADED', 'EXTRACTED', 'HIGH_CONFIDENCE'].includes(normalized)) {
    colorClasses = 'bg-blue-50 text-blue-800 border-blue-200';
  } else if (['NEEDS_REVIEW', 'REVIEW_REQUIRED', 'QUEUED', 'PENDING', 'DEGRADED'].includes(normalized)) {
    colorClasses = 'bg-amber-50 text-amber-800 border-amber-200';
  } else if (['CONFLICT', 'FAILED', 'ERROR', 'REJECTED'].includes(normalized)) {
    colorClasses = 'bg-rose-50 text-rose-800 border-rose-200';
  } else if (['NOT_CONFIGURED', 'NOT_READY'].includes(normalized)) {
    colorClasses = 'bg-slate-100 text-slate-600 border-slate-300';
  }

  return (
    <span className={`inline-flex items-center font-medium rounded border ${px} ${colorClasses}`}>
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-70"></span>
      {status.replace(/_/g, ' ')}
    </span>
  );
};
