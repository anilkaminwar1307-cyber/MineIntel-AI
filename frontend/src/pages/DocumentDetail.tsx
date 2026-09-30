import React, { useState, useEffect } from 'react';
import {
  FileText,
  ArrowLeft,
  RefreshCw,
  Play,
  Table,
  Database,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  Search,
  Copy,
  Check,
  Compass,
  FileCode,
  Sliders,
  ShieldCheck,
  Hash,
  Activity,
  X
} from 'lucide-react';
import {
  DocumentItem,
  DocumentPageItem,
  DocumentSheetItem,
  DocumentTableItem,
  DocumentChunkItem,
  DocumentQualityItem,
  ProcessingLogItem,
  ExtractedFact,
  FactSourceProvenance,
  ExtractionSummaryResponse,
  SourcePreviewResponse
} from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/common/StatusBadge';

interface DocumentDetailProps {
  document: DocumentItem;
  onBack: () => void;
  onRefreshDocument?: (updated: DocumentItem) => void;
}

type TabType = 'overview' | 'source' | 'content' | 'tables' | 'facts' | 'quality' | 'logs';

export const DocumentDetail: React.FC<DocumentDetailProps> = ({
  document: initialDoc,
  onBack,
  onRefreshDocument
}) => {
  const [doc, setDoc] = useState<DocumentItem>(initialDoc);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);

  // Tab Data States
  const [pages, setPages] = useState<DocumentPageItem[]>([]);
  const [selectedPageIdx, setSelectedPageIdx] = useState<number>(0);
  const [tables, setTables] = useState<DocumentTableItem[]>([]);
  const [selectedTableIdx, setSelectedTableIdx] = useState<number>(0);
  const [facts, setFacts] = useState<ExtractedFact[]>([]);
  const [quality, setQuality] = useState<DocumentQualityItem | null>(null);
  const [logs, setLogs] = useState<ProcessingLogItem[]>([]);
  const [chunks, setChunks] = useState<DocumentChunkItem[]>([]);
  const [sourcePreview, setSourcePreview] = useState<SourcePreviewResponse | null>(null);
  const [extractionSummary, setExtractionSummary] = useState<ExtractionSummaryResponse | null>(null);

  // UI helpers
  const [copied, setCopied] = useState(false);
  const [pageSearch, setPageSearch] = useState('');
  const [factFilter, setFactFilter] = useState('');
  const [selectedFactProvenance, setSelectedFactProvenance] = useState<FactSourceProvenance | null>(null);
  const [loadingProvenance, setLoadingProvenance] = useState<boolean>(false);

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

  // Load all sub-resources for tabs
  const fetchAllData = async (docId: string) => {
    setLoading(true);
    try {
      const [
        latestDoc,
        pagesData,
        tablesData,
        factsData,
        qualityData,
        logsData,
        chunksData,
        previewData,
        summaryData
      ] = await Promise.all([
        api.getDocument(docId).catch(() => doc),
        api.getDocumentPages(docId).catch(() => []),
        api.getDocumentTables(docId).catch(() => []),
        api.getDocumentFacts(docId).catch(() => []),
        api.getDocumentQuality(docId).catch(() => null),
        api.getDocumentProcessingLog(docId).catch(() => []),
        api.getDocumentChunks(docId).catch(() => []),
        api.getDocumentSourcePreview(docId).catch(() => null),
        api.getDocumentExtractionSummary(docId).catch(() => null)
      ]);

      setDoc(latestDoc);
      setPages(pagesData);
      setTables(tablesData);
      setFacts(factsData);
      setQuality(qualityData);
      setLogs(logsData);
      setChunks(chunksData);
      setSourcePreview(previewData);
      setExtractionSummary(summaryData);

      if (onRefreshDocument) {
        onRefreshDocument(latestDoc);
      }
    } catch (err) {
      console.error('Failed to load document sub-data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData(doc.id);
  }, [doc.id]);

  const handleProcessOrReprocess = async () => {
    setProcessing(true);
    try {
      const updated = await api.reprocessDocument(doc.id);
      setDoc(updated);
      await fetchAllData(doc.id);
    } catch (err) {
      console.error('Processing failed', err);
    } finally {
      setProcessing(false);
    }
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Filtered facts
  const filteredFacts = facts.filter(f => {
    if (!factFilter) return true;
    const q = factFilter.toLowerCase();
    return (
      f.metric_name.toLowerCase().includes(q) ||
      f.metric_code.toLowerCase().includes(q) ||
      (f.subsidiary && f.subsidiary.toLowerCase().includes(q)) ||
      (f.reporting_period && f.reporting_period.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Top action bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3">
          <button
            onClick={onBack}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 px-3 py-2 rounded-lg border border-slate-200 transition-colors shadow-xs"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Document Library</span>
          </button>
          <div className="h-4 w-px bg-slate-200" />
          <div className="flex items-center space-x-2">
            <span className="text-xs font-medium text-slate-500">Status:</span>
            <StatusBadge status={doc.status} size="md" />
            {doc.source_type && (
              <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">
                {doc.source_type}
              </span>
            )}
            {doc.quality_label && (
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                doc.quality_label === 'EXCELLENT' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                doc.quality_label === 'GOOD' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                'bg-amber-50 text-amber-700 border-amber-200'
              }`}>
                Quality: {doc.quality_label}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => fetchAllData(doc.id)}
            disabled={loading}
            className="inline-flex items-center space-x-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white px-3 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleProcessOrReprocess}
            disabled={processing}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 px-4 py-2 rounded-lg shadow-sm transition disabled:opacity-50"
          >
            {processing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Processing Pipeline...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{doc.status === 'READY' ? 'Re-run Pipeline' : 'Run Pipeline'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Document Banner Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start space-x-4">
            <div className="p-3.5 bg-amber-50 text-amber-700 rounded-xl border border-amber-200 shadow-xs">
              <FileText className="w-7 h-7" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                {doc.original_filename}
              </h2>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mt-1.5">
                <span className="font-semibold text-slate-700">{doc.organization}</span>
                <span>•</span>
                <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">{doc.document_category}</span>
                <span>•</span>
                <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                <span>•</span>
                <span>Period: <strong className="text-slate-700">{doc.reporting_period || 'All Period'}</strong></span>
                <span>•</span>
                <span>Uploaded: {new Date(doc.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          {/* KPI Snapshot Pills */}
          <div className="flex items-center gap-2 text-center">
            <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 min-w-[70px]">
              <span className="block text-base font-bold text-slate-800">{doc.page_count || pages.length || 1}</span>
              <span className="text-[10px] uppercase font-bold text-slate-400">Pages</span>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 min-w-[70px]">
              <span className="block text-base font-bold text-slate-800">{doc.table_count || tables.length}</span>
              <span className="text-[10px] uppercase font-bold text-slate-400">Tables</span>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 min-w-[70px]">
              <span className="block text-base font-bold text-amber-800">{doc.fact_count || facts.length}</span>
              <span className="text-[10px] uppercase font-bold text-amber-600">Facts</span>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 min-w-[70px]">
              <span className="block text-base font-bold text-slate-800">{chunks.length}</span>
              <span className="text-[10px] uppercase font-bold text-slate-400">Chunks</span>
            </div>
          </div>
        </div>

        {/* Progress Bar when running */}
        {processing && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <div className="flex justify-between text-xs text-slate-600 mb-1">
              <span className="font-semibold text-amber-700">Pipeline in progress...</span>
              <span>Extracting evidence</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div className="bg-amber-500 h-1.5 rounded-full animate-pulse w-3/4" />
            </div>
          </div>
        )}
      </div>

      <div className="border-b border-slate-200 bg-white rounded-t-xl px-2">
        <nav className="flex space-x-1 overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview', icon: Compass },
            { id: 'source', label: `Source Preview`, icon: FileCode },
            { id: 'content', label: `Pages (${pages.length || 1})`, icon: Eye },
            { id: 'tables', label: `Tables (${tables.length})`, icon: Table },
            { id: 'facts', label: `Facts (${facts.length})`, icon: Database },
            { id: 'quality', label: 'Quality', icon: Sliders },
            { id: 'logs', label: `Log (${logs.length})`, icon: Activity }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center space-x-1.5 py-3 px-3 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-amber-600 text-amber-700 bg-amber-50/50 rounded-t-md'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-amber-600' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Document Provenance Coordinates
            </h3>
            <div className="space-y-2.5 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px] mb-1">Storage Path</span>
                <code className="text-[11px] font-mono bg-slate-50 p-2 rounded border border-slate-200 block text-slate-700 break-all">
                  {doc.storage_path}
                </code>
              </div>
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <span className="text-slate-400 block text-[11px]">System Filename</span>
                  <span className="font-mono text-slate-700 text-[11px]">{doc.stored_filename}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">MIME Type</span>
                  <span className="font-mono text-slate-700 text-[11px]">{doc.mime_type}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">File Format</span>
                  <span className="font-semibold text-slate-800">{doc.file_type}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Source Classification</span>
                  <span className="font-semibold text-slate-800">{doc.source_type || 'Auto-Detected'}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-amber-600" />
              Pipeline Execution Summary
            </h3>
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <div className="flex items-center space-x-2 text-emerald-700 font-semibold mb-1">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Status: {doc.status}</span>
                </div>
                <p className="text-slate-600 text-[11px]">
                  {doc.processing_message || 'Pipeline successfully executed without errors.'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="bg-slate-50 p-2.5 rounded border border-slate-100">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Extracted Facts</span>
                  <span className="text-sm font-bold text-amber-700">{doc.fact_count} verifiable points</span>
                </div>
                <div className="bg-slate-50 p-2.5 rounded border border-slate-100">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Semantic Chunks</span>
                  <span className="text-sm font-bold text-slate-700">{chunks.length} chunks</span>
                </div>
              </div>

              {doc.processed_at && (
                <div className="text-[11px] text-slate-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>Last processed on {new Date(doc.processed_at).toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Content & Pages */}
      {activeTab === 'content' && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {/* Page list column */}
          <div className="md:col-span-1 bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Document Pages ({pages.length || 1})
            </h3>
            <div className="space-y-1.5 max-h-[500px] overflow-y-auto pr-1">
              {pages.length === 0 ? (
                <button
                  onClick={() => setSelectedPageIdx(0)}
                  className="w-full text-left p-2.5 rounded-lg border text-xs font-semibold bg-amber-50 border-amber-300 text-amber-900"
                >
                  Page 1 (Single Document)
                </button>
              ) : (
                pages.map((p, idx) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPageIdx(idx)}
                    className={`w-full text-left p-2.5 rounded-lg border text-xs transition flex items-center justify-between ${
                      selectedPageIdx === idx
                        ? 'bg-amber-50 border-amber-300 text-amber-900 font-bold'
                        : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-700'
                    }`}
                  >
                    <span>Page {p.page_number}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
                      {p.char_count} chars
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Page text preview */}
          <div className="md:col-span-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-slate-800">
                  Page {pages[selectedPageIdx]?.page_number || 1} Preview
                </span>
                {pages[selectedPageIdx]?.is_ocr_page && (
                  <span className="text-[10px] bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded font-semibold">
                    OCR Extracted ({((pages[selectedPageIdx]?.ocr_confidence || 0) * 100).toFixed(0)}%)
                  </span>
                )}
              </div>
              <button
                onClick={() => handleCopyText(pages[selectedPageIdx]?.raw_text || '')}
                className="inline-flex items-center space-x-1 text-xs text-slate-600 hover:text-slate-900 bg-slate-50 px-2.5 py-1.5 rounded border border-slate-200 hover:bg-slate-100"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy Text'}</span>
              </button>
            </div>

            <pre className="text-xs font-mono text-slate-800 bg-slate-50 p-4 rounded-lg border border-slate-200 whitespace-pre-wrap leading-relaxed max-h-[500px] overflow-y-auto">
              {pages[selectedPageIdx]?.raw_text || 'No extracted text found for this page.'}
            </pre>
          </div>
        </div>
      )}

      {/* Source Preview Tab */}
      {activeTab === 'source' && (
        <div className="space-y-5">
          {/* Extraction Summary Banner */}
          {extractionSummary && (
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                Extraction Summary
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'Total Facts', value: extractionSummary.total_facts, color: 'amber' },
                  { label: 'High Confidence', value: extractionSummary.high_confidence_facts, color: 'emerald' },
                  { label: 'Needs Review', value: extractionSummary.needs_review_facts, color: 'orange' },
                  { label: 'Conflicts', value: extractionSummary.conflicts_count, color: 'rose' },
                ].map(item => (
                  <div key={item.label} className={`bg-${item.color}-50 border border-${item.color}-200 rounded-lg p-3 text-center`}>
                    <span className={`block text-xl font-bold text-${item.color}-700`}>{item.value}</span>
                    <span className={`text-[10px] font-semibold text-${item.color}-600 uppercase`}>{item.label}</span>
                  </div>
                ))}
              </div>
              {extractionSummary.duration_seconds !== null && extractionSummary.duration_seconds !== undefined && (
                <p className="text-[11px] text-slate-500 mt-3 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Pipeline completed in {extractionSummary.duration_seconds.toFixed(2)}s
                  {extractionSummary.quality_score !== null && extractionSummary.quality_score !== undefined && (
                    <span className="ml-2">• Quality Score: {(extractionSummary.quality_score * 100).toFixed(0)}%</span>
                  )}
                </p>
              )}
              {extractionSummary.warnings.length > 0 && (
                <div className="mt-3 space-y-1">
                  {extractionSummary.warnings.map((w, i) => (
                    <div key={i} className="flex items-start space-x-1.5 text-[11px] text-amber-700 bg-amber-50 px-2 py-1 rounded border border-amber-200">
                      <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                      <span>{w}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Source Preview Content */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-1.5">
              <FileCode className="w-4 h-4 text-blue-600" />
              Raw Source Preview — {doc.file_type}
            </h3>

            {!sourcePreview ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                <RefreshCw className="w-6 h-6 mx-auto mb-2 text-slate-300" />
                No source preview available. Process the document first.
              </div>
            ) : doc.file_type === 'PDF' && sourcePreview.pages.length > 0 ? (
              <div className="space-y-4">
                {sourcePreview.pages.map(page => (
                  <div key={page.page_number} className="rounded-lg border border-slate-200 overflow-hidden">
                    <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
                      <span className="text-xs font-semibold text-slate-700">Page {page.page_number}</span>
                      <div className="flex items-center space-x-2 text-[11px] text-slate-500">
                        {page.is_ocr_page && <span className="px-1.5 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded font-semibold">OCR</span>}
                        {page.ocr_confidence !== null && page.ocr_confidence !== undefined && (
                          <span>Confidence: {(page.ocr_confidence * 100).toFixed(0)}%</span>
                        )}
                      </div>
                    </div>
                    <pre className="text-xs font-mono text-slate-800 bg-white p-4 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
                      {page.raw_text || '(No text extracted from this page)'}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (doc.file_type === 'XLSX' || doc.file_type === 'XLS') && sourcePreview.sheets.length > 0 ? (
              <div className="space-y-5">
                {sourcePreview.sheets.map(sheet => (
                  <div key={sheet.sheet_name} className="rounded-lg border border-slate-200 overflow-hidden">
                    <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-700">📊 {sheet.sheet_name}</span>
                      <span className="text-[11px] text-slate-500">{sheet.row_count} rows × {sheet.col_count} cols {sheet.used_range && `(${sheet.used_range})`}</span>
                    </div>
                    {sheet.headers.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-slate-100 border-b border-slate-200">
                            <tr>
                              {sheet.headers.map((h, i) => (
                                <th key={i} className="px-3 py-2 font-semibold text-slate-700 whitespace-nowrap">{h || `Col ${i + 1}`}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {sheet.rows.slice(0, 8).map((row, ri) => (
                              <tr key={ri} className="hover:bg-slate-50">
                                {row.map((cell, ci) => (
                                  <td key={ci} className="px-3 py-1.5 text-slate-700 whitespace-nowrap max-w-[200px] truncate" title={String(cell)}>
                                    {cell !== null && cell !== undefined ? String(cell) : '—'}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {sheet.rows.length > 8 && (
                          <p className="text-[11px] text-slate-400 px-3 py-2 bg-slate-50 border-t border-slate-100">
                            Showing 8 of {sheet.row_count} rows
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 px-4 py-6 text-center">No structured data found in this sheet.</p>
                    )}
                  </div>
                ))}
              </div>
            ) : sourcePreview.text_preview ? (
              <pre className="text-xs font-mono text-slate-800 bg-slate-50 p-4 rounded-lg border border-slate-200 whitespace-pre-wrap leading-relaxed max-h-[500px] overflow-y-auto">
                {sourcePreview.text_preview}
              </pre>
            ) : (
              <div className="text-center py-8 text-slate-400 text-xs">No preview content available for this document type.</div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Extracted Tables */}
      {activeTab === 'tables' && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          {tables.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs">
              <Table className="w-8 h-8 mx-auto text-slate-300 mb-2" />
              No tabular blocks detected in this document.
            </div>
          ) : (
            <>
              <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
                <span className="text-xs font-semibold text-slate-500">Select Table:</span>
                <div className="flex space-x-1">
                  {tables.map((tbl, idx) => (
                    <button
                      key={tbl.id}
                      onClick={() => setSelectedTableIdx(idx)}
                      className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition ${
                        selectedTableIdx === idx
                          ? 'bg-amber-600 text-white border-amber-600 shadow-xs'
                          : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
                      }`}
                    >
                      {tbl.sheet_name || `Table ${idx + 1}`} ({tbl.row_count} rows)
                    </button>
                  ))}
                </div>
              </div>

              {/* Table Data Preview */}
              {tables[selectedTableIdx] && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>
                      Sheet: <strong>{tables[selectedTableIdx].sheet_name || 'Table'}</strong> •{' '}
                      {tables[selectedTableIdx].row_count} rows × {tables[selectedTableIdx].col_count} cols
                    </span>
                    <span className="text-[11px] font-mono text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      Clean Deterministic Table Structure
                    </span>
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-slate-200">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase text-[10px] tracking-wider">
                        <tr>
                          {JSON.parse(tables[selectedTableIdx].headers_json || '[]').map((h: string, i: number) => (
                            <th key={i} className="px-3.5 py-2.5 border-r border-slate-200 last:border-r-0 whitespace-nowrap">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {(() => {
                          try {
                            const rows = JSON.parse(tables[selectedTableIdx].data_json || '[]');
                            const headers = JSON.parse(tables[selectedTableIdx].headers_json || '[]');
                            return rows.slice(0, 30).map((row: any, rIdx: number) => (
                              <tr key={rIdx} className="hover:bg-slate-50/80">
                                {headers.map((h: string, cIdx: number) => {
                                  const cellVal = row[h];
                                  const displayVal = typeof cellVal === 'object' && cellVal !== null
                                    ? cellVal.value
                                    : cellVal;
                                  return (
                                    <td key={cIdx} className="px-3.5 py-2 border-r border-slate-100 last:border-r-0 whitespace-nowrap text-slate-700 font-mono text-[11px]">
                                      {String(displayVal ?? '')}
                                    </td>
                                  );
                                })}
                              </tr>
                            ));
                          } catch {
                            return <tr><td className="p-4 text-center text-slate-400">Failed to render table</td></tr>;
                          }
                        })()}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Tab 4: Evidence Ledger Facts */}
      {activeTab === 'facts' && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Verifiable Mining Facts Extracted ({facts.length})
              </h3>
              <p className="text-[11px] text-slate-500">
                Extracted deterministically via NumberSafe AI. No LLM hallucinations.
              </p>
            </div>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={factFilter}
                onChange={(e) => setFactFilter(e.target.value)}
                placeholder="Filter facts..."
                className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 w-48"
              />
            </div>
          </div>

          {filteredFacts.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs">
              No facts match the filter or have been extracted yet.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-700 uppercase text-[10px] font-bold tracking-wider border-b border-slate-200">
                  <tr>
                    <th className="px-3 py-2.5">Canonical Metric</th>
                    <th className="px-3 py-2.5 text-right">Value & Unit</th>
                    <th className="px-3 py-2.5">Subsidiary / Mine</th>
                    <th className="px-3 py-2.5">Period</th>
                    <th className="px-3 py-2.5">Provenance Coordinates</th>
                    <th className="px-3 py-2.5 text-center">Confidence</th>
                    <th className="px-3 py-2.5 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredFacts.map((fact) => (
                    <tr key={fact.id} className="hover:bg-slate-50/80">
                      <td className="px-3 py-2.5">
                        <span className="font-semibold text-slate-900 block">{fact.metric_name}</span>
                        <code className="text-[10px] text-slate-400 font-mono">{fact.metric_code}</code>
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono font-bold text-slate-900">
                        {fact.numeric_value !== null && fact.numeric_value !== undefined
                          ? Number(fact.numeric_value).toLocaleString()
                          : fact.text_value || '—'}{' '}
                        <span className="text-xs font-semibold text-amber-700">{fact.unit}</span>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="font-semibold text-slate-800">{fact.subsidiary || 'CIL'}</span>
                        {fact.mine && <span className="text-slate-400 block text-[10px]">{fact.mine}</span>}
                      </td>
                      <td className="px-3 py-2.5 font-medium text-slate-700">
                        {fact.reporting_period || '—'}
                      </td>
                      <td className="px-3 py-2.5 text-[11px] font-mono text-slate-600">
                        {fact.page_number && <span>Page {fact.page_number} </span>}
                        {fact.sheet_name && <span>[{fact.sheet_name}] </span>}
                        {fact.cell_reference && <strong className="text-amber-700">{fact.cell_reference}</strong>}
                        {!fact.cell_reference && fact.row_number && <span>Row {fact.row_number}</span>}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {(fact.confidence_score * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <button
                          onClick={() => handleViewProvenance(fact.id)}
                          className="p-1 text-slate-500 hover:text-amber-600 hover:bg-amber-50 rounded transition inline-flex items-center"
                          title="Inspect Source Provenance"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Quality & Enhancements */}
      {activeTab === 'quality' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-4 h-4 text-amber-600" />
              Document Quality Profile
            </h3>
            {quality ? (
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div>
                    <span className="text-[11px] text-slate-500 block">Overall Score</span>
                    <span className="text-xl font-bold text-slate-900">
                      {((quality.quality_score || 0.9) * 100).toFixed(0)} / 100
                    </span>
                  </div>
                  <span className={`px-2.5 py-1 rounded text-xs font-bold border ${
                    quality.quality_label === 'EXCELLENT' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    quality.quality_label === 'GOOD' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                    'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {quality.quality_label || 'GOOD'}
                  </span>
                </div>

                <div className="space-y-2 pt-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Blur Level:</span>
                    <span className="font-semibold text-slate-800">{quality.blur_level || 'Low / Clear'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Contrast:</span>
                    <span className="font-semibold text-slate-800">{quality.contrast_level || 'Optimal'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Noise Level:</span>
                    <span className="font-semibold text-slate-800">{quality.noise_level || 'Low / Clean'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Estimated Skew:</span>
                    <span className="font-semibold text-slate-800">{quality.skew_angle ? `${quality.skew_angle}°` : '0.0° (Aligned)'}</span>
                  </div>
                  {quality.detected_dpi && (
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500">Estimated DPI:</span>
                      <span className="font-semibold text-slate-800">{quality.detected_dpi} DPI</span>
                    </div>
                  )}
                  {quality.quality_score_before !== null && quality.quality_score_after !== null && (
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500">Quality Progression:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {quality.quality_score_before} &rarr; <span className="text-emerald-700 font-bold">{quality.quality_score_after}</span>
                      </span>
                    </div>
                  )}
                  {quality.ocr_confidence_before !== null && quality.ocr_confidence_after !== null && (
                    <div className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-500">OCR Confidence Gain:</span>
                      <span className="font-semibold text-slate-800 font-mono">
                        {((quality.ocr_confidence_before || 0) * 100).toFixed(0)}% &rarr;{' '}
                        <span className="text-emerald-700 font-bold">{((quality.ocr_confidence_after || 0) * 100).toFixed(0)}%</span>
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-slate-400 text-xs py-8 text-center">
                Quality metrics evaluated during pipeline run.
              </div>
            )}
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Pre-processing & Enhancements
            </h3>
            <div className="space-y-2.5 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                <span className="font-semibold text-slate-800 block">Enhancement Status</span>
                <p className="text-slate-500 text-[11px]">
                  {quality?.enhancement_applied
                    ? `Applied: ${quality.enhancement_methods || 'CLAHE, Deskew, Denoise'}`
                    : 'Source quality sufficient — no enhancement required.'}
                </p>
              </div>
              <div className="p-3 bg-amber-50/50 rounded-lg border border-amber-200 text-amber-900 text-[11px]">
                <strong>NumberSafe Guarantee:</strong> Images with blur or distortion are enhanced prior to OCR extraction to maximize character fidelity and preserve numerical truth.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: Live Pipeline Log */}
      {activeTab === 'logs' && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Pipeline Execution Log
            </h3>
            <span className="text-xs text-slate-400">{logs.length} stages recorded</span>
          </div>

          {logs.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs">
              No processing logs found. Run the pipeline to view real-time stage execution.
            </div>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className={`p-3 rounded-lg border text-xs flex items-start space-x-3 ${
                    log.level === 'ERROR'
                      ? 'bg-red-50 border-red-200 text-red-900'
                      : 'bg-slate-50 border-slate-200 text-slate-800'
                  }`}
                >
                  <div className="mt-0.5">
                    {log.level === 'ERROR' ? (
                      <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    )}
                  </div>
                  <div className="flex-1 space-y-0.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[11px] uppercase tracking-wider text-slate-700">
                        {log.stage || 'STAGE'}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-slate-600 text-[11px]">{log.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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
                    Source Context Snippet
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
