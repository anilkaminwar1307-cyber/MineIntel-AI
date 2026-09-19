import React, { useState, useEffect, useRef } from 'react';
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
  CheckSquare
} from 'lucide-react';
import { api } from '../services/api';
import { DocumentItem } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { EmptyState } from '../components/common/EmptyState';

interface DocumentsProps {
  onViewDocument: (doc: DocumentItem) => void;
}

export const Documents: React.FC<DocumentsProps> = ({ onViewDocument }) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [processingDocId, setProcessingDocId] = useState<string | null>(null);

  // Filter & Search states
  const [search, setSearch] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  // Upload modal & form states
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [category, setCategory] = useState<string>('General Mining Report');
  const [period, setPeriod] = useState<string>('FY 2024-25');
  const [organization, setOrganization] = useState<string>('CMPDI / CIL');
  const [autoProcess, setAutoProcess] = useState<boolean>(true);
  const [dragOver, setDragOver] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDocuments({
        search: search || undefined,
        category: categoryFilter || undefined,
      });
      setDocuments(data.items);
    } catch (err: any) {
      console.error(err);
      setError('Unable to load document library. Please verify backend connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [categoryFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadDocuments();
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    try {
      setUploading(true);
      setError(null);
      const res = await api.uploadDocument(selectedFile, category, period, organization, autoProcess);
      setUploadSuccess(`Uploaded "${res.document.original_filename}" successfully.`);
      setSelectedFile(null);
      setShowUploadModal(false);
      await loadDocuments();
      setTimeout(() => setUploadSuccess(null), 5000);
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.detail || 'Failed to upload document.';
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleRunPipeline = async (doc: DocumentItem) => {
    try {
      setProcessingDocId(doc.id);
      const updated = await api.reprocessDocument(doc.id);
      setDocuments(prev => prev.map(d => d.id === doc.id ? updated : d));
      setUploadSuccess(`Pipeline finished for "${doc.original_filename}": ${updated.fact_count} facts extracted.`);
      setTimeout(() => setUploadSuccess(null), 4000);
    } catch (err: any) {
      console.error(err);
      setError(`Failed to process document: ${err.message || 'Unknown error'}`);
    } finally {
      setProcessingDocId(null);
    }
  };

  const handleDelete = async (doc: DocumentItem) => {
    if (!window.confirm(`Are you sure you want to delete "${doc.original_filename}"?`)) return;

    try {
      await api.deleteDocument(doc.id);
      setUploadSuccess(`Deleted "${doc.original_filename}".`);
      await loadDocuments();
      setTimeout(() => setUploadSuccess(null), 4000);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to delete document.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-slate-900">Document Library</h2>
            <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono">
              {documents.length} File{documents.length === 1 ? '' : 's'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Ingest and manage geological reports, production spreadsheets, drilling summaries, and dispatch statements.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold rounded bg-amber-600 text-white hover:bg-amber-700 transition-colors shadow-sm"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Document</span>
          </button>
          <button
            onClick={loadDocuments}
            className="p-1.5 rounded border border-slate-300 text-slate-600 hover:bg-slate-50"
            title="Reload library"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {uploadSuccess && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center space-x-2 text-emerald-800 text-xs">
          <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg flex items-center space-x-2 text-rose-800 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="w-full md:w-80 relative">
          <input
            type="text"
            placeholder="Search document filename..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:border-amber-500"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
        </form>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:border-amber-500"
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

      {/* Document Table / Empty State */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
            Loading Document Library...
          </div>
        ) : documents.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={Files}
              title="No Documents Uploaded"
              description="Upload mining PDFs, Excel sheets, CSVs, or text drill logs to start building your verified evidence ledger."
              actionText="Upload Document"
              onAction={() => setShowUploadModal(true)}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
                <tr>
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Category</th>
                  <th className="py-3 px-3">Organization</th>
                  <th className="py-3 px-3">Period</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-center">Quality</th>
                  <th className="py-3 px-3 text-center">Facts</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2.5">
                        <div className="p-1.5 rounded bg-slate-100 text-slate-600">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <button
                            onClick={() => onViewDocument(doc)}
                            className="font-semibold text-slate-900 hover:text-amber-700 text-left truncate max-w-xs md:max-w-sm block"
                            title={doc.original_filename}
                          >
                            {doc.original_filename}
                          </button>
                          <p className="text-[11px] text-slate-400">
                            {(doc.file_size / 1024).toFixed(1)} KB • {new Date(doc.created_at).toLocaleDateString()}
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
                    <td className="py-3 px-3 text-slate-600">{doc.organization}</td>
                    <td className="py-3 px-3 text-slate-600 font-mono text-[11px]">{doc.reporting_period || '—'}</td>
                    <td className="py-3 px-3">
                      <StatusBadge status={doc.status} />
                    </td>
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
                      ) : (
                        <span className="text-slate-400 font-mono text-[11px]">—</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-bold ${
                        doc.fact_count > 0 ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-slate-100 text-slate-500'
                      }`}>
                        <Database className="w-3 h-3" />
                        <span>{doc.fact_count}</span>
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => handleRunPipeline(doc)}
                          disabled={processingDocId === doc.id}
                          className="inline-flex items-center space-x-1 text-[11px] font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 px-2 py-1 rounded border border-amber-200 transition"
                          title={doc.status === 'READY' ? 'Reprocess document' : 'Run extraction pipeline'}
                        >
                          {processingDocId === doc.id ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <Play className="w-3 h-3 fill-current" />
                          )}
                          <span>{doc.status === 'READY' ? 'Reprocess' : 'Process'}</span>
                        </button>
                        <button
                          onClick={() => onViewDocument(doc)}
                          className="p-1.5 text-slate-600 hover:text-amber-700 hover:bg-slate-100 rounded transition-colors"
                          title="View metadata and details"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
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

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Upload Mining Document</h3>
                <p className="text-xs text-slate-500">PDF, XLSX, XLS, CSV, TXT, PNG, JPG (Max 50MB)</p>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-slate-600 text-base"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUpload} className="p-5 space-y-4">
              {/* Drag and drop zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`p-6 border-2 border-dashed rounded-lg text-center cursor-pointer transition-colors ${
                  dragOver
                    ? 'border-amber-500 bg-amber-50/50'
                    : selectedFile
                    ? 'border-emerald-400 bg-emerald-50/30'
                    : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileSelect}
                  accept=".pdf,.xlsx,.xls,.csv,.txt,.png,.jpg,.jpeg"
                  className="hidden"
                />
                <Upload className={`w-8 h-8 mx-auto mb-2 ${selectedFile ? 'text-emerald-600' : 'text-slate-400'}`} />
                {selectedFile ? (
                  <div>
                    <p className="text-xs font-semibold text-slate-900">{selectedFile.name}</p>
                    <p className="text-[11px] text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                    <span className="inline-block mt-2 text-[10px] text-emerald-700 font-semibold bg-emerald-100 px-2 py-0.5 rounded">
                      File Ready for Upload
                    </span>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-semibold text-slate-700">Drag & drop files here, or click to browse</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">Supports geological summaries, production sheets & dispatch logs</p>
                  </div>
                )}
              </div>

              {/* Document Category */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Document Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded px-3 py-2 bg-white text-slate-800 focus:outline-none focus:border-amber-500"
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
                {/* Reporting Period */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Reporting Period</label>
                  <input
                    type="text"
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                    placeholder="e.g. FY 2024-25"
                    className="w-full text-xs border border-slate-300 rounded px-3 py-2 text-slate-800 focus:outline-none focus:border-amber-500"
                  />
                </div>

                {/* Organization */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Organization</label>
                  <input
                    type="text"
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded px-3 py-2 text-slate-800 focus:outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              {/* Auto Process Checkbox */}
              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="auto_process"
                  checked={autoProcess}
                  onChange={(e) => setAutoProcess(e.target.checked)}
                  className="rounded text-amber-600 focus:ring-amber-500 h-4 w-4"
                />
                <label htmlFor="auto_process" className="text-xs text-slate-700 font-medium cursor-pointer">
                  Auto-run Document Intelligence Pipeline after upload (extract tables, text & facts)
                </label>
              </div>

              {/* Actions */}
              <div className="pt-2 flex items-center justify-end space-x-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  disabled={uploading}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded border border-slate-300 text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedFile || uploading}
                  className={`inline-flex items-center space-x-1.5 px-4 py-1.5 text-xs font-semibold rounded text-white shadow-sm transition-colors ${
                    !selectedFile || uploading
                      ? 'bg-slate-300 cursor-not-allowed'
                      : 'bg-amber-600 hover:bg-amber-700'
                  }`}
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>{autoProcess ? 'Uploading & Processing...' : 'Saving File...'}</span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-3.5 h-3.5" />
                      <span>{autoProcess ? 'Upload & Process' : 'Upload Only'}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
