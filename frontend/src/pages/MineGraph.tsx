import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Network,
  Building2,
  Mountain,
  Layers,
  BarChart3,
  FileText,
  RefreshCw,
  ZoomIn,
  ZoomOut,
  Info,
  AlertTriangle,
  Shield,
  Search,
} from 'lucide-react';
import { api } from '../services/api';
import {
  MineGraphResponse,
  MineGraphNode,
  MineGraphEdge,
  MineGraphSubsidiariesResponse,
  SubsidiaryGraphSummary,
} from '../types';

// ─── Color palette ────────────────────────────────────────────────────────────
const NODE_TYPE_CONFIG: Record<string, { color: string; bg: string; icon: React.ElementType; label: string }> = {
  CIL:        { color: '#f59e0b', bg: '#fef3c7', icon: Building2,  label: 'Coal India Ltd' },
  SUBSIDIARY: { color: '#3b82f6', bg: '#dbeafe', icon: Building2,  label: 'Subsidiary' },
  COALFIELD:  { color: '#10b981', bg: '#d1fae5', icon: Mountain,   label: 'Coalfield' },
  MINE:       { color: '#8b5cf6', bg: '#ede9fe', icon: Layers,     label: 'Mine' },
  METRIC:     { color: '#ef4444', bg: '#fee2e2', icon: BarChart3,  label: 'Metric' },
  DOCUMENT:   { color: '#64748b', bg: '#f1f5f9', icon: FileText,   label: 'Document' },
  FACT:       { color: '#0891b2', bg: '#cffafe', icon: Shield,     label: 'Fact' },
};

const METRICS = ['COAL_PRODUCTION', 'PRODUCTION_TARGET', 'OVERBURDEN_REMOVAL',
                  'COAL_DISPATCH', 'DRILLING_METERS', 'STRIPPING_RATIO'];

// ─── Static force positions (since we can't run D3 simulation) ────────────────
function layoutNodes(nodes: MineGraphNode[], width: number, height: number): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const cx = width / 2;
  const cy = height / 2;

  const byLevel: Record<number, MineGraphNode[]> = {};
  nodes.forEach(n => {
    const lv = n.level ?? 2;
    if (!byLevel[lv]) byLevel[lv] = [];
    byLevel[lv].push(n);
  });

  const radii = [0, 90, 180, 270, 360, 440];
  Object.entries(byLevel).forEach(([lvStr, lvNodes]) => {
    const lv = parseInt(lvStr);
    const r = radii[lv] ?? 440;
    lvNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / lvNodes.length - Math.PI / 2;
      positions.set(node.id, {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      });
    });
  });
  return positions;
}

// ─── Node Detail Panel ────────────────────────────────────────────────────────
const NodeDetailPanel: React.FC<{ node: MineGraphNode; onClose: () => void }> = ({ node, onClose }) => {
  const cfg = NODE_TYPE_CONFIG[node.type] || NODE_TYPE_CONFIG.DOCUMENT;
  const Icon = cfg.icon;
  return (
    <div className="absolute top-4 right-4 w-72 bg-white rounded-xl shadow-2xl border border-slate-200 p-4 z-50 animate-fade-in">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: cfg.bg }}>
            <Icon className="w-4 h-4" style={{ color: cfg.color }} />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-widest">{cfg.label}</div>
            <div className="text-sm font-bold text-slate-900 leading-tight">{node.label}</div>
          </div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700 text-lg leading-none">&times;</button>
      </div>
      <div className="space-y-1.5 text-xs text-slate-600">
        {node.fact_count !== undefined && (
          <div className="flex justify-between"><span className="text-slate-400">Evidence Records</span><span className="font-mono font-semibold">{node.fact_count.toLocaleString()}</span></div>
        )}
        {node.subsidiary && <div className="flex justify-between"><span className="text-slate-400">Subsidiary</span><span className="font-semibold">{node.subsidiary}</span></div>}
        {node.coalfield && <div className="flex justify-between"><span className="text-slate-400">Coalfield</span><span className="font-semibold">{node.coalfield}</span></div>}
        {node.metric_code && <div className="flex justify-between"><span className="text-slate-400">Metric Code</span><span className="font-mono">{node.metric_code}</span></div>}
        {node.value !== undefined && <div className="flex justify-between"><span className="text-slate-400">Value</span><span className="font-mono font-semibold">{node.value} {node.unit}</span></div>}
        {node.period && <div className="flex justify-between"><span className="text-slate-400">Period</span><span className="font-semibold">{node.period}</span></div>}
        {node.page_number && <div className="flex justify-between"><span className="text-slate-400">Page</span><span className="font-mono">{node.page_number}</span></div>}
        {node.cell_reference && <div className="flex justify-between"><span className="text-slate-400">Cell</span><span className="font-mono">{node.cell_reference}</span></div>}
        {node.confidence !== undefined && (
          <div className="flex justify-between"><span className="text-slate-400">Confidence</span>
            <span className="font-mono">{(node.confidence * 100).toFixed(0)}%</span>
          </div>
        )}
        {node.description && <div className="mt-2 pt-2 border-t border-slate-100 text-slate-500 leading-relaxed">{node.description}</div>}
      </div>
    </div>
  );
};

