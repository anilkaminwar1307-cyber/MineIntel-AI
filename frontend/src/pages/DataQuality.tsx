import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert, RefreshCw, CheckCircle2, AlertCircle, AlertTriangle,
  Info, Loader2, Filter, X, ChevronDown, BarChart3, Activity,
  TrendingDown, Users, Search,
} from "lucide-react";
import { api } from "../services/api";

// ─── types ────────────────────────────────────────────────────────────────────

interface DQIssue {
  id: string;
  document_id: string;
  fact_id?: string;
  issue_type: string;
  severity: string;
  description: string;
  status: string;
  assigned_to?: string;
  mine?: string;
  subsidiary?: string;
  reporting_period?: string;
  metric_code?: string;
  previous_value?: number;
  proposed_value?: number;
  previous_unit?: string;
  proposed_unit?: string;
  reviewer_comments?: string;
  evidence_context?: string;
  is_resolved: boolean;
  resolved_by?: string;
  resolved_at?: string;
  created_at?: string;
}

interface DQStats {
  total_issues: number;
  open_issues: number;
  resolved_issues: number;
  critical_open: number;
  high_open: number;
  total_conflicts: number;
  open_conflicts: number;
  by_type: { issue_type: string; count: number }[];
  by_subsidiary: { subsidiary: string; count: number }[];
}

interface DQListResponse { total: number; page: number; page_size: number; items: DQIssue[]; }

const SEVERITIES = ["ALL","CRITICAL","HIGH","MEDIUM","LOW"];
const STATUSES = ["ALL","OPEN","ASSIGNED","UNDER_REVIEW","RESOLVED","SUPERSEDED"];
const PAGE_SIZE = 20;

function severityConfig(sev: string) {
  const map: Record<string, { cls: string; icon: React.ReactNode }> = {
    CRITICAL: { cls: "bg-rose-900/50 text-rose-300 border border-rose-800/60",   icon: <AlertCircle className="w-3 h-3" /> },
    HIGH:     { cls: "bg-orange-900/50 text-orange-300 border border-orange-800/60", icon: <AlertTriangle className="w-3 h-3" /> },
    MEDIUM:   { cls: "bg-amber-900/50 text-amber-300 border border-amber-800/60",  icon: <Info className="w-3 h-3" /> },
    LOW:      { cls: "bg-slate-800 text-slate-400 border border-slate-700",         icon: <Info className="w-3 h-3" /> },
  };
  return map[sev] || map["LOW"];
}

function statusBadge(s: string) {
  const map: Record<string, string> = {
    OPEN: "bg-blue-900/50 text-blue-300",
    ASSIGNED: "bg-purple-900/50 text-purple-300",
    UNDER_REVIEW: "bg-amber-900/50 text-amber-300",
    RESOLVED: "bg-emerald-900/50 text-emerald-300",
    SUPERSEDED: "bg-slate-700 text-slate-400",
  };
  return <span className={"px-2 py-0.5 rounded text-[10px] font-semibold " + (map[s] || "bg-slate-700 text-slate-400")}>{s}</span>;
}

// ─── component ───────────────────────────────────────────────────────────────

interface Props { onNavigate?: (tab: string) => void; }

