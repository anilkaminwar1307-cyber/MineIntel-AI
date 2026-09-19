import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Shield,
  Sparkles,
  Layers,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Code2,
  Database,
  HelpCircle,
  BarChart3,
  TrendingUp,
  Cpu,
  RefreshCw
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Cell
} from 'recharts';
import { api } from '../services/api';
import { QueryResponse, EvidenceSourceCitation } from '../types';
import { ErrorBoundary } from '../components/common/ErrorBoundary';

const SUGGESTED_PROMPTS = [
  "What was SECL's raw coal production in FY 2024-25?",
  "Compare raw coal production across all subsidiaries in FY 2024-25",
  "Show CMPDI drilling meters achievement in FY 2024-25",
  "Verify claim: ECL raw coal production was 42.1 MT in FY 2024-25",
  "What were total Coal India dispatch figures in FY 2024-25?",
  "Show overburden removal (OBR) for NCL in FY 2023-24",
];

const COLORS = ['#d97706', '#2563eb', '#059669', '#dc2626', '#7c3aed', '#db2777', '#0891b2', '#4b5563'];

// Null-safe numeric formatting helper
const safeFormatNumber = (val: any, decimals: number = 2): string => {
  if (val === null || val === undefined || val === '') return '—';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return String(val);
  return num.toLocaleString(undefined, { maximumFractionDigits: decimals });
};

// Null-safe percentage formatting helper
const safeFormatPercent = (val: any, decimals: number = 1): string => {
  if (val === null || val === undefined || val === '') return '0.0%';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return '0.0%';
  const scaled = num <= 1.0 && num >= 0 ? num * 100 : num;
  return `${scaled.toFixed(decimals)}%`;
};