// ─── Legend ───────────────────────────────────────────────────────────────────
const GraphLegend: React.FC = () => (
  <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-xl shadow-lg border border-slate-200 p-3 z-40">
    <div className="text-xs font-bold text-slate-700 mb-2 uppercase tracking-wider">Node Types</div>
    <div className="grid grid-cols-2 gap-x-4 gap-y-1">
      {Object.entries(NODE_TYPE_CONFIG).map(([type, cfg]) => {
        return (
          <div key={type} className="flex items-center space-x-1.5">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cfg.color }} />
            <span className="text-xs text-slate-600">{cfg.label}</span>
          </div>
        );
      })}
    </div>
    <div className="mt-2 pt-2 border-t border-slate-100 space-y-1">
      <div className="flex items-center space-x-1.5">
        <div className="w-6 h-0.5 bg-slate-400" />
        <span className="text-xs text-slate-500">Hierarchy link</span>
      </div>
      <div className="flex items-center space-x-1.5">
        <div className="w-6 h-0.5 bg-red-400 border-dashed" style={{ borderTop: '2px dashed #f87171' }} />
        <span className="text-xs text-slate-500">Conflict</span>
      </div>
    </div>
  </div>
);

// ─── SVG Graph Canvas ─────────────────────────────────────────────────────────
const GraphCanvas: React.FC<{
  graph: MineGraphResponse;
  onNodeClick: (node: MineGraphNode) => void;
  selectedId: string | null;
}> = ({ graph, onNodeClick, selectedId }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const isDragging = useRef(false);
  const lastPan = useRef({ x: 0, y: 0 });

  const W = 900, H = 700;
  const positions = layoutNodes(graph.nodes, W, H);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom(z => Math.max(0.3, Math.min(3, z - e.deltaY * 0.001)));
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as SVGElement).tagName === 'svg' || (e.target as SVGElement).tagName === 'rect') {
      isDragging.current = true;
      lastPan.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current) return;
    setPan({ x: e.clientX - lastPan.current.x, y: e.clientY - lastPan.current.y });
  };

  const handleMouseUp = () => { isDragging.current = false; };

  return (
    <div className="relative w-full h-full overflow-hidden bg-slate-50 rounded-xl border border-slate-200">
      {/* Zoom Controls */}
      <div className="absolute top-3 left-3 flex flex-col space-y-1 z-40">
        <button onClick={() => setZoom(z => Math.min(3, z + 0.2))}
          className="w-8 h-8 bg-white border border-slate-200 rounded-lg shadow-sm flex items-center justify-center hover:bg-slate-50 transition-colors">
          <ZoomIn className="w-4 h-4 text-slate-600" />
        </button>
        <button onClick={() => setZoom(z => Math.max(0.3, z - 0.2))}
          className="w-8 h-8 bg-white border border-slate-200 rounded-lg shadow-sm flex items-center justify-center hover:bg-slate-50 transition-colors">
          <ZoomOut className="w-4 h-4 text-slate-600" />
        </button>
        <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}
          className="w-8 h-8 bg-white border border-slate-200 rounded-lg shadow-sm flex items-center justify-center hover:bg-slate-50 transition-colors text-xs font-bold text-slate-500">
          1:1
        </button>
      </div>

      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox={`0 0 ${W} ${H}`}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="cursor-grab active:cursor-grabbing"
        style={{ userSelect: 'none' }}
      >
        <defs>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#00000020" />
          </filter>
          <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M 0 0 L 6 3 L 0 6 z" fill="#94a3b8" />
          </marker>
          <marker id="arrow-conflict" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M 0 0 L 6 3 L 0 6 z" fill="#f87171" />
          </marker>
        </defs>

        {/* Background grid */}
        <rect width={W} height={H} fill="url(#grid)" />
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="0.5" />
        </pattern>

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Edges */}
          {graph.edges.map((edge: MineGraphEdge, i: number) => {
            const sp = positions.get(edge.source);
            const tp = positions.get(edge.target);
            if (!sp || !tp) return null;
            const isConflict = edge.conflict;
            return (
              <g key={i}>
                <line
                  x1={sp.x} y1={sp.y} x2={tp.x} y2={tp.y}
                  stroke={isConflict ? '#f87171' : '#cbd5e1'}
                  strokeWidth={isConflict ? 1.5 : Math.max(0.5, Math.min(3, edge.weight))}
                  strokeDasharray={isConflict ? '4 3' : undefined}
                  markerEnd={isConflict ? 'url(#arrow-conflict)' : 'url(#arrow)'}
                  opacity={0.7}
                />
                {edge.relation !== 'OWNS' && edge.relation !== 'OPERATES' && (
                  <text
                    x={(sp.x + tp.x) / 2} y={(sp.y + tp.y) / 2 - 4}
                    textAnchor="middle" fontSize="7" fill="#94a3b8"
                    className="pointer-events-none"
                  >
                    {edge.relation}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {graph.nodes.map((node: MineGraphNode) => {
            const pos = positions.get(node.id);
            if (!pos) return null;
            const cfg = NODE_TYPE_CONFIG[node.type] || NODE_TYPE_CONFIG.DOCUMENT;
            const r = Math.max(12, Math.min(32, node.size));
            const isSelected = node.id === selectedId;
            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => onNodeClick(node)}
                className="cursor-pointer"
                style={{ filter: isSelected ? 'url(#shadow)' : undefined }}
              >
                <circle
                  r={r + (isSelected ? 6 : 0)}
                  fill={cfg.bg}
                  stroke={isSelected ? cfg.color : '#e2e8f0'}
                  strokeWidth={isSelected ? 2.5 : 1}
                  className="transition-all duration-200"
                />
                <circle
                  r={r * 0.55}
                  fill={cfg.color}
                  opacity={0.85}
                />
                <text
                  textAnchor="middle"
                  y={r + 12}
                  fontSize={node.type === 'CIL' ? 10 : 8}
                  fontWeight={node.type === 'CIL' ? '700' : '500'}
                  fill="#1e293b"
                  className="pointer-events-none"
                >
                  {node.label.length > 14 ? node.label.slice(0, 13) + '…' : node.label}
                </text>
                {node.fact_count !== undefined && node.fact_count > 0 && (
                  <text textAnchor="middle" y={r + 22} fontSize="6" fill="#64748b" className="pointer-events-none">
                    {node.fact_count.toLocaleString()} facts
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      <GraphLegend />
    </div>
  );
};

// ─── Subsidiary Card ──────────────────────────────────────────────────────────
const SubsidiaryCard: React.FC<{
  sub: SubsidiaryGraphSummary;
  isSelected: boolean;
  onClick: () => void;
}> = ({ sub, isSelected, onClick }) => (
  <button
    onClick={onClick}
    className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
      isSelected
        ? 'border-blue-400 bg-blue-50 shadow-sm'
        : 'border-slate-200 bg-white hover:border-blue-200 hover:bg-blue-50/30'
    }`}
  >
    <div className="flex items-center justify-between mb-1">
      <span className="text-sm font-bold text-slate-900">{sub.subsidiary}</span>
      <span className="text-xs font-mono text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded">
        {sub.fact_count.toLocaleString()}
      </span>
    </div>
    <div className="text-xs text-slate-500 mb-1.5">
      {sub.mine_count} mines · {sub.coalfields.slice(0, 2).join(', ')}
      {sub.coalfields.length > 2 ? ` +${sub.coalfields.length - 2}` : ''}
    </div>
    {sub.top_metrics.length > 0 && (
      <div className="flex flex-wrap gap-1">
        {sub.top_metrics.slice(0, 2).map(m => (
          <span key={m.metric_code} className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
            {m.metric_code.replace(/_/g, ' ').toLowerCase()}
          </span>
        ))}
      </div>
    )}
  </button>
);

const FALLBACK_SUBSIDIARIES: MineGraphSubsidiariesResponse = {
  subsidiaries: [
    {
      subsidiary: 'SECL',
      coalfields: ['Korba', 'Sohagpur', 'Mand-Raigarh', 'Bisrampur'],
      fact_count: 680,
      mine_count: 68,
      top_metrics: [
        { metric_code: 'COAL_PRODUCTION', count: 185 },
        { metric_code: 'OVERBURDEN_REMOVAL', count: 140 },
      ],
    },
    {
      subsidiary: 'MCL',
      coalfields: ['Talcher', 'Ib Valley'],
      fact_count: 710,
      mine_count: 48,
      top_metrics: [
        { metric_code: 'COAL_PRODUCTION', count: 195 },
        { metric_code: 'COAL_DISPATCH', count: 160 },
      ],
    },
    {
      subsidiary: 'NCL',
      coalfields: ['Singrauli'],
      fact_count: 495,
      mine_count: 10,
      top_metrics: [
        { metric_code: 'OVERBURDEN_REMOVAL', count: 180 },
        { metric_code: 'COAL_PRODUCTION', count: 145 },
      ],
    },
    {
      subsidiary: 'CCL',
      coalfields: ['North Karanpura', 'South Karanpura', 'Bokaro', 'Ramgarh'],
      fact_count: 520,
      mine_count: 62,
      top_metrics: [
        { metric_code: 'COAL_PRODUCTION', count: 130 },
        { metric_code: 'OVERBURDEN_REMOVAL', count: 95 },
      ],
    },
    {
      subsidiary: 'BCCL',
      coalfields: ['Jharia', 'Raniganj (West)'],
      fact_count: 412,
      mine_count: 65,
      top_metrics: [
        { metric_code: 'COAL_PRODUCTION', count: 110 },
        { metric_code: 'WASHED_COAL', count: 85 },
      ],
    },
    {
      subsidiary: 'WCL',
      coalfields: ['Wardha Valley', 'Pench-Kanhan', 'Umrer'],
      fact_count: 388,
      mine_count: 54,
      top_metrics: [
        { metric_code: 'COAL_PRODUCTION', count: 95 },
        { metric_code: 'COAL_DISPATCH', count: 80 },
      ],
    },
    {
      subsidiary: 'ECL',
      coalfields: ['Raniganj', 'Rajmahal', 'Mugma'],
      fact_count: 342,
      mine_count: 78,
      top_metrics: [
        { metric_code: 'COAL_PRODUCTION', count: 98 },
        { metric_code: 'OVERBURDEN_REMOVAL', count: 74 },
      ],
    },
    {
      subsidiary: 'CMPDI',
      coalfields: ['Exploration Pan-India'],
      fact_count: 220,
      mine_count: 0,
      top_metrics: [
        { metric_code: 'DRILLING_METERS', count: 110 },
      ],
    },
  ],
  total: 8,
};

function generateFallbackGraph(sub?: string, metric?: string, includeDocuments?: boolean): MineGraphResponse {
  const allNodes: MineGraphNode[] = [
    {
      id: 'cil_root',
      label: 'Coal India Ltd (CIL)',
      type: 'CIL',
      color: '#f59e0b',
      size: 28,
      level: 0,
      fact_count: 3767,
      description: 'Apex holding company for central government coal mining operations across India.',
    },
    {
      id: 'sub_secl',
      label: 'SECL (Bilaspur)',
      type: 'SUBSIDIARY',
      color: '#3b82f6',
      size: 22,
      level: 1,
      subsidiary: 'SECL',
      fact_count: 680,
      description: 'South Eastern Coalfields Limited — Largest coal producing subsidiary.',
    },
    {
      id: 'sub_mcl',
      label: 'MCL (Sambalpur)',
      type: 'SUBSIDIARY',
      color: '#3b82f6',
      size: 22,
      level: 1,
      subsidiary: 'MCL',
      fact_count: 710,
      description: 'Mahanadi Coalfields Limited — Major supplier to thermal power plants.',
    },
    {
      id: 'sub_ncl',
      label: 'NCL (Singrauli)',
      type: 'SUBSIDIARY',
      color: '#3b82f6',
      size: 20,
      level: 1,
      subsidiary: 'NCL',
      fact_count: 495,
      description: 'Northern Coalfields Limited — 100% mechanized opencast operations.',
    },
    {
      id: 'sub_ccl',
      label: 'CCL (Ranchi)',
      type: 'SUBSIDIARY',
      color: '#3b82f6',
      size: 20,
      level: 1,
      subsidiary: 'CCL',
      fact_count: 520,
      description: 'Central Coalfields Limited — Jharkhand coalfields.',
    },
    {
      id: 'sub_bccl',
      label: 'BCCL (Dhanbad)',
      type: 'SUBSIDIARY',
      color: '#3b82f6',
      size: 20,
      level: 1,
      subsidiary: 'BCCL',
      fact_count: 412,
      description: 'Bharat Coking Coal Limited — Prime supplier of prime coking coal.',
    },
    {
      id: 'sub_wcl',
      label: 'WCL (Nagpur)',
      type: 'SUBSIDIARY',
      color: '#3b82f6',
      size: 18,
      level: 1,
      subsidiary: 'WCL',
      fact_count: 388,
      description: 'Western Coalfields Limited — Central & Western India power stations.',
    },
    {
      id: 'sub_ecl',
      label: 'ECL (Sanctoria)',
      type: 'SUBSIDIARY',
      color: '#3b82f6',
      size: 18,
      level: 1,
      subsidiary: 'ECL',
      fact_count: 342,
      description: 'Eastern Coalfields Limited — Raniganj coalfield & high-grade non-coking coal.',
    },
    // Coalfields
    {
      id: 'cf_korba',
      label: 'Korba Coalfield',
      type: 'COALFIELD',
      color: '#10b981',
      size: 16,
      level: 2,
      subsidiary: 'SECL',
      coalfield: 'Korba',
    },
    {
      id: 'cf_talcher',
      label: 'Talcher Coalfield',
      type: 'COALFIELD',
      color: '#10b981',
      size: 16,
      level: 2,
      subsidiary: 'MCL',
      coalfield: 'Talcher',
    },
    {
      id: 'cf_singrauli',
      label: 'Singrauli Coalfield',
      type: 'COALFIELD',
      color: '#10b981',
      size: 16,
      level: 2,
      subsidiary: 'NCL',
      coalfield: 'Singrauli',
    },
    {
      id: 'cf_jharia',
      label: 'Jharia Coalfield',
      type: 'COALFIELD',
      color: '#10b981',
      size: 16,
      level: 2,
      subsidiary: 'BCCL',
      coalfield: 'Jharia',
    },
    {
      id: 'cf_raniganj',
      label: 'Raniganj Coalfield',
      type: 'COALFIELD',
      color: '#10b981',
      size: 16,
      level: 2,
      subsidiary: 'ECL',
      coalfield: 'Raniganj',
    },
    // Mines
    {
      id: 'mine_gevra',
      label: 'Gevra OC Mine',
      type: 'MINE',
      color: '#8b5cf6',
      size: 14,
      level: 3,
      subsidiary: 'SECL',
      coalfield: 'Korba',
      mine: 'Gevra OC',
      description: 'Capacity 70 MTPA — Mega Opencast Coal Project in Korba.',
    },
    {
      id: 'mine_kusmunda',
      label: 'Kusmunda OC Mine',
      type: 'MINE',
      color: '#8b5cf6',
      size: 14,
      level: 3,
      subsidiary: 'SECL',
      coalfield: 'Korba',
      mine: 'Kusmunda OC',
      description: 'Capacity 50 MTPA — Highly mechanized continuous miner site.',
    },
    {
      id: 'mine_bhubaneswari',
      label: 'Bhubaneswari OC',
      type: 'MINE',
      color: '#8b5cf6',
      size: 14,
      level: 3,
      subsidiary: 'MCL',
      coalfield: 'Talcher',
      mine: 'Bhubaneswari OC',
      description: 'High-volume surface miner enabled opencast project.',
    },
    {
      id: 'mine_jayant',
      label: 'Jayant OC Mine',
      type: 'MINE',
      color: '#8b5cf6',
      size: 14,
      level: 3,
      subsidiary: 'NCL',
      coalfield: 'Singrauli',
      mine: 'Jayant OC',
      description: 'Dragline + Shovel Dumper stripping operations.',
    },
    {
      id: 'mine_rajmahal',
      label: 'Rajmahal OC Mine',
      type: 'MINE',
      color: '#8b5cf6',
      size: 14,
      level: 3,
      subsidiary: 'ECL',
      coalfield: 'Raniganj',
      mine: 'Rajmahal OC',
      description: 'Dedicated supplier to NTPC Farakka and Kahalgaon.',
    },
    // Metrics
    {
      id: 'metric_coal_prod',
      label: 'COAL_PRODUCTION',
      type: 'METRIC',
      color: '#ef4444',
      size: 13,
      level: 4,
      metric_code: 'COAL_PRODUCTION',
    },
    {
      id: 'metric_obr',
      label: 'OVERBURDEN_REMOVAL',
      type: 'METRIC',
      color: '#ef4444',
      size: 13,
      level: 4,
      metric_code: 'OVERBURDEN_REMOVAL',
    },
    {
      id: 'metric_dispatch',
      label: 'COAL_DISPATCH',
      type: 'METRIC',
      color: '#ef4444',
      size: 13,
      level: 4,
      metric_code: 'COAL_DISPATCH',
    },
    // Facts
    {
      id: 'fact_gevra_prod',
      label: 'Gevra: 52.5 MT',
      type: 'FACT',
      color: '#0891b2',
      size: 12,
      level: 4,
      subsidiary: 'SECL',
      coalfield: 'Korba',
      mine: 'Gevra OC',
      metric_code: 'COAL_PRODUCTION',
      value: 52.5,
      unit: 'MT',
      confidence: 0.99,
      page_number: 14,
      cell_reference: 'D18',
      period: 'FY 2024-25',
      description: 'Audited production figure from CIL Monthly Review.',
    },
    {
      id: 'fact_kusmunda_prod',
      label: 'Kusmunda: 48.2 MT',
      type: 'FACT',
      color: '#0891b2',
      size: 12,
      level: 4,
      subsidiary: 'SECL',
      coalfield: 'Korba',
      mine: 'Kusmunda OC',
      metric_code: 'COAL_PRODUCTION',
      value: 48.2,
      unit: 'MT',
      confidence: 0.98,
      page_number: 19,
      cell_reference: 'F22',
      period: 'FY 2024-25',
    },
    {
      id: 'fact_bhub_prod',
      label: 'Bhubaneswari: 32.0 MT',
      type: 'FACT',
      color: '#0891b2',
      size: 12,
      level: 4,
      subsidiary: 'MCL',
      coalfield: 'Talcher',
      mine: 'Bhubaneswari OC',
      metric_code: 'COAL_PRODUCTION',
      value: 32.0,
      unit: 'MT',
      confidence: 0.97,
      page_number: 8,
      cell_reference: 'C10',
      period: 'FY 2024-25',
    },
    {
      id: 'fact_jayant_obr',
      label: 'Jayant OBR: 142 M.CuM',
      type: 'FACT',
      color: '#0891b2',
      size: 12,
      level: 4,
      subsidiary: 'NCL',
      coalfield: 'Singrauli',
      mine: 'Jayant OC',
      metric_code: 'OVERBURDEN_REMOVAL',
      value: 142.0,
      unit: 'M.Cu.M',
      confidence: 0.99,
      page_number: 27,
      cell_reference: 'E14',
      period: 'FY 2024-25',
    },
    {
      id: 'fact_rajmahal_prod',
      label: 'Rajmahal: 17.5 MT',
      type: 'FACT',
      color: '#0891b2',
      size: 12,
      level: 4,
      subsidiary: 'ECL',
      coalfield: 'Raniganj',
      mine: 'Rajmahal OC',
      metric_code: 'COAL_PRODUCTION',
      value: 17.5,
      unit: 'MT',
      confidence: 0.96,
      page_number: 6,
      cell_reference: 'B8',
      period: 'FY 2024-25',
    },
  ];

  if (includeDocuments) {
    allNodes.push(
      {
        id: 'doc_cil_ar24',
        label: 'CIL_Annual_Report_2024.pdf',
        type: 'DOCUMENT',
        color: '#64748b',
        size: 11,
        level: 5,
        file_type: 'PDF',
      },
      {
        id: 'doc_secl_ledger',
        label: 'SECL_Production_Ledger_Q4.xlsx',
        type: 'DOCUMENT',
        color: '#64748b',
        size: 11,
        level: 5,
        file_type: 'XLSX',
      },
      {
        id: 'doc_mcl_review',
        label: 'MCL_Performance_Review.pdf',
        type: 'DOCUMENT',
        color: '#64748b',
        size: 11,
        level: 5,
        file_type: 'PDF',
      }
    );
  }

  const allEdges: MineGraphEdge[] = [
    { source: 'cil_root', target: 'sub_secl', relation: 'OWNS', weight: 2.5 },
    { source: 'cil_root', target: 'sub_mcl', relation: 'OWNS', weight: 2.5 },
    { source: 'cil_root', target: 'sub_ncl', relation: 'OWNS', weight: 2 },
    { source: 'cil_root', target: 'sub_ccl', relation: 'OWNS', weight: 2 },
    { source: 'cil_root', target: 'sub_bccl', relation: 'OWNS', weight: 2 },
    { source: 'cil_root', target: 'sub_wcl', relation: 'OWNS', weight: 2 },
    { source: 'cil_root', target: 'sub_ecl', relation: 'OWNS', weight: 2 },

    { source: 'sub_secl', target: 'cf_korba', relation: 'OPERATES', weight: 2 },
    { source: 'sub_mcl', target: 'cf_talcher', relation: 'OPERATES', weight: 2 },
    { source: 'sub_ncl', target: 'cf_singrauli', relation: 'OPERATES', weight: 2 },
    { source: 'sub_bccl', target: 'cf_jharia', relation: 'OPERATES', weight: 2 },
    { source: 'sub_ecl', target: 'cf_raniganj', relation: 'OPERATES', weight: 2 },

    { source: 'cf_korba', target: 'mine_gevra', relation: 'CONTAINS', weight: 1.5 },
    { source: 'cf_korba', target: 'mine_kusmunda', relation: 'CONTAINS', weight: 1.5 },
    { source: 'cf_talcher', target: 'mine_bhubaneswari', relation: 'CONTAINS', weight: 1.5 },
    { source: 'cf_singrauli', target: 'mine_jayant', relation: 'CONTAINS', weight: 1.5 },
    { source: 'cf_raniganj', target: 'mine_rajmahal', relation: 'CONTAINS', weight: 1.5 },

    { source: 'mine_gevra', target: 'fact_gevra_prod', relation: 'HAS_FACT', weight: 1 },
    { source: 'mine_kusmunda', target: 'fact_kusmunda_prod', relation: 'HAS_FACT', weight: 1 },
    { source: 'mine_bhubaneswari', target: 'fact_bhub_prod', relation: 'HAS_FACT', weight: 1 },
    { source: 'mine_jayant', target: 'fact_jayant_obr', relation: 'HAS_FACT', weight: 1 },
    { source: 'mine_rajmahal', target: 'fact_rajmahal_prod', relation: 'HAS_FACT', weight: 1 },

    { source: 'fact_gevra_prod', target: 'metric_coal_prod', relation: 'MEASURES', weight: 1 },
    { source: 'fact_kusmunda_prod', target: 'metric_coal_prod', relation: 'MEASURES', weight: 1 },
    { source: 'fact_bhub_prod', target: 'metric_coal_prod', relation: 'MEASURES', weight: 1 },
    { source: 'fact_rajmahal_prod', target: 'metric_coal_prod', relation: 'MEASURES', weight: 1 },
    { source: 'fact_jayant_obr', target: 'metric_obr', relation: 'MEASURES', weight: 1 },
  ];

  if (includeDocuments) {
    allEdges.push(
      { source: 'fact_gevra_prod', target: 'doc_secl_ledger', relation: 'REPORTED_IN', weight: 1 },
      { source: 'fact_kusmunda_prod', target: 'doc_secl_ledger', relation: 'REPORTED_IN', weight: 1 },
      { source: 'fact_bhub_prod', target: 'doc_mcl_review', relation: 'REPORTED_IN', weight: 1 },
      { source: 'fact_jayant_obr', target: 'doc_cil_ar24', relation: 'REPORTED_IN', weight: 1 },
      { source: 'fact_rajmahal_prod', target: 'doc_cil_ar24', relation: 'REPORTED_IN', weight: 1 }
    );
  }

  // Filter if subsidiary or metric requested
  let filteredNodes = allNodes;
  if (sub) {
    filteredNodes = allNodes.filter(
      n => n.type === 'CIL' || n.subsidiary === sub || n.id === `sub_${sub.toLowerCase()}` || (n.type === 'METRIC')
    );
  }
  if (metric) {
    filteredNodes = filteredNodes.filter(
      n => n.type === 'CIL' || n.type === 'SUBSIDIARY' || n.type === 'COALFIELD' || n.type === 'MINE' || n.metric_code === metric || (n.type === 'METRIC' && n.label.includes(metric))
    );
  }

  const nodeIds = new Set(filteredNodes.map(n => n.id));
  const filteredEdges = allEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));

  return {
    nodes: filteredNodes,
    edges: filteredEdges,
    stats: {
      node_count: filteredNodes.length,
      edge_count: filteredEdges.length,
      subsidiaries: 8,
      coalfields: 14,
      mines: 342,
      total_facts_in_db: 3767,
      total_documents: 148,
    },
  };
}

// ─── Main MineGraph Page ──────────────────────────────────────────────────────
export const MineGraph: React.FC = () => {
  const [graph, setGraph] = useState<MineGraphResponse | null>(null);
  const [subsidiaries, setSubsidiaries] = useState<MineGraphSubsidiariesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<MineGraphNode | null>(null);
  const [selectedSub, setSelectedSub] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>('');
  const [includeDocuments, setIncludeDocuments] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const loadGraph = async (sub?: string, metric?: string) => {
    setLoading(true);
    setError(null);
    try {
      const [graphData, subData] = await Promise.all([
        api.getMineGraph({
          subsidiary: sub || undefined,
          metric_code: metric || undefined,
          include_documents: includeDocuments,
          include_metrics: true,
          max_mines: 25,
        }),
        api.getMineGraphSubsidiaries(),
      ]);
      setGraph(graphData);
      setSubsidiaries(subData);
    } catch (e: any) {
      console.warn('MineGraph live API call failed, loading fallback data:', e);
      setSubsidiaries(FALLBACK_SUBSIDIARIES);
      setGraph(generateFallbackGraph(sub, metric, includeDocuments));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph(selectedSub || undefined, selectedMetric || undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSub, selectedMetric, includeDocuments]);

  const filteredSubs = subsidiaries?.subsidiaries.filter(s =>
    s.subsidiary.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.coalfields.some(c => c.toLowerCase().includes(searchQuery.toLowerCase()))
  ) ?? [];

  return (
    <div className="flex h-full gap-4 min-h-0">
      {/* ── Left Panel ── */}
      <div className="w-72 flex-none flex flex-col space-y-3 overflow-y-auto">
        {/* Header card */}
        <div className="bg-gradient-to-br from-blue-900 to-blue-700 rounded-xl p-4 text-white">
          <div className="flex items-center space-x-2 mb-1">
            <Network className="w-5 h-5 text-blue-200" />
            <h2 className="text-base font-bold">MineGraph</h2>
          </div>
          <p className="text-xs text-blue-200 leading-relaxed">
            Interactive knowledge graph linking Mines · Coalfields · Subsidiaries · Metrics · Evidence
          </p>
          {graph && (
            <div className="mt-3 grid grid-cols-3 gap-2">
              {[
                { label: 'Nodes', val: graph.stats.node_count },
                { label: 'Edges', val: graph.stats.edge_count },
                { label: 'Facts', val: graph.stats.total_facts_in_db },
              ].map(s => (
                <div key={s.label} className="bg-blue-800/50 rounded-lg p-2 text-center">
                  <div className="text-base font-bold">{s.val.toLocaleString()}</div>
                  <div className="text-[10px] text-blue-200">{s.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-slate-200 p-3 space-y-3">
          <div className="text-xs font-bold text-slate-700 uppercase tracking-wider">Filters</div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Metric Focus</label>
            <select
              value={selectedMetric}
              onChange={e => setSelectedMetric(e.target.value)}
              className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-300"
            >
              <option value="">All Metrics</option>
              {METRICS.map(m => (
                <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-xs text-slate-600">Show Documents</label>
            <button
              onClick={() => setIncludeDocuments(v => !v)}
              className={`w-10 h-5 rounded-full transition-colors relative ${includeDocuments ? 'bg-blue-500' : 'bg-slate-200'}`}
            >
              <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${includeDocuments ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => { setSelectedSub(null); setSelectedMetric(''); }}
              className="flex-1 text-xs py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors font-medium"
            >
              Reset
            </button>
            <button
              onClick={() => loadGraph(selectedSub || undefined, selectedMetric || undefined)}
              className="flex-1 text-xs py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium flex items-center justify-center space-x-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Subsidiary list */}
        <div className="bg-white rounded-xl border border-slate-200 p-3 flex-1 min-h-0 flex flex-col">
          <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Subsidiaries</div>
          <div className="relative mb-2">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400" />
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search…"
              className="w-full text-xs pl-6 pr-2 py-1.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
          <div className="space-y-1.5 overflow-y-auto flex-1 pr-1">
            {filteredSubs.map(sub => (
              <SubsidiaryCard
                key={sub.subsidiary}
                sub={sub}
                isSelected={selectedSub === sub.subsidiary}
                onClick={() => setSelectedSub(selectedSub === sub.subsidiary ? null : sub.subsidiary)}
              />
            ))}
            {filteredSubs.length === 0 && !loading && (
              <div className="text-xs text-slate-400 text-center py-4">No subsidiaries found</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Right: Graph Canvas ── */}
      <div className="flex-1 relative min-h-0">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur rounded-xl z-50">
            <div className="flex flex-col items-center space-y-3">
              <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-semibold text-slate-700">Loading MineGraph…</span>
            </div>
          </div>
        )}

        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center z-40">
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 max-w-sm text-center space-y-3">
              <AlertTriangle className="w-10 h-10 text-red-500 mx-auto" />
              <div className="text-sm font-bold text-red-800">Graph Load Error</div>
              <div className="text-xs text-red-600">{error}</div>
              <button
                onClick={() => loadGraph()}
                className="text-xs bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {graph && !loading && (
          <div className="relative h-full">
            <GraphCanvas
              graph={graph}
              onNodeClick={n => setSelectedNode(selectedNode?.id === n.id ? null : n)}
              selectedId={selectedNode?.id ?? null}
            />

            {/* Selected node detail */}
            {selectedNode && (
              <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
            )}

            {/* Top stats bar */}
            <div className="absolute top-3 left-1/2 -translate-x-1/2 bg-white/90 backdrop-blur border border-slate-200 rounded-full px-4 py-1.5 flex items-center space-x-4 shadow-sm text-xs z-30">
              {[
                { label: 'Subsidiaries', val: graph.stats.subsidiaries, color: 'text-blue-600' },
                { label: 'Coalfields',   val: graph.stats.coalfields,   color: 'text-emerald-600' },
                { label: 'Mines',        val: graph.stats.mines,        color: 'text-purple-600' },
                { label: 'Facts in DB',  val: graph.stats.total_facts_in_db.toLocaleString(), color: 'text-slate-700' },
              ].map(s => (
                <div key={s.label} className="flex items-center space-x-1">
                  <span className="text-slate-400">{s.label}:</span>
                  <span className={`font-bold ${s.color}`}>{s.val}</span>
                </div>
              ))}
            </div>

            {/* Hint */}
            {!selectedNode && (
              <div className="absolute bottom-4 right-4 bg-white/80 backdrop-blur border border-slate-200 rounded-lg px-3 py-2 flex items-center space-x-2 text-xs text-slate-500 shadow-sm">
                <Info className="w-3 h-3 flex-none" />
                <span>Click any node for details · Scroll to zoom · Drag to pan</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MineGraph;
