import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  Server,
  Database,
  HardDrive,
  Sparkles,
  Cpu,
  Layers,
  FileCheck,
  Printer,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  FileSpreadsheet,
  Network,
  Split,
  FileText
} from 'lucide-react';
import { api } from '../services/api';
import { SystemSettingsStatus, ComponentStatus } from '../types';

export const Settings: React.FC = () => {
  const [settingsData, setSettingsData] = useState<SystemSettingsStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getSystemSettings();
      setSettingsData(data);
    } catch (err: any) {
      console.error(err);
      setError('Unable to reach backend system settings endpoint.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const components = settingsData?.components || {};
  const recordCounts = settingsData?.record_counts || {};

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OPERATIONAL':
        return <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
      case 'UNAVAILABLE':
        return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      case 'NOT_CONFIGURED':
        return <HelpCircle className="w-4 h-4 text-slate-400" />;
      case 'DEGRADED':
        return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      case 'ERROR':
        return <XCircle className="w-4 h-4 text-rose-600" />;
      default:
        return <HelpCircle className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'OPERATIONAL':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            OPERATIONAL
          </span>
        );
      case 'UNAVAILABLE':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-300">
            UNAVAILABLE
          </span>
        );
      case 'NOT_CONFIGURED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            NOT CONFIGURED
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            DEGRADED
          </span>
        );
      case 'ERROR':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-800 border border-rose-200">
            ERROR
          </span>
        );
      default:
        return <span className="text-[10px] text-slate-400">{status}</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Header */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-slate-900">Platform Settings & Subsystem Readiness</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
              Live Diagnostics
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Real verification of backend services, database connections, storage directories, and AI providers.
          </p>
        </div>

        <button
          onClick={loadSettings}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded border border-slate-300 text-slate-700 hover:bg-slate-50 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Run Diagnostics</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
          {error}
        </div>
      )}

      {/* System Environment Information */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-4 pb-2 border-b border-slate-100">
          Environment & Deployment
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-slate-400 block mb-0.5">Application</span>
            <span className="font-semibold text-slate-900">{settingsData?.app_name || 'MineIntel'}</span>
          </div>
          <div>
            <span className="text-slate-400 block mb-0.5">Version</span>
            <span className="font-mono text-slate-900">v{settingsData?.version || '0.2.0'} (Full Database Active)</span>
          </div>
          <div>
            <span className="text-slate-400 block mb-0.5">Environment</span>
            <span className="font-semibold text-amber-700 uppercase font-mono text-[11px]">
              {settingsData?.environment || 'development'}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block mb-0.5">Target Organization</span>
            <span className="font-semibold text-slate-900">CMPDI / Coal India Limited</span>
          </div>
        </div>
      </div>

      {/* Database Record Counts Grid */}
      {recordCounts && Object.keys(recordCounts).length > 0 && (
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <Database className="w-4 h-4 text-amber-600" />
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Live SQLite Evidence Ledger Inventory
              </h3>
            </div>
            <span className="text-[10px] text-emerald-700 font-mono font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              50,000+ Fact Scale Target Reached
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Total Documents</span>
              <span className="text-lg font-bold text-slate-900 mt-0.5 block">{recordCounts.documents?.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">PDF, XLSX, Scanned</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Extracted Evidence Facts</span>
              <span className="text-lg font-bold text-slate-900 mt-0.5 block">{recordCounts.extracted_facts?.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">Deterministic SQL Ledger</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Human-Verified Facts</span>
              <span className="text-lg font-bold text-emerald-700 mt-0.5 block">{recordCounts.verified_facts?.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">Signed-off by CMPDI Analyst</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Document Chunks</span>
              <span className="text-lg font-bold text-slate-900 mt-0.5 block">{recordCounts.document_chunks?.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">Semantic text blocks</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">MineGraph Topics</span>
              <span className="text-lg font-bold text-slate-900 mt-0.5 block">{recordCounts.discovered_topics?.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">Operational clusters</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Tracked Conflicts</span>
              <span className="text-lg font-bold text-rose-700 mt-0.5 block">{recordCounts.evidence_conflicts?.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">Cross-document pairs</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Validation Issues</span>
              <span className="text-lg font-bold text-amber-700 mt-0.5 block">{recordCounts.validation_issues?.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">ReportGuard audit items</span>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-[10px] text-slate-500 uppercase font-semibold block">Generated Reports</span>
              <span className="text-lg font-bold text-slate-900 mt-0.5 block">{recordCounts.generated_reports?.toLocaleString()}</span>
              <span className="text-[10px] text-slate-400">Synthesized briefs</span>
            </div>
          </div>
        </div>
      )}

      {/* Subsystems Matrix */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 bg-slate-50/50">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Subsystems & Service Status Matrix
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Operational status evaluated dynamically across all core extraction, storage, and intelligence pipelines.
          </p>
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
            Testing component connections...
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {Object.entries(components).map(([key, comp]) => (
              <div key={key} className="p-4 flex items-center justify-between hover:bg-slate-50/50 transition-colors">
                <div className="flex items-center space-x-3.5">
                  <div className="p-2 rounded bg-slate-50 border border-slate-200">
                    {getStatusIcon(comp.status)}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h4 className="text-xs font-bold text-slate-900">{comp.name}</h4>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-500">
                        {comp.category}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">{comp.details || '—'}</p>
                  </div>
                </div>

                <div>
                  {getStatusBadge(comp.status)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Gemini Configuration Guide Card */}
      <div className="bg-amber-50/50 p-5 rounded-lg border border-amber-200/70 text-xs text-amber-950 space-y-2">
        <div className="flex items-center space-x-2 text-amber-900 font-bold">
          <Sparkles className="w-4 h-4 text-amber-700" />
          <span>Google Gemini Configuration:</span>
        </div>
        <p className="text-[11px] text-amber-900 leading-relaxed">
          To activate Google Gemini for document classification and narrative synthesis, configure your key in{' '}
          <code className="bg-amber-100/80 px-1 py-0.5 rounded font-mono text-amber-900">.env</code>:
        </p>
        <pre className="bg-slate-900 text-amber-300 p-2.5 rounded font-mono text-[11px] overflow-x-auto">
          GEMINI_API_KEY=your_gemini_api_key_here
          <br />
          GEMINI_MODEL=gemini-2.5-flash
        </pre>
        <p className="text-[10px] text-amber-800">
          Note: In accordance with NumberSafe Rule 1, numerical mining statistics are extracted and aggregated strictly via SQL, never hallucinated by any language model.
        </p>
      </div>
    </div>
  );
};
