import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Upload,
  Files,
  Trash2,
  Eye,
  FileText,
  AlertCircle,
  CheckCircle,
  Search,
  RefreshCw,
  Play,
  Database,
  X,
  AlertTriangle,
  Layers,
  ShieldCheck,
  Clock,
  Copy,
  ChevronRight,
  FilePlus2,
  Info,
  Zap,
  XCircle
} from 'lucide-react';
import { api } from '../services/api';
import { DocumentItem, BatchUploadItemResult, DataScope } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';

interface DocumentsProps {
  onViewDocument: (doc: DocumentItem) => void;
}

interface UploadFileEntry {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'done' | 'error' | 'duplicate';
  result?: BatchUploadItemResult;
  error?: string;
}

const DATA_SCOPE_OPTIONS: { value: DataScope; label: string; color: string }[] = [
  { value: 'ALL', label: 'All Evidence', color: 'bg-slate-100 text-slate-700 border-slate-300' },
  { value: 'REAL', label: 'Real Only', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
  { value: 'DEMO', label: 'Demo Only', color: 'bg-blue-100 text-blue-800 border-blue-300' },
];

const FILE_ICONS: Record<string, string> = {
  PDF: '📄', XLSX: '📊', XLS: '📊', CSV: '📋', TXT: '📝',
  PNG: '🖼️', JPG: '🖼️', JPEG: '🖼️',
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export const Documents: React.FC<DocumentsProps> = ({ onViewDocument }) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);
  const [processingDocId, setProcessingDocId] = useState<string | null>(null);

  // Filter & Search
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [dataScope, setDataScope] = useState<DataScope>('ALL');
  const [totalCount, setTotalCount] = useState(0);

  // Batch Upload Modal
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [fileEntries, setFileEntries] = useState<UploadFileEntry[]>([]);
  const [category, setCategory] = useState('General Mining Report');
  const [period, setPeriod] = useState('FY 2024-25');
  const [organization, setOrganization] = useState('CMPDI / CIL');
  const [autoProcess, setAutoProcess] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [batchResult, setBatchResult] = useState<{ successful: number; duplicates: number; failed: number } | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDocuments({
        search: search || undefined,
        category: categoryFilter || undefined,
      });
      // Apply data scope filter client-side
      let filtered = data.items;
      if (dataScope === 'REAL') filtered = data.items.filter(d => !d.is_demo);
      else if (dataScope === 'DEMO') filtered = data.items.filter(d => d.is_demo);
      setDocuments(filtered);
      setTotalCount(data.total);
    } catch (err: any) {
      setError('Unable to load document library. Please verify backend connection.');
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, dataScope]);

  useEffect(() => { loadDocuments(); }, [categoryFilter, dataScope]);

  const handleSearchSubmit = (e: React.FormEvent) => { e.preventDefault(); loadDocuments(); };

  const addFiles = (newFiles: File[]) => {
    const allowed = ['.pdf', '.xlsx', '.csv', '.txt', '.png', '.jpg', '.jpeg'];
    const valid = newFiles.filter(f => allowed.some(ext => f.name.toLowerCase().endsWith(ext)));
    const combined = [...fileEntries, ...valid.map(f => ({
      file: f,
      id: `${f.name}-${Date.now()}-${Math.random()}`,
      status: 'pending' as const
    }))].slice(0, 10);
    setFileEntries(combined);
    setBatchResult(null);
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files) addFiles(Array.from(e.dataTransfer.files));
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(Array.from(e.target.files));
    e.target.value = '';
  };

  const removeFile = (id: string) => {
    setFileEntries(prev => prev.filter(e => e.id !== id));
  };

  const resetModal = () => {
    setFileEntries([]);
    setBatchResult(null);
    setUploading(false);
  };

  const handleBatchUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (fileEntries.length === 0) return;

    setUploading(true);
    setBatchResult(null);
    setFileEntries(prev => prev.map(e => ({ ...e, status: 'uploading' })));

    try {
      const files = fileEntries.map(e => e.file);
      const resp = await api.batchUploadDocuments(files, category, period, organization, autoProcess);

      const updatedEntries = fileEntries.map((entry, i) => {
        const item = resp.items[i];
        if (!item) return { ...entry, status: 'error' as const, error: 'No result returned' };
        return {
          ...entry,
          status: item.is_duplicate ? 'duplicate' as const :
                  item.error ? 'error' as const : 'done' as const,
          result: item,
          error: item.error || undefined
        };
      });
      setFileEntries(updatedEntries);
      setBatchResult({
        successful: resp.successful,
        duplicates: resp.duplicates,
        failed: resp.failed
      });
      setSuccessBanner(`Batch upload complete: ${resp.successful} processed, ${resp.duplicates} duplicate(s), ${resp.failed} failed.`);
      setTimeout(() => setSuccessBanner(null), 6000);
      await loadDocuments();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Batch upload failed.';
      setError(msg);
      setFileEntries(prev => prev.map(e => ({ ...e, status: 'error', error: msg })));
    } finally {
      setUploading(false);
    }
  };

  const handleRunPipeline = async (doc: DocumentItem) => {
    try {
      setProcessingDocId(doc.id);
      const updated = await api.reprocessDocument(doc.id);
      setDocuments(prev => prev.map(d => d.id === doc.id ? updated : d));
      setSuccessBanner(`Pipeline finished for "${doc.original_filename}": ${updated.fact_count} facts extracted.`);
      setTimeout(() => setSuccessBanner(null), 5000);
    } catch (err: any) {
      setError(`Failed to process: ${err.message || 'Unknown error'}`);
    } finally {
      setProcessingDocId(null);
    }
  };

  const handleDelete = async (doc: DocumentItem) => {
    if (!window.confirm(`Delete "${doc.original_filename}"?`)) return;
    try {
      await api.deleteDocument(doc.id);
      setSuccessBanner(`Deleted "${doc.original_filename}".`);
      await loadDocuments();
      setTimeout(() => setSuccessBanner(null), 4000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete document.');
    }
  };

  const getFileIcon = (fileType: string) => FILE_ICONS[fileType?.toUpperCase()] || '📄';

  const getStatusIcon = (s: UploadFileEntry['status']) => {
    switch (s) {
      case 'done': return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'error': return <XCircle className="w-4 h-4 text-rose-500" />;
      case 'duplicate': return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      case 'uploading': return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />;
      default: return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-amber-50 border border-amber-200">
              <Files className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Document Library</h2>
              <p className="text-xs text-slate-500">
                {totalCount.toLocaleString()} document{totalCount !== 1 ? 's' : ''} •{' '}
                <span className="font-medium text-slate-700">{documents.length} shown</span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Data Scope Toggle */}
          <div className="flex items-center bg-slate-100 rounded-lg p-0.5 text-xs">
            {DATA_SCOPE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setDataScope(opt.value)}
                className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
                  dataScope === opt.value
                    ? 'bg-white shadow-sm text-slate-900 border border-slate-200'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => { resetModal(); setShowUploadModal(true); }}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-amber-600 text-white hover:bg-amber-700 transition-colors shadow-sm"
          >
            <FilePlus2 className="w-4 h-4" />
            <span>Upload Documents</span>
          </button>
          <button
            onClick={loadDocuments}
            className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
            title="Reload library"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successBanner && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-emerald-800 text-xs">
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{successBanner}</span>
          </div>
          <button onClick={() => setSuccessBanner(null)}><X className="w-3.5 h-3.5" /></button>
        </div>
      )}
      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between text-rose-800 text-xs">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)}><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="w-full md:w-80 relative">
          <input
            type="text"
            placeholder="Search document filename..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-200"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
        </form>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:border-amber-500"
          >
            <option value="">All Categories</option>
            <option value="Production Report">Production Report</option>
            <option value="Drilling & Exploration">Drilling & Exploration</option>
            <option value="Dispatch Statement">Dispatch Statement</option>
            <option value="Geological Assessment">Geological Assessment</option>
            <option value="Reserve Estimation">Reserve Estimation</option>
            <option value="General Mining Report">General Mining Report</option>
          </select>
        </div>
      </div>

      {/* Document Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
            Loading Document Library...
          </div>
        ) : documents.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={Files}
              title="No Documents Found"
              description={dataScope !== 'ALL'
                ? `No ${dataScope.toLowerCase()} documents match your filters. Try changing the data scope.`
                : "Upload mining PDFs, Excel sheets, CSVs, or text drill logs to start building your verified evidence ledger."}
              actionText="Upload Documents"
              onAction={() => { resetModal(); setShowUploadModal(true); }}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                <tr>
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Category</th>
                  <th className="py-3 px-3">Organization</th>
                  <th className="py-3 px-3">Period</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-center">Quality</th>
                  <th className="py-3 px-3 text-center">Facts</th>
                  <th className="py-3 px-3 text-center">Scope</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors group">
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2.5">
                        <div className="text-lg leading-none">{getFileIcon(doc.file_type)}</div>
                        <div>
                          <button
                            onClick={() => onViewDocument(doc)}
                            className="font-semibold text-slate-900 hover:text-amber-700 text-left truncate max-w-xs md:max-w-sm block transition-colors"
                            title={doc.original_filename}
                          >
                            {doc.original_filename}
                          </button>
                          <p className="text-[11px] text-slate-400 flex items-center space-x-1">
                            <span>{formatBytes(doc.file_size)}</span>
                            <span>•</span>
                            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                            {doc.sha256 && (
                              <>
                                <span>•</span>
                                <span className="font-mono text-[10px] text-slate-300" title={`SHA-256: ${doc.sha256}`}>
                                  {doc.sha256.slice(0, 8)}…
                                </span>
                              </>
                            )}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                        {doc.file_type}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-700">{doc.document_category}</td>
                    <td className="py-3 px-3 text-slate-600 truncate max-w-[120px]">{doc.organization}</td>
                    <td className="py-3 px-3 text-slate-600 font-mono text-[11px]">{doc.reporting_period || '—'}</td>
                    <td className="py-3 px-3"><StatusBadge status={doc.status} /></td>
                    <td className="py-3 px-3 text-center">
                      {doc.quality_label ? (
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                          doc.quality_label === 'EXCELLENT' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                          doc.quality_label === 'GOOD' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                          doc.quality_label === 'FAIR' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                          'bg-rose-50 text-rose-700 border border-rose-200'
                        }`}>
                          {doc.quality_label}
                        </span>
                      ) : <span className="text-slate-300 text-[11px]">—</span>}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-bold ${
                        doc.fact_count > 0 ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-slate-100 text-slate-500'
                      }`}>
                        <Database className="w-3 h-3" />
                        <span>{doc.fact_count}</span>
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      {doc.is_demo ? (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          DEMO
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          REAL
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => handleRunPipeline(doc)}
                          disabled={processingDocId === doc.id}
                          className="inline-flex items-center space-x-1 text-[11px] font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 px-2 py-1 rounded-lg border border-amber-200 transition disabled:opacity-50"
                          title={doc.status === 'READY' ? 'Reprocess' : 'Run extraction pipeline'}
                        >
                          {processingDocId === doc.id ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : <Play className="w-3 h-3 fill-current" />}
                          <span>{doc.status === 'READY' ? 'Reprocess' : 'Process'}</span>
                        </button>
                        <button
                          onClick={() => onViewDocument(doc)}
                          className="p-1.5 text-slate-500 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition-colors"
                          title="View document"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                          title="Delete document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Batch Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-start justify-end p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-xl h-full max-h-screen overflow-y-auto flex flex-col animate-in slide-in-from-right duration-200">
            {/* Modal Header */}
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg bg-amber-50 border border-amber-200">
                  <Upload className="w-4 h-4 text-amber-600" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Batch Document Upload</h3>
                  <p className="text-[11px] text-slate-500">Up to 10 files • PDF, XLSX, XLS, CSV, TXT, PNG, JPG</p>
                </div>
              </div>
              <button
                onClick={() => { setShowUploadModal(false); resetModal(); }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleBatchUpload} className="flex flex-col flex-1 overflow-y-auto">
              <div className="p-5 space-y-5 flex-1">
                {/* Drop Zone */}
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleFileDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`p-6 border-2 border-dashed rounded-xl text-center cursor-pointer transition-all ${
                    dragOver ? 'border-amber-500 bg-amber-50' :
                    fileEntries.length > 0 ? 'border-emerald-400 bg-emerald-50/30' :
                    'border-slate-300 hover:border-amber-400 hover:bg-amber-50/20 bg-slate-50/50'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={handleFileSelect}
                    accept=".pdf,.xlsx,.csv,.txt,.png,.jpg,.jpeg"
                    className="hidden"
                  />
                  <Upload className={`w-8 h-8 mx-auto mb-2 ${dragOver ? 'text-amber-600' : 'text-slate-400'}`} />
                  {fileEntries.length > 0 ? (
                    <div>
                      <p className="text-xs font-semibold text-slate-900">{fileEntries.length} file{fileEntries.length > 1 ? 's' : ''} selected</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">Click to add more (max 10)</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-semibold text-slate-700">Drag & drop up to 10 files, or click to browse</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">Geological summaries, production sheets, dispatch logs</p>
                    </div>
                  )}
                </div>

                {/* File List */}
                {fileEntries.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold text-slate-700">Files ({fileEntries.length}/10)</p>
                      {!uploading && (
                        <button
                          type="button"
                          onClick={() => setFileEntries([])}
                          className="text-[11px] text-slate-400 hover:text-rose-600 transition-colors"
                        >
                          Clear all
                        </button>
                      )}
                    </div>
                    <div className="space-y-1.5 max-h-52 overflow-y-auto">
                      {fileEntries.map((entry) => (
                        <div
                          key={entry.id}
                          className={`flex items-center space-x-2.5 p-2.5 rounded-lg border text-xs transition-colors ${
                            entry.status === 'done' ? 'bg-emerald-50 border-emerald-200' :
                            entry.status === 'error' ? 'bg-rose-50 border-rose-200' :
                            entry.status === 'duplicate' ? 'bg-amber-50 border-amber-200' :
                            entry.status === 'uploading' ? 'bg-blue-50 border-blue-200' :
                            'bg-slate-50 border-slate-200'
                          }`}
                        >
                          <span className="text-base leading-none flex-shrink-0">
                            {getFileIcon(entry.file.name.split('.').pop()?.toUpperCase() || '')}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-slate-800 truncate">{entry.file.name}</p>
                            <p className="text-[11px] text-slate-500">{formatBytes(entry.file.size)}</p>
                            {entry.result?.facts_extracted !== undefined && entry.result.facts_extracted > 0 && (
                              <p className="text-[11px] text-emerald-700 font-semibold">
                                ✓ {entry.result.facts_extracted} facts extracted
                              </p>
                            )}
                            {entry.result?.is_duplicate && (
                              <p className="text-[11px] text-amber-700">
                                ⚠ Duplicate of: {entry.result.duplicate_of_filename}
                              </p>
                            )}
                            {entry.error && (
                              <p className="text-[11px] text-rose-700 truncate">{entry.error}</p>
                            )}
                          </div>
                          <div className="flex-shrink-0">{getStatusIcon(entry.status)}</div>
                          {entry.status === 'pending' && !uploading && (
                            <button
                              type="button"
                              onClick={() => removeFile(entry.id)}
                              className="flex-shrink-0 text-slate-400 hover:text-rose-500 transition-colors"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Batch Result Summary */}
                {batchResult && (
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                    <p className="font-semibold text-slate-700 flex items-center space-x-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      <span>Upload Complete</span>
                    </p>
                    <div className="grid grid-cols-3 gap-2 mt-2">
                      <div className="text-center p-2 bg-emerald-50 rounded-lg border border-emerald-200">
                        <p className="text-lg font-bold text-emerald-700">{batchResult.successful}</p>
                        <p className="text-[10px] text-emerald-600">Processed</p>
                      </div>
                      <div className="text-center p-2 bg-amber-50 rounded-lg border border-amber-200">
                        <p className="text-lg font-bold text-amber-700">{batchResult.duplicates}</p>
                        <p className="text-[10px] text-amber-600">Duplicates</p>
                      </div>
                      <div className="text-center p-2 bg-rose-50 rounded-lg border border-rose-200">
                        <p className="text-lg font-bold text-rose-700">{batchResult.failed}</p>
                        <p className="text-[10px] text-rose-600">Failed</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Metadata Fields */}
                <div className="space-y-3 pt-1 border-t border-slate-100">
                  <p className="text-xs font-semibold text-slate-700">Document Metadata</p>
                  <div>
                    <label className="block text-[11px] font-medium text-slate-600 mb-1">Category</label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800 focus:outline-none focus:border-amber-500"
                    >
                      <option value="Production Report">Production Report</option>
                      <option value="Drilling & Exploration">Drilling & Exploration</option>
                      <option value="Dispatch Statement">Dispatch Statement</option>
                      <option value="Geological Assessment">Geological Assessment</option>
                      <option value="Reserve Estimation">Reserve Estimation</option>
                      <option value="General Mining Report">General Mining Report</option>
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-medium text-slate-600 mb-1">Reporting Period</label>
                      <input
                        type="text"
                        value={period}
                        onChange={(e) => setPeriod(e.target.value)}
                        placeholder="e.g. FY 2024-25"
                        className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-medium text-slate-600 mb-1">Organization</label>
                      <input
                        type="text"
                        value={organization}
                        onChange={(e) => setOrganization(e.target.value)}
                        className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoProcess}
                      onChange={(e) => setAutoProcess(e.target.checked)}
                      className="rounded text-amber-600 focus:ring-amber-500 h-4 w-4"
                    />
                    <span className="text-xs text-slate-700 font-medium">
                      Auto-run Document Intelligence Pipeline (extract facts immediately)
                    </span>
                  </label>
                </div>

                {/* Info box */}
                <div className="flex items-start space-x-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                  <p className="text-[11px] text-blue-700">
                    Each file is SHA-256 fingerprinted for duplicate detection. Duplicate files are flagged but still recorded for audit purposes.
                  </p>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-5 py-4 border-t border-slate-200 flex items-center justify-between flex-shrink-0 bg-slate-50">
                <button
                  type="button"
                  onClick={() => { setShowUploadModal(false); resetModal(); }}
                  disabled={uploading}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50"
                >
                  {batchResult ? 'Close' : 'Cancel'}
                </button>
                {!batchResult && (
                  <button
                    type="submit"
                    disabled={fileEntries.length === 0 || uploading}
                    className={`inline-flex items-center space-x-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg text-white shadow-sm transition-colors ${
                      fileEntries.length === 0 || uploading
                        ? 'bg-slate-300 cursor-not-allowed'
                        : 'bg-amber-600 hover:bg-amber-700'
                    }`}
                  >
                    {uploading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Processing {fileEntries.length} file{fileEntries.length > 1 ? 's' : ''}…</span>
                      </>
                    ) : (
                      <>
                        <Zap className="w-3.5 h-3.5" />
                        <span>
                          {autoProcess
                            ? `Upload & Process ${fileEntries.length} File${fileEntries.length > 1 ? 's' : ''}`
                            : `Upload ${fileEntries.length} File${fileEntries.length > 1 ? 's' : ''}`}
                        </span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