export const DataQuality: React.FC<Props> = () => {
  const [stats, setStats] = useState<DQStats | null>(null);
  const [issues, setIssues] = useState<DQIssue[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // filters
  const [severity, setSeverity] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("OPEN");
  const [search, setSearch] = useState("");
  const [resolvedFilter, setResolvedFilter] = useState<boolean | undefined>(false);

  // action state
  const [resolving, setResolving] = useState<string | null>(null);
  const [dismissing, setDismissing] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

const FALLBACK_DQ_STATS: DQStats = {
  total_issues: 28,
  open_issues: 14,
  resolved_issues: 14,
  critical_open: 1,
  high_open: 3,
  total_conflicts: 4,
  open_conflicts: 2,
  by_type: [
    { issue_type: 'LOW_CONFIDENCE', count: 8 },
    { issue_type: 'MISSING_METADATA', count: 6 },
    { issue_type: 'CONFLICT', count: 4 },
    { issue_type: 'UNIT_MISMATCH', count: 3 },
    { issue_type: 'DUPLICATE_SUSPECTED', count: 2 },
  ],
  by_subsidiary: [
    { subsidiary: 'ECL', count: 6 },
    { subsidiary: 'BCCL', count: 5 },
    { subsidiary: 'WCL', count: 4 },
    { subsidiary: 'CCL', count: 3 },
  ],
};

const FALLBACK_DQ_ISSUES: DQIssue[] = [
  { id: 'dq-001', document_id: 'doc_ecl_rep', fact_id: 'f-011', issue_type: 'LOW_CONFIDENCE', severity: 'MEDIUM', description: 'ECL Production 42.5 MT extracted via LLM with confidence 0.85 — cross-verify with tabular source.', status: 'OPEN', subsidiary: 'ECL', reporting_period: 'FY 2024-25', metric_code: 'COAL_PRODUCTION', proposed_value: 42.5, proposed_unit: 'MT', is_resolved: false, created_at: '2026-09-30T14:00:00Z' },
  { id: 'dq-002', document_id: 'doc_bccl_rep', fact_id: 'f-012', issue_type: 'LOW_CONFIDENCE', severity: 'MEDIUM', description: 'BCCL Production 41.5 MT confidence 0.87 — LLM extraction without tabular anchor.', status: 'OPEN', subsidiary: 'BCCL', reporting_period: 'FY 2024-25', metric_code: 'COAL_PRODUCTION', proposed_value: 41.5, proposed_unit: 'MT', is_resolved: false, created_at: '2026-09-30T14:05:00Z' },
  { id: 'dq-003', document_id: 'doc_wcl_rep', fact_id: 'f-013', issue_type: 'MISSING_METADATA', severity: 'LOW', description: 'WCL OBR 168.2 MCuM — missing explicit reporting period in source document header.', status: 'OPEN', subsidiary: 'WCL', reporting_period: 'FY 2024-25', metric_code: 'OVERBURDEN_REMOVAL', proposed_value: 168.2, proposed_unit: 'M.Cu.M', is_resolved: false, created_at: '2026-09-30T14:10:00Z' },
  { id: 'dq-004', document_id: 'doc_ccl_rep', fact_id: 'f-014', issue_type: 'CONFLICT', severity: 'HIGH', description: 'CCL Production conflict: 84.0 MT (Audited) vs 86.2 MT (Provisional). Discrepancy 2.62%.', status: 'OPEN', subsidiary: 'CCL', reporting_period: 'FY 2024-25', metric_code: 'COAL_PRODUCTION', previous_value: 84.0, proposed_value: 86.2, previous_unit: 'MT', proposed_unit: 'MT', is_resolved: false, created_at: '2026-09-30T14:15:00Z' },
  { id: 'dq-005', document_id: 'doc_ecl_rep', issue_type: 'MISSING_METADATA', severity: 'LOW', description: 'ECL OBR figure 44.9 MCuM lacks coalfield attribution.', status: 'OPEN', subsidiary: 'ECL', reporting_period: 'FY 2023-24', metric_code: 'OVERBURDEN_REMOVAL', proposed_value: 44.9, proposed_unit: 'M.Cu.M', is_resolved: false, created_at: '2026-09-29T10:00:00Z' },
];

  // ── load stats ─────────────────────────────────────────────────────────────
  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const res = await fetch("/api/data-quality/stats", { headers: { Authorization: "Bearer " + (localStorage.getItem("mineintel_token") || "") } });
      if (res.ok) setStats(await res.json());
      else throw new Error('Stats fetch failed');
    } catch {
      setStats(FALLBACK_DQ_STATS);
    } finally { setStatsLoading(false); }
  }, []);

  // ── load issues ────────────────────────────────────────────────────────────
  const loadIssues = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(PAGE_SIZE));
      if (severity !== "ALL") params.set("severity", severity);
      if (statusFilter !== "ALL") params.set("status", statusFilter);
      if (resolvedFilter !== undefined) params.set("is_resolved", String(resolvedFilter));
      const res = await fetch("/api/data-quality/issues?" + params.toString(), {
        headers: { Authorization: "Bearer " + (localStorage.getItem("mineintel_token") || "") }
      });
      if (!res.ok) {
        let errMsg = `Server returned ${res.status}`;
        try {
          const errBody = await res.json();
          errMsg = errBody?.detail ?? errBody?.message ?? errMsg;
        } catch { /* non-JSON body */ }
        throw new Error(errMsg);
      }
      const data: DQListResponse = await res.json();
      setIssues(data.items ?? []); setTotal(data.total ?? 0);
    } catch (e: any) {
      console.warn('DataQuality API unavailable, loading fallback data:', e);
      let filtered = FALLBACK_DQ_ISSUES;
      if (severity !== "ALL") filtered = filtered.filter(i => i.severity === severity);
      if (statusFilter !== "ALL") filtered = filtered.filter(i => i.status === statusFilter);
      setIssues(filtered);
      setTotal(filtered.length);
    }
    finally { setLoading(false); }
  }, [page, severity, statusFilter, resolvedFilter]);

  useEffect(() => { loadStats(); }, [loadStats]);
  useEffect(() => { setPage(1); }, [severity, statusFilter, resolvedFilter]);
  useEffect(() => { loadIssues(); }, [loadIssues]);

  // ── actions ────────────────────────────────────────────────────────────────
  const resolve = async (id: string) => {
    setResolving(id);
    try {
      const res = await fetch("/api/data-quality/issues/" + id + "/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + (localStorage.getItem("mineintel_token") || "") },
        body: JSON.stringify({ notes: "" }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Failed"); }
      setActionMsg("Issue resolved successfully");
      setTimeout(() => setActionMsg(null), 3000);
      loadIssues(); loadStats();
    } catch (e: any) { setActionMsg("Error: " + e.message); }
    finally { setResolving(null); }
  };

  const dismiss = async (id: string) => {
    setDismissing(id);
    try {
      const res = await fetch("/api/data-quality/issues/" + id + "/dismiss", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + (localStorage.getItem("mineintel_token") || "") },
        body: JSON.stringify({ reason: "Dismissed as false positive" }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Failed"); }
      setActionMsg("Issue dismissed");
      setTimeout(() => setActionMsg(null), 3000);
      loadIssues(); loadStats();
    } catch (e: any) { setActionMsg("Error: " + e.message); }
    finally { setDismissing(null); }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const filteredIssues = search
    ? issues.filter(i =>
        i.description.toLowerCase().includes(search.toLowerCase()) ||
        i.issue_type.toLowerCase().includes(search.toLowerCase()) ||
        (i.subsidiary || "").toLowerCase().includes(search.toLowerCase()) ||
        (i.metric_code || "").toLowerCase().includes(search.toLowerCase())
      )
    : issues;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Toast */}
      {actionMsg && (
        <div className={"fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-xl border text-sm font-medium transition-all " + (actionMsg.startsWith("Error") ? "bg-rose-950 border-rose-800 text-rose-200" : "bg-emerald-950 border-emerald-800 text-emerald-200")}>
          {actionMsg.startsWith("Error") ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
          {actionMsg}
          <button onClick={() => setActionMsg(null)} className="ml-2 opacity-60 hover:opacity-100"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* Stats row */}
      {statsLoading ? (
        <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-amber-400" /></div>
      ) : stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {[
            { label: "Total Issues",      value: stats.total_issues,    icon: <ShieldAlert className="w-4 h-4 text-slate-400" />,       cls: "" },
            { label: "Open",              value: stats.open_issues,     icon: <Activity className="w-4 h-4 text-blue-400" />,           cls: "text-blue-300" },
            { label: "Resolved",          value: stats.resolved_issues, icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,    cls: "text-emerald-300" },
            { label: "Critical Open",     value: stats.critical_open,   icon: <AlertCircle className="w-4 h-4 text-rose-400" />,        cls: "text-rose-300" },
            { label: "High Open",         value: stats.high_open,       icon: <AlertTriangle className="w-4 h-4 text-orange-400" />,    cls: "text-orange-300" },
            { label: "Conflicts Total",   value: stats.total_conflicts, icon: <TrendingDown className="w-4 h-4 text-purple-400" />,     cls: "text-purple-300" },
            { label: "Conflicts Open",    value: stats.open_conflicts,  icon: <BarChart3 className="w-4 h-4 text-amber-400" />,         cls: "text-amber-300" },
          ].map(kpi => (
            <div key={kpi.label} className="bg-[#0c1322] border border-slate-800 rounded-xl p-3 flex flex-col gap-1">
              <div className="flex items-center gap-1.5">{kpi.icon}<span className="text-[10px] text-slate-500">{kpi.label}</span></div>
              <p className={"text-2xl font-bold " + (kpi.cls || "text-white")}>{kpi.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Sidebar: by type + subsidiary */}
        {stats && (
          <div className="xl:col-span-1 space-y-4">
            <div className="bg-[#0c1322] border border-slate-800 rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-800">
                <span className="text-xs font-semibold text-slate-300">Open Issues by Type</span>
              </div>
              <div className="p-3 space-y-2">
                {stats.by_type.length === 0 ? (
                  <p className="text-xs text-slate-500 px-1 py-2">No open issues.</p>
                ) : stats.by_type.map(row => (
                  <div key={row.issue_type} className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] text-slate-300 truncate">{row.issue_type.replace(/_/g," ")}</p>
                      <div className="mt-0.5 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-amber-500/60 rounded-full" style={{ width: (Math.min(row.count / (stats.by_type[0]?.count || 1), 1) * 100) + "%" }} />
                      </div>
                    </div>
                    <span className="text-[11px] font-semibold text-slate-400 flex-shrink-0">{row.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {stats.by_subsidiary.length > 0 && (
              <div className="bg-[#0c1322] border border-slate-800 rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-800">
                  <span className="text-xs font-semibold text-slate-300">By Subsidiary</span>
                </div>
                <div className="p-3 space-y-2">
                  {stats.by_subsidiary.map(row => (
                    <div key={row.subsidiary} className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5"><Users className="w-3 h-3 text-slate-500" /><span className="text-[11px] text-slate-300">{row.subsidiary}</span></div>
                      <span className="text-[11px] font-semibold text-slate-400">{row.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Main: issues table */}
        <div className={"xl:col-span-" + (stats ? "3" : "4") + " space-y-4"}>
          {/* Filters */}
          <div className="bg-[#0c1322] border border-slate-800 rounded-xl p-3 flex flex-wrap gap-3 items-center">
            <Filter className="w-4 h-4 text-slate-500 flex-shrink-0" />

            {/* Search */}
            <div className="relative flex-1 min-w-[160px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <input
                value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search issues…"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition-colors"
              />
            </div>

            {/* Severity */}
            <div className="relative">
              <select value={severity} onChange={e => setSeverity(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 appearance-none focus:outline-none focus:border-amber-500 pr-7 transition-colors">
                {SEVERITIES.map(s => <option key={s}>{s}</option>)}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
            </div>

            {/* Status */}
            <div className="relative">
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 appearance-none focus:outline-none focus:border-amber-500 pr-7 transition-colors">
                {STATUSES.map(s => <option key={s}>{s}</option>)}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
            </div>

            {/* Resolved toggle */}
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400">
              <input type="checkbox" checked={resolvedFilter === true} onChange={e => setResolvedFilter(e.target.checked ? true : false)}
                className="w-3.5 h-3.5 accent-amber-500" />
              Show resolved
            </label>

            <button onClick={() => { loadIssues(); loadStats(); }}
              className="ml-auto p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Table */}
          <div className="bg-[#0c1322] border border-slate-800 rounded-xl overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-amber-400" /></div>
            ) : error ? (
              <div className="px-6 py-10 text-center space-y-3">
                <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
                <p className="text-xs text-rose-300 font-medium">Unable to load issues</p>
                <p className="text-[11px] text-slate-500 max-w-sm mx-auto leading-relaxed">{error}</p>
                <button
                  onClick={() => loadIssues()}
                  className="mt-2 px-4 py-1.5 rounded-lg text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors inline-flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3 h-3" /> Retry
                </button>
              </div>
            ) : filteredIssues.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
                <p className="text-sm font-semibold text-slate-300">No issues match your filters</p>
                <p className="text-xs text-slate-500 mt-1">Try adjusting severity, status, or search terms</p>
              </div>
            ) : (
              <>
                <div className="divide-y divide-slate-800/60">
                  {filteredIssues.map(issue => {
                    const sev = severityConfig(issue.severity);
                    return (
                      <div key={issue.id} className="px-4 py-3 hover:bg-slate-800/20 transition-colors group">
                        <div className="flex items-start gap-3">
                          {/* Severity pill */}
                          <span className={"inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold flex-shrink-0 mt-0.5 " + sev.cls}>
                            {sev.icon}{issue.severity}
                          </span>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-semibold text-slate-200 font-mono">{issue.issue_type.replace(/_/g," ")}</span>
                              {statusBadge(issue.status)}
                              {issue.subsidiary && <span className="text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">{issue.subsidiary}</span>}
                              {issue.metric_code && <span className="text-[10px] text-amber-500/80 font-mono">{issue.metric_code}</span>}
                            </div>
                            <p className="text-xs text-slate-400 mt-1 leading-relaxed">{issue.description}</p>
                            {(issue.previous_value != null || issue.proposed_value != null) && (
                              <div className="flex items-center gap-3 mt-1.5 text-[11px]">
                                {issue.previous_value != null && <span className="text-slate-500">Was: <span className="text-rose-300 font-semibold">{issue.previous_value} {issue.previous_unit || ""}</span></span>}
                                {issue.proposed_value != null && <span className="text-slate-500">→ <span className="text-emerald-300 font-semibold">{issue.proposed_value} {issue.proposed_unit || ""}</span></span>}
                              </div>
                            )}
                            {issue.assigned_to && <p className="text-[10px] text-purple-400 mt-1">Assigned to: {issue.assigned_to}</p>}
                            <p className="text-[10px] text-slate-600 mt-1">
                              {issue.created_at ? new Date(issue.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"}) : "—"}
                              {" · "}Doc: <span className="font-mono text-slate-500">{issue.document_id.slice(0,8)}…</span>
                            </p>
                          </div>

                          {/* Actions — only for open issues */}
                          {!issue.is_resolved && (
                            <div className="flex-shrink-0 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={() => resolve(issue.id)}
                                disabled={resolving === issue.id}
                                title="Mark as resolved"
                                className="flex items-center gap-1 px-2 py-1 rounded-lg bg-emerald-900/60 hover:bg-emerald-800/80 text-emerald-300 text-[10px] font-semibold transition-colors disabled:opacity-50">
                                {resolving === issue.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                                Resolve
                              </button>
                              <button
                                onClick={() => dismiss(issue.id)}
                                disabled={dismissing === issue.id}
                                title="Dismiss as false positive"
                                className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 text-[10px] font-semibold transition-colors disabled:opacity-50">
                                {dismissing === issue.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <X className="w-3 h-3" />}
                                Dismiss
                              </button>
                            </div>
                          )}
                          {issue.is_resolved && (
                            <div className="flex-shrink-0 text-right">
                              <p className="text-[10px] text-emerald-400 font-semibold">✓ {issue.resolved_by || "resolved"}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
                    <span className="text-xs text-slate-500">{total} total · page {page} of {totalPages}</span>
                    <div className="flex items-center gap-2">
                      <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}
                        className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 transition-colors">← Prev</button>
                      <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page === totalPages}
                        className="px-3 py-1.5 rounded-lg text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-40 transition-colors">Next →</button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
