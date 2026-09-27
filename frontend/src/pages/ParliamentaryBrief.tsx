import React, { useState, useEffect, useRef } from 'react';
import {
  Landmark,
  Send,
  BookOpen,
  Shield,
  Database,
  FileText,
  ChevronRight,
  Download,
  Copy,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Star,
  Clock,
  Printer,
} from 'lucide-react';
import { api } from '../services/api';
import { ParliamentaryBriefResponse, ParliamentarySampleQuestion, EvidenceSourceCitation } from '../types';

const SUBSIDIARIES = ['ALL', 'ECL', 'BCCL', 'CCL', 'WCL', 'SECL', 'MCL', 'NCL', 'CMPDI'];
const PERIODS = ['ALL', 'FY 2024-25', 'FY 2023-24', 'FY 2022-23', 'FY 2021-22', 'FY 2020-21'];

const CATEGORY_COLORS: Record<string, string> = {
  Production: 'bg-amber-100 text-amber-700 border-amber-200',
  'Target Achievement': 'bg-blue-100 text-blue-700 border-blue-200',
  OBR: 'bg-purple-100 text-purple-700 border-purple-200',
  Exploration: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  Dispatch: 'bg-rose-100 text-rose-700 border-rose-200',
};

// ─── Citation Row ──────────────────────────────────────────────────────────────
const CitationRow: React.FC<{ cite: EvidenceSourceCitation; index: number }> = ({ cite, index }) => (
  <div className="flex items-start space-x-3 p-3 rounded-lg border border-slate-100 bg-slate-50 hover:bg-white transition-colors">
    <span className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600 flex-none mt-0.5">
      {index}
    </span>
    <div className="flex-1 min-w-0">
      <div className="flex items-center space-x-2 mb-0.5">
        <span className="text-xs font-bold text-slate-800 truncate">{cite.document_name}</span>
        {cite.human_verified && (
          <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full flex items-center space-x-0.5 flex-none">
            <CheckCircle2 className="w-2.5 h-2.5" /><span>Verified</span>
          </span>
        )}
      </div>
      <div className="text-xs text-slate-500 flex flex-wrap gap-x-3 gap-y-0.5">
        <span className="font-mono font-semibold text-blue-700">
          {cite.numeric_value?.toLocaleString()} {cite.unit}
        </span>
        {cite.page_number && <span>Page {cite.page_number}</span>}
        {cite.sheet_name && <span>Sheet: {cite.sheet_name}</span>}
        {cite.cell_reference && <span className="font-mono">Cell {cite.cell_reference}</span>}
        <span className="text-emerald-600">
          {Math.round((cite.confidence_score || 0) * 100)}% conf.
        </span>
      </div>
    </div>
  </div>
);

