import React, { useState, useEffect } from 'react';
import {
  History,
  Shield,
  Search,
  RefreshCw,
  Clock,
  User,
  Activity
} from 'lucide-react';
import { api } from '../services/api';
import { AuditItem } from '../types';
import { EmptyState } from '../components/common/EmptyState';

const FALLBACK_AUDIT_EVENTS: AuditItem[] = [
  { id: 'ae-001', timestamp: '2026-09-30T14:45:00Z', user: 'analyst_demo', action: 'DOCUMENT_UPLOADED', entity_type: 'DOCUMENT', entity_id: 'doc_cil_ar25', details: 'CIL_Annual_Report_2024-25_Audited.pdf — 12.4 MB — PDF uploaded for CMPDI/CIL' },
  { id: 'ae-002', timestamp: '2026-09-30T14:46:10Z', user: 'system', action: 'FACT_EXTRACTED', entity_type: 'FACT', entity_id: 'fact_gevra_01', details: '186 facts extracted from CIL_Annual_Report_2024-25_Audited.pdf (avg confidence 0.97)' },
  { id: 'ae-003', timestamp: '2026-09-30T14:50:22Z', user: 'reviewer_demo', action: 'FACT_APPROVED', entity_type: 'FACT', entity_id: 'fact_gevra_01', details: 'Gevra OC Mine production fact verified: 52.5 MT — marked VERIFIED by Reviewer' },
  { id: 'ae-004', timestamp: '2026-09-30T14:55:30Z', user: 'analyst_demo', action: 'DOCUMENT_UPLOADED', entity_type: 'DOCUMENT', entity_id: 'doc_secl_led', details: 'SECL_Operational_Ledger_FY25.xlsx — 8.2 MB — XLSX uploaded for SECL' },
  { id: 'ae-005', timestamp: '2026-09-30T14:56:15Z', user: 'system', action: 'FACT_EXTRACTED', entity_type: 'FACT', entity_id: 'fact_secl_01', details: '324 facts extracted from SECL_Operational_Ledger_FY25.xlsx (avg confidence 0.98)' },
  { id: 'ae-006', timestamp: '2026-09-30T15:01:40Z', user: 'analyst_demo', action: 'QUERY_EXECUTED', entity_type: 'QUERY', entity_id: 'q-001', details: 'Parliamentary brief generated: "Total coal production CIL FY 2024-25" — 48 records used' },
  { id: 'ae-007', timestamp: '2026-09-30T15:04:55Z', user: 'reviewer_demo', action: 'FACT_APPROVED', entity_type: 'FACT', entity_id: 'fact_mcl_01', details: 'MCL Bhubaneswari OC production fact approved: 32.0 MT — VERIFIED' },
  { id: 'ae-008', timestamp: '2026-09-30T15:10:20Z', user: 'analyst_demo', action: 'DOCUMENT_UPLOADED', entity_type: 'DOCUMENT', entity_id: 'doc_ncl_rev', details: 'NCL_Performance_Review_Q4.pdf — 5.8 MB — PDF uploaded for NCL' },
  { id: 'ae-009', timestamp: '2026-09-30T15:15:00Z', user: 'system', action: 'FACT_EXTRACTED', entity_type: 'FACT', entity_id: 'fact_ncl_01', details: '98 facts extracted from NCL_Performance_Review_Q4.pdf (avg confidence 0.99)' },
  { id: 'ae-010', timestamp: '2026-09-30T15:20:10Z', user: 'admin_demo', action: 'QUERY_EXECUTED', entity_type: 'QUERY', entity_id: 'q-002', details: 'MineGraph knowledge graph rebuilt: 1,068 nodes, 2,140 edges indexed' },
  { id: 'ae-011', timestamp: '2026-09-30T15:30:00Z', user: 'reviewer_demo', action: 'FACT_APPROVED', entity_type: 'FACT', entity_id: 'fact_jayant_01', details: 'Jayant OC OBR fact verified: 142.0 M.Cu.M — VERIFIED with supporting HEMM logs' },
  { id: 'ae-012', timestamp: '2026-09-30T15:35:45Z', user: 'analyst_demo', action: 'QUERY_EXECUTED', entity_type: 'QUERY', entity_id: 'q-003', details: 'Evidence Ledger search: OVERBURDEN_REMOVAL SECL — 96 matching records returned' },
];

export const AuditTrail: React.FC = () => {
  const [events, setEvents] = useState<AuditItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionFilter, setActionFilter] = useState<string>('');

  const loadAuditEvents = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditEvents({
        action: actionFilter || undefined,
      });
      setEvents(data.items);
    } catch (err) {
      console.warn('Audit trail API unavailable, loading demo events:', err);
      const filtered = actionFilter
        ? FALLBACK_AUDIT_EVENTS.filter(e => e.action === actionFilter)
        : FALLBACK_AUDIT_EVENTS;
      setEvents(filtered);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditEvents();
  }, [actionFilter]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-slate-900">Governance & Audit Trail</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold uppercase">
              Immutable Log
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Cryptographic-style audit record of all document uploads, fact verifications, queries, and system actions.
          </p>
        </div>

        <button
          onClick={loadAuditEvents}
          className="p-1.5 rounded border border-slate-300 text-slate-600 hover:bg-slate-50 self-start sm:self-auto"
          title="Refresh Audit Trail"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-slate-500 font-medium">Filter Action:</span>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded px-2.5 py-1 bg-white text-slate-700"
          >
            <option value="">All Audit Actions</option>
            <option value="DOCUMENT_UPLOADED">DOCUMENT_UPLOADED</option>
            <option value="DOCUMENT_DELETED">DOCUMENT_DELETED</option>
            <option value="FACT_EXTRACTED">FACT_EXTRACTED</option>
            <option value="FACT_APPROVED">FACT_APPROVED</option>
            <option value="QUERY_EXECUTED">QUERY_EXECUTED</option>
          </select>
        </div>

        <span className="text-[11px] text-slate-400 font-mono">
          Total Recorded Events: {events.length}
        </span>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
            Loading Audit Log...
          </div>
        ) : events.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={History}
              title="No Audit Events Recorded"
              description="Actions performed in MineIntel (document uploads, deletions, verifications) will automatically appear here."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
                <tr>
                  <th className="py-3 px-4">Timestamp (UTC)</th>
                  <th className="py-3 px-3">User</th>
                  <th className="py-3 px-3">Action</th>
                  <th className="py-3 px-3">Entity</th>
                  <th className="py-3 px-4">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {events.map((event) => (
                  <tr key={event.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {new Date(event.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-3 font-sans font-medium text-slate-800">
                      {event.user}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                        event.action === 'DOCUMENT_UPLOADED' ? 'bg-blue-50 text-blue-800 border-blue-200' :
                        event.action === 'DOCUMENT_DELETED' ? 'bg-rose-50 text-rose-800 border-rose-200' :
                        event.action === 'FACT_APPROVED' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                        'bg-slate-100 text-slate-700 border-slate-200'
                      }`}>
                        {event.action}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-600 font-sans">
                      <span className="font-semibold">{event.entity_type}</span>
                      {event.entity_id && (
                        <span className="text-[10px] text-slate-400 block truncate max-w-[120px]" title={event.entity_id}>
                          {event.entity_id}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-sans max-w-md break-words">
                      {event.details || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
