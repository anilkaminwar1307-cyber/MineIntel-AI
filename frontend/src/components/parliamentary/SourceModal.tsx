import React from 'react';
import { X, FileText, CheckCircle2, MapPin, Hash, Table, Calendar, Building, Layers } from 'lucide-react';
import { EvidenceSourceCitation } from '../../types';

interface SourceModalProps {
  citation: EvidenceSourceCitation | null;
  onClose: () => void;
}

export const SourceModal: React.FC<SourceModalProps> = ({ citation, onClose }) => {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div
        className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full overflow-hidden flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-200"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex items-start justify-between bg-slate-50/70">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-700 flex-shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-semibold text-rose-800 uppercase tracking-wider">Source Evidence Audit</div>
              <h3 className="text-sm font-bold text-slate-900 truncate max-w-xs" title={citation.document_name}>
                {citation.document_name}
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Status & Value Banner */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                {citation.metric_name || citation.metric_code}
              </span>
              <div className="text-lg font-bold text-slate-900 mt-0.5">
                {citation.numeric_value !== undefined && citation.numeric_value !== null
                  ? `${citation.numeric_value.toLocaleString()} ${citation.unit || ''}`
                  : (citation as any).value || '—'}
              </div>
            </div>
            <div>
              {citation.human_verified ? (
                <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Auditor Verified</span>
                </span>
              ) : (
                <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  <span>NumberSafe Extracted</span>
                </span>
              )}
            </div>
          </div>

          {/* Coordinates Grid */}
          <div>
            <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <MapPin className="w-3.5 h-3.5 text-rose-600" />
              <span>Provenance Coordinates</span>
            </div>
            <div className="grid grid-cols-2 gap-2 bg-slate-50/60 p-3 rounded-xl border border-slate-100">
              <div className="flex items-center space-x-2 text-slate-600">
                <Layers className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                <span>Page: <strong>{citation.page_number ?? 'N/A'}</strong></span>
              </div>
              <div className="flex items-center space-x-2 text-slate-600">
                <Table className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                <span>Sheet: <strong>{citation.sheet_name || 'Primary'}</strong></span>
              </div>
              <div className="flex items-center space-x-2 text-slate-600">
                <Hash className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                <span>Cell / Ref: <strong>{citation.cell_reference || (citation.row_number ? `Row ${citation.row_number}` : 'Ledger')}</strong></span>
              </div>
              <div className="flex items-center space-x-2 text-slate-600">
                <Building className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                <span>Subsidiary: <strong>{citation.subsidiary || 'CIL'}</strong></span>
              </div>
              <div className="flex items-center space-x-2 text-slate-600 col-span-2">
                <Calendar className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                <span>Reporting Period: <strong>{citation.reporting_period || 'Consolidated'}</strong></span>
              </div>
            </div>
          </div>

          {/* Source Context */}
          {citation.source_context && (
            <div>
              <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Extracted Text Snippet
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 leading-relaxed font-mono text-[11px]">
                "{citation.source_context}"
              </div>
            </div>
          )}

          {/* Confidence */}
          <div className="flex items-center justify-between text-slate-500 pt-1 text-[11px]">
            <span>Extraction Confidence: <strong className="text-emerald-700">{Math.round((citation.confidence_score || 0.95) * 100)}%</strong></span>
            <span>Document ID: <span className="font-mono text-slate-400">{citation.document_id.slice(0, 8)}…</span></span>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-50 border-t border-slate-100 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold bg-white border border-slate-200 hover:bg-slate-100 rounded-lg text-slate-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
