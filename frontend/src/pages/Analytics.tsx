import React, { useState, useEffect } from 'react';
import {
  LineChart as LucideLineChart,
  BarChart3,
  PieChart as LucidePieChart,
  TrendingUp,
  Filter,
  RefreshCw,
  Layers,
  Database,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Pickaxe,
  Activity,
  FileBarChart,
  GitCompare,
  Gauge,
  Mountain,
  FileCheck,
  Building2,
  CalendarDays,
  ChevronRight
} from 'lucide-react';
import { api } from '../services/api';
import { AnalyticsOverview, AnalyticsExtended } from '../types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ComposedChart,
} from 'recharts';

// ─── Colour palette ────────────────────────────────────────────────────────────
const COLORS_PIE = ['#d97706', '#2563eb', '#059669', '#dc2626', '#7c3aed', '#0891b2', '#db2777', '#84cc16', '#f97316', '#8b5cf6'];
const COLORS_SUB = { ECL: '#d97706', BCCL: '#2563eb', CCL: '#059669', WCL: '#dc2626', SECL: '#7c3aed', MCL: '#0891b2', NCL: '#db2777' } as Record<string, string>;

// ─── Helper: no-data guard ─────────────────────────────────────────────────────
const NoData: React.FC = () => (
  <div className="flex items-center justify-center h-full">
    <div className="text-center">
      <Database className="w-8 h-8 text-slate-300 mx-auto mb-2" />
      <p className="text-xs text-slate-400 font-medium">No data available for selected filters.</p>
      <p className="text-[10px] text-slate-300 mt-0.5">Upload documents to populate this chart.</p>
    </div>
  </div>
);

// ─── Helper: chart card wrapper ────────────────────────────────────────────────
interface CardProps {
  icon: React.ReactNode;
  title: string;
  badge?: string;
  children: React.ReactNode;
}
const ChartCard: React.FC<CardProps> = ({ icon, title, badge, children }) => (
  <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-3">
    <div className="flex items-center justify-between pb-2 border-b border-slate-100">
      <div className="flex items-center space-x-2">
        {icon}
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">{title}</h3>
      </div>
      {badge && (
        <span className="text-[10px] text-slate-400 font-mono">{badge}</span>
      )}
    </div>
    {children}
  </div>
);

// ─── Custom tooltip ────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-xs max-w-xs">
      <p className="font-bold text-slate-700 mb-1.5">{label}</p>
      {payload.map((p: any, i: number) => (
        <div key={i} className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color || p.fill }} />
          <span className="text-slate-600">{p.name}:</span>
          <span className="font-semibold text-slate-800 ml-auto pl-2">
            {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
          </span>
        </div>
      ))}
    </div>
  );
};

