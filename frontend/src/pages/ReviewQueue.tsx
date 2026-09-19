import React, { useState, useEffect } from 'react';
import {
  CheckSquare,
  AlertTriangle,
  Flame,
  HelpCircle,
  Clock,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Edit3,
  Split,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { ReviewQueueResponse, ConflictItem } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';

interface ReviewQueueProps {
  onNavigate: (tab: string) => void;
}

export const ReviewQueue: React.FC<ReviewQueueProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<'issues' | 'conflicts'>('issues');
  const [queue, setQueue] = useState<ReviewQueueResponse | null>(null);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters & Pagination for Issues
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [issueTypeFilter, setIssueTypeFilter] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;

  // Edit Modal State
  const [editingIssue, setEditingIssue] = useState<any | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('Analyst verified against primary coal report.');

  // Conflict Resolution Modal State
  const [resolvingConflict, setResolvingConflict] = useState<ConflictItem | null>(null);
  const [chosenFactId, setChosenFactId] = useState<string>('');
  const [conflictNotes, setConflictNotes] = useState<string>('Selected based on audited CMPDI exploration/annual filing.');

  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const loadQueue = async () => {
    try {
      setLoading(true);
      const data = await api.getReviewQueue({
        status: 'OPEN',
        severity: severityFilter || undefined,
        issue_type: issueTypeFilter || undefined,
        page,
        page_size: pageSize
      });
      setQueue(data);

      const conflictData = await api.getConflicts();
      setConflicts(conflictData.conflicts || []);
    } catch (err) {
      console.error('Error loading review queue:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [severityFilter, issueTypeFilter, page]);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleApprove = async (issueId: string) => {
    try {
      const res = await api.approveReview(issueId);
      showToast(res.message);
      await loadQueue();
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Failed to approve issue', 'error');
    }
  };

  const handleReject = async (issueId: string) => {
    try {
      const res = await api.rejectReview(issueId);
      showToast(res.message);
      await loadQueue();
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Failed to reject issue', 'error');
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingIssue) return;
    const val = parseFloat(editValue);
    if (isNaN(val)) {
      showToast('Please enter a valid numeric value', 'error');
      return;
    }
    try {
      const res = await api.editReview(editingIssue.id, {
        corrected_value: val,
        notes: editNotes
      });
      showToast(res.message);
      setEditingIssue(null);
      await loadQueue();
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Failed to update and approve', 'error');
    }
  };

  const handleConflictResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvingConflict || !chosenFactId) return;
    try {
      const res = await api.resolveConflict(resolvingConflict.id, {
        chosen_fact_id: chosenFactId,
        resolution_notes: conflictNotes
      });
      showToast(res.message);
      setResolvingConflict(null);
      await loadQueue();
    } catch (err: any) {
      showToast(err.response?.data?.detail || 'Failed to resolve conflict', 'error');
    }
  };

  const items = queue?.items || [];
  const totalItems = queue?.total || 0;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-slate-900">Review & Conflict Queue</h2>
            <span className="text-[11px] px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
              CMPDI Human-In-The-Loop Sign-Off
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit-ready human resolution for outlier values, low-confidence extractions, and multi-document contradictions.
          </p>
        </div>

        <button
          onClick={loadQueue}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold"
          title="Refresh Review Queue"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Database</span>
        </button>
      </div>

      {toast && (
        <div className={`p-3.5 rounded-lg text-xs font-medium border flex items-center justify-between ${
          toast.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-rose-50 border-rose-200 text-rose-900'
        }`}>
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)}><X className="w-4 h-4" /></button>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          onClick={() => setActiveTab('issues')}
          className={`cursor-pointer p-4 rounded-lg border transition-all ${
            activeTab === 'issues' ? 'bg-amber-50/50 border-amber-300 shadow-sm' : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span>Open Validation Issues</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-extrabold text-slate-900">{queue?.open_reviews || 0}</div>
          <span className="text-[10px] text-slate-400">Awaiting analyst action</span>
        </div>

        <div
          onClick={() => setActiveTab('conflicts')}
          className={`cursor-pointer p-4 rounded-lg border transition-all ${
            activeTab === 'conflicts' ? 'bg-rose-50/50 border-rose-300 shadow-sm' : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span>Contradictory Conflicts</span>
            <Flame className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-extrabold text-rose-700">{queue?.conflicts || conflicts.length}</div>
          <span className="text-[10px] text-slate-400">Multi-source discrepancies</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span>Low Confidence Extractions</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-extrabold text-amber-700">{queue?.low_confidence || 0}</div>
          <span className="text-[10px] text-slate-400">Confidence below 75%</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-1">
            <span>Missing Units / Context</span>
            <HelpCircle className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-extrabold text-slate-900">{queue?.missing_metadata || 0}</div>
          <span className="text-[10px] text-slate-400">Incomplete metadata rows</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('issues')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center space-x-2 ${
            activeTab === 'issues'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <CheckSquare className="w-4 h-4" />
          <span>Validation Issues ({queue?.open_reviews || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('conflicts')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center space-x-2 ${
            activeTab === 'conflicts'
              ? 'bg-rose-700 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Flame className="w-4 h-4" />
          <span>Contradictory Conflicts ({conflicts.length})</span>
        </button>
      </div>

      {/* TAB 1: Validation Issues */}
      {activeTab === 'issues' && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden space-y-4">
          {/* Filters Bar */}
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase mr-1.5">Severity:</label>
                <select
                  value={severityFilter}
                  onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
                  className="text-xs border border-slate-300 rounded px-2.5 py-1 bg-white text-slate-800"
                >
                  <option value="">All Severities</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase mr-1.5">Issue Type:</label>
                <select
                  value={issueTypeFilter}
                  onChange={(e) => { setIssueTypeFilter(e.target.value); setPage(1); }}
                  className="text-xs border border-slate-300 rounded px-2.5 py-1 bg-white text-slate-800"
                >
                  <option value="">All Types</option>
                  <option value="OUTLIER">Outlier Detection</option>
                  <option value="LOW_CONFIDENCE">Low Confidence</option>
                  <option value="MISSING_METADATA">Missing Metadata</option>
                  <option value="CONFLICT">Cross-Doc Conflict</option>
                </select>
              </div>
            </div>

            <div className="text-xs text-slate-500">
              Showing page <strong>{page}</strong> of <strong>{totalPages}</strong> ({totalItems} total issues)
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="p-12 text-center text-xs text-slate-500">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
              Loading database review queue...
            </div>
          ) : items.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={CheckSquare}
                title="Review Queue Clear"
                description="No open validation issues matching your filters. All evidence is verified or approved."
                actionText="View Evidence Ledger"
                onAction={() => onNavigate('evidence')}
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
                  <tr>
                    <th className="py-3 px-4">Metric & Value</th>
                    <th className="py-3 px-3">Issue Reason</th>
                    <th className="py-3 px-3">Coordinates / Context</th>
                    <th className="py-3 px-3">Severity</th>
                    <th className="py-3 px-4 text-right">Analyst Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900">{item.metric_name || 'Unspecified Metric'}</div>
                        {item.raw_value && (
                          <div className="text-[11px] font-mono text-slate-500 mt-0.5">Value: {item.raw_value}</div>
                        )}
                      </td>
                      <td className="py-3 px-3 text-slate-700 max-w-sm">
                        <span className="font-semibold text-slate-800 block">{item.issue_type}</span>
                        <span className="text-[11px] text-slate-500">{item.description}</span>
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px] text-slate-500 max-w-xs truncate" title={item.source_reference || ''}>
                        {item.source_reference || '—'}
                      </td>
                      <td className="py-3 px-3">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          item.severity === 'CRITICAL' ? 'bg-rose-50 text-rose-800 border-rose-200' :
                          item.severity === 'HIGH' ? 'bg-amber-50 text-amber-800 border-amber-200' :
                          'bg-slate-100 text-slate-700 border-slate-200'
                        }`}>
                          {item.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            type="button"
                            onClick={() => handleApprove(item.id)}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-800 text-[11px] font-semibold"
                            title="Confirm and verify fact"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Approve</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => {
                              setEditingIssue(item);
                              setEditValue(item.raw_value || '');
                            }}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-50 hover:bg-slate-100 border border-slate-300 text-slate-700 text-[11px] font-semibold"
                            title="Edit value before approving"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                            <span>Edit</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => handleReject(item.id)}
                            className="inline-flex items-center space-x-1 px-2 py-1 rounded bg-rose-50 hover:bg-rose-100 border border-rose-300 text-rose-800 text-[11px] font-semibold"
                            title="Reject fact"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="inline-flex items-center space-x-1 px-3 py-1 rounded text-xs border border-slate-300 bg-white text-slate-700 disabled:opacity-40"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </button>

              <span className="text-xs text-slate-600 font-medium">Page {page} of {totalPages}</span>

              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="inline-flex items-center space-x-1 px-3 py-1 rounded text-xs border border-slate-300 bg-white text-slate-700 disabled:opacity-40"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Conflicts */}
      {activeTab === 'conflicts' && (
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden space-y-4">
          <div className="p-4 bg-rose-50/50 border-b border-rose-200 flex items-center justify-between">
            <div>
              <h4 className="text-xs font-bold text-rose-900 uppercase">Cross-Document Evidence Conflicts ({conflicts.length})</h4>
              <p className="text-[11px] text-rose-700 mt-0.5">
                Two or more official documents report contradictory values for the same subsidiary, metric, and period. Choose the canonical record.
              </p>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300 uppercase">
              Rule 5: Never Hide Conflicts
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
                <tr>
                  <th className="py-3 px-4">Subsidiary & Period</th>
                  <th className="py-3 px-3">Metric</th>
                  <th className="py-3 px-3 text-slate-900 font-bold">Document A Value</th>
                  <th className="py-3 px-3 text-slate-900 font-bold">Document B Value</th>
                  <th className="py-3 px-3">Variance %</th>
                  <th className="py-3 px-4 text-right">Resolve</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {conflicts.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4">
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 font-bold text-slate-800 text-[10px] mr-1.5">
                        {c.subsidiary}
                      </span>
                      <span className="text-slate-600 font-mono text-[11px]">{c.reporting_period}</span>
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-800">{c.metric_code}</td>
                    <td className="py-3 px-3">
                      <div className="font-mono font-bold text-slate-900">{c.fact_a_value.toFixed(2)}</div>
                      <div className="text-[10px] text-slate-400 truncate max-w-xs" title={c.fact_a_doc}>{c.fact_a_doc}</div>
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-mono font-bold text-slate-900">{c.fact_b_value.toFixed(2)}</div>
                      <div className="text-[10px] text-slate-400 truncate max-w-xs" title={c.fact_b_doc}>{c.fact_b_doc}</div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 text-[10px]">
                        +{c.discrepancy_pct.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={() => {
                          setResolvingConflict(c);
                          setChosenFactId(c.fact_a_id);
                        }}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 rounded bg-rose-700 hover:bg-rose-800 text-white font-bold text-xs shadow-sm"
                      >
                        <Split className="w-3.5 h-3.5" />
                        <span>Resolve</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* EDIT MODAL */}
      {editingIssue && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white w-full max-w-md rounded-lg border border-slate-300 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <h3 className="text-sm font-bold text-slate-900">Edit & Verify Evidence Fact</h3>
              <button onClick={() => setEditingIssue(null)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>

            <form onSubmit={handleEditSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Metric</label>
                <input
                  type="text"
                  value={editingIssue.metric_name || ''}
                  disabled
                  className="w-full text-xs border border-slate-200 bg-slate-50 rounded px-3 py-2 text-slate-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Corrected Value</label>
                <input
                  type="number"
                  step="any"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded px-3 py-2 text-slate-900 font-mono font-bold focus:border-amber-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Analyst Audit Note</label>
                <textarea
                  rows={2}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded p-2 text-slate-800"
                  required
                />
              </div>

              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setEditingIssue(null)}
                  className="px-3 py-1.5 rounded text-xs border border-slate-300 text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded text-xs font-bold bg-slate-900 text-white hover:bg-slate-800"
                >
                  Confirm & Verify
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CONFLICT RESOLUTION MODAL */}
      {resolvingConflict && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white w-full max-w-lg rounded-lg border border-slate-300 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <h3 className="text-sm font-bold text-slate-900">Resolve Cross-Document Conflict</h3>
              <button onClick={() => setResolvingConflict(null)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>

            <p className="text-xs text-slate-600">
              Conflict detected for <strong>{resolvingConflict.subsidiary}</strong> — <strong>{resolvingConflict.metric_code}</strong> ({resolvingConflict.reporting_period}).
              Select the canonical document value to establish as the ground truth.
            </p>

            <form onSubmit={handleConflictResolve} className="space-y-3">
              <div className="space-y-2">
                {/* Fact A Option */}
                <label className={`block p-3 rounded border cursor-pointer transition-colors ${
                  chosenFactId === resolvingConflict.fact_a_id ? 'bg-amber-50 border-amber-400' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="flex items-start space-x-2">
                    <input
                      type="radio"
                      name="chosenFact"
                      value={resolvingConflict.fact_a_id}
                      checked={chosenFactId === resolvingConflict.fact_a_id}
                      onChange={() => setChosenFactId(resolvingConflict.fact_a_id)}
                      className="mt-0.5 text-amber-600"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-900">
                        {resolvingConflict.fact_a_value.toFixed(2)} (Document A)
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{resolvingConflict.fact_a_doc}</div>
                    </div>
                  </div>
                </label>

                {/* Fact B Option */}
                <label className={`block p-3 rounded border cursor-pointer transition-colors ${
                  chosenFactId === resolvingConflict.fact_b_id ? 'bg-amber-50 border-amber-400' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="flex items-start space-x-2">
                    <input
                      type="radio"
                      name="chosenFact"
                      value={resolvingConflict.fact_b_id}
                      checked={chosenFactId === resolvingConflict.fact_b_id}
                      onChange={() => setChosenFactId(resolvingConflict.fact_b_id)}
                      className="mt-0.5 text-amber-600"
                    />
                    <div>
                      <div className="text-xs font-bold text-slate-900">
                        {resolvingConflict.fact_b_value.toFixed(2)} (Document B)
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{resolvingConflict.fact_b_doc}</div>
                    </div>
                  </div>
                </label>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Resolution Audit Trail Justification</label>
                <textarea
                  rows={2}
                  value={conflictNotes}
                  onChange={(e) => setConflictNotes(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded p-2 text-slate-800"
                  required
                />
              </div>

              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setResolvingConflict(null)}
                  className="px-3 py-1.5 rounded text-xs border border-slate-300 text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded text-xs font-bold bg-rose-700 text-white hover:bg-rose-800"
                >
                  Apply Resolution
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
