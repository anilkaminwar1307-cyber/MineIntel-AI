import React from 'react';
import { User, Calendar, Building2, Clock } from 'lucide-react';

interface UserQuestionProps {
  question: string;
  period?: string;
  subsidiary?: string;
  timestamp?: string;
}

export const UserQuestion: React.FC<UserQuestionProps> = ({
  question,
  period,
  subsidiary,
  timestamp = 'Just now',
}) => {
  return (
    <div className="flex items-start space-x-3 p-4 rounded-2xl bg-slate-50/90 border border-slate-200/80 shadow-2xs">
      <div className="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-xs">
        <User className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between space-x-2 mb-1.5">
          <span className="text-xs font-bold text-slate-800 tracking-wide uppercase">
            Parliamentary Question
          </span>
          <span className="text-[11px] text-slate-400 flex items-center space-x-1">
            <Clock className="w-3 h-3" />
            <span>{timestamp}</span>
          </span>
        </div>

        <p className="text-sm font-semibold text-slate-900 leading-relaxed">
          {question}
        </p>

        <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-slate-200/60 text-[11px]">
          {period && (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-white border border-slate-200 font-medium text-slate-600">
              <Calendar className="w-3 h-3 text-slate-400" />
              <span>Period: <strong>{period}</strong></span>
            </span>
          )}

          {subsidiary && (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-white border border-slate-200 font-medium text-slate-600">
              <Building2 className="w-3 h-3 text-slate-400" />
              <span>Scope: <strong>{subsidiary === 'ALL' ? 'Consolidated CIL' : subsidiary}</strong></span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