// ─── Brief Display ─────────────────────────────────────────────────────────────
const BriefDisplay: React.FC<{ brief: ParliamentaryBriefResponse }> = ({ brief }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(brief.brief_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`
      <html><head><title>Parliamentary Brief — MineIntel</title>
      <style>
        body { font-family: 'Courier New', monospace; white-space: pre-wrap; font-size: 12px; padding: 40px; max-width: 800px; margin: auto; }
        h1 { font-size: 16px; text-align: center; }
      </style></head>
      <body><h1>PARLIAMENTARY BRIEF — MINEINTEL</h1><pre>${brief.brief_text}</pre></body></html>
    `);
    w.document.close();
    w.print();
  };

  return (
    <div className="space-y-4">
      {/* Status banner */}
      <div className={`flex items-center justify-between rounded-xl px-4 py-3 ${
        brief.status === 'SUCCESS'
          ? 'bg-emerald-50 border border-emerald-200'
          : 'bg-amber-50 border border-amber-200'
      }`}>
        <div className="flex items-center space-x-3">
          <Shield className={`w-5 h-5 ${brief.status === 'SUCCESS' ? 'text-emerald-600' : 'text-amber-600'}`} />
          <div>
            <div className={`text-sm font-bold ${brief.status === 'SUCCESS' ? 'text-emerald-800' : 'text-amber-800'}`}>
              {brief.status === 'SUCCESS' ? 'NumberSafe Certified — Deterministic Evidence' : 'Partial Evidence — Manual Review Advised'}
            </div>
            <div className="text-xs text-slate-500">
              {brief.records_used} records · {(brief.confidence * 100).toFixed(0)}% confidence
              {brief.direct_metric_value != null && ` · ${brief.direct_metric_value.toLocaleString()} ${brief.metric_unit || ''}`}
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button onClick={handleCopy}
            className="text-xs flex items-center space-x-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            {copied ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>
          <button onClick={handlePrint}
            className="text-xs flex items-center space-x-1 px-3 py-1.5 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-colors">
            <Printer className="w-3 h-3" />
            <span>Print</span>
          </button>
        </div>
      </div>

      {/* Brief text */}
      <div className="bg-slate-900 text-slate-100 rounded-xl p-6 font-mono text-xs leading-relaxed overflow-auto max-h-[420px] shadow-inner">
        <pre className="whitespace-pre-wrap">{brief.brief_text}</pre>
      </div>

      {/* Citations */}
      {brief.citations.length > 0 && (
        <div>
          <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center space-x-2">
            <Database className="w-3.5 h-3.5" />
            <span>Evidence Sources ({brief.citations.length})</span>
          </div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {brief.citations.map((c, i) => (
              <CitationRow key={i} cite={c} index={i + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Sample Question Card ─────────────────────────────────────────────────────
const QuestionCard: React.FC<{
  q: ParliamentarySampleQuestion;
  onSelect: (q: ParliamentarySampleQuestion) => void;
}> = ({ q, onSelect }) => (
  <button
    onClick={() => onSelect(q)}
    className="w-full text-left p-3 rounded-xl border border-slate-200 bg-white hover:border-amber-300 hover:bg-amber-50/30 transition-all group"
  >
    <div className="flex items-start space-x-3">
      <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center flex-none mt-0.5">
        <Star className="w-3.5 h-3.5 text-amber-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-slate-700 leading-relaxed group-hover:text-slate-900 transition-colors">
          {q.question}
        </div>
        <div className="flex items-center space-x-2 mt-1.5">
          <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${CATEGORY_COLORS[q.category] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
            {q.category}
          </span>
          <span className="text-[10px] text-slate-400">{q.period}</span>
          {q.subsidiary !== 'ALL' && (
            <span className="text-[10px] text-blue-500">{q.subsidiary}</span>
          )}
        </div>
      </div>
      <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-amber-500 transition-colors flex-none mt-1" />
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
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [sampleQuestions, setSampleQuestions] = useState<ParliamentarySampleQuestion[]>([]);
  const [history, setHistory] = useState<{ query: string; time: string }[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.getParliamentarySampleQuestions()
      .then(r => setSampleQuestions(r.questions))
      .catch(() => {});
  }, []);

  const handleSubmit = async () => {
    if (!query.trim()) return;
    setSubmitting(true);
    setErrorMsg(null);
    setBrief(null);
    try {
      const result = await api.generateParliamentaryBrief({ query, period, subsidiary });
      setBrief(result);
      setHistory(prev => [{ query: query.slice(0, 80), time: new Date().toLocaleTimeString() }, ...prev.slice(0, 4)]);
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.detail || 'Failed to generate brief. Ensure the backend is running.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSampleSelect = (q: ParliamentarySampleQuestion) => {
    setQuery(q.question);
    setPeriod(q.period);
    setSubsidiary(q.subsidiary);
    textareaRef.current?.focus();
  };

  return (
    <div className="flex gap-5 h-full min-h-0">
      {/* ── Left: Input Panel ── */}
      <div className="w-80 flex-none flex flex-col space-y-4 overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-br from-rose-900 via-rose-800 to-amber-700 rounded-xl p-4 text-white">
          <div className="flex items-center space-x-2 mb-1">
            <Landmark className="w-5 h-5 text-rose-200" />
            <h2 className="text-base font-bold">Parliamentary Brief</h2>
          </div>
          <p className="text-xs text-rose-200 leading-relaxed">
            Generate official Lok Sabha / Rajya Sabha–style question briefs backed by grounded evidence from the Evidence Ledger. Zero hallucination — NumberSafe 2.0 certified.
          </p>
        </div>

        {/* Query form */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
          <div className="text-xs font-bold text-slate-700 uppercase tracking-wider">Question</div>
          <textarea
            ref={textareaRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="e.g. What was the total raw coal production of CIL in FY 2024-25?"
            className="w-full text-xs border border-slate-200 rounded-lg p-3 resize-none h-28 focus:outline-none focus:ring-2 focus:ring-rose-300 placeholder-slate-400"
          />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Period</label>
              <select value={period} onChange={e => setPeriod(e.target.value)}
                className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-rose-300">
                {PERIODS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Subsidiary</label>
              <select value={subsidiary} onChange={e => setSubsidiary(e.target.value)}
                className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-rose-300">
                {SUBSIDIARIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <button
            onClick={handleSubmit}
            disabled={!query.trim() || submitting}
            className="w-full py-2.5 bg-rose-700 hover:bg-rose-800 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-xs font-bold transition-colors flex items-center justify-center space-x-2"
          >
            {submitting ? (
              <><RefreshCw className="w-4 h-4 animate-spin" /><span>Generating Brief…</span></>
            ) : (
              <><Send className="w-4 h-4" /><span>Generate Parliamentary Brief</span></>
            )}
          </button>
        </div>

        {/* Sample questions */}
        <div className="bg-white rounded-xl border border-slate-200 p-3 space-y-2">
          <div className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
            <BookOpen className="w-3.5 h-3.5" />
            <span>Sample Questions</span>
          </div>
          {sampleQuestions.map(q => (
            <QuestionCard key={q.id} q={q} onSelect={handleSampleSelect} />
          ))}
        </div>

        {/* History */}
        {history.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-3">
            <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>Recent Queries</span>
            </div>
            <div className="space-y-1.5">
              {history.map((h, i) => (
                <button key={i} onClick={() => setQuery(h.query)}
                  className="w-full text-left text-xs text-slate-600 hover:text-slate-900 py-1 px-2 rounded hover:bg-slate-50 transition-colors flex items-start space-x-2">
                  <span className="text-slate-300 flex-none">{h.time}</span>
                  <span className="truncate">{h.query}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Right: Brief Panel ── */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {!brief && !submitting && !errorMsg && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-4 max-w-md">
              <div className="w-20 h-20 rounded-2xl bg-rose-50 border-2 border-rose-100 flex items-center justify-center mx-auto">
                <Landmark className="w-10 h-10 text-rose-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">Parliamentary Brief Generator</h3>
                <p className="text-sm text-slate-500 leading-relaxed">
                  Enter a parliamentary question on the left and click "Generate Parliamentary Brief" to receive a Ministry of Coal–style response backed entirely by verified evidence from the Evidence Ledger.
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs text-slate-500">
                {[
                  { icon: Shield, label: 'NumberSafe 2.0', sub: 'Zero LLM hallucination' },
                  { icon: Database, label: 'Evidence-Backed', sub: 'Every figure cited' },
                  { icon: FileText, label: 'Print-Ready', sub: 'Official brief format' },
                ].map(f => (
                  <div key={f.label} className="bg-white rounded-xl border border-slate-100 p-3 text-center">
                    <f.icon className="w-5 h-5 text-rose-500 mx-auto mb-1" />
                    <div className="font-semibold text-slate-700">{f.label}</div>
                    <div className="text-[10px] text-slate-400">{f.sub}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {submitting && (
          <div className="h-full flex items-center justify-center">
            <div className="flex flex-col items-center space-y-4">
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-rose-200 rounded-full animate-ping opacity-50" />
                <div className="absolute inset-0 border-4 border-rose-600 border-t-transparent rounded-full animate-spin" />
              </div>
              <div className="text-center">
                <div className="text-sm font-bold text-slate-800">Generating Parliamentary Brief</div>
                <div className="text-xs text-slate-500 mt-1">
                  Querying Evidence Ledger · Assembling NumberSafe citations…
                </div>
              </div>
            </div>
          </div>
        )}

        {errorMsg && (
          <div className="h-full flex items-center justify-center">
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 max-w-sm text-center space-y-3">
              <AlertTriangle className="w-10 h-10 text-red-500 mx-auto" />
              <div className="text-sm font-bold text-red-800">Brief Generation Failed</div>
              <div className="text-xs text-red-600">{errorMsg}</div>
              <button onClick={handleSubmit}
                className="text-xs bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors">
                Retry
              </button>
            </div>
          </div>
        )}

        {brief && !submitting && (
          <div className="p-1">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Generated Brief</h3>
                <p className="text-xs text-slate-500 mt-0.5 italic">"{brief.query.slice(0, 80)}{brief.query.length > 80 ? '…' : ''}"</p>
              </div>
              <div className="text-xs text-slate-400 flex items-center space-x-1">
                <Clock className="w-3 h-3" />
                <span>Just now</span>
              </div>
            </div>
            <BriefDisplay brief={brief} />
          </div>
        )}
      </div>
    </div>
  );
};
