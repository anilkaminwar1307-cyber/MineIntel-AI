/**
 * CalculationTrace — NumberSafe 2.0 Audit Card
 *
 * Displays the full deterministic evidence chain for any NumberSafe calculation:
 *  • Result & canonical unit with confidence badge
 *  • Data Source Mode: REAL / DEMO / MIXED warning
 *  • Verification status derived strictly from evidence (never hard-coded)
 *  • Expandable "How was this calculated?" panel
 *    – SQL description / formula
 *    – Included facts table with document + page/cell provenance
 *    – Excluded facts table with explicit reasons
 *    – Active warnings
 *    – Lineage ID (copy to clipboard)
 */
import React, { useState, useCallback } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Shield,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Database,
  FileText,
  FlaskConical,
  Layers,
  Info,
} from 'lucide-react';
import { CalculationResult, IncludedFact, ExclusionDecision } from '../../types';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(val: number | null | undefined, decimals = 2): string {
  if (val === null || val === undefined) return '—';
  return val.toLocaleString(undefined, { maximumFractionDigits: decimals });
}

function pct(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return `${val.toFixed(1)}%`;
}

function provenanceLabel(f: IncludedFact): string {
  const parts: string[] = [];
  if (f.sheet_name) parts.push(`Sheet: ${f.sheet_name}`);
  if (f.cell_reference) parts.push(`Cell: ${f.cell_reference}`);
  if (f.page_number) parts.push(`Page: ${f.page_number}`);
  return parts.length ? parts.join(' · ') : '—';
}

// ─── Sub-components ──────────────────────────────────────────────────────────

interface DataSourceBadgeProps {
  scope: string;
}
const DataSourceBadge: React.FC<DataSourceBadgeProps> = ({ scope }) => {
  if (scope === 'REAL') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 border border-emerald-300">
        <Database className="w-3 h-3" />
        REAL UPLOADED DATA
      </span>
    );
  }
  if (scope === 'DEMO') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-sky-100 text-sky-700 border border-sky-300">
        <FlaskConical className="w-3 h-3" />
        DEMO DATA
      </span>
    );
  }
  if (scope === 'MIXED') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-amber-100 text-amber-800 border border-amber-400 animate-pulse">
        <AlertTriangle className="w-3 h-3" />
        MIXED — REAL + DEMO
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-100 text-slate-500 border border-slate-300">
      <Layers className="w-3 h-3" />
      UNKNOWN
    </span>
  );
};

interface VerificationBadgeProps {
  result: CalculationResult;
}
const VerificationBadge: React.FC<VerificationBadgeProps> = ({ result }) => {
  if (!result.success) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-rose-100 text-rose-800 border border-rose-300">
        <ShieldX className="w-3.5 h-3.5" />
        {result.error_code ?? 'CALCULATION ERROR'}
      </span>
    );
  }
  if (result.evidence_count_used === 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-100 text-slate-600 border border-slate-300">
        <Shield className="w-3.5 h-3.5" />
        INSUFFICIENT EVIDENCE
      </span>
    );
  }
  const vPct = result.verified_pct ?? 0;
  if (result.warnings.some(w => w.includes('GRAIN') || w.includes('OVERLAP'))) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-orange-100 text-orange-800 border border-orange-400">
        <ShieldAlert className="w-3.5 h-3.5" />
        MIXED GRAIN — REVIEW REQUIRED
      </span>
    );
  }
  if (vPct >= 100) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 border border-emerald-300">
        <ShieldCheck className="w-3.5 h-3.5" />
        VERIFIED RESULT — {pct(vPct)} VERIFIED
      </span>
    );
  }
  if (vPct >= 60) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-amber-100 text-amber-800 border border-amber-300">
        <ShieldAlert className="w-3.5 h-3.5" />
        PARTIALLY VERIFIED — {pct(vPct)}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-orange-100 text-orange-800 border border-orange-400">
      <Shield className="w-3.5 h-3.5" />
      LOW VERIFICATION — {pct(vPct)}
    </span>
  );
};

// ─── Included Facts Table ─────────────────────────────────────────────────────

