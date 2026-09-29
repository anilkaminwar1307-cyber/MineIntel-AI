import React, { useState, useEffect, useRef } from 'react';
import {
  Landmark,
  Send,
  BookOpen,
  Shield,
  Database,
  FileText,
  ChevronRight,
  RefreshCw,
  Star,
  Clock,
  Sparkles,
  HelpCircle,
} from 'lucide-react';
import { api } from '../services/api';
import {
  ParliamentaryBriefResponse,
  ParliamentarySampleQuestion,
} from '../types';
import { UserQuestion } from '../components/parliamentary/UserQuestion';
import { AIResponse } from '../components/parliamentary/AIResponse';
import { LoadingIndicator } from '../components/parliamentary/LoadingIndicator';
import { ErrorMessage } from '../components/parliamentary/ErrorMessage';

const SUBSIDIARIES = ['ALL', 'ECL', 'BCCL', 'CCL', 'WCL', 'SECL', 'MCL', 'NCL', 'CMPDI'];
const PERIODS = ['ALL', 'FY 2024-25', 'FY 2023-24', 'FY 2022-23', 'FY 2021-22', 'FY 2020-21'];

const CATEGORY_COLORS: Record<string, string> = {
  Production: 'bg-amber-100 text-amber-800 border-amber-200',
  'Target Achievement': 'bg-blue-100 text-blue-800 border-blue-200',
  OBR: 'bg-purple-100 text-purple-800 border-purple-200',
  Exploration: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  Dispatch: 'bg-rose-100 text-rose-800 border-rose-200',
};

