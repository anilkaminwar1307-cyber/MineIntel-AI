import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  UploadCloud, FileText, FileSpreadsheet, File, X,
  CheckCircle2, AlertCircle, Clock, Loader2, RefreshCw,
  ChevronDown, Info, Layers, BarChart2, Zap, Shield,
} from "lucide-react";
import { api } from "../services/api";
import { DocumentItem } from "../types";

interface UploadQueueItem {
  id: string;
  file: File;
  status: "queued" | "uploading" | "processing" | "done" | "error" | "duplicate";
  progress: number;
  message?: string;
  document?: DocumentItem;
}

const CATEGORIES = [
  "General Mining Report","Production Report","Drilling & Exploration",
  "Dispatch Statement","Geological Assessment","Reserve Estimation",
  "Annual Report","Quarterly Report","Coking Coal Report","Environmental Report",
];
const ORGANIZATIONS = ["CMPDI / CIL","SECL","NCL","WCL","ECL","BCCL","CCL","MCL","NEC"];
const PERIODS = [
  "","Q1 FY2024-25","Q2 FY2024-25","Q3 FY2024-25","Q4 FY2024-25",
  "Q1 FY2025-26","Q2 FY2025-26","Q3 FY2025-26","Q4 FY2025-26",
  "FY2023-24","FY2024-25","FY2025-26",
];
const ACCEPTED_EXT = ".pdf,.xlsx,.xls,.docx,.csv,.tif,.tiff,.png,.jpg,.jpeg";

function fileIcon(name: string): React.ReactNode {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "pdf") return <FileText className="w-4 h-4 text-rose-400" />;
  if (["xlsx","xls","csv"].includes(ext||"")) return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
  return <File className="w-4 h-4 text-slate-400" />;
}