const IncludedFactsTable: React.FC<{ facts: IncludedFact[] }> = ({ facts }) => (
  <div className="overflow-x-auto rounded border border-emerald-200">
    <table className="w-full text-[11px] divide-y divide-emerald-100">
      <thead className="bg-emerald-50">
        <tr>
          {['Metric', 'Subsidiary', 'Period', 'Value', 'Unit', 'Status', 'Provenance', 'Confidence'].map(h => (
            <th key={h} className="px-2 py-1.5 text-left font-semibold text-emerald-900 uppercase tracking-wide whitespace-nowrap">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-emerald-50 bg-white">
        {facts.map(f => (
          <tr key={f.fact_id} className="hover:bg-emerald-50/50 transition-colors">
            <td className="px-2 py-1.5 font-mono text-slate-700 whitespace-nowrap">{f.metric_code}</td>
            <td className="px-2 py-1.5 text-slate-600">{f.subsidiary ?? '—'}</td>
            <td className="px-2 py-1.5 text-slate-600 whitespace-nowrap">{f.reporting_period ?? '—'}</td>
            <td className="px-2 py-1.5 font-semibold text-slate-900 text-right whitespace-nowrap">
              {fmt(f.numeric_value)}
            </td>
            <td className="px-2 py-1.5 text-slate-500">{f.unit ?? '—'}</td>
            <td className="px-2 py-1.5 whitespace-nowrap">
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                  f.validation_status === 'VERIFIED'
                    ? 'bg-emerald-100 text-emerald-800'
                    : f.validation_status === 'PENDING'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {f.validation_status}
              </span>
            </td>
            <td className="px-2 py-1.5 text-slate-500 font-mono">{provenanceLabel(f)}</td>
            <td className="px-2 py-1.5 text-slate-600 text-right whitespace-nowrap">
              {pct(f.confidence_score * (f.confidence_score <= 1 ? 100 : 1))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// ─── Excluded Facts Table ─────────────────────────────────────────────────────

const ExcludedFactsTable: React.FC<{ exclusions: ExclusionDecision[] }> = ({ exclusions }) => (
  <div className="overflow-x-auto rounded border border-rose-200">
    <table className="w-full text-[11px] divide-y divide-rose-100">
      <thead className="bg-rose-50">
        <tr>
          {['Fact ID', 'Exclusion Reason', 'Kept In Favour Of'].map(h => (
            <th key={h} className="px-2 py-1.5 text-left font-semibold text-rose-900 uppercase tracking-wide">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-rose-50 bg-white">
        {exclusions.map(e => (
          <tr key={e.fact_id} className="hover:bg-rose-50/40 transition-colors">
            <td className="px-2 py-1.5 font-mono text-slate-600 text-[10px]">{e.fact_id.slice(0, 8)}…</td>
            <td className="px-2 py-1.5 text-rose-800">{e.reason}</td>
            <td className="px-2 py-1.5 font-mono text-slate-500 text-[10px]">
              {e.excluded_in_favour_of ? `${e.excluded_in_favour_of.slice(0, 8)}…` : '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────

interface CalculationTraceProps {
  result: CalculationResult;
  /** Optional label override for the card title */
  label?: string;
}

export const CalculationTrace: React.FC<CalculationTraceProps> = ({ result, label }) => {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyLineage = useCallback(() => {
    if (!result.lineage_id) return;
    navigator.clipboard.writeText(result.lineage_id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [result.lineage_id]);

  const hasIncluded = result.included_facts.length > 0;
  const hasExcluded = result.exclusions.length > 0;
  const hasWarnings = result.warnings.length > 0;

  return (
    <div
      className={`rounded-xl border-2 shadow-sm overflow-hidden transition-all duration-200 ${
        !result.success
          ? 'border-rose-300 bg-rose-50'
          : result.is_demo_scope === 'MIXED'
          ? 'border-amber-400 bg-amber-50'
          : result.is_demo_scope === 'DEMO'
          ? 'border-sky-300 bg-sky-50'
          : 'border-emerald-300 bg-white'
      }`}
    >
      {/* ── Header ── */}
      <div className="px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        {/* Left: icon + title + result */}
        <div className="flex items-start gap-3">
          <div className="mt-0.5">
            {result.success ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            )}
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-0.5">
              {label ?? `NumberSafe: ${result.metric_code}`}
            </p>
            {result.success && result.result !== null && result.result !== undefined ? (
              <p className="text-2xl font-black text-slate-900 leading-none">
                {fmt(result.result, 2)}
                {result.unit && (
                  <span className="ml-1.5 text-sm font-semibold text-slate-500">{result.unit}</span>
                )}
              </p>
            ) : (
              <p className="text-sm font-semibold text-rose-700 mt-1">
                {result.error_message ?? 'No result computed'}
              </p>
            )}
            {result.formula && (
              <p className="mt-1 text-[11px] font-mono text-slate-500 bg-slate-100 rounded px-1.5 py-0.5 inline-block">
                {result.formula}
              </p>
            )}
          </div>
        </div>

        {/* Right: badges */}
        <div className="flex flex-wrap items-center gap-1.5">
          <DataSourceBadge scope={result.is_demo_scope} />
          <VerificationBadge result={result} />
        </div>
      </div>

      {/* ── Stats bar ── */}
      {result.success && (
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-200 flex flex-wrap gap-4 text-[11px] text-slate-600">
          <span>
            <span className="font-semibold text-slate-800">{result.evidence_count_used}</span> facts used
          </span>
          <span>
            <span className="font-semibold text-slate-800">{result.excluded_count}</span> excluded
          </span>
          <span>
            <span className="font-semibold text-emerald-700">{result.verified_count}</span> verified (
            {pct(result.verified_pct)})
          </span>
          {result.calculation_method && (
            <span className="font-mono text-slate-500">
              method: <span className="font-semibold text-slate-700">{result.calculation_method}</span>
            </span>
          )}
        </div>
      )}

      {/* ── Warnings ── */}
      {hasWarnings && (
        <div className="px-4 py-2 bg-amber-50 border-t border-amber-200 space-y-0.5">
          {result.warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[11px] text-amber-800">
              <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Expand / Collapse toggle ── */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-4 py-2 border-t border-slate-200 hover:bg-slate-50 transition-colors text-xs font-semibold text-slate-600"
        id={`calc-trace-toggle-${result.lineage_id ?? result.metric_code}`}
      >
        <span className="flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5" />
          How was this calculated?
        </span>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* ── Detail panel ── */}
      {expanded && (
        <div className="px-4 py-3 border-t border-slate-200 space-y-4">

          {/* SQL / Method description */}
          {result.sql_description && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">
                Deterministic SQL Operation
              </p>
              <pre className="text-[11px] font-mono bg-slate-900 text-emerald-300 rounded-lg px-3 py-2.5 whitespace-pre-wrap overflow-x-auto">
                {result.sql_description}
              </pre>
            </div>
          )}

          {/* Included facts */}
          {hasIncluded && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-700 mb-1.5 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Included Evidence ({result.included_facts.length} records)
              </p>
              <IncludedFactsTable facts={result.included_facts} />
            </div>
          )}

          {/* Excluded facts */}
          {hasExcluded && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-rose-700 mb-1.5 flex items-center gap-1">
                <XCircle className="w-3 h-3" />
                Excluded Facts — with explicit reasons ({result.exclusions.length})
              </p>
              <ExcludedFactsTable exclusions={result.exclusions} />
            </div>
          )}

          {/* Filters applied */}
          {Object.keys(result.filters_applied).length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Filters Applied</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(result.filters_applied)
                  .filter(([, v]) => v !== null && v !== undefined && v !== '')
                  .map(([k, v]) => (
                    <span
                      key={k}
                      className="px-2 py-0.5 rounded bg-slate-100 border border-slate-300 text-[11px] font-mono text-slate-700"
                    >
                      {k}={String(v)}
                    </span>
                  ))}
              </div>
            </div>
          )}

          {/* Lineage ID */}
          {result.lineage_id && (
            <div className="flex items-center justify-between rounded bg-slate-900 px-3 py-2">
              <div>
                <p className="text-[10px] font-bold uppercase text-slate-400 mb-0.5">Lineage ID</p>
                <p className="text-[11px] font-mono text-amber-300">{result.lineage_id}</p>
              </div>
              <button
                onClick={handleCopyLineage}
                className="flex items-center gap-1 px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-xs text-slate-200 transition-colors"
                title="Copy Lineage ID"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CalculationTrace;
