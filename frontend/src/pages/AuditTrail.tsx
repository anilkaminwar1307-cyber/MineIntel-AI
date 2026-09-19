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
      console.error(err);
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