export const AskMineIntel: React.FC = () => {
  const [query, setQuery] = useState<string>('');
  const [scope, setScope] = useState<string>('ALL_EVIDENCE');
  const [responseMode, setResponseMode] = useState<string>('STANDARD');
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [showSql, setShowSql] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastSubmittedQuery, setLastSubmittedQuery] = useState<string>('');

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  const executeQuery = async (queryText: string) => {
    const textToRun = (queryText || '').trim();
    if (!textToRun) return;

    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    setSubmitting(true);
    setErrorMessage(null);
    setLastSubmittedQuery(textToRun);

    // 25-second loading timeout to guarantee UI never continues thinking indefinitely
    timerRef.current = setTimeout(() => {
      setSubmitting(false);
      setErrorMessage('Unable to complete query.');
    }, 25000);

    try {
      const res = await api.submitQuery({
        query: textToRun,
        scope,
        response_mode: responseMode
      });

      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }

      setResponse(res);
      setErrorMessage(null);
    } catch (err: any) {
      console.error('Query execution error:', err);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      setErrorMessage('Unable to complete query.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    executeQuery(query);
  };

  const handleChipClick = (prompt: string) => {
    setQuery(prompt);
    executeQuery(prompt);
  };

  const getVerificationBadge = (result?: string | null) => {
    const status = (result || '').toUpperCase();
    if (status.includes('SUPPORTED') && !status.includes('PARTIAL')) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-100 text-emerald-800 text-xs font-semibold border border-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>CLAIM VERIFIED (SUPPORTED)</span>
        </span>
      );
    } else if (status.includes('CONFLICT') || status.includes('DISCREPANCY')) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-rose-100 text-rose-800 text-xs font-semibold border border-rose-300">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>CLAIM CONFLICTING (DISCREPANCY DETECTED)</span>
        </span>
      );
    } else if (status.includes('PARTIAL')) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-amber-100 text-amber-800 text-xs font-semibold border border-amber-300">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>PARTIALLY SUPPORTED</span>
        </span>
      );
    } else if (status.includes('INSUFFICIENT')) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-300">
          <HelpCircle className="w-3.5 h-3.5" />
          <span>INSUFFICIENT EVIDENCE</span>
        </span>
      );
    }
    return null;
  };

  const sourcesList: EvidenceSourceCitation[] = Array.isArray(response?.sources)
    ? response!.sources
    : [];

  const suggestionsList: string[] = Array.isArray(response?.suggestions)
    ? response!.suggestions
    : [];

  const calculationStepsList: string[] = Array.isArray(response?.calculation_steps)
    ? response!.calculation_steps
    : [];

  const isChartAvailable = Boolean(
    response?.chart &&
    typeof response.chart === 'object' &&
    Array.isArray(response.chart.data) &&
    response.chart.data.length > 0
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-slate-900">Ask MineIntel</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 uppercase font-semibold">
              NumberSafe SQL & Claim Copilot
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Deterministic mining intelligence powered by CMPDI exploration records, CIL subsidiary data, and verified evidence facts.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-semibold text-slate-700">Database Ledger: 50,000+ Facts Active</span>
        </div>
      </div>

      {/* Query Formulation Card */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          {/* Scope Selector */}
          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-500 font-medium">Scope:</span>
            <div className="inline-flex rounded border border-slate-200 p-0.5 bg-slate-50">
              <button
                type="button"
                onClick={() => setScope('ALL_EVIDENCE')}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  scope === 'ALL_EVIDENCE' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                All 8 Subsidiaries
              </button>
              <button
                type="button"
                onClick={() => setScope('VERIFIED_ONLY')}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  scope === 'VERIFIED_ONLY' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                Human-Verified Evidence Only
              </button>
            </div>
          </div>

          {/* Response Mode Selector */}
          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-500 font-medium">Response Mode:</span>
            <select
              value={responseMode}
              onChange={(e) => setResponseMode(e.target.value)}
              className="text-xs border border-slate-300 rounded px-2.5 py-1 bg-white text-slate-800 focus:outline-none focus:border-amber-500 font-medium"
            >
              <option value="STANDARD">Standard Analysis</option>
              <option value="OFFICIAL">Official CMPDI Memo</option>
              <option value="PARLIAMENTARY">Parliamentary Query (PQ) Brief</option>
            </select>
          </div>
        </div>

        {/* Suggested Prompts */}
        <div className="space-y-1.5">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Suggested Queries:</div>
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTED_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleChipClick(prompt)}
                className="text-left text-[11px] px-2.5 py-1 rounded-full bg-slate-50 hover:bg-amber-50 hover:border-amber-300 border border-slate-200 text-slate-700 transition-colors font-medium"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="space-y-3 pt-2">
          <div className="relative">
            <textarea
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  executeQuery(query);
                }
              }}
              placeholder="Ask about coal production, dispatch, stripping ratio, CMPDI drilling, reserves, or verify claims..."
              className="w-full text-xs border border-slate-300 rounded-lg p-3 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 resize-none font-sans"
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-[11px] text-slate-500">
              <Shield className="w-4 h-4 text-emerald-600" />
              <span>NumberSafe AI: Hallucinated metrics prevented via direct SQL execution</span>
            </div>

            <button
              type="submit"
              disabled={!query.trim() || submitting}
              className={`inline-flex items-center space-x-1.5 px-4 py-1.5 rounded text-xs font-semibold text-white shadow-sm transition-colors ${
                !query.trim() || submitting
                  ? 'bg-slate-300 cursor-not-allowed'
                  : 'bg-slate-900 hover:bg-slate-800'
              }`}
            >
              <Send className="w-3.5 h-3.5" />
              <span>{submitting ? 'Executing NumberSafe Engine...' : 'Run Intelligence Query'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Loading Progress State */}
      {submitting && (
        <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm flex items-center space-x-3 text-slate-700 text-xs font-medium">
          <RefreshCw className="w-4 h-4 text-amber-600 animate-spin flex-shrink-0" />
          <span>Executing NumberSafe Engine & Grounded SQL Synthesis across 50,000+ facts...</span>
        </div>
      )}

      {/* Error State with Retry Button */}
      {errorMessage && !submitting && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg flex items-center justify-between gap-3 text-xs text-rose-900 shadow-sm">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span className="font-semibold">{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => executeQuery(lastSubmittedQuery || query)}
            className="inline-flex items-center space-x-1 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded font-semibold text-xs shadow-sm transition-colors flex-shrink-0"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Response Display */}
      {response && !submitting && (
        <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-5">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200 gap-2">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">Synthesized Intelligence</h3>
              {response.verification_result && getVerificationBadge(response.verification_result)}
            </div>
            <div className="flex items-center space-x-3 text-xs text-slate-500">
              <span>
                Evidence Facts: <strong className="text-slate-800">{safeFormatNumber(response.verified_facts_count, 0)}</strong>
              </span>
              <span>
                Confidence: <strong className="text-emerald-700 font-mono">{safeFormatPercent(response.confidence_score)}</strong>
              </span>
            </div>
          </div>

          {/* Metric KPI Card (if direct single metric) */}
          {response.direct_metric_value !== null && response.direct_metric_value !== undefined && (
            <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold text-amber-800 uppercase tracking-wider block">
                  Deterministic Verified Metric
                </span>
                <div className="text-2xl font-extrabold text-slate-900 mt-0.5">
                  {safeFormatNumber(response.direct_metric_value)}
                  <span className="text-sm font-medium text-slate-600 ml-1.5">{response.metric_unit || ''}</span>
                </div>
              </div>
              <div className="text-right">
                <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>PROVENANCE VERIFIED</span>
                </span>
              </div>
            </div>
          )}

          {/* Answer Narrative */}
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-800 leading-relaxed font-sans space-y-2">
            <p className="font-semibold text-slate-900 whitespace-pre-line">{response.answer || 'No narrative text returned.'}</p>
          </div>

          {/* Interactive Chart with Fault-Isolated ChartErrorBoundary */}
          {isChartAvailable && (
            <ErrorBoundary
              isCompact
              fallbackMessage="Chart unavailable for this result."
            >
              <div className="p-4 bg-white rounded-lg border border-slate-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="w-4 h-4 text-amber-600" />
                    <h4 className="text-xs font-bold text-slate-900">{response.chart?.title || 'Visual Summary'}</h4>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">Live SQL Aggregation</span>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    {response.chart?.type === 'line' ? (
                      <LineChart data={response.chart.data} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Line type="monotone" dataKey="value" stroke="#d97706" strokeWidth={2} dot={{ r: 4 }} />
                      </LineChart>
                    ) : (
                      <BarChart data={response.chart?.data || []} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                          {(response.chart?.data || []).map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </div>
            </ErrorBoundary>
          )}

          {/* NumberSafe Calculation Steps */}
          {calculationStepsList.length > 0 && (
            <div className="p-3 bg-amber-50/50 rounded-lg border border-amber-200 space-y-2">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-amber-900">
                <Cpu className="w-4 h-4 text-amber-600" />
                <span>NumberSafe Calculation Audit Trail:</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-xs text-amber-950 font-mono">
                {calculationStepsList.map((step, idx) => (
                  <li key={idx} className="leading-snug">{step}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Deterministic SQL Query Accordion */}
          {response.sql_query && (
            <div>
              <button
                type="button"
                onClick={() => setShowSql(!showSql)}
                className="flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
              >
                <Code2 className="w-3.5 h-3.5 text-slate-500" />
                <span>{showSql ? 'Hide SQL Query' : 'View Generated SQL Query'}</span>
              </button>
              {showSql && (
                <div className="mt-2 p-3 bg-slate-900 rounded-md text-emerald-400 font-mono text-[11px] overflow-x-auto shadow-inner">
                  <pre>{response.sql_query}</pre>
                </div>
              )}
            </div>
          )}

          {/* Grounded Citations & Provenance Table */}
          {sourcesList.length > 0 && (
            <div className="space-y-3 pt-3 border-t border-slate-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileText className="w-4 h-4 text-slate-600" />
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Evidence Citations ({sourcesList.length} Records)
                  </h4>
                </div>
                <span className="text-[10px] text-slate-500">Every figure verified to source cell/page</span>
              </div>

              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="w-full text-left text-xs text-slate-700">
                  <thead className="bg-slate-50 text-[11px] text-slate-500 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2 px-3">Metric</th>
                      <th className="py-2 px-3">Value & Unit</th>
                      <th className="py-2 px-3">Entity / Subsidiary</th>
                      <th className="py-2 px-3">Period</th>
                      <th className="py-2 px-3">Source Document</th>
                      <th className="py-2 px-3">Location Coordinates</th>
                      <th className="py-2 px-3 text-center">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {sourcesList.map((src, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-2 px-3 font-semibold text-slate-900">{src.metric_name || src.metric_code || 'Evidence Fact'}</td>
                        <td className="py-2 px-3 font-mono font-medium text-slate-950">
                          {src.numeric_value !== undefined && src.numeric_value !== null
                            ? `${safeFormatNumber(src.numeric_value)} ${src.unit || ''}`
                            : (src as any).value || '—'}
                        </td>
                        <td className="py-2 px-3">
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 font-semibold text-slate-800 text-[10px]">
                            {src.subsidiary || 'CIL'}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-slate-600 text-[11px]">{src.reporting_period || '—'}</td>
                        <td className="py-2 px-3">
                          <span className="text-slate-800 font-medium truncate block max-w-xs" title={src.document_name || 'Document'}>
                            {src.document_name || 'Document'}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-[11px] font-mono text-slate-600">
                          {src.page_number ? `Pg ${src.page_number} ` : ''}
                          {src.sheet_name ? `Sheet: ${src.sheet_name} ` : ''}
                          {src.cell_reference ? `[Cell ${src.cell_reference}] ` : ''}
                          {src.row_number ? `R${src.row_number}:C${src.column_name || ''}` : ''}
                          {!src.page_number && !src.sheet_name && !src.cell_reference && !src.row_number ? 'Relational Record' : ''}
                        </td>
                        <td className="py-2 px-3 text-center">
                          <span className="font-mono text-emerald-700 font-semibold">
                            {safeFormatPercent(src.confidence_score, 0)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Follow-up Suggestions */}
          {suggestionsList.length > 0 && (
            <div className="pt-2 border-t border-slate-100 space-y-1.5">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Suggested Next Queries:</span>
              <div className="flex flex-wrap gap-1.5">
                {suggestionsList.map((sug, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleChipClick(sug)}
                    className="text-xs px-2.5 py-1 rounded bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-900 transition-colors font-medium"
                  >
                    {sug}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