// ─── Main Component ────────────────────────────────────────────────────────────
export const Analytics: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [extended, setExtended] = useState<AnalyticsExtended | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [extLoading, setExtLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [subsidiary, setSubsidiary] = useState<string>('ALL');
  const [financialYear, setFinancialYear] = useState<string>('ALL');

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getAnalyticsOverview({
        subsidiary: subsidiary === 'ALL' ? undefined : subsidiary,
        financial_year: financialYear === 'ALL' ? undefined : financialYear,
      });
      setOverview(data);
    } catch (err) {
      console.error('Error loading overview analytics:', err);
      setError('Failed to load analytics. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const loadExtended = async () => {
    try {
      setExtLoading(true);
      const data = await api.getAnalyticsExtended({
        subsidiary: subsidiary === 'ALL' ? undefined : subsidiary,
        financial_year: financialYear === 'ALL' ? undefined : financialYear,
      });
      setExtended(data);
    } catch (err) {
      console.error('Error loading extended analytics:', err);
    } finally {
      setExtLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
    loadExtended();
  }, [subsidiary, financialYear]);

  const handleRefresh = () => {
    loadAnalytics();
    loadExtended();
  };

  // ── derived values ──────────────────────────────────────────────────────────
  const kpis = overview?.kpis;
  const subsidiaries = overview?.subsidiaries || [];
  const trends = overview?.multi_year_production_trends || [];
  const targetVsAch = overview?.target_vs_achievement || [];
  const prodVsDisp = overview?.production_vs_dispatch || [];
  const confDist = (overview?.confidence_distribution as Record<string, number>) || {};

  const pieData = [
    { name: 'High (≥90%)', value: confDist['high_confidence'] || 0, color: '#059669' },
    { name: 'Medium (75-89%)', value: confDist['medium_confidence'] || 0, color: '#d97706' },
    { name: 'Low (<75%)', value: confDist['low_confidence'] || 0, color: '#dc2626' },
  ].filter(d => d.value > 0);

  // ── render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 max-w-7xl mx-auto">

      {/* ── Top Header ── */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-slate-900">Mining Intelligence Analytics</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-semibold uppercase">
              CMPDI NumberSafe SQL Engine
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-subsidiary production trends, target vs achievements, dispatch volumes, and evidence quality metrics.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRefresh}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold"
            title="Refresh Analytics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading || extLoading ? 'animate-spin' : ''}`} />
            <span>Recalculate SQL Aggregates</span>
          </button>
        </div>
      </div>

      {/* ── Error Banner ── */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center space-x-2 text-xs text-red-700">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Filter Bar ── */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <span className="text-slate-700 font-semibold">Financial Year:</span>
            <select
              value={financialYear}
              onChange={(e) => setFinancialYear(e.target.value)}
              className="border border-slate-300 rounded px-2.5 py-1 bg-white text-slate-800 font-medium focus:border-amber-500"
            >
              <option value="ALL">All Available Years (Consolidated)</option>
              {overview?.available_financial_years?.map(fy => (
                <option key={fy} value={fy}>{fy}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-slate-700 font-semibold">Subsidiary:</span>
            <select
              value={subsidiary}
              onChange={(e) => setSubsidiary(e.target.value)}
              className="border border-slate-300 rounded px-2.5 py-1 bg-white text-slate-800 font-medium focus:border-amber-500"
            >
              <option value="ALL">All Subsidiaries (CIL Total)</option>
              {overview?.available_subsidiaries?.map(sub => (
                <option key={sub} value={sub}>{sub}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex items-center space-x-2 text-[11px] text-slate-500">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Calculated directly in SQL without LLM estimation</span>
        </div>
      </div>

      {/* ── 4 KPI Cards ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-slate-500 text-xs font-medium">Total Evidence Facts</span>
          <div className="text-2xl font-extrabold text-slate-900 mt-1">{kpis?.facts_extracted?.toLocaleString() || 0}</div>
          <span className="text-[10px] text-slate-400">Indexed in database ledger</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-slate-500 text-xs font-medium">Human-Verified Evidence</span>
          <div className="text-2xl font-extrabold text-emerald-700 mt-1">
            {kpis?.verified_evidence?.toLocaleString() || 0}
            <span className="text-xs font-semibold text-emerald-600 ml-1">
              ({kpis && kpis.facts_extracted > 0 ? Math.round((kpis.verified_evidence / kpis.facts_extracted) * 100) : 0}%)
            </span>
          </div>
          <span className="text-[10px] text-slate-400">Zero-hallucination ground truth</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-slate-500 text-xs font-medium">Mean Extraction Confidence</span>
          <div className="text-2xl font-extrabold text-indigo-700 mt-1">
            {kpis ? `${(kpis.average_confidence * 100).toFixed(1)}%` : '0%'}
          </div>
          <span className="text-[10px] text-slate-400">Heuristic parser certainty</span>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-slate-500 text-xs font-medium">Active Subsidiaries</span>
          <div className="text-2xl font-extrabold text-amber-700 mt-1">{subsidiaries.length}</div>
          <span className="text-[10px] text-slate-400">8 CIL subsidiaries + CMPDI</span>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          ROW 1 — Multi-Year Trend & Target vs Achievement
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Chart 1: Multi-Year Production Trends */}
        <ChartCard
          icon={<TrendingUp className="w-4 h-4 text-amber-600" />}
          title="Multi-Year Coal Production vs Target (MT)"
          badge="SQL Aggregations"
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              {trends.length > 0 ? (
                <LineChart data={trends} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="total_production_mt" stroke="#d97706" name="Actual Production (MT)" strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="target_mt" stroke="#2563eb" name="Target (MT)" strokeDasharray="4 4" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="dispatch_mt" stroke="#059669" name="Dispatch (MT)" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              ) : <NoData />}
            </ResponsiveContainer>
          </div>
        </ChartCard>

        {/* Chart 2: Target vs Achievement by Subsidiary */}
        <ChartCard
          icon={<BarChart3 className="w-4 h-4 text-indigo-600" />}
          title="Subsidiary Target vs Actual Production (MT)"
          badge="Comparative Variance"
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              {targetVsAch.length > 0 ? (
                <BarChart data={targetVsAch} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="subsidiary" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="actual_mt" fill="#d97706" radius={[4, 4, 0, 0]} name="Actual Production (MT)" />
                  <Bar dataKey="target_mt" fill="#94a3b8" radius={[4, 4, 0, 0]} name="Target (MT)" />
                </BarChart>
              ) : <NoData />}
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          ROW 2 — Production vs Dispatch & Confidence Distribution
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Chart 3: Production vs Dispatch */}
        <ChartCard
          icon={<BarChart3 className="w-4 h-4 text-emerald-600" />}
          title="Production vs Offtake / Dispatch by Subsidiary"
          badge="Stock Analysis"
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              {prodVsDisp.length > 0 ? (
                <BarChart data={prodVsDisp} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="subsidiary" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="production_mt" fill="#0284c7" radius={[4, 4, 0, 0]} name="Production (MT)" />
                  <Bar dataKey="dispatch_mt" fill="#059669" radius={[4, 4, 0, 0]} name="Dispatch / Offtake (MT)" />
                </BarChart>
              ) : <NoData />}
            </ResponsiveContainer>
          </div>
        </ChartCard>

        {/* Chart 4: Evidence Confidence Distribution */}
        <ChartCard
          icon={<LucidePieChart className="w-4 h-4 text-amber-600" />}
          title="Evidence Confidence Distribution"
          badge="50,000+ Facts"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                {pieData.length > 0 ? (
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={75} innerRadius={45} paddingAngle={3}>
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                ) : <NoData />}
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {pieData.length > 0 ? pieData.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs p-2 rounded bg-slate-50 border border-slate-100">
                  <div className="flex items-center space-x-2">
                    <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="font-semibold text-slate-800">{item.name}</span>
                  </div>
                  <span className="font-mono text-slate-700 font-bold">{item.value.toLocaleString()}</span>
                </div>
              )) : (
                <p className="text-xs text-slate-400 text-center">No confidence data yet.</p>
              )}
            </div>
          </div>
          <div className="text-[10px] text-slate-400 pt-3 border-t border-slate-100 flex items-center justify-between">
            <span>ReportGuard extraction validation</span>
            <span>Deterministic provenance attached</span>
          </div>
        </ChartCard>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          EXTENDED CHARTS — loading skeleton
      ═══════════════════════════════════════════════════════════════════════ */}
      {extLoading && !extended ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm h-56 flex items-center justify-center">
              <div className="flex flex-col items-center space-y-2">
                <RefreshCw className="w-5 h-5 text-slate-300 animate-spin" />
                <span className="text-xs text-slate-400">Loading SQL aggregates…</span>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {extended && (
        <>
          {/* ═══════════════════════════════════════════════════════════════════
              ROW 3 — YoY Growth & Coalfield Production
          ═══════════════════════════════════════════════════════════════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Chart 5: Year-over-Year Production Growth */}
            <ChartCard
              icon={<TrendingUp className="w-4 h-4 text-emerald-600" />}
              title="Year-over-Year Production Growth (%)"
              badge="Trend Δ"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.production_growth_yoy.length > 1 ? (
                    <ComposedChart data={extended.production_growth_yoy} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} unit="%" />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar yAxisId="left" dataKey="production_mt" fill="#d97706" radius={[3, 3, 0, 0]} name="Production (MT)" opacity={0.7} />
                      <Line yAxisId="right" type="monotone" dataKey="yoy_growth_pct" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 4 }} name="YoY Growth (%)" />
                    </ComposedChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Chart 6: Coalfield Production */}
            <ChartCard
              icon={<Mountain className="w-4 h-4 text-stone-600" />}
              title="Coal Production by Coalfield (MT)"
              badge="Geological Distribution"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.coalfield_production.length > 0 ? (
                    <BarChart data={extended.coalfield_production} layout="vertical" margin={{ top: 5, right: 30, left: 60, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="coalfield" tick={{ fontSize: 10 }} width={60} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="production_mt" name="Production (MT)" radius={[0, 4, 4, 0]}>
                        {extended.coalfield_production.map((_, index) => (
                          <Cell key={index} fill={COLORS_PIE[index % COLORS_PIE.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* ═══════════════════════════════════════════════════════════════════
              ROW 4 — Extraction Method Mix & Document Type Distribution
          ═══════════════════════════════════════════════════════════════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Chart 7: Extraction Method Mix */}
            <ChartCard
              icon={<Layers className="w-4 h-4 text-violet-600" />}
              title="Extraction Method Mix (Fact Count)"
              badge="Parser Distribution"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.extraction_method_mix.length > 0 ? (
                    <BarChart data={extended.extraction_method_mix} margin={{ top: 10, right: 20, left: 0, bottom: 30 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="method" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="count" name="Facts" radius={[4, 4, 0, 0]}>
                        {extended.extraction_method_mix.map((_, index) => (
                          <Cell key={index} fill={COLORS_PIE[index % COLORS_PIE.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Chart 8: Document Type Distribution */}
            <ChartCard
              icon={<FileBarChart className="w-4 h-4 text-cyan-600" />}
              title="Document Type Distribution"
              badge="Corpus Composition"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center mt-2">
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    {extended.doc_type_mix.length > 0 ? (
                      <PieChart>
                        <Pie data={extended.doc_type_mix} dataKey="count" nameKey="file_type" cx="50%" cy="50%" outerRadius={70} innerRadius={38} paddingAngle={3}>
                          {extended.doc_type_mix.map((_, index) => (
                            <Cell key={index} fill={COLORS_PIE[index % COLORS_PIE.length]} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                      </PieChart>
                    ) : <NoData />}
                  </ResponsiveContainer>
                </div>
                <div className="space-y-2">
                  {extended.doc_type_mix.map((d, i) => (
                    <div key={i} className="flex items-center justify-between text-xs p-1.5 rounded bg-slate-50 border border-slate-100">
                      <div className="flex items-center space-x-2">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS_PIE[i % COLORS_PIE.length] }} />
                        <span className="font-medium text-slate-700">{d.file_type}</span>
                      </div>
                      <span className="font-mono font-bold text-slate-800">{d.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </ChartCard>
          </div>

          {/* ═══════════════════════════════════════════════════════════════════
              ROW 5 — Confidence Histogram & Verification Rate by Subsidiary
          ═══════════════════════════════════════════════════════════════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Chart 9: Confidence Score Histogram */}
            <ChartCard
              icon={<Gauge className="w-4 h-4 text-amber-600" />}
              title="Evidence Confidence Histogram (0–100%)"
              badge="10-pt Buckets"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.confidence_histogram.some(b => b.count > 0) ? (
                    <BarChart data={extended.confidence_histogram} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="bucket" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="count" name="Facts" radius={[3, 3, 0, 0]}>
                        {extended.confidence_histogram.map((b, index) => {
                          const lo = parseInt(b.bucket);
                          const color = lo >= 90 ? '#059669' : lo >= 75 ? '#d97706' : '#dc2626';
                          return <Cell key={index} fill={color} />;
                        })}
                      </Bar>
                    </BarChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Chart 10: Verification Rate by Subsidiary */}
            <ChartCard
              icon={<FileCheck className="w-4 h-4 text-emerald-600" />}
              title="Verification Rate by Subsidiary (%)"
              badge="Human Review Coverage"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.verification_rate_by_sub.some(v => v.total_facts > 0) ? (
                    <BarChart data={extended.verification_rate_by_sub} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="subsidiary" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="verification_rate_pct" name="Verified (%)" radius={[4, 4, 0, 0]}>
                        {extended.verification_rate_by_sub.map((v, i) => (
                          <Cell key={i} fill={v.verification_rate_pct >= 80 ? '#059669' : v.verification_rate_pct >= 50 ? '#d97706' : '#dc2626'} />
                        ))}
                      </Bar>
                    </BarChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* ═══════════════════════════════════════════════════════════════════
              ROW 6 — Top Mines & Offtake Gap
          ═══════════════════════════════════════════════════════════════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Chart 11: Top 10 Mines by Production */}
            <ChartCard
              icon={<Pickaxe className="w-4 h-4 text-amber-700" />}
              title="Top 10 Mines by Production (MT)"
              badge="Mine-Level Ranking"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.top_mines.length > 0 ? (
                    <BarChart data={extended.top_mines} layout="vertical" margin={{ top: 5, right: 30, left: 80, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="mine" tick={{ fontSize: 10 }} width={80} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="production_mt" name="Production (MT)" fill="#d97706" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Chart 12: Offtake Gap per Subsidiary */}
            <ChartCard
              icon={<GitCompare className="w-4 h-4 text-red-600" />}
              title="Offtake Gap per Subsidiary (MT)"
              badge="Production − Offtake"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.offtake_gap.length > 0 ? (
                    <ComposedChart data={extended.offtake_gap} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="subsidiary" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="production_mt" fill="#0284c7" radius={[3, 3, 0, 0]} name="Production (MT)" />
                      <Bar dataKey="offtake_mt" fill="#059669" radius={[3, 3, 0, 0]} name="Offtake (MT)" />
                      <Line type="monotone" dataKey="gap_mt" stroke="#dc2626" strokeWidth={2.5} dot={{ r: 4 }} name="Gap (MT)" />
                    </ComposedChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* ═══════════════════════════════════════════════════════════════════
              ROW 7 — Stripping Ratio & Validation Issues
          ═══════════════════════════════════════════════════════════════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Chart 13: Stripping Ratio Trend */}
            <ChartCard
              icon={<Activity className="w-4 h-4 text-purple-600" />}
              title="Stripping Ratio Trend (OB BCM vs Coal MT)"
              badge="Overburden Analysis"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.stripping_ratio_trend.length > 0 ? (
                    <ComposedChart data={extended.stripping_ratio_trend} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar yAxisId="left" dataKey="ob_bcm" fill="#7c3aed" opacity={0.7} radius={[3, 3, 0, 0]} name="OB Removal (BCM)" />
                      <Bar yAxisId="left" dataKey="coal_mt" fill="#d97706" opacity={0.7} radius={[3, 3, 0, 0]} name="Coal (MT)" />
                      <Line yAxisId="right" type="monotone" dataKey="stripping_ratio" stroke="#dc2626" strokeWidth={2.5} dot={{ r: 4 }} name="Strip Ratio" />
                    </ComposedChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Chart 14: Validation Issues by Type */}
            <ChartCard
              icon={<AlertTriangle className="w-4 h-4 text-red-600" />}
              title="Open Validation Issues by Type"
              badge="Review Queue"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.issue_type_dist.length > 0 ? (
                    <BarChart data={extended.issue_type_dist} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="type" tick={{ fontSize: 10 }} width={100} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="count" name="Issues" radius={[0, 4, 4, 0]}>
                        {extended.issue_type_dist.map((_, index) => (
                          <Cell key={index} fill={index === 0 ? '#dc2626' : index === 1 ? '#f97316' : '#fbbf24'} />
                        ))}
                      </Bar>
                    </BarChart>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                        <p className="text-xs text-slate-500 font-medium">No open validation issues.</p>
                      </div>
                    </div>
                  )}
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* ═══════════════════════════════════════════════════════════════════
              ROW 8 — Subsidiary Fact Share & Monthly Document Uploads
          ═══════════════════════════════════════════════════════════════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Chart 15: Subsidiary Fact Share */}
            <ChartCard
              icon={<Building2 className="w-4 h-4 text-indigo-600" />}
              title="Subsidiary Fact Share (% of Total Evidence)"
              badge="Evidence Distribution"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center mt-2">
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    {extended.subsidiary_fact_share.length > 0 ? (
                      <PieChart>
                        <Pie data={extended.subsidiary_fact_share} dataKey="count" nameKey="subsidiary" cx="50%" cy="50%" outerRadius={70} innerRadius={38} paddingAngle={3}>
                          {extended.subsidiary_fact_share.map((d, i) => (
                            <Cell key={i} fill={COLORS_SUB[d.subsidiary] || COLORS_PIE[i % COLORS_PIE.length]} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                      </PieChart>
                    ) : <NoData />}
                  </ResponsiveContainer>
                </div>
                <div className="space-y-1.5">
                  {extended.subsidiary_fact_share.slice(0, 7).map((d, i) => (
                    <div key={i} className="flex items-center justify-between text-xs p-1.5 rounded bg-slate-50 border border-slate-100">
                      <div className="flex items-center space-x-2">
                        <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: COLORS_SUB[d.subsidiary] || COLORS_PIE[i % COLORS_PIE.length] }} />
                        <span className="font-medium text-slate-700">{d.subsidiary}</span>
                      </div>
                      <span className="font-mono font-bold text-slate-800">{d.share_pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </ChartCard>

            {/* Chart 16: Monthly Document Uploads */}
            <ChartCard
              icon={<CalendarDays className="w-4 h-4 text-sky-600" />}
              title="Documents Uploaded per Month"
              badge="Ingestion Pipeline"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.monthly_uploads.length > 0 ? (
                    <AreaChart data={extended.monthly_uploads} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                      <defs>
                        <linearGradient id="uploadGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0284c7" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#0284c7" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area type="monotone" dataKey="count" stroke="#0284c7" strokeWidth={2.5} fill="url(#uploadGrad)" name="Documents Uploaded" dot={{ r: 3 }} />
                    </AreaChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>

          {/* ═══════════════════════════════════════════════════════════════════
              ROW 9 — Audit Activity & Metric Type Breakdown
          ═══════════════════════════════════════════════════════════════════ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Chart 17: Audit Activity Trend */}
            <ChartCard
              icon={<Activity className="w-4 h-4 text-teal-600" />}
              title="Audit Activity (Events per Day)"
              badge="Last 30 Days"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.audit_activity_trend.length > 0 ? (
                    <AreaChart data={extended.audit_activity_trend} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                      <defs>
                        <linearGradient id="auditGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0d9488" stopOpacity={0.25} />
                          <stop offset="95%" stopColor="#0d9488" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="day" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area type="monotone" dataKey="events" stroke="#0d9488" strokeWidth={2.5} fill="url(#auditGrad)" name="Audit Events" dot={{ r: 3 }} />
                    </AreaChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Chart 18: Metric Type Breakdown */}
            <ChartCard
              icon={<Database className="w-4 h-4 text-slate-600" />}
              title="Metric Type Breakdown (Top 8)"
              badge="Evidence Ledger Schema"
            >
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  {extended.metric_type_breakdown.length > 0 ? (
                    <BarChart data={extended.metric_type_breakdown} layout="vertical" margin={{ top: 5, right: 30, left: 110, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="metric_name" tick={{ fontSize: 10 }} width={110} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="count" name="Facts" radius={[0, 4, 4, 0]}>
                        {extended.metric_type_breakdown.map((_, i) => (
                          <Cell key={i} fill={COLORS_PIE[i % COLORS_PIE.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  ) : <NoData />}
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
};
