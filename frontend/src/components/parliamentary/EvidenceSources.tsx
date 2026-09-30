import React, { useState } from 'react';
import { Database, FileText, CheckCircle2, ChevronRight, ExternalLink } from 'lucide-react';
import { EvidenceSourceCitation } from '../../types';
import { SourceModal } from './SourceModal';

interface EvidenceSourcesProps {
  citations: EvidenceSourceCitation[];
}

export const EvidenceSources: React.FC<EvidenceSourcesProps> = ({ citations }) => {
  const [selectedCitation, setSelectedCitation] = useState<EvidenceSourceCitation | null>(null);

  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3 pt-4 border-t border-slate-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Database className="w-4 h-4 text-rose-700" />
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Supporting Evidence Sources ({citations.length} Records)
          </h4>
        </div>
        <span className="text-[11px] text-slate-400">
          Click any citation to inspect source coordinates
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {citations.map((cite, index) => {
          const valStr = cite.numeric_value !== undefined && cite.numeric_value !== null
            ? `${cite.numeric_value.toLocaleString()} ${cite.unit || ''}`
            : (cite as any).value || '—';

          return (
            <button
              key={index}
              onClick={() => setSelectedCitation(cite)}
              className="w-full text-left p-3 rounded-xl border border-slate-200/90 bg-white hover:border-rose-300 hover:shadow-xs hover:bg-rose-50/20 transition-all flex items-start space-x-3 group"
            >
              <div className="w-6 h-6 rounded-lg bg-slate-100 group-hover:bg-rose-100 flex items-center justify-center text-xs font-bold text-slate-600 group-hover:text-rose-700 flex-shrink-0 mt-0.5 transition-colors">
                {index + 1}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between space-x-2 mb-1">
                  <span className="text-xs font-bold text-slate-800 truncate group-hover:text-rose-950 transition-colors" title={cite.document_name}>
                    {cite.document_name}
                  </span>
                  {cite.human_verified ? (
                    <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded-full flex items-center space-x-0.5 flex-shrink-0 font-medium">
                      <CheckCircle2 className="w-2.5 h-2.5" />
                      <span>Verified</span>
                    </span>
                  ) : (
                    <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-full flex-shrink-0">
                      Extracted
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-2 text-[11px] text-slate-500">
                  <span className="font-semibold text-rose-800 font-mono">
                    {valStr}
                  </span>
                  <span>·</span>
                  <span className="truncate">
                    {cite.page_number ? `Pg ${cite.page_number}` : ''}
                    {cite.sheet_name ? ` · ${cite.sheet_name}` : ''}
                    {cite.cell_reference ? ` [${cite.cell_reference}]` : ''}
                    {!cite.page_number && !cite.sheet_name && !cite.cell_reference ? 'Ledger Record' : ''}
                  </span>
                </div>
              </div>

              <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-rose-500 transition-colors flex-shrink-0 mt-1" />
            </button>
          );
        })}
      </div>

      {selectedCitation && (
        <SourceModal
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </div>
  );
};