function statusBadge(status: UploadQueueItem["status"]) {
  const map: Record<UploadQueueItem["status"], { label: string; cls: string; icon: React.ReactNode }> = {
    queued:     { label: "Queued",     cls: "bg-slate-700 text-slate-300",        icon: <Clock className="w-3 h-3" /> },
    uploading:  { label: "Uploading",  cls: "bg-blue-900/60 text-blue-300",       icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    processing: { label: "Processing", cls: "bg-amber-900/60 text-amber-300",     icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    done:       { label: "Indexed",    cls: "bg-emerald-900/60 text-emerald-300", icon: <CheckCircle2 className="w-3 h-3" /> },
    error:      { label: "Error",      cls: "bg-rose-900/60 text-rose-300",       icon: <AlertCircle className="w-3 h-3" /> },
    duplicate:  { label: "Duplicate",  cls: "bg-yellow-900/60 text-yellow-300",   icon: <Info className="w-3 h-3" /> },
  };
  const { label, cls, icon } = map[status];
  return (
    <span className={"inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold " + cls}>
      {icon}{label}
    </span>
  );
}

interface Props { onNavigate?: (tab: string) => void; }

export const UploadIngestion: React.FC<Props> = ({ onNavigate }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [queue, setQueue] = useState<UploadQueueItem[]>([]);
  const [category, setCategory] = useState("General Mining Report");
  const [organization, setOrganization] = useState("CMPDI / CIL");
  const [period, setPeriod] = useState("");
  const [autoProcess, setAutoProcess] = useState(true);
  const [recentDocs, setRecentDocs] = useState<DocumentItem[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isBusy = queue.some(q => q.status === "uploading" || q.status === "processing");

  const loadRecent = useCallback(async () => {
    setLoadingRecent(true);
    try { const res = await api.getDocuments({ page: 1, page_size: 10 }); setRecentDocs(res.items || []); }
    catch { /* silent */ } finally { setLoadingRecent(false); }
  }, []);

  useEffect(() => { loadRecent(); }, [loadRecent]);

  const enqueue = useCallback((files: File[]) => {
    const items: UploadQueueItem[] = files.map(f => ({
      id: `${Date.now()}-${Math.random()}`,
      file: f,
      status: f.size > 200*1024*1024 ? "error" : "queued",
      progress: 0,
      message: f.size > 200*1024*1024 ? "Exceeds 200 MB limit" : undefined,
    }));
    setQueue(prev => [...prev, ...items]);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); }, []);
  const onDragLeave = useCallback(() => setIsDragging(false), []);
  const onDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); enqueue(Array.from(e.dataTransfer.files)); }, [enqueue]);

  const uploadAll = useCallback(async () => {
    const toUpload = queue.filter(q => q.status === "queued");
    if (!toUpload.length) return;
    for (const item of toUpload) {
      setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: "uploading", progress: 30 } : q));
      try {
        const res = await api.uploadDocument(item.file, category, period || undefined, organization, autoProcess);
        const nextStatus: UploadQueueItem["status"] = res.is_duplicate ? "duplicate" : autoProcess ? "processing" : "done";
        setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: nextStatus, progress: 100, message: res.is_duplicate ? "Duplicate detected" : res.message, document: res.document } : q));
      } catch (err: any) {
        const msg = err?.response?.data?.detail || err?.message || "Upload failed";
        setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: "error", progress: 0, message: msg } : q));
      }
    }
    setTimeout(loadRecent, 2000);
  }, [queue, category, period, organization, autoProcess, loadRecent]);

  const removeItem = (id: string) => setQueue(prev => prev.filter(q => q.id !== id));
  const clearDone = () => setQueue(prev => prev.filter(q => ["queued","uploading","processing"].includes(q.status)));

  const queuedCount = queue.filter(q => q.status === "queued").length;
  const doneCount = queue.filter(q => q.status === "done" || q.status === "duplicate").length;
  const errorCount = queue.filter(q => q.status === "error").length;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Supported Formats", value: "8+", sub: "PDF, DOCX, XLSX, CSV, TIF…", icon: <Layers className="w-5 h-5 text-amber-400" /> },
          { label: "Max File Size", value: "200 MB", sub: "Per file limit", icon: <Shield className="w-5 h-5 text-emerald-400" /> },
          { label: "Auto-Extraction", value: "AI", sub: "Tables, facts, OCR", icon: <Zap className="w-5 h-5 text-blue-400" /> },
          { label: "Provenance", value: "100%", sub: "Page and cell coordinates", icon: <BarChart2 className="w-5 h-5 text-purple-400" /> },
        ].map(kpi => (
          <div key={kpi.label} className="bg-[#0c1322] border border-slate-800 rounded-xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-800/80 flex items-center justify-center flex-shrink-0">{kpi.icon}</div>
            <div>
              <p className="text-lg font-bold text-white leading-tight">{kpi.value}</p>
              <p className="text-[11px] text-slate-400">{kpi.label}</p>
              <p className="text-[10px] text-slate-500">{kpi.sub}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: drop zone + config + queue */}
        <div className="lg:col-span-2 space-y-4">
          {/* Drop zone */}
          <div
            onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={"relative rounded-2xl border-2 border-dashed transition-all cursor-pointer flex flex-col items-center justify-center gap-3 p-10 text-center " + (isDragging ? "border-amber-500 bg-amber-500/5 shadow-lg shadow-amber-500/10" : "border-slate-700 bg-[#0c1322] hover:border-amber-600/60 hover:bg-slate-800/30")}
          >
            <input ref={fileInputRef} type="file" multiple accept={ACCEPTED_EXT} className="sr-only"
              onChange={e => enqueue(Array.from(e.target.files || []))} />
            <div className={"w-16 h-16 rounded-2xl flex items-center justify-center transition-colors " + (isDragging ? "bg-amber-500/20" : "bg-slate-800")}>
              <UploadCloud className={"w-8 h-8 transition-colors " + (isDragging ? "text-amber-400" : "text-slate-400")} />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-200">{isDragging ? "Release to add files" : "Drop files or click to browse"}</p>
              <p className="text-xs text-slate-500 mt-1">PDF · DOCX · XLSX · CSV · TIFF · PNG · JPEG — up to 200 MB each</p>
            </div>
          </div>

          {/* Config */}
          <div className="bg-[#0c1322] border border-slate-800 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { label: "Document Category", value: category, setter: setCategory, opts: CATEGORIES },
              { label: "Organization / Subsidiary", value: organization, setter: setOrganization, opts: ORGANIZATIONS },
            ].map(sel => (
              <div key={sel.label} className="space-y-1">
                <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">{sel.label}</label>
                <div className="relative">
                  <select value={sel.value} onChange={e => sel.setter(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 appearance-none focus:outline-none focus:border-amber-500 transition-colors">
                    {sel.opts.map(o => <option key={o}>{o}</option>)}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                </div>
              </div>
            ))}
            <div className="space-y-1">
              <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Reporting Period</label>
              <div className="relative">
                <select value={period} onChange={e => setPeriod(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 appearance-none focus:outline-none focus:border-amber-500 transition-colors">
                  <option value="">— Unspecified —</option>
                  {PERIODS.filter(Boolean).map(p => <option key={p}>{p}</option>)}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
              </div>
            </div>
            <div className="sm:col-span-3 flex items-center gap-3 pt-1">
              <button type="button" onClick={() => setAutoProcess(v => !v)}
                className={"relative w-9 h-5 rounded-full transition-colors flex-shrink-0 " + (autoProcess ? "bg-amber-500" : "bg-slate-700")}>
                <span className={"absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform " + (autoProcess ? "translate-x-4" : "translate-x-0.5")} />
              </button>
              <span className="text-xs text-slate-300">
                <span className="font-semibold text-slate-200">Auto-process on upload</span>
                <span className="text-slate-500 ml-2">— Extract facts, OCR, populate Evidence Ledger</span>
              </span>
            </div>
          </div>

          {/* Queue */}
          {queue.length > 0 && (
            <div className="bg-[#0c1322] border border-slate-800 rounded-xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-slate-300">Upload Queue</span>
                  <div className="flex items-center gap-2 text-[10px]">
                    {queuedCount > 0 && <span className="px-1.5 py-0.5 rounded bg-slate-700 text-slate-300">{queuedCount} queued</span>}
                    {doneCount > 0 && <span className="px-1.5 py-0.5 rounded bg-emerald-900/60 text-emerald-300">{doneCount} done</span>}
                    {errorCount > 0 && <span className="px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300">{errorCount} error</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {doneCount > 0 && <button onClick={clearDone} className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors">Clear done</button>}
                  <button onClick={uploadAll} disabled={isBusy || queuedCount === 0}
                    className={"flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all " + (isBusy || queuedCount === 0 ? "bg-slate-700 text-slate-500 cursor-not-allowed" : "bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-md")}>
                    {isBusy ? <Loader2 className="w-3 h-3 animate-spin" /> : <UploadCloud className="w-3 h-3" />}
                    {isBusy ? "Uploading…" : ("Upload " + queuedCount + (queuedCount !== 1 ? " files" : " file"))}
                  </button>
                </div>
              </div>
              <div className="divide-y divide-slate-800/60 max-h-72 overflow-y-auto">
                {queue.map(item => (
                  <div key={item.id} className="flex items-center gap-3 px-4 py-2.5 group">
                    <div className="flex-shrink-0">{fileIcon(item.file.name)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-slate-200 truncate">{item.file.name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-slate-500">{(item.file.size/1024/1024).toFixed(2)} MB</span>
                        {item.message && <span className="text-[10px] text-slate-400 truncate max-w-[200px]">{item.message}</span>}
                      </div>
                      {(item.status === "uploading" || item.status === "processing") && (
                        <div className="mt-1.5 h-1 bg-slate-700 rounded-full overflow-hidden">
                          <div className="h-full bg-amber-500 rounded-full transition-all duration-500" style={{ width: item.progress + "%" }} />
                        </div>
                      )}
                    </div>
                    <div className="flex-shrink-0 flex items-center gap-2">
                      {statusBadge(item.status)}
                      {["queued","error","done","duplicate"].includes(item.status) && (
                        <button onClick={() => removeItem(item.id)}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-all">
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: recent + pipeline info */}
        <div className="space-y-4">
          <div className="bg-[#0c1322] border border-slate-800 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-300">Recent Ingestions</span>
              <button onClick={loadRecent} disabled={loadingRecent} className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors">
                <RefreshCw className={"w-3.5 h-3.5 " + (loadingRecent ? "animate-spin" : "")} />
              </button>
            </div>
            {loadingRecent ? (
              <div className="flex items-center justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-amber-400" /></div>
            ) : recentDocs.length === 0 ? (
              <div className="px-4 py-8 text-center text-xs text-slate-500">No documents ingested yet.<br />Upload your first file above.</div>
            ) : (
              <div className="divide-y divide-slate-800/60 max-h-[400px] overflow-y-auto">
                {recentDocs.map(doc => (
                  <div key={doc.id} className="px-4 py-3 cursor-pointer hover:bg-slate-800/40 transition-colors group" onClick={() => onNavigate?.("documents")}>
                    <div className="flex items-start gap-2.5">
                      <div className="mt-0.5 flex-shrink-0">{fileIcon(doc.original_filename)}</div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-slate-200 truncate group-hover:text-amber-300 transition-colors">{doc.original_filename}</p>
                        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                          <span className={"text-[9px] px-1.5 py-0.5 rounded font-semibold " + (doc.status === "processed" ? "bg-emerald-900/60 text-emerald-300" : doc.status === "processing" ? "bg-amber-900/60 text-amber-300" : doc.status === "error" ? "bg-rose-900/60 text-rose-300" : "bg-slate-700 text-slate-400")}>{doc.status}</span>
                          <span className="text-[10px] text-slate-500 truncate">{doc.organization}</span>
                        </div>
                        <p className="text-[10px] text-slate-600 mt-0.5">{doc.created_at ? new Date(doc.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}) : "—"}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {recentDocs.length > 0 && (
              <div className="px-4 py-2.5 border-t border-slate-800">
                <button onClick={() => onNavigate?.("documents")} className="w-full text-[11px] text-amber-400 hover:text-amber-300 transition-colors font-semibold">View All in Document Library →</button>
              </div>
            )}
          </div>

          <div className="bg-gradient-to-br from-amber-900/20 to-amber-800/10 border border-amber-800/30 rounded-xl p-4 space-y-2">
            <p className="text-xs font-semibold text-amber-300 flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" /> AI Ingestion Pipeline</p>
            {["① Magic-byte & OOXML security validation","② Atomic write to evidence storage","③ PDF/DOCX text + table extraction","④ Excel sheet & cell parsing with row coordinates","⑤ NumberSafe fact normalization & unit tagging","⑥ Chunk embedding for semantic search","⑦ Data-quality issue auto-flagging"].map(s => (
              <p key={s} className="text-[11px] text-amber-200/70">{s}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
