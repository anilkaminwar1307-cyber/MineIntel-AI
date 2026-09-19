import React, { useState, useEffect } from 'react';
import {
  Database,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Search,
  RefreshCw,
  Eye,
  ShieldCheck,
  FileText,
  Compass,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { ExtractedFact, ExtractedFactListResponse, FactSourceProvenance } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';

interface EvidenceLedgerProps {
  onNavigate: (tab: string) => void;
}

export const EvidenceLedger: React.FC<EvidenceLedgerProps> = ({ onNavigate }) => {
  const [data, setData] = useState<ExtractedFactListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [metricFilter, setMetricFilter] = useState<string>('');
  const [periodFilter, setPeriodFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Selected Fact for Provenance Drawer
  const [selectedFactProvenance, setSelectedFactProvenance] = useState<FactSourceProvenance | null>(null);
  const [loadingProvenance, setLoadingProvenance] = useState<boolean>(false);

  const loadEvidence = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getEvidence({
        search: search || undefined,
        metric: metricFilter || undefined,
        period: periodFilter || undefined,
        status_filter: statusFilter || undefined,
      });
      setData(res);
    } catch (err: any) {
      console.error(err);
      setError('Unable to load Evidence Ledger.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvidence();
  }, [metricFilter, periodFilter, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadEvidence();
  };

  const handleViewProvenance = async (factId: string) => {
    setLoadingProvenance(true);
    try {
      const prov = await api.getFactSource(factId);
      setSelectedFactProvenance(prov);
    } catch (err) {
      console.error('Failed to load fact provenance', err);
    } finally {
      setLoadingProvenance(false);
    }
  };

  const facts = data?.items || [];
  const verifiedCount = data?.verified_count || 0;
  const needsReviewCount = data?.needs_review_count || 0;
  const conflictCount = data?.conflict_count || 0;
  const totalCount = data?.total || 0;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-slate-900">Evidence Ledger</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 uppercase font-semibold">
              EvidenceChain
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Traceable structured facts extracted from source documents with page, sheet, row, and cell coordinates.
          </p>
        </div>

        <button
          onClick={loadEvidence}
          className="p-1.5 rounded border border-slate-300 text-slate-600 hover:bg-slate-50 self-start sm:self-auto"
          title="Refresh Evidence Ledger"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span>Total Facts</span>
            <Database className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-xl font-bold text-slate-900">{totalCount}</div>
          <span className="text-[10px] text-slate-400">Extracted data points</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span>Verified Facts</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-xl font-bold text-emerald-700">{verifiedCount}</div>
          <span className="text-[10px] text-slate-400">100% provenance confirmed</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span>Needs Review</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-xl font-bold text-amber-700">{needsReviewCount}</div>
          <span className="text-[10px] text-slate-400">Requires analyst confirmation</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span>Conflicts</span>
            <Flame className="w-4 h-4 text-rose-600" />
          </div>
          <div className="text-xl font-bold text-rose-700">{conflictCount}</div>
          <span className="text-[10px] text-slate-400">Contradictions identified</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="w-full md:w-80 relative">
          <input
            type="text"
            placeholder="Search metric, mine, or context..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:border-amber-500"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
        </form>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:border-amber-500"
          >
            <option value="">All Statuses</option>
            <option value="VERIFIED">Verified</option>
            <option value="EXTRACTED">Extracted</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
            <option value="CONFLICT">Conflict</option>
          </select>
        </div>
      </div>

      {/* Evidence Table or Empty State */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
            Querying Evidence Ledger...
          </div>
        ) : facts.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={Database}
              title="Evidence Ledger Empty"
              description="No structured facts extracted yet. Upload and process mining documents in Document Library."
              actionText="Go to Documents"
              onAction={() => onNavigate('documents')}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
                <tr>
                  <th className="py-3 px-4">Metric</th>
                  <th className="py-3 px-3">Value</th>
                  <th className="py-3 px-2">Unit</th>
                  <th className="py-3 px-3">Period</th>
                  <th className="py-3 px-3">Entity (Mine/Org)</th>
                  <th className="py-3 px-3">Provenance Source</th>
                  <th className="py-3 px-3 text-center">Confidence</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {facts.map((fact) => (
                  <tr key={fact.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-semibold text-slate-900">{fact.metric_name}</p>
                        <p className="text-[10px] font-mono text-slate-400">{fact.metric_code}</p>
                      </div>
                    </td>
                    <td className="py-3 px-3 font-mono font-bold text-slate-900">
                      {fact.numeric_value !== null && fact.numeric_value !== undefined ? Number(fact.numeric_value).toLocaleString() : fact.text_value || '—'}
                    </td>
                    <td className="py-3 px-2 text-slate-600 font-mono text-[11px]">{fact.unit || fact.raw_unit || '—'}</td>
                    <td className="py-3 px-3 text-slate-600 font-mono text-[11px]">{fact.reporting_period || '—'}</td>
                    <td className="py-3 px-3 text-slate-700">
                      <span className="font-medium">{fact.subsidiary || fact.organization}</span>
                      {fact.mine && <span className="text-[11px] text-slate-400 block">{fact.mine}</span>}
                    </td>
                    <td className="py-3 px-3 text-slate-500 text-[11px] font-mono">
                      {fact.sheet_name && <span>[{fact.sheet_name}] </span>}
                      {fact.cell_reference && <strong className="text-amber-700">{fact.cell_reference}</strong>}
                      {!fact.cell_reference && fact.page_number && <span>Page {fact.page_number}</span>}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {(fact.confidence_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge status={fact.validation_status} />
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => handleViewProvenance(fact.id)}
                        className="inline-flex items-center space-x-1 text-[11px] font-semibold text-amber-700 hover:text-amber-900 bg-amber-50 hover:bg-amber-100 px-2 py-1 rounded border border-amber-200 transition"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Source</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Provenance Coordinates Modal */}
      {selectedFactProvenance && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="px-5 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Evidence Provenance Audit</h3>
                  <p className="text-[11px] text-slate-500">Immutable source coordinate traceability (Rule 2)</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedFactProvenance(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              {/* Fact summary */}
              <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg flex items-center justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold text-amber-800">Verified Metric</span>
                  <p className="font-bold text-sm text-slate-900">{selectedFactProvenance.metric_name}</p>
                  <span className="text-slate-500 font-mono text-[10px]">{selectedFactProvenance.metric_code}</span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-500">Extracted Value</span>
                  <p className="text-base font-bold text-slate-900 font-mono">
                    {selectedFactProvenance.numeric_value} <span className="text-amber-700">{selectedFactProvenance.unit}</span>
                  </p>
                </div>
              </div>

              {/* Provenance Coordinates */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
                  Origin Coordinates
                </span>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="p-2 bg-slate-50 rounded border border-slate-200">
                    <span className="text-slate-400 block text-[10px]">Source Document</span>
                    <span className="font-semibold text-slate-800 truncate block">
                      {selectedFactProvenance.provenance.document_name}
                    </span>
                  </div>
                  <div className="p-2 bg-slate-50 rounded border border-slate-200">
                    <span className="text-slate-400 block text-[10px]">Extraction Method</span>
                    <span className="font-mono text-slate-800">
                      {selectedFactProvenance.provenance.extraction_method}
                    </span>
                  </div>
                  <div className="p-2 bg-slate-50 rounded border border-slate-200">
                    <span className="text-slate-400 block text-[10px]">Sheet / Table</span>
                    <span className="font-semibold text-slate-800">
                      {selectedFactProvenance.provenance.sheet_name || selectedFactProvenance.provenance.table_reference || 'N/A'}
                    </span>
                  </div>
                  <div className="p-2 bg-slate-50 rounded border border-slate-200">
                    <span className="text-slate-400 block text-[10px]">Cell / Page Coordinates</span>
                    <span className="font-mono font-bold text-amber-700">
                      {selectedFactProvenance.provenance.cell_reference
                        ? `Cell ${selectedFactProvenance.provenance.cell_reference}`
                        : selectedFactProvenance.provenance.page_number
                        ? `Page ${selectedFactProvenance.provenance.page_number}`
                        : selectedFactProvenance.provenance.row_number
                        ? `Row ${selectedFactProvenance.provenance.row_number}`
                        : 'Document Body'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Source Snippet */}
              {selectedFactProvenance.provenance.source_context && (
                <div>
                  <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block mb-1">
                    Source Text Snippet
                  </span>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 font-mono text-[11px] text-slate-700 whitespace-pre-wrap leading-relaxed">
                    {selectedFactProvenance.provenance.source_context}
                  </div>
                </div>
              )}

              {/* Close Button */}
              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => setSelectedFactProvenance(null)}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-900 text-white transition"
                >
                  Close Provenance Inspector
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
