import React, { useState } from 'react';
import {
  Landmark,
  Shield,
  Send,
  BarChart3,
  TrendingUp,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import { ParliamentaryBriefResponse } from '../../types';
import { VerificationBadge } from './VerificationBadge';
import { ResponseMarkdown } from './ResponseMarkdown';
import { EvidenceSources } from './EvidenceSources';
import { ResponseActions } from './ResponseActions';

const CHART_COLORS = ['#881337', '#b45309', '#0369a1', '#047857', '#6d28d9', '#c2410c', '#475569'];

interface AIResponseProps {
  brief: ParliamentaryBriefResponse;
  onRegenerate: () => void;
  onFollowUp: (question: string) => void;
  isRegenerating?: boolean;
}

export const AIResponse: React.FC<AIResponseProps> = ({
  brief,
  onRegenerate,
  onFollowUp,
  isRegenerating = false,
}) => {
  const [followUpText, setFollowUpText] = useState('');

  const handleFollowUpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!followUpText.trim()) return;
    onFollowUp(followUpText.trim());
    setFollowUpText('');
  };

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white shadow-xs overflow-hidden">
      {/* Response Header */}
      <div className="p-4 md:p-5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-rose-800 to-amber-700 text-white flex items-center justify-center flex-shrink-0 shadow-2xs">
            <Landmark className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xs md:text-sm font-bold text-slate-900">
                MineIntel Parliamentary AI
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 font-semibold">
                Ministry of Coal Brief
              </span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold border ${
                brief.mode === 'gemini_llm'
                  ? 'bg-purple-50 text-purple-700 border-purple-200'
                  : 'bg-slate-100 text-slate-700 border-slate-300'
              }`}>
                mode: {brief.mode || 'extractive_no_llm'}
              </span>
            </div>
            <div className="text-[11px] text-slate-500">
              Evidence-grounded brief · NumberSafe 2.0 zero-hallucination verified
            </div>
          </div>
        </div>

        <VerificationBadge
          status={brief.verification_status || brief.status}
          confidence={brief.confidence}
          recordsUsed={brief.records_used}
        />
      </div>

      {/* Main Response Body (ChatGPT Style Pure White Background) */}
      <div className="p-5 md:p-7 space-y-6 bg-white text-slate-800">
        {/* Direct Metric KPI Card (if present) */}
        {brief.direct_metric_value != null && (
          <div className="p-4 rounded-xl bg-gradient-to-r from-rose-50/70 via-amber-50/40 to-white border border-rose-200/80 flex items-center justify-between shadow-2xs">
            <div>
              <div className="text-[11px] font-bold text-rose-900 uppercase tracking-wider">
                Audited Deterministic Metric
              </div>
              <div className="text-2xl md:text-3xl font-extrabold text-slate-900 mt-1">
                {brief.direct_metric_value.toLocaleString(undefined, {
                  maximumFractionDigits: 2,
                })}{' '}
                <span className="text-base font-semibold text-rose-800">
                  {brief.metric_unit || ''}
                </span>
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Aggregated deterministically across {brief.records_used} verified records in the Evidence Ledger
              </div>
            </div>

            <div className="text-right flex-shrink-0">
              <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
                <Shield className="w-3.5 h-3.5" />
                <span>Zero Hallucination</span>
              </span>
            </div>
          </div>
        )}

        {/* Formatted Markdown Content */}
        <ResponseMarkdown content={brief.brief_text} />

        {/* Optional Interactive Chart */}
        {brief.chart && brief.chart.data && brief.chart.data.length > 0 && (
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/30 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <BarChart3 className="w-4 h-4 text-rose-700" />
                <h4 className="text-xs font-bold text-slate-900">
                  {brief.chart.title || 'Operational Breakdown'}
                </h4>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">
                SQL Deterministic Grouping
              </span>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                {brief.chart.type === 'line' ? (
                  <LineChart data={brief.chart.data} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="value" stroke="#881337" strokeWidth={2.5} dot={{ r: 4 }} />
                  </LineChart>
                ) : (
                  <BarChart data={brief.chart.data} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {brief.chart.data.map((_: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Supporting Evidence Sources */}
        <EvidenceSources citations={brief.citations || []} />

        {/* Follow-up Suggestions Chips */}
        {brief.suggestions && brief.suggestions.length > 0 && (
          <div className="space-y-2 pt-3 border-t border-slate-100">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span>Recommended Follow-up Parliamentary Queries:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {brief.suggestions.map((sug, i) => (
                <button
                  key={i}
                  onClick={() => onFollowUp(sug)}
                  className="text-xs px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-rose-50 hover:border-rose-300 text-slate-700 hover:text-rose-900 transition-all font-medium flex items-center space-x-1.5 group"
                >
                  <span>{sug}</span>
                  <ArrowRight className="w-3 h-3 text-slate-400 group-hover:text-rose-600 transition-colors" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Actions Bar (Copy, Print, Export, Regenerate) */}
        <ResponseActions
          brief={brief}
          onRegenerate={onRegenerate}
          isRegenerating={isRegenerating}
        />

        {/* Conversational Follow-up Input Bar */}
        <div className="pt-2">
          <form
            onSubmit={handleFollowUpSubmit}
            className="flex items-center space-x-2 p-1.5 rounded-xl border border-slate-300 bg-slate-50/70 focus-within:border-rose-500 focus-within:bg-white focus-within:ring-2 focus-within:ring-rose-200 transition-all"
          >
            <input
              type="text"
              value={followUpText}
              onChange={e => setFollowUpText(e.target.value)}
              placeholder="Ask a follow-up or refine this parliamentary brief…"
              className="flex-1 px-3 py-1.5 bg-transparent text-xs text-slate-800 placeholder-slate-400 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!followUpText.trim()}
              className="px-3 py-1.5 rounded-lg bg-rose-700 hover:bg-rose-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white text-xs font-semibold transition-colors flex items-center space-x-1"
            >
              <span>Ask</span>
              <Send className="w-3 h-3" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