// ─── Sample Question Card ─────────────────────────────────────────────────────
const QuestionCard: React.FC<{
  q: ParliamentarySampleQuestion;
  onSelect: (q: ParliamentarySampleQuestion) => void;
}> = ({ q, onSelect }) => (
  <button
    onClick={() => onSelect(q)}
    className="w-full text-left p-3 rounded-xl border border-slate-200/90 bg-white hover:border-rose-300 hover:bg-rose-50/20 hover:shadow-2xs transition-all group"
  >
    <div className="flex items-start space-x-2.5">
      <div className="w-6 h-6 rounded-lg bg-amber-50 group-hover:bg-rose-100 flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors">
        <Star className="w-3.5 h-3.5 text-amber-600 group-hover:text-rose-700" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-slate-800 font-medium leading-relaxed group-hover:text-rose-950 transition-colors">
          {q.question}
        </div>
        <div className="flex items-center space-x-2 mt-1.5">
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded-md border font-semibold ${
              CATEGORY_COLORS[q.category] || 'bg-slate-100 text-slate-600 border-slate-200'
            }`}
          >
            {q.category}
          </span>
          <span className="text-[10px] text-slate-400 font-medium">{q.period}</span>
          {q.subsidiary !== 'ALL' && (
            <span className="text-[10px] text-rose-700 font-semibold">{q.subsidiary}</span>
          )}
        </div>
      </div>
      <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-rose-500 transition-colors flex-shrink-0 mt-1" />
    </div>
  </button>
);

// ─── Main Page ─────────────────────────────────────────────────────────────────
export const ParliamentaryBrief: React.FC = () => {
  const [query, setQuery] = useState('');
  const [period, setPeriod] = useState('FY 2024-25');
  const [subsidiary, setSubsidiary] = useState('ALL');
  const [submitting, setSubmitting] = useState(false);
  const [brief, setBrief] = useState<ParliamentaryBriefResponse | null>(null);
  const [activeQuestion, setActiveQuestion] = useState<{ query: string; period: string; subsidiary: string; time: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [sampleQuestions, setSampleQuestions] = useState<ParliamentarySampleQuestion[]>([]);
  const [history, setHistory] = useState<{ query: string; period: string; subsidiary: string; time: string }[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const responseEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getParliamentarySampleQuestions()
      .then(r => setSampleQuestions(r.questions))
      .catch(() => {});
  }, []);

  const executeGeneration = async (qText: string, pText: string, sText: string) => {
    if (!qText.trim()) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const result = await api.generateParliamentaryBrief({
        query: qText,
        period: pText,
        subsidiary: sText,
      });
      setBrief(result);
      const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setActiveQuestion({
        query: qText,
        period: pText,
        subsidiary: sText,
        time: nowStr,
      });
      setHistory(prev => [
        { query: qText, period: pText, subsidiary: sText, time: nowStr },
        ...prev.filter(h => h.query !== qText).slice(0, 5),
      ]);
      // Scroll to response
      setTimeout(() => {
        responseEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.detail || 'Failed to generate brief. Please verify backend service.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = () => {
    executeGeneration(query, period, subsidiary);
  };

  const handleSampleSelect = (q: ParliamentarySampleQuestion) => {
    setQuery(q.question);
    setPeriod(q.period);
    setSubsidiary(q.subsidiary);
    executeGeneration(q.question, q.period, q.subsidiary);
  };

  const handleFollowUp = (followUpText: string) => {
    setQuery(followUpText);
    executeGeneration(followUpText, period, subsidiary);
  };

  const handleRegenerate = () => {
    if (activeQuestion) {
      executeGeneration(activeQuestion.query, activeQuestion.period, activeQuestion.subsidiary);
    } else {
      executeGeneration(query, period, subsidiary);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-5 h-full min-h-0 bg-slate-50/30">
      {/* ── Left: Input Panel ── */}
      <div className="w-full lg:w-84 xl:w-96 flex-none flex flex-col space-y-4 overflow-y-auto pr-1">
        {/* Header Banner */}
        <div className="bg-gradient-to-br from-rose-900 via-rose-800 to-amber-700 rounded-2xl p-4 text-white shadow-sm">
          <div className="flex items-center space-x-2.5 mb-1.5">
            <div className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center">
              <Landmark className="w-4 h-4 text-rose-100" />
            </div>
            <div>
              <h2 className="text-sm font-bold tracking-tight">Parliamentary Brief</h2>
              <div className="text-[10px] text-rose-200 font-medium">Lok Sabha / Rajya Sabha Query Portal</div>
            </div>
          </div>
          <p className="text-xs text-rose-100/90 leading-relaxed mt-2">
            Generate official Ministry of Coal–standard briefs grounded in verified relational records. NumberSafe 2.0 certified zero-hallucination guarantee.
          </p>
        </div>

        {/* Query Input Card */}
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4 space-y-3 shadow-2xs">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-1.5">
              <span>Question Specification</span>
            </div>
            <span className="text-[10px] text-slate-400">Formal Query</span>
          </div>

          <textarea
            ref={textareaRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="e.g. What was the total raw coal production of Coal India Limited in FY 2024-25?"
            className="w-full text-xs text-slate-800 border border-slate-200 rounded-xl p-3 resize-none h-28 focus:outline-none focus:ring-2 focus:ring-rose-400 focus:border-rose-400 placeholder-slate-400 leading-relaxed"
          />

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[11px] font-semibold text-slate-600 mb-1 block">Reporting Period</label>
              <select
                value={period}
                onChange={e => setPeriod(e.target.value)}
                className="w-full text-xs font-medium border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-rose-400 bg-white text-slate-700"
              >
                {PERIODS.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600 mb-1 block">Subsidiary / Scope</label>
              <select
                value={subsidiary}
                onChange={e => setSubsidiary(e.target.value)}
                className="w-full text-xs font-medium border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-rose-400 bg-white text-slate-700"
              >
                {SUBSIDIARIES.map(s => (
                  <option key={s} value={s}>{s === 'ALL' ? 'ALL (Consolidated)' : s}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!query.trim() || submitting}
            className="w-full py-2.5 bg-rose-700 hover:bg-rose-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold shadow-2xs transition-colors flex items-center justify-center space-x-2"
          >
            {submitting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Synthesizing Brief…</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Generate Parliamentary Brief</span>
              </>
            )}
          </button>
        </div>

        {/* Sample Questions */}
        <div className="bg-white rounded-2xl border border-slate-200/90 p-3.5 space-y-2.5 shadow-2xs">
          <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center justify-between">
            <div className="flex items-center space-x-1.5">
              <BookOpen className="w-3.5 h-3.5 text-rose-700" />
              <span>Official Sample Inquiries</span>
            </div>
            <span className="text-[10px] text-slate-400">Click to run</span>
          </div>

          <div className="space-y-2">
            {sampleQuestions.map(q => (
              <QuestionCard key={q.id} q={q} onSelect={handleSampleSelect} />
            ))}
          </div>
        </div>

        {/* Recent Queries */}
        {history.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200/90 p-3.5 shadow-2xs">
            <div className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>Recent Briefs</span>
            </div>
            <div className="space-y-1.5">
              {history.map((h, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setQuery(h.query);
                    setPeriod(h.period);
                    setSubsidiary(h.subsidiary);
                    executeGeneration(h.query, h.period, h.subsidiary);
                  }}
                  className="w-full text-left text-xs text-slate-600 hover:text-slate-900 py-1.5 px-2.5 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-between group"
                >
                  <span className="truncate flex-1 font-medium">{h.query}</span>
                  <span className="text-[10px] text-slate-400 group-hover:text-rose-600 ml-2 flex-shrink-0">
                    {h.time}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Right: Brief Panel (ChatGPT Inspired Conversational View) ── */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Empty State */}
        {!brief && !submitting && !errorMsg && (
          <div className="h-full flex items-center justify-center p-6">
            <div className="text-center space-y-6 max-w-lg">
              <div className="relative w-20 h-20 mx-auto flex items-center justify-center">
                <div className="absolute inset-0 rounded-3xl bg-rose-100 rotate-6 transition-transform hover:rotate-12 duration-300" />
                <div className="relative w-20 h-20 rounded-3xl bg-gradient-to-br from-rose-800 to-amber-700 flex items-center justify-center text-white shadow-lg">
                  <Landmark className="w-10 h-10" />
                </div>
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                  Parliamentary Brief Intelligence Generator
                </h3>
                <p className="text-xs md:text-sm text-slate-500 leading-relaxed mt-2 max-w-md mx-auto">
                  Submit any mining, geological, or operational query on the left. MineIntel deterministically extracts figures from the Evidence Ledger and formats an official Lok Sabha / Rajya Sabha response.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
                {[
                  {
                    icon: Shield,
                    title: 'NumberSafe 2.0',
                    desc: 'Zero hallucinated figures; all numbers computed in SQL.',
                  },
                  {
                    icon: Database,
                    title: 'Full Provenance',
                    desc: 'Every metric links to page, sheet, cell, and document.',
                  },
                  {
                    icon: FileText,
                    title: 'Ministry Standard',
                    desc: 'Print-ready official 5-section government brief.',
                  },
                ].map((feat, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl border border-slate-200/80 bg-white shadow-2xs hover:shadow-xs transition-shadow"
                  >
                    <feat.icon className="w-4 h-4 text-rose-700 mb-1.5" />
                    <h5 className="text-xs font-bold text-slate-800">{feat.title}</h5>
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{feat.desc}</p>
                  </div>
                ))}
              </div>

              <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200/80 text-amber-800 text-xs flex items-center justify-center space-x-2">
                <Sparkles className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                <span>Select any sample inquiry on the left to see an instant live demonstration</span>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {submitting && <LoadingIndicator />}

        {/* Error State */}
        {errorMsg && !submitting && (
          <ErrorMessage
            message={errorMsg}
            onRetry={handleSubmit}
          />
        )}

        {/* Active Conversational Brief Thread */}
        {brief && !submitting && (
          <div className="p-1 space-y-4 max-w-5xl mx-auto">
            {/* 1. User Submitted Question Card */}
            {activeQuestion && (
              <UserQuestion
                question={activeQuestion.query}
                period={activeQuestion.period}
                subsidiary={activeQuestion.subsidiary}
                timestamp={activeQuestion.time}
              />
            )}

            {/* 2. ChatGPT Inspired AI Response Area (Pure White Background, Rich Formatting) */}
            <AIResponse
              brief={brief}
              onRegenerate={handleRegenerate}
              onFollowUp={handleFollowUp}
              isRegenerating={submitting}
            />

            <div ref={responseEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};
